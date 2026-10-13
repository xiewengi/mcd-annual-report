"""
社交媒体素材批量生成器 v2
从 output/report_data.json 读真实数据，生成 6 张 1080×1920 竖屏素材图。
核心修复：draw_emoji 正确 paste 到 canvas Image，不再访问私有属性。
"""
import json
import os
import sys
import math

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from personality_card import generate_persona_card, _find_font, _gradient_background, _draw_text

W, H = 1080, 1920
OUT = "assets/social"

BG_TOP = (255, 193, 7)
BG_BOT = (244, 67, 54)
PRIMARY = (216, 67, 21)
SECONDARY = (255, 152, 0)
TEXT_DARK = (61, 61, 61)
TEXT_MID = (117, 117, 117)
TEXT_LIGHT = (255, 255, 255)
CARD_BG = (255, 255, 255)

EMOJI_FONT_PATH = "/System/Library/Fonts/Apple Color Emoji.ttc"


# ============================================================
# 核心：正确的 emoji 渲染
# Apple Color Emoji.ttc 仅 160px 可加载，渲染后 paste 到目标 canvas
# ============================================================
def make_canvas(w, h):
    """创建 RGBA 渐变画布"""
    bg = _gradient_background(w, h)
    return bg.convert("RGBA")


def rounded_rect(draw, xy, radius, fill):
    draw.rounded_rectangle(xy, radius=radius, fill=fill)


def draw_emoji(canvas, emoji, cx, cy, size=80):
    """在 canvas (Image) 上画彩色 emoji。
    Apple Color Emoji 仅 160px 能渲染彩色，先渲染再缩放 paste。
    """
    if not os.path.exists(EMOJI_FONT_PATH):
        # fallback：用系统默认字体渲染单色
        draw = ImageDraw.Draw(canvas)
        font = _find_font(size)
        draw.text((cx, cy), emoji, font=font, fill=TEXT_LIGHT, anchor="mm")
        return

    # 1. 在 160×160 小画布上用 Apple Color Emoji 渲染彩色
    src = Image.new("RGBA", (200, 200), (0, 0, 0, 0))
    src_draw = ImageDraw.Draw(src)
    try:
        font = ImageFont.truetype(EMOJI_FONT_PATH, 160)
        src_draw.text((100, 100), emoji, font=font, anchor="mm", embedded_color=True)
    except Exception:
        # 如果彩色渲染失败，fallback 单色
        font = _find_font(size)
        draw = ImageDraw.Draw(canvas)
        draw.text((cx, cy), emoji, font=font, fill=TEXT_LIGHT, anchor="mm")
        return

    # 2. 缩放 patch 到目标 size
    target = max(int(size * 1.4), 40)
    scaled = src.resize((target, target), Image.LANCZOS)

    # 3. paste 到目标 canvas（用 scaled 自己当 mask 实现透明）
    paste_x = int(cx - target // 2)
    paste_y = int(cy - target // 2)
    canvas.paste(scaled, (paste_x, paste_y), scaled)


def load_report():
    json_path = os.path.join("output", "report_data.json")
    if os.path.exists(json_path):
        with open(json_path) as f:
            return json.load(f)
    print("⚠️  report_data.json 不存在")
    sys.exit(1)


def save(img, path):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    img.save(path, "PNG", optimize=True)
    print(f"  ✅ {path}")


# ============================================================
# 图 1：封面大字
# ============================================================
def make_cover(d):
    canvas = make_canvas(W, H)
    draw = ImageDraw.Draw(canvas)

    # 顶部 🍔 emoji（加半透明圆衬底）
    circle = Image.new("RGBA", (280, 280), (0, 0, 0, 0))
    ImageDraw.Draw(circle).ellipse([0, 0, 280, 280], fill=(255, 255, 255, 35))
    canvas.paste(circle, (W // 2 - 140, 180), circle)
    draw_emoji(canvas, "🍔", W // 2, 320, size=120)

    # 主标题
    title_font = _find_font(80, bold=True)
    sub_font = _find_font(38)
    _draw_text(draw, "我帮麦当劳", W // 2, 470, title_font, TEXT_LIGHT, anchor="mt")
    _draw_text(draw, "做了个年度体检报告", W // 2, 570, title_font, TEXT_LIGHT, anchor="mt")
    _draw_text(draw, "基于麦当劳官方 MCP API · 纯 Python · 零服务器", W // 2, 690, sub_font, (255, 255, 255, 220), anchor="mt")

    # 3 个亮点卡
    features = [
        ("📊", "10 笔订单", "¥119.3", "佛系食客"),
        ("💪", "健康评分 81", "钠摄入最弱", "BMR 个人化"),
        ("🗓️", "7×24 热力图", "周五 12:00", "黄金麦门时间"),
    ]

    card_w = 310
    gap = 28
    total_w = len(features) * card_w + (len(features) - 1) * gap
    start_x = (W - total_w) // 2
    card_cy = 960

    for i, (emoji, t1, t2, t3) in enumerate(features):
        cx = start_x + i * (card_w + gap) + card_w // 2
        rounded_rect(draw, [cx - card_w // 2, card_cy - 160, cx + card_w // 2, card_cy + 160], 28, (255, 255, 255, 240))
        draw_emoji(canvas, emoji, cx, card_cy - 85, size=72)
        small_font = _find_font(28)
        _draw_text(draw, t1, cx, card_cy - 15, small_font, TEXT_DARK, anchor="mm")
        _draw_text(draw, t2, cx, card_cy + 20, small_font, SECONDARY, anchor="mm")
        _draw_text(draw, t3, cx, card_cy + 55, small_font, TEXT_MID, anchor="mm")

    # CTA 白卡
    cta_y = 1520
    rounded_rect(draw, [120, cta_y - 75, W - 120, cta_y + 145], 28, (255, 255, 255, 240))
    cta_font = _find_font(50, bold=True)
    _draw_text(draw, "你的麦门年度报告", W // 2, cta_y - 25, cta_font, PRIMARY, anchor="mt")
    _draw_text(draw, "跑一跑，看你一年吃了多少可乐", W // 2, cta_y + 45, sub_font, TEXT_MID, anchor="mt")

    # 水印
    wm_font = _find_font(28)
    _draw_text(draw, "2026 麦当劳程序员创意开发大赛参赛作品", W // 2, H - 80, wm_font, (255, 255, 255, 200), anchor="mt")

    return canvas.convert("RGB")


# ============================================================
# 图 2：关键数字页
# ============================================================
def make_stats(d):
    summary = d.get("summary", {})
    health = d.get("health_assessment", {})
    persona = d.get("persona", {}).get("main", {})

    canvas = make_canvas(W, H)
    draw = ImageDraw.Draw(canvas)

    title_font = _find_font(62, bold=True)
    sub_font = _find_font(34)
    big_num_font = _find_font(170, bold=True)

    # 顶部小 emoji（汉堡 🍔）
    draw_emoji(canvas, "🍔", 90, 95, size=56)

    _draw_text(draw, "这一年我吃了多少麦当劳？", W // 2, 90, title_font, TEXT_LIGHT, anchor="mt")
    span = summary.get("days_span", 209)
    _draw_text(draw, f"真实数据 · {summary.get('total_orders', 10)} 笔订单 · {span} 天", W // 2, 180, sub_font, (255, 255, 255, 220), anchor="mt")

    # 4 卡 2×2
    stats_meta = [
        ("📋", str(summary.get("total_orders", 0)), "年度总单数", "佛系食客" if "佛系" in persona.get("name", "") else ""),
        ("💰", f"¥{summary.get('total_amount', 0)}", "总消费", ""),
        ("❤️", str(health.get("overall_score", "--")), "健康评分", health.get("grade", "")[:10].replace("⭐", "").strip()),
        ("🍀", persona.get("emoji", "") + " " + persona.get("name", "--"), "麦门人设", ""),
    ]

    card_w, card_h = 470, 370
    gap = 30
    grid_w = card_w * 2 + gap
    start_x = (W - grid_w) // 2
    start_y = 270

    for idx, (emoji, num, label, sub) in enumerate(stats_meta):
        row, col = divmod(idx, 2)
        cx = start_x + col * (card_w + gap)
        cy = start_y + row * (card_h + gap)
        rounded_rect(draw, [cx, cy, cx + card_w, cy + card_h], 28, (255, 255, 255, 245))

        draw_emoji(canvas, emoji, cx + 80, cy + 80, size=64)

        if idx == 3:
            # 人设卡：emoji + 名字
            p_emoji = persona.get("emoji", "")
            p_name = persona.get("name", "--")
            if p_emoji:
                draw_emoji(canvas, p_emoji, cx + 80, cy + 200, size=120)
            pfont = _find_font(56, bold=True)
            _draw_text(draw, p_name, cx + 210, cy + 160, pfont, PRIMARY, anchor="lt")
            bd = d.get("persona", {}).get("breakdown", {})
            bd_text = " · ".join([f"{k}:{v}" for k, v in list(bd.items())[:3]])
            if bd_text:
                bdfont = _find_font(26)
                _draw_text(draw, bd_text[:38], cx + 80, cy + 270, bdfont, TEXT_DARK, anchor="lt")
        else:
            # 数字
            nf = big_num_font if len(num) <= 6 else _find_font(110, bold=True)
            _draw_text(draw, num, cx + 120, cy + 50, nf, PRIMARY, anchor="mt")

        # label + sub
        label_font = _find_font(32)
        _draw_text(draw, label, cx + 80, cy + 280, label_font, TEXT_MID, anchor="lt")
        if sub:
            _draw_text(draw, sub, cx + 80, cy + 320, _find_font(26), TEXT_DARK, anchor="lt")

    # Top 3
    top_y = start_y + 2 * (card_h + gap) + 10
    rounded_rect(draw, [80, top_y, W - 80, top_y + 300], 28, (255, 255, 255, 245))
    top_font = _find_font(44, bold=True)
    _draw_text(draw, "你最常点的 Top 3", 130, top_y + 30, top_font, PRIMARY, anchor="lt")
    draw_emoji(canvas, "⭐", 95, top_y + 52, size=48)

    top_products = d.get("top_products", [])[:3]
    medals = ["🥇", "🥈", "🥉"]
    for i, tp in enumerate(top_products):
        row_y = top_y + 120 + i * 58
        draw_emoji(canvas, medals[i], 130, row_y + 25, size=46)
        _draw_text(draw, tp.get("name", "--"), 205, row_y + 15, _find_font(36), TEXT_DARK, anchor="lt")
        _draw_text(draw, f"× {tp.get('quantity', 0)}", W - 140, row_y + 15, _find_font(36, bold=True), PRIMARY, anchor="rt")

    # 底部 CTA
    cta_font = _find_font(42, bold=True)
    _draw_text(draw, "想知道你这一年吃了多少可乐？跑一跑！", W // 2, H - 160, cta_font, (255, 255, 255, 230), anchor="mt")
    _draw_text(draw, "GitHub: xiewengi/mcd-annual-report", W // 2, H - 110, _find_font(30), (255, 255, 255, 180), anchor="mt")

    return canvas.convert("RGB")


# ============================================================
# 图 3：热力图 + 黄金时间
# ============================================================
def make_heatmap(d):
    sa = d.get("store_analysis", {})
    canvas = make_canvas(W, H)
    draw = ImageDraw.Draw(canvas)

    title_font = _find_font(56, bold=True)
    sub_font = _find_font(32)

    draw_emoji(canvas, "🗓️", W // 2 - 180, 130, size=56)
    _draw_text(draw, "7×24 点餐热力图", W // 2, 120, title_font, TEXT_LIGHT, anchor="mt")
    _draw_text(draw, "每格=该天某小时的下单次数", W // 2, 190, sub_font, (255, 255, 255, 220), anchor="mt")

    # 黄金时间大卡
    golden_y = 230
    rounded_rect(draw, [80, golden_y, W - 80, golden_y + 200], 28, (255, 255, 255, 245))
    golden_big = _find_font(72, bold=True)
    draw_emoji(canvas, "🕐", W // 2 - 200, golden_y + 100, size=64)
    _draw_text(draw, "黄金麦门时间", W // 2 + 30, golden_y + 30, sub_font, TEXT_MID, anchor="mt")
    _draw_text(draw, sa.get("golden_time", "周五 18:00"), W // 2 + 30, golden_y + 78, golden_big, PRIMARY, anchor="mt")
    _draw_text(draw, sa.get("golden_time_desc", ""), W // 2 + 30, golden_y + 160, _find_font(28), TEXT_DARK, anchor="mt")

    # 热力图网格
    hm_y = golden_y + 230
    hm_h = 880
    hm_w = W - 200
    cell_w = hm_w / 24
    cell_h = hm_h / 7
    days = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    hm_data = sa.get("heatmap", [])
    if not hm_data:
        hm_data = [{"day": d, "cells": [{"hour": h, "count": 0, "pct": 0} for h in range(24)]} for d in days]

    max_count = max((c["count"] for row in hm_data for c in row["cells"]), default=1)

    for row_idx, row in enumerate(hm_data):
        _draw_text(draw, days[row_idx], 75, hm_y + row_idx * cell_h + cell_h / 2, _find_font(26), (255, 255, 255, 230), anchor="mm")
        for cell in row["cells"]:
            cnt = cell["count"]
            ratio = cell["pct"] / 100
            if cnt == 0:
                color = (255, 248, 225)
            elif ratio < 0.2:
                color = (255, 224, 178)
            elif ratio < 0.5:
                color = (255, 183, 77)
            elif ratio < 0.8:
                color = (255, 112, 67)
            else:
                color = (216, 67, 21)
            cx = 100 + cell["hour"] * cell_w + 2
            cy = hm_y + row_idx * cell_h + 2
            cw = cell_w - 4
            ch = cell_h - 4
            rounded_rect(draw, [cx, cy, cx + cw, cy + ch], 3, color)

    # 图例
    legend_y = hm_y + hm_h + 18
    _draw_text(draw, "少", 100, legend_y + 14, _find_font(28), (255, 255, 255, 220), anchor="mt")
    for i, c in enumerate([(255, 248, 225), (255, 224, 178), (255, 183, 77), (255, 112, 67), (216, 67, 21)]):
        rounded_rect(draw, [160 + i * 80, legend_y + 10, 210 + i * 80, legend_y + 52], 8, c)
    _draw_text(draw, "多", 600, legend_y + 14, _find_font(28), (255, 255, 255, 220), anchor="mt")

    # 门店 Top
    store_font = _find_font(44, bold=True)
    store_y = legend_y + 70
    draw_emoji(canvas, "🏪", W // 2 - 220, store_y + 20, size=52)
    _draw_text(draw, "你最常去的门店", W // 2, store_y, title_font, TEXT_LIGHT, anchor="mt")

    top_stores = sa.get("top_stores", [])[:3]
    row_font = _find_font(30)
    for i, st in enumerate(top_stores):
        line_y = store_y + 75 + i * 52
        draw_emoji(canvas, ["🥇", "🥈", "🥉"][i], 105, line_y + 18, size=38)
        _draw_text(draw, st.get("name", "--"), 170, line_y + 18, row_font, TEXT_LIGHT, anchor="lm")
        _draw_text(draw, f'{st.get("count", 0)} 单 ¥{st.get("amount", 0)}', W - 105, line_y + 18, row_font, (255, 255, 255, 230), anchor="rm")

    # CTA
    _draw_text(draw, "看看你自己的 7×24 麦门时间表 🧐", W // 2, H - 95, _find_font(38, bold=True), (255, 255, 255, 230), anchor="mt")

    return canvas.convert("RGB")


# ============================================================
# 图 4：健康改进模拟器
# ============================================================
def make_simulator(d):
    health = d.get("health_assessment", {})
    sims = d.get("health_simulations", [])
    scores = health.get("scores", {})

    canvas = make_canvas(W, H)
    draw = ImageDraw.Draw(canvas)

    title_font = _find_font(60, bold=True)
    sub_font = _find_font(34)

    draw_emoji(canvas, "💪", W // 2 - 200, 130, size=58)
    _draw_text(draw, "健康改进模拟器", W // 2, 120, title_font, TEXT_LIGHT, anchor="mt")
    _draw_text(draw, "基于你这一年的真实点餐数据", W // 2, 190, sub_font, (255, 255, 255, 220), anchor="mt")

    # 健康总览卡
    ov_y = 240
    rounded_rect(draw, [80, ov_y, W - 80, ov_y + 280], 28, (255, 255, 255, 245))
    _draw_text(draw, "健康分", 120, ov_y + 30, sub_font, TEXT_MID, anchor="lt")
    _draw_text(draw, str(health.get("overall_score", "--")), 120, ov_y + 65, _find_font(130, bold=True), PRIMARY, anchor="lt")
    _draw_text(draw, health.get("grade", "").replace("⭐", "").strip(), 120, ov_y + 215, _find_font(36, bold=True), SECONDARY, anchor="lt")

    # 4 个维度进度条（垂直排列，不溢出）
    dims = [("热量", 560), ("钠摄入", 620), ("蛋白质", 680), ("脂肪", 740)]
    for dim, bar_y in dims:
        sc = scores.get(dim, 0)
        # 背景条
        rounded_rect(draw, [350, bar_y, 720, bar_y + 26], 13, (255, 224, 178))
        # 填充
        ratio = min(max(sc / 100, 0), 1.0)
        color = (76, 175, 80) if sc >= 80 else ((255, 183, 77) if sc >= 60 else (255, 112, 67))
        rounded_rect(draw, [350, bar_y, 350 + int(370 * ratio), bar_y + 26], 13, color)
        # 标签
        _draw_text(draw, f"{dim}  {sc}", 120, bar_y + 13, _find_font(28), TEXT_DARK, anchor="lm")

    # 模拟器卡片（垂直排 4 张，每张 340 高）
    card_y0 = 820  # 进度条区 560~780 + 40 间距
    # 垂直居中：根据实际数量调整起始 y
    card_h = 340
    n = min(len(sims), 4)
    total_h = n * card_h + (n - 1) * 20
    card_y0 = max(card_y0, (H - total_h) // 2 + 150)  # 至少在健康卡下面，且尽量居中
    for i, sim in enumerate(sims[:4]):
        cy = card_y0 + i * 360
        rounded_rect(draw, [80, cy, W - 80, cy + 340], 24, (255, 255, 255, 245))
        # emoji 图标
        draw_emoji(canvas, sim.get("icon", "💡"), 145, cy + 70, size=64)
        # action
        act = sim.get("action", "")
        _draw_text(draw, act[:38], 225, cy + 40, _find_font(36, bold=True), PRIMARY, anchor="lt")
        if len(act) > 38:
            _draw_text(draw, act[38:76], 225, cy + 80, _find_font(36, bold=True), PRIMARY, anchor="lt")
        # impact（分两行）
        imp = sim.get("impact", "")
        imp_font = _find_font(28)
        _draw_text(draw, imp[:48], 120, cy + 150, imp_font, TEXT_DARK, anchor="lt")
        _draw_text(draw, imp[48:96], 120, cy + 188, imp_font, TEXT_DARK, anchor="lt")
        # score_hint / grade_hint
        hint_font = _find_font(24)
        _draw_text(draw, f"📈 {sim.get('score_hint', '')[:36]}", 120, cy + 250, hint_font, SECONDARY, anchor="lt")
        _draw_text(draw, f"🎯 {sim.get('grade_hint', '')[:36]}", 120, cy + 282, hint_font, PRIMARY, anchor="lt")

    return canvas.convert("RGB")


# ============================================================
# 图 5：行动号召 CTA
# ============================================================
def make_cta(d):
    canvas = make_canvas(W, H)
    draw = ImageDraw.Draw(canvas)

    # 大 🎁 emoji（加圆衬底）
    circle = Image.new("RGBA", (300, 300), (0, 0, 0, 0))
    ImageDraw.Draw(circle).ellipse([0, 0, 300, 300], fill=(255, 255, 255, 35))
    canvas.paste(circle, (W // 2 - 150, 240), circle)
    draw_emoji(canvas, "🎁", W // 2, 390, size=120)

    title_font = _find_font(72, bold=True)
    sub_font = _find_font(36)
    step_font = _find_font(30)

    _draw_text(draw, "想看看你自己的", W // 2, 560, title_font, TEXT_LIGHT, anchor="mt")
    _draw_text(draw, "麦门年度体检报告？", W // 2, 650, title_font, TEXT_LIGHT, anchor="mt")

    # 3 步
    cta_y = 780
    rounded_rect(draw, [80, cta_y, W - 80, cta_y + 600], 32, (255, 255, 255, 245))

    steps = [
        ("申请 MCP Token", "open.mcd.cn/mcp · 手机号登录一键复制", "⚡"),
        ("克隆项目", "git clone github.com/xiewengi/mcd-annual-report", "📦"),
        ("一行命令生成", "python3 generate_report.py --token \"你的Token\" --save-json", "🚀"),
    ]

    for i, (title, desc, icon) in enumerate(steps):
        sy = cta_y + 80 + i * 170
        # 序号圈
        num_circle = Image.new("RGBA", (80, 80), (0, 0, 0, 0))
        nc_draw = ImageDraw.Draw(num_circle)
        nc_draw.ellipse([0, 0, 80, 80], fill=PRIMARY)
        nc_draw.text((40, 40), str(i + 1), font=_find_font(44, bold=True), fill=TEXT_LIGHT, anchor="mm")
        canvas.paste(num_circle, (120, sy - 10), num_circle)
        # 图标
        draw_emoji(canvas, icon, 260, sy + 30, size=48)
        # 标题 + 描述
        _draw_text(draw, title, 325, sy + 15, _find_font(36, bold=True), TEXT_DARK, anchor="lt")
        _draw_text(draw, desc, 325, sy + 60, _find_font(26), TEXT_MID, anchor="lt")

    # 卖点
    sell_font = _find_font(34, bold=True)
    draw_emoji(canvas, "✅", W // 2 - 280, cta_y + 660, size=38)
    _draw_text(draw, "全程本地运行，Token 不上传，还能生成人格卡发朋友圈！", W // 2, cta_y + 670, _find_font(30, bold=True), (255, 255, 255, 230), anchor="mt")

    # GitHub
    _draw_text(draw, "github.com/xiewengi/mcd-annual-report", W // 2, H - 100, _find_font(32, bold=True), TEXT_LIGHT, anchor="mt")

    return canvas.convert("RGB")


# ============================================================
# 主流程
# ============================================================
def main():
    print("🎨 开始生成社交媒体素材 v2...")
    d = load_report()
    os.makedirs(OUT, exist_ok=True)

    print("\n1/6 封面大字...")
    save(make_cover(d), f"{OUT}/01_cover.png")

    print("2/6 人格卡...")
    generate_persona_card(d, f"{OUT}/02_persona_card.png")
    print(f"  ✅ {OUT}/02_persona_card.png")

    print("3/6 关键数字...")
    save(make_stats(d), f"{OUT}/03_stats.png")

    print("4/6 热力图...")
    save(make_heatmap(d), f"{OUT}/04_heatmap.png")

    print("5/6 健康模拟器...")
    save(make_simulator(d), f"{OUT}/05_simulator.png")

    print("6/6 行动号召...")
    save(make_cta(d), f"{OUT}/06_cta.png")

    print(f"\n🎉 全部生成完毕 → {OUT}/")
    for f in sorted(os.listdir(OUT)):
        p = os.path.join(OUT, f)
        sz = os.path.getsize(p) / 1024
        print(f"   {f:<30} {sz:7.1f} KB")


if __name__ == "__main__":
    main()
