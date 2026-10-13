"""
麦门年度体检报告 - 生成器

使用方法:
    python generate_report.py [--token YOUR_MCD_TOKEN] [--output output.html]
"""
import os
import sys
import json
import argparse
from datetime import datetime

from string import Template as _Template
from mcd_client import McDormandMCPClient
from analyzer import AnnualAnalyzer


HTML_TEMPLATE_STR = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>麦门年度体检报告</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Microsoft YaHei', sans-serif;
    background: linear-gradient(135deg, #ffeb3b 0%, #ff9800 50%, #f44336 100%);
    min-height: 100vh;
    padding: 40px 20px;
    color: #333;
  }
  .container {
    max-width: 900px;
    margin: 0 auto;
  }
  .card {
    background: rgba(255, 255, 255, 0.97);
    border-radius: 24px;
    padding: 40px;
    margin-bottom: 30px;
    box-shadow: 0 20px 60px rgba(0,0,0,0.15);
    backdrop-filter: blur(10px);
  }
  .hero {
    text-align: center;
    background: linear-gradient(135deg, #ffc107 0%, #ff5722 100%);
    color: white;
    border-radius: 24px;
    padding: 60px 40px;
    margin-bottom: 30px;
    box-shadow: 0 20px 60px rgba(255,87,34,0.4);
  }
  .hero h1 {
    font-size: 3em;
    margin-bottom: 10px;
    text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
  }
  .hero .year {
    font-size: 6em;
    font-weight: 900;
    letter-spacing: 10px;
    opacity: 0.3;
    margin: 10px 0;
  }
  .hero p {
    font-size: 1.2em;
    opacity: 0.95;
  }
  .big-number {
    font-size: 3em;
    font-weight: bold;
    color: #ff5722;
  }
  .stat-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 20px;
    margin-top: 20px;
  }
  .stat-item {
    text-align: center;
    padding: 20px;
    background: linear-gradient(135deg, #fff3e0, #ffe0b2);
    border-radius: 16px;
  }
  .stat-item .value {
    font-size: 2.2em;
    font-weight: bold;
    color: #ff5722;
  }
  .stat-item .label {
    color: #666;
    font-size: 0.9em;
    margin-top: 5px;
  }
  h2 {
    font-size: 1.8em;
    margin-bottom: 24px;
    color: #d84315;
    display: flex;
    align-items: center;
    gap: 10px;
  }
  h2::before {
    content: '';
    width: 6px;
    height: 32px;
    background: linear-gradient(180deg, #ff5722, #ffc107);
    border-radius: 3px;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 10px;
  }
  th, td {
    padding: 12px 16px;
    text-align: left;
    border-bottom: 1px solid #ffe0b2;
  }
  th {
    background: #fff3e0;
    font-weight: 600;
    color: #5d4037;
  }
  .progress-bar {
    height: 24px;
    background: #ffe0b2;
    border-radius: 12px;
    overflow: hidden;
    margin-top: 8px;
  }
  .progress-fill {
    height: 100%;
    border-radius: 12px;
    transition: width 0.5s ease;
  }
  .persona-emoji {
    font-size: 5em;
    text-align: center;
    display: block;
  }
  .persona-name {
    font-size: 2em;
    text-align: center;
    color: #ff5722;
    font-weight: bold;
  }
  .persona-desc {
    text-align: center;
    color: #666;
    margin-top: 10px;
    font-style: italic;
  }
  .health-score {
    font-size: 5em;
    font-weight: 900;
    text-align: center;
    background: linear-gradient(135deg, #4caf50, #8bc34a);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }
  .health-grade {
    text-align: center;
    font-size: 1.5em;
    color: #388e3c;
    margin-top: 10px;
  }
  .highlights li {
    padding: 12px 0;
    border-bottom: 1px dashed #ffcc80;
    font-size: 1.05em;
  }
  .highlights li:last-child {
    border: none;
  }
  .month-bar {
    display: flex;
    align-items: flex-end;
    gap: 8px;
    height: 200px;
    margin-top: 20px;
    padding: 0 10px;
    border-bottom: 2px solid #ffcc80;
  }
  .month-bar-item {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
  }
  .month-bar-fill {
    width: 100%;
    background: linear-gradient(180deg, #ff9800, #f44336);
    border-radius: 6px 6px 0 0;
    min-height: 4px;
  }
  .month-bar-label {
    font-size: 0.75em;
    color: #666;
  }
  .footer {
    text-align: center;
    color: #888;
    padding: 40px 30px 30px;
    opacity: 1;
    font-size: 0.9em;
  }
  .footer a {
    color: #f44336;
    text-decoration: underline;
  }
  .orders-table tr:hover {
    background: #fff8e1;
  }
  @media (max-width: 600px) {
    .hero h1 { font-size: 2em; }
    .hero .year { font-size: 4em; }
    .card { padding: 25px 20px; }
  }
</style>
</head>
<body>
<div class="container">

<!-- HERO -->
<div class="hero">
  <h1>🍔 麦门年度体检报告</h1>
  <div class="year">YEAR IN MCD</div>
  <p>由麦当劳中国官方 MCP 驱动 · 你吃的每一口都被 AI 记下来了</p>
</div>

<!-- 年度总览 -->
<div class="card">
  <h2>📊 年度总览</h2>
  <div class="stat-grid">
    <div class="stat-item">
      <div class="value" id="dyn_total_orders">__total_orders__</div>
      <div class="label">麦当劳订单数</div>
    </div>
    <div class="stat-item">
      <div class="value" id="dyn_total_amount">¥__total_amount__</div>
      <div class="label">年度消费总额</div>
    </div>
    <div class="stat-item">
      <div class="value">__avg_orders_per_week__</div>
      <div class="label">每周平均单数</div>
    </div>
    <div class="stat-item">
      <div class="value" id="dyn_match_rate">__nutrition_match_rate__%</div>
      <div class="label">营养数据匹配率</div>
    </div>
  </div>
</div>

<!-- 数据可信度总览 -->
<div class="card">
  <h2>🔍 数据可信度</h2>
  <p style="color:#888; font-size:0.9em; margin-bottom:20px;">
    营养数据来自麦当劳官方营养表。以下是你历史订单中各条商品的匹配情况——精确匹配越多，报告越准。
  </p>
  __match_breakdown_html__
</div>

<!-- 健康评估 -->
<div class="card">
  <h2>❤️ 健康评分</h2>
  <div style="text-align:center; margin-bottom:30px;">
    <div class="health-score" id="dyn_score">__health_overall__</div>
    <div class="health-grade">__health_grade__</div>
  </div>
  <table>
    <thead>
      <tr><th>维度</th><th>得分</th><th>详情</th></tr>
    </thead>
    <tbody>
      __health_rows__
    </tbody>
  </table>
</div>

<!-- 麦门人设 -->
<div class="card">
  <h2>🎭 你的麦门人设</h2>
  <span class="persona-emoji">__persona_emoji__</span>
  <div class="persona-name" id="dyn_persona">__persona_name__</div>
  <div class="persona-desc">__persona_desc__</div>
  
  __sub_personas_html__
  
  <div style="margin-top:30px;">
    <h3 style="color:#5d4037; margin-bottom:16px;">消费画像拆解</h3>
    __breakdown_html__
  </div>
</div>

<!-- 热量统计 -->
<div class="card">
  <h2>🔥 热量画像</h2>
  <div class="stat-grid">
    <div class="stat-item">
      <div class="value">__avg_kcal_per_order__</div>
      <div class="label">平均每单 kcal</div>
    </div>
    <div class="stat-item">
      <div class="value">__max_kcal_order__</div>
      <div class="label">最高单餐 kcal</div>
    </div>
    <div class="stat-item">
      <div class="value">__min_kcal_order__</div>
      <div class="label">最低单餐 kcal</div>
    </div>
  </div>
  
  <h3 style="color:#5d4037; margin-top:30px; margin-bottom:16px;">各餐段热量分析</h3>
  <table>
    <thead>
      <tr><th>餐段</th><th>单数</th><th>平均 kcal</th><th>推荐区间</th><th>状态</th></tr>
    </thead>
    <tbody>
      __meal_kcal_rows__
    </tbody>
  </table>
</div>

<!-- 餐段分布 -->
<div class="card">
  <h2>📅 你在什么时候吃麦当劳</h2>
  __meal_distribution_html__
</div>

<!-- 7×24 热力图 -->
<div class="card">
  <h2>🗓️ 7×24 点餐热力图</h2>
  <p style="color:#888; font-size:0.9em; margin-bottom:20px;">
    每格代表该天某小时的麦当劳下单次数，颜色越深点得越多。<br>
    你最常在 <strong style="color:#ff5722;" id="dyn_golden">__golden_time__</strong> 吃麦当劳（黄金麦门时间）
  </p>
  __heatmap_html__
</div>

<!-- 月度趋势 -->
<div class="card">
  <h2>📈 月度消费趋势</h2>
  __monthly_chart__
  <table style="margin-top:20px;">
    <thead>
      <tr><th>月份</th><th>单数</th><th>总 kcal</th><th>消费金额</th><th>平均 kcal/单</th></tr>
    </thead>
    <tbody>
      __monthly_rows__
    </tbody>
  </table>
</div>

<!-- 最爱 Top 15 -->
<div class="card">
  <h2>⭐ 你最常点的 Top 15</h2>
  <table>
    <thead>
      <tr><th>排名</th><th>商品</th><th>次数</th></tr>
    </thead>
    <tbody>
      __top_products_rows__
    </tbody>
  </table>
</div>

<!-- 年度高光 -->
<div class="card">
  <h2>✨ 年度高光时刻</h2>
  <ul class="highlights">
    __highlights_html__
  </ul>
</div>

<!-- 门店排行 -->
<div class="card">
  <h2>🏪 你最常去的门店</h2>
  __top_stores_html__
</div>

<!-- 健康改进模拟器 -->
<div class="card">
  <h2>💪 健康改进模拟器</h2>
  <p style="color:#888; font-size:0.9em; margin-bottom:20px;">
    基于你这一年的真实点餐数据，算一下如果做这些小改变，健康能好多少——不是"别吃麦当劳"，而是"吃麦当劳也能更健康"。
  </p>
  __simulations_html__
</div>

<!-- 营养总汇总 -->
<div class="card">
  <h2>🥗 年度营养总量估算</h2>
  <div class="stat-grid">
    <div class="stat-item"><div class="value">__n_energy_kcal__</div><div class="label">总热量 kcal</div></div>
    <div class="stat-item"><div class="value">__n_protein__g</div><div class="label">总蛋白质</div></div>
    <div class="stat-item"><div class="value">__n_fat__g</div><div class="label">总脂肪</div></div>
    <div class="stat-item"><div class="value">__n_carb__g</div><div class="label">总碳水</div></div>
    <div class="stat-item"><div class="value">__n_sodium__mg</div><div class="label">总钠（控！）</div></div>
    <div class="stat-item"><div class="value">__n_calcium__mg</div><div class="label">总钙</div></div>
  </div>
</div>

<!-- 订单详情 -->
<div class="card">
  <h2>📝 全部订单明细</h2>
  <table class="orders-table">
    <thead>
      <tr><th>时间</th><th>餐段</th><th>门店</th><th>金额</th><th>热量</th><th>商品</th></tr>
    </thead>
    <tbody>
      __orders_rows__
    </tbody>

<!-- 获取你的报告 -->
<div class="card" style="background:linear-gradient(135deg,#ff9800,#f44336); color:white;">
  <h2 style="color:white; text-align:center;">🎁 想看看你自己的麦门年度报告？</h2>
  <p style="text-align:center; line-height:1.8; font-size:1.05em; opacity:0.95; margin:16px 0 24px;">
    全程本地运行，Token 不上传。3 步搞定👇
  </p>
  <div style="background:rgba(255,255,255,0.15); border-radius:16px; padding:24px 28px; line-height:2.2;">
    <div><strong>① 申请 MCP Token</strong>（10 秒）<br>
    👉 <a href="https://open.mcd.cn/mcp" target="_blank" style="color:white; text-decoration:underline; font-weight:normal;">open.mcd.cn/mcp</a> 手机号登录 → 一键复制</div>
    <div><strong>② 克隆项目</strong><br>
    <code style="background:rgba(0,0,0,0.3); padding:4px 12px; border-radius:6px; font-family:monospace; display:inline-block; margin-top:2px;">git clone https://github.com/xiewengi/mcd-annual-report.git && cd mcd-annual-report</code></div>
    <div><strong>③ 一行命令生成</strong><br>
    <code style="background:rgba(0,0,0,0.3); padding:4px 12px; border-radius:6px; font-family:monospace; display:inline-block; margin-top:2px;">python3 generate_report.py --token "你的Token" --save-json</code><br>
    <span style="font-size:0.85em; opacity:0.85; margin-top:2px; display:block;">📌 加 <code style="background:rgba(0,0,0,0.3); padding:1px 6px; border-radius:3px;">--gender male --weight 70 --height 175 --age 28</code> 算你的 BMR，健康评分更准</span></div>
  </div>
  <div style="text-align:center; margin-top:20px; font-size:0.95em; opacity:0.9;">
    ✅ 本地运行 · Token 不上传 · 自动生成人格卡 PNG 分享
  </div>
</div>

<div class="footer">
  <p>🍟 麦门年度体检报告 · Powered by 麦当劳中国官方 MCP Server</p>
  <p style="margin-top:10px;">参赛作品 · 2026 麦当劳程序员创意开发大赛</p>
  <p style="margin-top:5px; font-size:0.8em;">生成于 __generated_at__</p>
</div>

</div>

</body></body>
</html>
"""


def render_report(data: dict, output_path: str):
    """渲染 HTML 报告"""
    summary = data.get("summary", {})
    nutrition_total = data.get("nutrition_total", {})
    kcal_stats = data.get("kcal_stats", {})
    meal_dist = data.get("meal_period_distribution", [])
    monthly = data.get("monthly_trend", [])
    top_products = data.get("top_products", [])
    health = data.get("health_assessment", {})
    persona = data.get("persona", {})
    keywords = data.get("keywords", [])
    orders = data.get("orders_detail", [])
    match_breakdown = data.get("match_breakdown", [])
    simulations = data.get("health_simulations", [])
    store_analysis = data.get("store_analysis", {})
    
    # 匹配可信度总览
    match_breakdown_html = ""
    for mb in match_breakdown:
        if mb["count"] == 0 and mb["level"] != "unmatched":
            continue
        # 颜色：exact 绿 / fuzzy 橙 / contain 蓝 / fallback 红 / unmatched 灰
        color_map = {
            "exact": "#4caf50", "fuzzy": "#ff9800", "contain": "#2196f3",
            "fallback": "#f44336", "unmatched": "#9e9e9e",
        }
        bar_color = color_map.get(mb["level"], "#9e9e9e")
        match_breakdown_html += f"""
          <div style="margin:12px 0;">
            <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
              <span style="font-weight:600;">{mb['label']}</span>
              <span style="color:#666;">{mb['count']} 项 · {mb['pct']}%</span>
            </div>
            <div style="background:#ffe0b2; border-radius:12px; height:20px; overflow:hidden;">
              <div style="width:{mb['pct']}%; height:100%; background:{bar_color}; border-radius:12px;"></div>
            </div>
          </div>
        """

    # ====== 健康改进模拟器 ======
    simulations_html = ""
    for sim in simulations:
        simulations_html += f"""
          <div style="background:linear-gradient(135deg,#fff3e0,#ffe0b2); border-radius:16px; padding:20px; margin:16px 0; border-left:4px solid #ff5722;">
            <div style="display:flex; align-items:center; gap:12px; margin-bottom:10px;">
              <span style="font-size:2em;">{sim['icon']}</span>
              <span style="font-weight:bold; font-size:1.1em; color:#d84315;">{sim['action']}</span>
            </div>
            <div style="color:#5d4037; margin-bottom:6px;">💡 {sim['impact']}</div>
            <div style="color:#666; font-size:0.9em;">
              <span style="color:#ff9800;">📈 {sim['score_hint']}</span>
              <span style="color:#4caf50; margin-left:12px;">🎯 {sim['grade_hint']}</span>
            </div>
          </div>
        """

    # ====== 门店排行 ======
    top_stores = store_analysis.get("top_stores", [])
    if top_stores:
        top_stores_html = '<table style="margin-top:10px;"><thead><tr><th>排名</th><th>门店</th><th>单数</th><th>消费</th><th>常去时段</th></tr></thead><tbody>'
        for i, s in enumerate(top_stores):
            medal = ["🥇","🥈","🥉"][i] if i < 3 else f"#{i+1}"
            top_stores_html += f"""
              <tr>
                <td style="width:60px;">{medal}</td>
                <td>{s['name']}</td>
                <td>{s['count']} 单</td>
                <td>¥{s['amount']}</td>
                <td>{s['typical_period']} ({s['avg_hour_text']})</td>
              </tr>
            """
        top_stores_html += "</tbody></table>"
    else:
        top_stores_html = "<p>暂无门店数据</p>"

    # ====== 7×24 热力图 ======
    heatmap_data = store_analysis.get("heatmap", [])
    golden_time = store_analysis.get("golden_time", "")
    if heatmap_data:
        heatmap_html = '<div style="overflow-x:auto;"><table style="border-collapse:collapse; font-size:0.75em; min-width:700px;">'
        heatmap_html += '<tr><th style="padding:4px 2px; background:#fff3e0;"></th>'
        for h in range(24):
            heatmap_html += f'<th style="padding:4px 2px; background:#fff3e0; color:#666; font-weight:normal;">{h}</th>'
        heatmap_html += '</tr>'
        for row in heatmap_data:
            heatmap_html += f'<tr><td style="padding:2px 8px; font-weight:600; background:#fff3e0;">{row["day"]}</td>'
            for cell in row["cells"]:
                cnt = cell["count"]
                pct = cell["pct"]
                if cnt == 0:
                    bg = "#fff8e1"
                elif pct < 20:
                    bg = "#ffe0b2"
                elif pct < 50:
                    bg = "#ffb74d"
                elif pct < 80:
                    bg = "#ff7043"
                else:
                    bg = "#d84315"
                heatmap_html += f'<td title="{cnt} 单" style="width:20px; height:20px; background:{bg}; border-radius:3px; text-align:center; font-size:0.6em; color:white; padding:0;">{cnt if cnt > 0 else ""}</td>'
            heatmap_html += '</tr>'
        heatmap_html += '</table></div>'
        heatmap_html += '<div style="margin-top:12px; display:flex; align-items:center; gap:8px; font-size:0.8em; color:#666;">'
        heatmap_html += '<span>少</span>'
        for c in ["#fff8e1", "#ffe0b2", "#ffb74d", "#ff7043", "#d84315"]:
            heatmap_html += f'<div style="width:18px; height:18px; background:{c}; border-radius:3px;"></div>'
        heatmap_html += '<span>多</span></div>'
    else:
        heatmap_html = "<p>暂无足够数据生成热力图</p>"

    # 健康评分行
    health_rows = ""
    scores = health.get("scores", {})
    details = health.get("details", {})
    for dim, score in scores.items():
        bar_color = "#4caf50" if score >= 85 else ("#ff9800" if score >= 70 else "#f44336")
        health_rows += f"""
          <tr>
            <td>{dim}</td>
            <td>
              <div style="display:flex; align-items:center; gap:10px;">
                <strong>{score}</strong>
                <div class="progress-bar" style="flex:1;">
                  <div class="progress-fill" style="width:{score}%; background:{bar_color};"></div>
                </div>
              </div>
            </td>
            <td>{details.get(dim, "")}</td>
          </tr>
        """
    
    # 人设
    main_p = persona.get("main", {})
    persona_emoji = main_p.get("emoji", "🍔")
    persona_name = main_p.get("name", "麦门食客")
    persona_desc = main_p.get("desc", "")
    
    sub_personas = persona.get("sub", [])
    if sub_personas:
        sub_personas_html = "<div style='margin-top:20px; text-align:center; color:#888;'>次要人设：" + \
            "、".join(f"{s['emoji']} {s['name']}" for s in sub_personas) + "</div>"
    else:
        sub_personas_html = ""
    
    # 人设拆解
    breakdown_html = ""
    for key, val in persona.get("breakdown", {}).items():
        breakdown_html += f"""
          <div style="margin:12px 0;">
            <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
              <span>{key}</span><span>{val}</span>
            </div>
            <div class="progress-bar"><div class="progress-fill" style="width:{val.rstrip('%')}%; background:linear-gradient(90deg,#ff9800,#f44336);"></div></div>
          </div>
        """
    
    # 餐段热量
    meal_kcal_rows = ""
    for mk in kcal_stats.get("meal_period_breakdown", []):
        status = "✅ 合理" if mk.get("within_range") else "⚠️ 注意"
        meal_kcal_rows += f"""
          <tr>
            <td>{mk['period']}</td>
            <td>{mk['count']}</td>
            <td>{mk['avg_kcal']}</td>
            <td>{mk['recommended_range']} kcal</td>
            <td>{status}</td>
          </tr>
        """
    
    # 餐段分布
    meal_distribution_html = ""
    max_count = max((m["count"] for m in meal_dist), default=1)
    for md in meal_dist:
        pct = md["count"] / max_count * 100
        meal_distribution_html += f"""
          <div style="display:flex; align-items:center; gap:15px; margin:12px 0;">
            <div style="width:80px; font-weight:600;">{md['period']}</div>
            <div style="flex:1; background:#ffe0b2; border-radius:12px; height:28px; overflow:hidden;">
              <div style="width:{pct}%; height:100%; background:linear-gradient(90deg,#ff9800,#f44336); border-radius:12px; display:flex; align-items:center; justify-content:flex-end; padding-right:10px; color:white; font-weight:bold; font-size:0.9em;">{md['count']}</div>
            </div>
          </div>
        """
    
    # 月度柱状图
    if monthly:
        max_orders = max(m["orders"] for m in monthly) or 1
        monthly_chart = '<div class="month-bar">'
        for m in monthly:
            h = m["orders"] / max_orders * 180 + 10
            monthly_chart += f'''
              <div class="month-bar-item">
                <div style="font-size:0.7em; color:#ff5722; font-weight:bold;">{m["orders"]}</div>
                <div class="month-bar-fill" style="height:{h}px;"></div>
                <div class="month-bar-label">{m["month"][5:]}</div>
              </div>'''
        monthly_chart += "</div>"
    else:
        monthly_chart = "<p>暂无月度数据</p>"
    
    # 月度表格
    monthly_rows = ""
    for m in monthly:
        monthly_rows += f"""
          <tr>
            <td>{m['month']}</td>
            <td>{m['orders']}</td>
            <td>{m['total_kcal']}</td>
            <td>¥{m['total_amount']}</td>
            <td>{m['avg_kcal_per_order']}</td>
          </tr>
        """
    
    # Top 商品
    top_products_rows = ""
    for tp in top_products:
        rank = tp["rank"]
        medal = ["🥇","🥈","🥉"][rank-1] if rank <= 3 else f"#{rank}"
        top_products_rows += f"""
          <tr>
            <td style="width:60px;">{medal}</td>
            <td>{tp['name']}</td>
            <td>{tp['quantity']} 次</td>
          </tr>
        """
    
    # 年度高光
    highlights_html = ""
    for kw in keywords:
        highlights_html += f"<li>{kw}</li>\n"
    
    # 订单明细
    orders_rows = ""
    for o in orders[:100]:  # 最多展示 100 单
        items_str = ", ".join(f"{it['name']}×{it['qty']}" for it in o.get("items", [])[:3])
        if len(o.get("items", [])) > 3:
            items_str += "..."
        orders_rows += f"""
          <tr>
            <td style="white-space:nowrap;">{o['time']}</td>
            <td>{o['meal_period']}</td>
            <td>{o['store']}</td>
            <td>¥{o['amount']}</td>
            <td>{o['kcal']}</td>
            <td style="max-width:300px; overflow:hidden; text-overflow:ellipsis;">{items_str}</td>
          </tr>
        """
    
    # 填充模板
    html = HTML_TEMPLATE_STR
    html = html.replace("__total_orders__", str(summary.get("total_orders", 0)))
    html = html.replace("__total_amount__", str(summary.get("total_amount", 0)))
    html = html.replace("__avg_orders_per_week__", str(summary.get("avg_orders_per_week", 0)))
    html = html.replace("__nutrition_match_rate__", str(summary.get("nutrition_match_rate", 0)))
    html = html.replace("__match_breakdown_html__", match_breakdown_html)
    html = html.replace("__health_overall__", str(health.get("overall_score", "--")))
    html = html.replace("__health_grade__", str(health.get("grade", "")))
    html = html.replace("__health_rows__", health_rows)
    html = html.replace("__persona_emoji__", persona_emoji)
    html = html.replace("__persona_name__", persona_name)
    html = html.replace("__persona_desc__", persona_desc)
    html = html.replace("__sub_personas_html__", sub_personas_html)
    html = html.replace("__breakdown_html__", breakdown_html)
    html = html.replace("__avg_kcal_per_order__", str(kcal_stats.get("avg_per_order", 0)))
    html = html.replace("__max_kcal_order__", str(kcal_stats.get("max_single_order", 0)))
    html = html.replace("__min_kcal_order__", str(kcal_stats.get("min_single_order", 0)))
    html = html.replace("__meal_kcal_rows__", meal_kcal_rows)
    html = html.replace("__meal_distribution_html__", meal_distribution_html)
    html = html.replace("__monthly_chart__", monthly_chart)
    html = html.replace("__monthly_rows__", monthly_rows)
    html = html.replace("__top_products_rows__", top_products_rows)
    html = html.replace("__highlights_html__", highlights_html)
    html = html.replace("__top_stores_html__", top_stores_html)
    html = html.replace("__simulations_html__", simulations_html)
    html = html.replace("__heatmap_html__", heatmap_html)
    html = html.replace("__golden_time__", golden_time)
    
    html = html.replace("__n_energy_kcal__", str(nutrition_total.get("energy_kcal", 0)))
    html = html.replace("__n_protein__", str(nutrition_total.get("protein", 0)))
    html = html.replace("__n_fat__", str(nutrition_total.get("fat", 0)))
    html = html.replace("__n_carb__", str(nutrition_total.get("carbohydrate", 0)))
    html = html.replace("__n_sodium__", str(nutrition_total.get("sodium", 0)))
    html = html.replace("__n_calcium__", str(nutrition_total.get("calcium", 0)))
    html = html.replace("__orders_rows__", orders_rows)
    html = html.replace("__generated_at__", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    
    return output_path


def _build_profile(args):
    """从 args 构建 BMR profile dict（缺字段就返回 None）"""
    if args.gender and args.weight and args.height:
        return {
            "gender": args.gender,
            "weight": args.weight,
            "height": args.height,
            "age": args.age,
            "activity": args.activity,
        }
    return None


def main():
    parser = argparse.ArgumentParser(description="麦门年度体检报告生成器")
    parser.add_argument("--token", default=os.environ.get("MCD_TOKEN", ""), help="麦当劳 MCP Token")
    parser.add_argument("--output", default="output/annual_report.html", help="输出 HTML 路径")
    parser.add_argument("--save-json", action="store_true", help="同时保存 JSON 数据")
    parser.add_argument("--json-path", default="output/report_data.json", help="JSON 输出路径")
    parser.add_argument("--use-sample", action="store_true", help="用示例数据生成报告（无需 Token）")
    parser.add_argument("--gender", choices=["male", "female"], help="性别（BMR 计算）")
    parser.add_argument("--weight", type=float, help="体重 kg（BMR 计算）")
    parser.add_argument("--height", type=float, help="身高 cm（BMR 计算）")
    parser.add_argument("--age", type=int, default=28, help="年龄（BMR 计算，默认 28）")
    parser.add_argument("--activity", default="sedentary",
                        choices=["sedentary", "light", "moderate", "active", "very_active"],
                        help="活动水平（默认 sedentary 久坐）")
    parser.add_argument("--no-card", action="store_true", help="不生成人格卡 PNG")
    
    args = parser.parse_args()
    profile = _build_profile(args)
    
    if args.use_sample:
        print("📦 使用示例数据生成报告...")
        sample_orders = _sample_orders()
        sample_nutrition = _sample_nutrition()
        analyzer = AnnualAnalyzer(sample_orders, sample_nutrition, profile)
        data = analyzer.analyze()
    else:
        if not args.token:
            print("❌ 需要 MCP Token。通过 --token 或 MCD_TOKEN 环境变量提供，或 --use-sample")
            sys.exit(1)
        
        print(f"🔌 连接麦当劳 MCP Server...")
        client = McDormandMCPClient(args.token)
        
        init_resp = client.initialize()
        print(f"✅ 已连接: {init_resp.get('result', {}).get('serverInfo', {})}")
        
        print("📋 拉取历史订单...")
        orders = client.get_orders()
        print(f"   获取到 {len(orders)} 笔订单")
        
        print("🥗 拉取营养数据...")
        nutrition = client.get_nutrition()
        print(f"   获取到 {len(nutrition)} 种食物营养")
        
        if not orders:
            print("⚠️ 没有历史订单数据，使用示例数据演示...")
            orders = _sample_orders()
        
        analyzer = AnnualAnalyzer(orders, nutrition, profile)
        data = analyzer.analyze()
    
    print("📊 分析完成，生成报告...")
    
    # 确保输出目录存在
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    
    output_path = render_report(data, args.output)
    print(f"✅ HTML 报告已生成: {output_path}")
    
    if args.save_json:
        os.makedirs(os.path.dirname(args.json_path) or ".", exist_ok=True)
        with open(args.json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"✅ JSON 数据已保存: {args.json_path}")
    
    # 生成人格卡 PNG
    if not args.no_card:
        try:
            from personality_card import generate_persona_card
            card_path = "output/persona_card.png"
            card_output = generate_persona_card(data, card_path)
            print(f"🖼️  人格卡 PNG 已生成: {card_output}")
        except ImportError:
            print("⚠️  Pillow 未安装，跳过人格卡生成。pip install Pillow")
        except Exception as e:
            print(f"⚠️  人格卡生成失败: {e}")
    
    # 打印简要预览
    summary = data.get("summary", {})
    health = data.get("health_assessment", {})
    persona = data.get("persona", {}).get("main", {})
    print("\n" + "=" * 50)
    print("🍔 麦门年度体检报告 · 预览")
    print("=" * 50)
    print(f"  订单数: {summary.get('total_orders', 0)}")
    print(f"  总消费: ¥{summary.get('total_amount', 0)}")
    print(f"  健康评分: {health.get('overall_score', '--')} ({health.get('grade', '')})")
    print(f"  麦门人设: {persona.get('emoji', '')} {persona.get('name', '')}")
    print("=" * 50)
    
    return output_path


# ====== 示例数据（无 Token 时演示用） ======
def _sample_orders():
    import random
    from datetime import datetime, timedelta
    
    random.seed(42)
    orders = []
    
    store_names = ["麦当劳杭州文三路店", "麦当劳杭州西湖银泰店", "麦当劳杭州庆春路店"]
    
    # 模拟过去一年里 ~30 笔订单
    base_date = datetime.now() - timedelta(days=365)
    
    for i in range(30):
        dt = base_date + timedelta(
            days=random.randint(0, 364),
            hours=random.randint(6, 23),
            minutes=random.randint(0, 59)
        )
        
        # 随机组合商品
        products = []
        products.append({
            "productCode": f"P{random.randint(1000,9999)}",
            "productName": random.choice(["巨无霸", "板烧鸡腿堡", "麦香鱼", "麦辣鸡腿汉堡", "双层吉士汉堡"]),
            "quantity": 1
        })
        if random.random() > 0.3:
            products.append({
                "productCode": f"P{random.randint(1000,9999)}",
                "productName": random.choice(["中薯条", "麦乐鸡5块", "麦辣鸡翅-2块"]),
                "quantity": 1
            })
        if random.random() > 0.2:
            products.append({
                "productCode": f"P{random.randint(1000,9999)}",
                "productName": random.choice(["可乐中杯", "雪碧中杯", "咖啡中杯"]),
                "quantity": random.choice([1, 2])
            })
        if random.random() > 0.5:
            products.append({
                "productCode": f"P{random.randint(1000,9999)}",
                "productName": random.choice(["圆筒冰淇淋", "草莓新地", "菠萝派"]),
                "quantity": 1
            })
        
        amount = round(random.uniform(25, 80), 1)
        
        orders.append({
            "orderId": f"SAMPLE-{dt.strftime('%Y%m%d')}-{i}",
            "orderType": "1",
            "createTime": dt.strftime("%Y-%m-%d %H:%M:%S"),
            "beType": "1",
            "beCode": "",
            "storeCode": "1400471",
            "storeName": random.choice(store_names),
            "orderStatus": "订单已完成",
            "orderProductList": products,
            "realTotalAmount": str(amount)
        })
    
    return orders


def _sample_nutrition():
    """精简版营养数据（够用就行）"""
    foods = [
        ("巨无霸", 513, 27, 26, 42, 961, 171),
        ("板烧鸡腿堡", 391, 23, 17, 35, 1041, 93),
        ("麦香鱼", 325, 16, 13, 35, 556, 99),
        ("麦辣鸡腿汉堡", 485, 24, 24, 42, 1208, 154),
        ("双层吉士汉堡", 429, 27, 22, 31, 1017, 232),
        ("中薯条", 289, 4, 12, 38, 165, 18),
        ("大薯条", 379, 6, 16, 50, 216, 23),
        ("麦乐鸡5块", 213, 12, 12, 13, 422, 9),
        ("麦辣鸡翅-2块", 224, 13, 15, 9, 537, 13),
        ("可乐中杯", 147, 0, 0, 36, 0, 10),
        ("雪碧中杯", 105, 0, 0, 26, 29, 0),
        ("圆筒冰淇淋", 93, 2, 3, 14, 36, 77),
        ("草莓新地", 245, 4, 6, 43, 84, 158),
        ("菠萝派", 221, 2, 11, 27, 147, 5),
        ("咖啡中杯", 13, 1, 0, 2, 0, 7),
    ]
    return [
        {"name": n, "energy_kcal": e, "protein": p, "fat": f_, "carbohydrate": c, "sodium": s, "calcium": ca,
         "energy_kj": e * 4.184, "description": ""}
        for (n, e, p, f_, c, s, ca) in foods
    ]


if __name__ == "__main__":
    main()
