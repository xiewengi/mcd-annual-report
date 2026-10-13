"""
麦门年度体检报告 - 核心分析引擎

输入：历史订单列表 + 麦当劳营养数据
输出：年度分析数据（供报告生成使用）
"""
import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from typing import Optional


# === 健康参考标准（成人日均） ===
HEALTH_STANDARDS = {
    "energy_kcal": 2000,      # 日均热量 kcal
    "protein": 60,            # 日均蛋白质 g
    "fat": 65,                # 日均脂肪 g
    "carbohydrate": 300,      # 日均碳水 g
    "sodium": 2000,           # 日均钠 mg（WHO 推荐）
    "calcium": 800,           # 日均钙 mg
}

# 麦当劳单次建议热量区间（成人）
MCD_MEAL_KCAL_RANGE = {
    "breakfast": (300, 600),   # 早餐
    "lunch": (500, 1000),      # 午餐
    "afternoon": (150, 450),   # 下午茶
    "dinner": (500, 1000),     # 晚餐
    "supper": (300, 600),      # 宵夜
}


def get_meal_period(hour: int) -> str:
    """根据小时判断餐段"""
    if 5 <= hour < 10:
        return "breakfast"
    elif 10 <= hour < 15:
        return "lunch"
    elif 15 <= hour < 18:
        return "afternoon"
    elif 18 <= hour < 22:
        return "dinner"
    else:
        return "supper"


MEAL_NAMES_CN = {
    "breakfast": "早餐",
    "lunch": "午餐", 
    "afternoon": "下午茶",
    "dinner": "晚餐",
    "supper": "宵夜"
}


class AnnualAnalyzer:
    """年度体检报告分析器"""
    
    def __init__(self, orders: list, nutrition: list):
        self.orders = orders
        self.nutrition = nutrition
        # 建立菜单名 -> 营养的映射
        self.nutrition_map = {n["name"]: n for n in nutrition}
        # 同义词/模糊匹配表
        self._fuzzy_patterns = [
            # (营养表里的名字, 订单里可能的变体)
            ("巨无霸", ["巨无霸汉堡"]),
            ("板烧鸡腿堡", ["板烧鸡腿堡套餐", "板烧堡"]),
            ("麦辣鸡腿汉堡", ["麦辣鸡腿堡", "麦辣鸡腿堡套餐"]),
            ("麦香鱼", ["麦香鱼汉堡"]),
            ("双层吉士汉堡", ["双层吉士汉堡包"]),
            ("吉士汉堡包", ["吉士汉堡"]),
            ("麦香鸡", ["麦香鸡汉堡"]),
            ("可乐中杯", ["中杯可乐", "可乐(中)", "可口可乐中杯"]),
            ("可乐大杯", ["大杯可乐", "可乐(大)", "可口可乐大杯"]),
            ("可乐小杯", ["小杯可乐", "可乐(小)", "可口可乐小杯"]),
            ("雪碧中杯", ["中杯雪碧"]),
            ("雪碧大杯", ["大杯雪碧"]),
            ("雪碧小杯", ["小杯雪碧"]),
            ("中薯条", ["中份薯条", "薯条(中)"]),
            ("大薯条", ["大份薯条", "薯条(大)"]),
            ("小薯条", ["小份薯条", "薯条(小)"]),
            ("麦乐鸡5块", ["麦乐鸡5pc", "麦乐鸡(5)"]),
            ("麦乐鸡4块", ["麦乐鸡4pc", "麦乐鸡(4)"]),
            ("麦辣鸡翅-2块", ["麦辣鸡翅2pc", "麦辣鸡翅(2)"]),
            ("原味板烧鸡腿堡", ["板烧鸡腿堡原味"]),
            ("圆筒冰淇淋", ["圆筒冰激凌"]),
            ("甜筒", ["圆筒", "雪糕"]),
        ]
        
        # 新品/限定品的近似估算表（当营养表里没有时，用类似食物的数据）
        # 注意：参考食物的名字必须是营养表里实际存在的！
        # 格式: (关键词列表, 估算用的参考食物名)
        self._fallback_estimations = [
            # 各类双牛堡/厚牛/安格斯 → 培根安格斯厚牛堡（707 kcal）
            (["双牛堡", "双层牛堡", "厚牛", "安格斯"], "培根安格斯厚牛堡"),
            # 椰香/东南亚鸡扒/鸡排 → 板烧鸡腿堡（391 kcal，最接近的鸡腿堡）
            (["椰香", "东南亚", "鸡扒", "鸡排"], "板烧鸡腿堡"),
            # 风味鸡/照烧/炭烤鸡 → 板烧鸡腿堡
            (["风味鸡", "照烧", "炭烤鸡"], "板烧鸡腿堡"),
            # 培根/芝士/牛堡 → 培根安格斯厚牛堡
            (["培根", "芝士", "牛堡"], "培根安格斯厚牛堡"),
            # 创意/新品汉堡兜底 → 不素之霸双层牛堡（493 kcal）
            (["汉堡"], "不素之霸双层牛堡"),
        ]
    
    # 匹配等级常量
    MATCH_EXACT = "exact"          # 精确匹配
    MATCH_FUZZY = "fuzzy"          # 模糊词匹配（同义词表命中）
    MATCH_CONTAIN = "contain"      # 包含匹配
    MATCH_FALLBACK = "fallback"    # Fallback 估算（新品/限定品）

    MATCH_LABEL = {
        "exact": ("✅", "精确匹配"),
        "fuzzy": ("🔶", "模糊匹配"),
        "contain": ("🔸", "包含匹配"),
        "fallback": ("⚠️", "估算（基于类似商品）"),
    }

    def _match_nutrition(self, product_name: str) -> Optional[dict]:
        """把订单里的商品名匹配到营养表，带可信度标注"""
        if not product_name:
            return None

        # 1. 精确匹配
        if product_name in self.nutrition_map:
            result = dict(self.nutrition_map[product_name])
            result["_match_level"] = self.MATCH_EXACT
            result["_match_desc"] = f"精确匹配到「{product_name}」"
            return result

        # 2. 模糊匹配表（同义词/变体）
        for canonical, variants in self._fuzzy_patterns:
            if product_name == canonical or product_name in variants:
                result = dict(self.nutrition_map.get(canonical, {}))
                if result:
                    result["_match_level"] = self.MATCH_FUZZY
                    result["_match_desc"] = f"模糊匹配：「{product_name}」→ 营养表「{canonical}」"
                    return result
            if canonical in product_name:
                result = dict(self.nutrition_map.get(canonical, {}))
                if result:
                    result["_match_level"] = self.MATCH_FUZZY
                    result["_match_desc"] = f"模糊匹配（包含）：「{product_name}」→ 营养表「{canonical}」"
                    return result
            for v in variants:
                if v in product_name or product_name in v:
                    result = dict(self.nutrition_map.get(canonical, {}))
                    if result:
                        result["_match_level"] = self.MATCH_FUZZY
                        result["_match_desc"] = f"模糊匹配：「{product_name}」→ 营养表「{canonical}」"
                        return result

        # 3. 包含匹配（营养表名字包含商品名或反之）
        for nname, ndata in self.nutrition_map.items():
            if nname in product_name or product_name in nname:
                result = dict(ndata)
                result["_match_level"] = self.MATCH_CONTAIN
                result["_match_desc"] = f"包含匹配：「{product_name}」↔「{nname}」"
                return result

        # 4. Fallback 估算（新品/限定品在营养表里找不到时）
        for keywords, ref_food in self._fallback_estimations:
            for kw in keywords:
                if kw in product_name:
                    ref = self.nutrition_map.get(ref_food)
                    if ref:
                        estimated = dict(ref)
                        estimated["_estimated"] = True
                        estimated["_estimated_from"] = ref_food
                        estimated["name"] = product_name  # 保留原商品名
                        estimated["_match_level"] = self.MATCH_FALLBACK
                        estimated["_match_desc"] = f"估算（营养表无此商品）：基于「{ref_food}」近似"
                        return estimated

        return None
    
    def _extract_products(self, order: dict) -> list:
        """从一个订单里提取所有商品（含套餐子项），展平为 [(name, qty)]"""
        products = []
        for prod in order.get("orderProductList", []):
            name = prod.get("productName", "")
            qty = prod.get("quantity", 1)
            
            # 如果是套餐/随心配，子项也展开
            combo = prod.get("comboItemList", [])
            if combo:
                for sub in combo:
                    sub_name = sub.get("name", "")
                    sub_qty = sub.get("quantity", 1)
                    products.append((sub_name, sub_qty))
            else:
                products.append((name, qty))
        
        return products
    
    def analyze(self) -> dict:
        """执行完整分析"""
        if not self.orders:
            return self._empty_report()
        
        # === 逐单解析 ===
        parsed_orders = []
        unmatched_products = Counter()
        total_proteins = Counter()  # 统计匹配情况
        match_level_counts = Counter()  # 各匹配级别计数
        
        for order in self.orders:
            create_time = order.get("createTime", "")
            try:
                dt = datetime.strptime(create_time, "%Y-%m-%d %H:%M:%S")
            except:
                continue
            
            hour = dt.hour
            meal_period = get_meal_period(hour)
            
            products = self._extract_products(order)
            item_nutritions = []
            
            for pname, pqty in products:
                nutri = self._match_nutrition(pname)
                if nutri:
                    item_nutritions.append({
                        "name": pname,
                        "qty": pqty,
                        **nutri
                    })
                    total_proteins["matched"] += 1
                    # 记录匹配级别
                    lvl = nutri.get("_match_level", self.MATCH_EXACT)
                    match_level_counts[lvl] += 1
                else:
                    unmatched_products[pname] += 1
                    item_nutritions.append({
                        "name": pname,
                        "qty": pqty,
                        "name_only": True
                    })
                    total_proteins["unmatched"] += 1
                    match_level_counts["unmatched"] += 1
            
            # 累计本单营养
            order_kcal = sum(item.get("energy_kcal", 0) * item["qty"] 
                           for item in item_nutritions if "energy_kcal" in item and not item.get("name_only"))
            
            parsed_orders.append({
                "order_id": order.get("orderId"),
                "time": create_time,
                "datetime": dt,
                "meal_period": meal_period,
                "meal_period_cn": MEAL_NAMES_CN[meal_period],
                "store_name": order.get("storeName", ""),
                "order_amount": order.get("realTotalAmount", "0"),
                "products": products,  # 原始 [(name, qty)]
                "items": item_nutritions,  # 带营养数据
                "total_kcal": order_kcal,
            })
        
        # === 年度总览 ===
        total_orders = len(parsed_orders)
        total_amount = sum(float(o["order_amount"]) for o in parsed_orders)
        
        # 营养总汇总
        nutrition_totals = self._sum_nutrition(parsed_orders)
        
        # 餐段分布
        meal_period_dist = Counter(o["meal_period"] for o in parsed_orders)
        
        # 月度趋势
        monthly = self._monthly_trend(parsed_orders)
        
        # 热门商品 Top N
        product_counter = Counter()
        for o in parsed_orders:
            for pname, pqty in o["products"]:
                product_counter[pname] += pqty
        top_products = product_counter.most_common(15)
        
        # 热量统计
        kcals = [o["total_kcal"] for o in parsed_orders if o["total_kcal"] > 0]
        avg_kcal_per_order = sum(kcals) / len(kcals) if kcals else 0
        max_kcal_order = max(kcals) if kcals else 0
        min_kcal_order = min(kcals) if kcals else 0
        
        # 餐段平均热量
        meal_kcal_stats = self._meal_kcal_stats(parsed_orders)
        
        # === 健康评估 ===
        health_scores = self._health_assessment(nutrition_totals, total_orders)
        
        # === 麦门人设 ===
        persona = self._determine_persona(parsed_orders, product_counter, nutrition_totals)
        
        # === 年度关键词 ===
        keywords = self._yearly_highlights(parsed_orders, nutrition_totals, health_scores)
        
        # === 健康改进模拟器 ===
        simulations = self._build_health_simulations(parsed_orders, nutrition_totals, health_scores)
        
        # === 门店维度 + 7×24 热力图 ===
        store_analysis = self._build_store_analysis(parsed_orders)
        
        return {
            "meta": {
                "report_title": "麦门年度体检报告",
                "report_year": "2025-2026",
                "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            },
            "summary": {
                "total_orders": total_orders,
                "total_amount": round(total_amount, 2),
                "days_between": self._days_span(parsed_orders),
                "avg_orders_per_week": round(total_orders / max(self._weeks_span(parsed_orders), 1), 1),
                "nutrition_match_rate": round(
                    total_proteins["matched"] / max(total_proteins["matched"] + total_proteins["unmatched"], 1) * 100, 1
                ),
                "unmatched_products": list(unmatched_products.most_common(10)),
            },
            # 营养匹配可信度总览
            "match_breakdown": self._build_match_breakdown(
                match_level_counts,
                total_proteins["matched"] + total_proteins["unmatched"]
            ),
            "nutrition_total": nutrition_totals,
            "kcal_stats": {
                "avg_per_order": round(avg_kcal_per_order, 0),
                "max_single_order": round(max_kcal_order, 0),
                "min_single_order": round(min_kcal_order, 0),
                "meal_period_breakdown": meal_kcal_stats,
            },
            "meal_period_distribution": [
                {"period": MEAL_NAMES_CN[k], "count": v, "period_key": k}
                for k, v in meal_period_dist.most_common()
            ],
            "monthly_trend": monthly,
            "top_products": [
                {"rank": i+1, "name": name, "quantity": qty}
                for i, (name, qty) in enumerate(top_products)
            ],
            "health_assessment": health_scores,
            "persona": persona,
            "keywords": keywords,
            "orders_detail": [
                {
                    "time": o["time"],
                    "meal_period": o["meal_period_cn"],
                    "store": o["store_name"],
                    "amount": o["order_amount"],
                    "kcal": round(o["total_kcal"], 0),
                    "items": [
                        {"name": it["name"], "qty": it["qty"], 
                         "kcal": round(it.get("energy_kcal", 0) * it["qty"], 0) if not it.get("name_only") else None}
                        for it in o["items"]
                    ]
                }
                for o in parsed_orders
            ],
            "health_simulations": simulations,
            "store_analysis": store_analysis,
        }
    
    # ============ 辅助方法 ============
    
    def _empty_report(self) -> dict:
        return {"meta": {"report_title": "麦门年度体检报告", "note": "暂无历史订单"}, "summary": {"total_orders": 0}}
    
    def _sum_nutrition(self, parsed_orders: list) -> dict:
        totals = defaultdict(float)
        for o in parsed_orders:
            for item in o["items"]:
                if item.get("name_only"):
                    continue
                for key in ["energy_kj", "energy_kcal", "protein", "fat", "carbohydrate", "sodium", "calcium"]:
                    totals[key] += item.get(key, 0) * item["qty"]
        return {k: round(v, 1) for k, v in totals.items()}
    
    def _days_span(self, parsed_orders: list) -> int:
        if not parsed_orders:
            return 0
        times = [o["datetime"] for o in parsed_orders]
        return (max(times) - min(times)).days + 1
    
    def _weeks_span(self, parsed_orders: list) -> int:
        return max(self._days_span(parsed_orders) // 7, 1)
    
    def _monthly_trend(self, parsed_orders: list) -> list:
        monthly = defaultdict(lambda: {"orders": 0, "kcal": 0.0, "amount": 0.0})
        for o in parsed_orders:
            m = o["datetime"].strftime("%Y-%m")
            monthly[m]["orders"] += 1
            monthly[m]["kcal"] += o["total_kcal"]
            monthly[m]["amount"] += float(o["order_amount"])
        
        result = []
        for m in sorted(monthly.keys()):
            v = monthly[m]
            result.append({
                "month": m,
                "orders": v["orders"],
                "total_kcal": round(v["kcal"], 0),
                "total_amount": round(v["amount"], 2),
                "avg_kcal_per_order": round(v["kcal"] / max(v["orders"], 1), 0),
            })
        return result
    
    def _meal_kcal_stats(self, parsed_orders: list) -> list:
        buckets = defaultdict(list)
        for o in parsed_orders:
            if o["total_kcal"] > 0:
                buckets[o["meal_period"]].append(o["total_kcal"])
        
        stats = []
        for period_key, kcals in buckets.items():
            avg = sum(kcals) / len(kcals)
            lo, hi = MCD_MEAL_KCAL_RANGE[period_key]
            within = lo <= avg <= hi
            stats.append({
                "period": MEAL_NAMES_CN[period_key],
                "period_key": period_key,
                "count": len(kcals),
                "avg_kcal": round(avg, 0),
                "recommended_range": f"{lo}-{hi}",
                "within_range": within,
            })
        return stats
    
    def _health_assessment(self, nutrition_totals: dict, total_orders: int) -> dict:
        """计算健康评分（百分制）"""
        if total_orders == 0:
            return {}
        
        days_covered = total_orders  # 简化：假设每单代表一天（至少有数据）
        
        scores = {}
        details = {}
        
        # 计算"假设这些麦当劳占了你日常饮食的 X%"，给合理的评估
        # 假设麦当劳占日常热量的 30%
        assumed_mcd_ratio = 0.3
        
        # 各维度得分
        # 1. 热量
        avg_kcal_per_order = nutrition_totals.get("energy_kcal", 0) / max(total_orders, 1)
        # 麦当劳一单建议 500-900 kcal
        if 500 <= avg_kcal_per_order <= 900:
            scores["热量"] = 90
            details["热量"] = f"平均每单 {round(avg_kcal_per_order, 0)} kcal，在合理区间内"
        elif avg_kcal_per_order < 500:
            scores["热量"] = 75
            details["热量"] = f"平均每单 {round(avg_kcal_per_order, 0)} kcal，偏低，注意营养补充"
        else:
            scores["热量"] = max(50, 90 - int((avg_kcal_per_order - 900) / 20))
            details["热量"] = f"平均每单 {round(avg_kcal_per_order, 0)} kcal，偏高，建议选择轻食搭配"
        
        # 2. 钠（盐）—— 麦当劳最容易超标
        avg_sodium = nutrition_totals.get("sodium", 0) / max(total_orders, 1)
        # 麦当劳单餐建议钠 < 800mg
        if avg_sodium <= 800:
            scores["钠摄入"] = 95
            details["钠摄入"] = f"平均每单钠 {round(avg_sodium, 0)}mg，健康水平"
        elif avg_sodium <= 1200:
            scores["钠摄入"] = 75
            details["钠摄入"] = f"平均每单钠 {round(avg_sodium, 0)}mg，略高，注意少喝可乐多吃蔬菜水果"
        else:
            scores["钠摄入"] = max(40, 75 - int((avg_sodium - 1200) / 50))
            details["钠摄入"] = f"平均每单钠 {round(avg_sodium, 0)}mg，偏高！注意控盐"
        
        # 3. 蛋白质
        avg_protein = nutrition_totals.get("protein", 0) / max(total_orders, 1)
        # 麦当劳一单蛋白质建议 20-40g
        if 20 <= avg_protein <= 40:
            scores["蛋白质"] = 90
            details["蛋白质"] = f"平均每单蛋白质 {round(avg_protein, 1)}g，优秀"
        elif avg_protein < 20:
            scores["蛋白质"] = 70
            details["蛋白质"] = f"平均每单蛋白质 {round(avg_protein, 1)}g，偏少，多加份鸡肉吧"
        else:
            scores["蛋白质"] = 85
            details["蛋白质"] = f"平均每单蛋白质 {round(avg_protein, 1)}g，充足"
        
        # 4. 脂肪
        avg_fat = nutrition_totals.get("fat", 0) / max(total_orders, 1)
        if avg_fat <= 40:
            scores["脂肪"] = 85
            details["脂肪"] = f"平均每单脂肪 {round(avg_fat, 1)}g，合理"
        elif avg_fat <= 55:
            scores["脂肪"] = 70
            details["脂肪"] = f"平均每单脂肪 {round(avg_fat, 1)}g，注意减少油炸食品"
        else:
            scores["脂肪"] = max(50, 70 - int((avg_fat - 55) / 5))
            details["脂肪"] = f"平均每单脂肪 {round(avg_fat, 1)}g，偏高！"
        
        # 综合评分
        avg_score = round(sum(scores.values()) / len(scores), 0)
        
        # 评级
        if avg_score >= 85:
            grade = "麦门健康达人 ⭐⭐⭐"
        elif avg_score >= 70:
            grade = "麦门稳健选手 ⭐⭐"
        elif avg_score >= 55:
            grade = "麦门谨慎食客 ⭐"
        else:
            grade = "麦门放纵战士 🔥"
        
        return {
            "scores": scores,
            "details": details,
            "overall_score": avg_score,
            "grade": grade,
        }
    
    def _determine_persona(self, parsed_orders: list, product_counter: Counter, nutrition_totals: dict) -> dict:
        """根据消费模式判断麦门人设"""
        total_count = sum(product_counter.values()) or 1
        
        # 统计类别
        burger_keywords = ["堡", "霸", "堡包", "堡皇"]
        chicken_keywords = ["鸡", "辣", "脆", "香酥", "麦乐鸡"]
        drink_keywords = ["可乐", "雪碧", "咖啡", "拿铁", "雪冰", "牛奶", "红茶", "果汁", "奶"]
        dessert_keywords = ["派", "甜筒", "圆筒", "新地", "麦旋风", "雪冰", "奶冻", "爆珠"]
        breakfast_keywords = ["早晨", "早餐", "蛋堡", "薯饼", "营养卷"]
        
        burger_pct = sum(cnt for name, cnt in product_counter.items() 
                        if any(k in name for k in burger_keywords)) / total_count
        chicken_pct = sum(cnt for name, cnt in product_counter.items()
                         if any(k in name for k in chicken_keywords)) / total_count
        drink_pct = sum(cnt for name, cnt in product_counter.items()
                       if any(k in name for k in drink_keywords)) / total_count
        dessert_pct = sum(cnt for name, cnt in product_counter.items()
                         if any(k in name for k in dessert_keywords)) / total_count
        
        meal_period_counts = Counter(o["meal_period"] for o in parsed_orders)
        total_meals = len(parsed_orders) or 1
        breakfast_freq = meal_period_counts.get("breakfast", 0) / total_meals
        supper_freq = meal_period_counts.get("supper", 0) / total_meals
        
        # 规则匹配
        personas = []
        
        if chicken_pct > 0.4:
            personas.append({"name": "脆皮鸡肉爱好者", "emoji": "🍗", "desc": "没有炸鸡的一天不值得一过"})
        if burger_pct > 0.35:
            personas.append({"name": "汉堡收藏家", "emoji": "🍔", "desc": "巨无霸是信仰，板烧是底线"})
        if drink_pct > 0.4:
            personas.append({"name": "饮料达人", "emoji": "🥤", "desc": "每单必点喝的，少了可乐活不下去"})
        if dessert_pct > 0.25:
            personas.append({"name": "甜品终结者", "emoji": "🍦", "desc": "派和新地是正餐，汉堡是配菜"})
        if breakfast_freq > 0.3:
            personas.append({"name": "麦门早起党", "emoji": "🌅", "desc": "麦当劳早餐治好了我的赖床"})
        if supper_freq > 0.25:
            personas.append({"name": "深夜麦客", "emoji": "🌙", "desc": "凌晨的麦当劳是我的午夜食堂"})
        
        if not personas:
            personas.append({"name": "佛系食客", "emoji": "☯️", "desc": "想吃就点，不太纠结"})
        
        # 最显著的人设排第一
        main_persona = personas[0]
        if len(personas) > 1:
            sub_personas = personas[1:]
        else:
            sub_personas = []
        
        return {
            "main": main_persona,
            "sub": sub_personas,
            "breakdown": {
                "汉堡占比": f"{round(burger_pct * 100)}%",
                "鸡肉占比": f"{round(chicken_pct * 100)}%",
                "饮料占比": f"{round(drink_pct * 100)}%",
                "甜品占比": f"{round(dessert_pct * 100)}%",
                "早餐频率": f"{round(breakfast_freq * 100)}%",
                "宵夜频率": f"{round(supper_freq * 100)}%",
            }
        }
    
    def _yearly_highlights(self, parsed_orders: list, nutrition_totals: dict, health_scores: dict) -> list:
        """年度关键词/高光时刻"""
        highlights = []
        
        # 最热月份
        monthly = self._monthly_trend(parsed_orders)
        if monthly:
            hottest = max(monthly, key=lambda x: x["orders"])
            highlights.append(f"📅 {hottest['month']} 是你最想吃麦当劳的月份，点了 {hottest['orders']} 单")
        
        # 最贵一餐
        if parsed_orders:
            most_expensive = max(parsed_orders, key=lambda x: float(x["order_amount"]))
            highlights.append(f"💰 最贵一餐：{most_expensive['order_amount']} 元（{most_expensive['time']}）")
        
        # 热量爆棚一餐
        if parsed_orders:
            hottest_meal = max(parsed_orders, key=lambda x: x["total_kcal"])
            if hottest_meal["total_kcal"] > 0:
                highlights.append(f"🔥 热量巅峰：{round(hottest_meal['total_kcal'])} kcal 的一餐（{hottest_meal['time']}）")
        
        # 健康评分关键词
        if health_scores:
            overall = health_scores.get("overall_score", 0)
            if overall >= 85:
                highlights.append("✨ 麦门健康达人——吃麦当劳也能吃出平衡")
            elif overall < 55:
                highlights.append("😂 麦门放纵战士——兄弟悠着点")
        
        # 消费频次
        if parsed_orders:
            days = self._days_span(parsed_orders)
            freq = len(parsed_orders) / max(days / 30, 1)  # 每月单数
            highlights.append(f"📊 每月平均 {round(freq, 1)} 单麦当劳")
        
        return highlights

    def _build_match_breakdown(self, match_level_counts: Counter, total: int) -> list:
        """构建营养匹配可信度总览"""
        breakdown = []
        # 按可信度从高到低排列
        level_order = [
            (self.MATCH_EXACT, "✅ 精确匹配"),
            (self.MATCH_FUZZY, "🔶 模糊匹配"),
            (self.MATCH_CONTAIN, "🔸 包含匹配"),
            (self.MATCH_FALLBACK, "⚠️ 估算（新品/限定品）"),
            ("unmatched", "❌ 未匹配"),
        ]
        for level, label in level_order:
            cnt = match_level_counts.get(level, 0)
            if cnt == 0 and level != "unmatched":
                continue  # 跳过零项
            pct = round(cnt / max(total, 1) * 100, 1)
            breakdown.append({
                "level": level,
                "label": label,
                "count": cnt,
                "pct": pct,
            })
        return breakdown

    def _build_health_simulations(self, parsed_orders: list, nutrition_totals: dict, health_scores: dict) -> list:
        """健康改进模拟器——基于真实历史数据，算"如果改了能好多少" """
        simulations = []
        total_orders = len(parsed_orders)
        h = health_scores or {}
        overall = h.get("overall_score", 0)

        if total_orders == 0:
            return simulations

        # 先算一下各类食物的实际点单频次
        product_counter = Counter()
        for o in parsed_orders:
            for pname, pqty in o["products"]:
                product_counter[pname] += pqty

        def count_keyword_orders(keywords):
            """算包含指定关键词的商品总次数"""
            return sum(cnt for name, cnt in product_counter.items()
                       if any(kw in name for kw in keywords))

        # ====== 模拟 1：把可乐换成无糖/雪碧（省糖） ======
        drink_count = count_keyword_orders(["可乐", "雪碧", "果汁", "拿铁"])
        sugary_drink_count = count_keyword_orders(["可乐"])  # 假设主要是可乐
        if sugary_drink_count >= 3:
            # 中杯可乐 36g 糖 → 无糖可乐约 0g，省 36g/次
            yearly_saved_sugar_g = sugary_drink_count * 36
            yearly_saved_carb_g = sugary_drink_count * 36  # 碳水主要就是糖
            simulations.append({
                "icon": "🥤",
                "action": f"把可乐换成无糖可乐（{sugary_drink_count} 次/年）",
                "impact": f"每年少摄入约 {yearly_saved_sugar_g}g 糖，相当于 {(yearly_saved_sugar_g/4.2):.0f} 碗白米饭的碳水",
                "score_hint": "钠摄入得分可升 5-8 分",
                "grade_hint": "如果当前在 70-80 分段 → 有望到 85+",
            })

        # ====== 模拟 2：每周少一次大薯条（省脂肪/热量） ======
        fries_count = count_keyword_orders(["薯条"])
        big_fries_count = count_keyword_orders(["大薯条"])
        if fries_count >= 8:  # 至少每月一次
            # 大薯条 16g 脂肪 / 379 kcal → 换成中薯条 12g / 289 kcal
            yearly_saved_fat_g = big_fries_count * 4 if big_fries_count > 0 else fries_count * 2
            yearly_saved_kcal = (big_fries_count * 90 + (fries_count - big_fries_count) * 50)
            simulations.append({
                "icon": "🍟",
                "action": f"大薯条换中薯条（{f'其中 {big_fries_count} 次大薯条' if big_fries_count > 0 else f'共 {fries_count} 次薯条'}）",
                "impact": f"每年少摄入约 {yearly_saved_fat_g}g 脂肪、{yearly_saved_kcal} kcal",
                "score_hint": "脂肪 + 热量 两个维度可同时提升",
                "grade_hint": "健康综合分 +3~+7",
            })

        # ====== 模拟 3：宵夜提前到睡前 3 小时 ======
        supper_orders = [o for o in parsed_orders if o["meal_period"] == "supper"]
        supper_count = len(supper_orders)
        if supper_count >= 3:
            late_supper = [o for o in supper_orders if o["datetime"].hour >= 0 and o["datetime"].hour < 5]
            simulations.append({
                "icon": "🌙",
                "action": f"{supper_count} 次宵夜提前到睡前 3 小时吃",
                "impact": f"其中 {len(late_supper)} 次是凌晨 0-5 点的极限宵夜，调整后可改善夜间代谢",
                "score_hint": "不改变摄入量，但能降低「放纵战士」评级",
                "grade_hint": "称号可能从「放纵战士」→「谨慎食客」",
            })

        # ====== 模拟 4：汉堡换板烧（非油炸，省油） ======
        fried_burger_count = count_keyword_orders(["麦辣", "脆", "香酥"])
        grilled_count = count_keyword_orders(["板烧"])
        if fried_burger_count >= 3 and grilled_count < fried_burger_count:
            # 假设每次换板烧省 9g 脂肪（麦辣鸡腿堡 24g vs 板烧鸡腿堡 17g）
            yearly_saved_fat = fried_burger_count * 7
            simulations.append({
                "icon": "🍔",
                "action": f"{fried_burger_count} 次麦辣类汉堡换板烧（非油炸）",
                "impact": f"每年少摄入约 {yearly_saved_fat}g 脂肪，油脂摄入下降 {(yearly_saved_fat/2000*100):.1f}%",
                "score_hint": "脂肪得分可大幅提升",
                "grade_hint": "如果脂肪当前是红灯（<70），有望升到绿灯区",
            })

        # ====== 模拟 5：最适合你的一步（基于当前最弱项） ======
        weak_dim = None
        min_score = 100
        scores = h.get("scores", {})
        for dim, sc in scores.items():
            if sc < min_score:
                min_score = sc
                weak_dim = dim
        if weak_dim and min_score < 85:
            suggestion_map = {
                "钠摄入": ("降钠计划", "每次多加一份麦乐鸡时，把饮料换成无糖的——省 36g 糖 ≈ 一杯可乐的钠一半"),
                "脂肪": ("低脂替换", "下次点巨无霸 + 薯条时，试试板烧鸡腿堡 + 麦乐鸡——少 15g 脂肪"),
                "热量": ("控卡组合", "巨无霸套餐换板烧套餐——省 120 kcal，蛋白质反而多 4g"),
                "蛋白质": ("蛋白加成", "每次多加一份麦乐鸡 5 块——+12g 蛋白质，而且比汉堡省脂肪"),
            }
            title, tip = suggestion_map.get(weak_dim, ("综合优化", "每次点餐前多花 30 秒想想——真的需要这么多吗？"))
            simulations.insert(0, {
                "icon": "🎯",
                "action": f"【当前最弱项：{weak_dim}】{title}",
                "impact": tip,
                "score_hint": f"当前得分 {min_score}，针对性调整提升最快",
                "grade_hint": f"每改善一个维度 +5~+10 分，综合评分能到 {min(min_score + 10, 100)}+",
            })

        # 如果什么都没命中，给一个通用建议
        if not simulations:
            simulations.append({
                "icon": "💪",
                "action": "保持你现在的节奏",
                "impact": f"你已经是「{h.get('grade', '稳健选手')}」了，继续保持！",
                "score_hint": f"当前综合分 {overall}，离「麦门健康达人」还差 {max(0, 85 - overall):.0f} 分",
                "grade_hint": "试着每周少一次薯条或可乐，就能升级",
            })

        return simulations

    def _build_store_analysis(self, parsed_orders: list) -> dict:
        """门店维度 + 7×24 点餐热力图"""
        if not parsed_orders:
            return {"top_stores": [], "heatmap": []}

        # === 门店排行 ===
        store_counter = Counter()
        store_amount = defaultdict(float)
        store_hours = defaultdict(list)  # 每个门店的到访时间
        for o in parsed_orders:
            sn = o.get("store_name", "未知门店")
            store_counter[sn] += 1
            try:
                store_amount[sn] += float(o.get("order_amount", 0))
            except:
                pass
            store_hours[sn].append(o["datetime"])

        top_stores = []
        for name, count in store_counter.most_common(5):
            hours = store_hours[name]
            avg_hour = sum(h.hour + h.minute / 60 for h in hours) / len(hours) if hours else 12
            avg_hour_int = int(avg_hour)
            period = get_meal_period(avg_hour_int)
            top_stores.append({
                "name": name,
                "count": count,
                "amount": round(store_amount[name], 2),
                "avg_hour_text": f"{avg_hour_int}:{int((avg_hour % 1) * 60):02d}",
                "typical_period": MEAL_NAMES_CN.get(period, period),
            })

        # === 7×24 热力图 ===
        # 7 天 × 24 小时 = 168 格
        # 用 day_of_week 0=Monday ... 6=Sunday, hour 0-23
        heatmap = Counter()
        for o in parsed_orders:
            dow = o["datetime"].weekday()
            hour = o["datetime"].hour
            heatmap[(dow, hour)] += 1

        # 转成矩阵：days[7][24]
        day_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        heatmap_data = []
        max_count = max(heatmap.values()) if heatmap else 1
        for dow in range(7):
            row = {"day": day_names[dow], "cells": []}
            for hour in range(24):
                cnt = heatmap.get((dow, hour), 0)
                row["cells"].append({
                    "hour": hour,
                    "count": cnt,
                    "pct": round(cnt / max_count * 100, 1) if max_count > 0 else 0,
                })
            heatmap_data.append(row)

        # 找"黄金麦门时间"
        all_hours = Counter()
        for o in parsed_orders:
            all_hours[o["datetime"].hour] += 1
        best_hour = all_hours.most_common(1)[0] if all_hours else (12, 0)
        best_dow = Counter(o["datetime"].weekday() for o in parsed_orders).most_common(1)[0] if parsed_orders else (0, 0)

        return {
            "top_stores": top_stores,
            "heatmap": heatmap_data,
            "golden_time": f"周{day_names[best_dow[0]][1]} {best_hour[0]}:00",
            "golden_time_desc": f"你最常在周{day_names[best_dow[0]][1]}的 {best_hour[0]} 点吃麦当劳",
        }
