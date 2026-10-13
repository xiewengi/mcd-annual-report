"""社交媒体素材批量生成器 v3
核心修复：draw_emoji 不再 size*1.4 放大，用 LANCZOS 精准缩放到请求尺寸。
所有边缘 emoji 位置重新校准。布局间距统一。
"""
import json, os, sys
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from personality_card import (
    generate_persona_card, _find_font, _gradient_background, _draw_text,
    EMOJI_FONT_PATH, TEXT_LIGHT, PRIMARY, SECONDARY, TEXT_DARK, TEXT_MID,
)

W, H = 1080, 1920
OUT = "assets/social"

def rounded_rect(draw, xy, radius, fill):
    draw.rounded_rectangle(xy, radius=radius, fill=fill)

def draw_emoji(canvas, emoji, cx, cy, size=60):
    """精准尺寸的彩色 emoji paste。
    Apple Color Emoji 仅 160px 能渲染彩色，200px 画布渲染 → LANCZOS 缩到 size×size → paste。
    """
    if not os.path.exists(EMOJI_FONT_PATH):
        draw = ImageDraw.Draw(canvas)
        font = _find_font(size)
        draw.text((cx, cy), emoji, font=font, fill=TEXT_LIGHT, anchor="mm")
        return
    src = Image.new("RGBA", (200, 200), (0, 0, 0, 0))
    src_draw = ImageDraw.Draw(src)
    try:
        font = ImageFont.truetype(EMOJI_FONT_PATH, 160)
        src_draw.text((100, 100), emoji, font=font, anchor="mm", embedded_color=True)
    except Exception:
        draw = ImageDraw.Draw(canvas)
        font = _find_font(size)
        draw.text((cx, cy), emoji, font=font, fill=TEXT_LIGHT, anchor="mm")
        return
    # 精准缩放到 size×size（不再 *1.4）
    target = max(size, 20)
    scaled = src.resize((target, target), Image.LANCZOS)
    canvas.paste(scaled, (cx - target // 2, cy - target // 2), scaled)

def load_report():
    jp = os.path.join("output", "report_data.json")
    if os.path.exists(jp):
        with open(jp) as f: return json.load(f)
    sys.exit("需要 output/report_data.json")

def save(img, path):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    img.save(path, "PNG", optimize=True)
    print(f"  ✅ {path}")

# ============================================================
# 1. 封面
# ============================================================
def make_cover(d):
    canvas = _gradient_background(W, H).convert("RGBA")
    draw = ImageDraw.Draw(canvas)

    # 🍔 居中（加浅金圆衬底）
    circle = Image.new("RGBA", (300, 300), (0, 0, 0, 0))
    ImageDraw.Draw(circle).ellipse([0, 0, 300, 300], fill=(255, 255, 255, 30))
    canvas.paste(circle, (W // 2 - 150, 170), circle)
    draw_emoji(canvas, "🍔", W // 2, 320, size=120)

    title_font = _find_font(80, bold=True)
    sub_font = _find_font(38)
    _draw_text(draw, "我帮麦当劳", W // 2, 460, title_font, TEXT_LIGHT, anchor="mt")
    _draw_text(draw, "做了个年度体检报告", W // 2, 560, title_font, TEXT_LIGHT, anchor="mt")
    _draw_text(draw, "基于麦当劳官方 MCP API · 纯 Python · 零服务器", W // 2, 680, sub_font, (255, 255, 255, 220), anchor="mt")

    features = [("📊", "10 笔订单", "¥119.3", "佛系食客"),
                ("💪", "健康评分 81", "钠摄入最弱", "BMR 个人化"),
                ("🗓️", "7×24 热力图", "周五 12:00", "黄金麦门时间")]
    card_w, gap = 310, 28
    total_w = len(features) * card_w + gap * 2
    start_x = (W - total_w) // 2
    cy = 960
    for i, (em, t1, t2, t3) in enumerate(features):
        cx = start_x + i * (card_w + gap) + card_w // 2
        rounded_rect(draw, [cx - card_w//2, cy - 160, cx + card_w//2, cy + 160], 28, (255, 255, 255, 240))
        draw_emoji(canvas, em, cx, cy - 80, size=64)
        sf = _find_font(28)
        _draw_text(draw, t1, cx, cy - 15, sf, TEXT_DARK, anchor="mm")
        _draw_text(draw, t2, cx, cy + 20, sf, SECONDARY, anchor="mm")
        _draw_text(draw, t3, cx, cy + 55, sf, TEXT_MID, anchor="mm")

    cta_y = 1520
    rounded_rect(draw, [120, cta_y - 75, W - 120, cta_y + 145], 28, (255, 255, 255, 240))
    _draw_text(draw, "你的麦门年度报告", W // 2, cta_y - 25, _find_font(50, bold=True), PRIMARY, anchor="mt")
    _draw_text(draw, "跑一跑，看你一年吃了多少可乐", W // 2, cta_y + 45, sub_font, TEXT_MID, anchor="mt")
    _draw_text(draw, "2026 麦当劳程序员创意开发大赛参赛作品", W // 2, H - 80, _find_font(28), (255,255,255,200), anchor="mt")
    return canvas.convert("RGB")

# ============================================================
# 2. 关键数字
# ============================================================
def make_stats(d):
    summary = d.get("summary", {})
    health = d.get("health_assessment", {})
    persona = d.get("persona", {}).get("main", {})
    canvas = _gradient_background(W, H).convert("RGBA")
    draw = ImageDraw.Draw(canvas)

    title_font = _find_font(62, bold=True)
    sub_font = _find_font(34)
    big_num = _find_font(160, bold=True)

    # 顶部：emoji + 标题 居中一行
    draw_emoji(canvas, "🍔", W // 2 - 380, 85, size=44)
    _draw_text(draw, "这一年我吃了多少麦当劳？", W // 2, 80, title_font, TEXT_LIGHT, anchor="mt")
    span = summary.get("days_span", 209)
    _draw_text(draw, f"真实数据 · {summary.get('total_orders', 10)} 笔订单 · {span} 天", W // 2, 170, sub_font, (255,255,255,220), anchor="mt")

    # 4 卡 2×2：card 宽 470，边界 60px，内缩 emoji 位置
    card_w, card_h = 470, 370
    gap = 30
    grid_w = card_w * 2 + gap
    start_x = (W - grid_w) // 2
    start_y = 250

    stat_meta = [
        ("📋", str(summary.get("total_orders", 0)), "年度总单数", ""),
        ("💰", f"¥{summary.get('total_amount', 0)}", "总消费", ""),
        ("❤️", str(health.get("overall_score", "--")), "健康评分", health.get("grade", "")[:10].replace("⭐","").strip()),
        ("🍀", "", "麦门人设", ""),
    ]
    for idx, (em, num, label, sub) in enumerate(stat_meta):
        row, col = divmod(idx, 2)
        cx = start_x + col * (card_w + gap)
        cy = start_y + row * (card_h + gap)
        rounded_rect(draw, [cx, cy, cx + card_w, cy + card_h], 28, (255,255,255,245))
        # emoji 内缩到 card 中心偏上
        draw_emoji(canvas, em, cx + 80, cy + 80, size=54)

        if idx == 3:  # 人设卡
            p_emoji = persona.get("emoji", "")
            p_name = persona.get("name", "--")
            # emoji 在左，名字紧接右边，都居中在 card
            if p_emoji:
                draw_emoji(canvas, p_emoji, cx + card_w // 2 - 80, cy + 180, size=80)
            _draw_text(draw, p_name, cx + card_w // 2 + 20, cy + 140, _find_font(44, bold=True), PRIMARY, anchor="lt")
            bd = d.get("persona", {}).get("breakdown", {})
            bd_text = " · ".join([f"{k}:{v}" for k, v in list(bd.items())[:3]])
            if bd_text:
                _draw_text(draw, bd_text[:50], cx + 120, cy + 240, _find_font(22), TEXT_DARK, anchor="lt")
        else:
            # 数字大字体
            nf = big_num if len(num) <= 6 else _find_font(100, bold=True)
            _draw_text(draw, num, cx + 110, cy + 50, nf, PRIMARY, anchor="mt")

        # label（底部）
        _draw_text(draw, label, cx + 80, cy + 285, _find_font(30), TEXT_MID, anchor="lt")
        if sub and idx != 3:
            _draw_text(draw, sub, cx + 80, cy + 320, _find_font(26), TEXT_DARK, anchor="lt")

    # Top 3 card（紧接 4 卡下方，不留大空隙）
    top_y = start_y + 2 * card_h + 2 * gap + 10
    rounded_rect(draw, [60, top_y, W - 60, top_y + 300], 28, (255,255,255,245))
    draw_emoji(canvas, "⭐", 105, top_y + 48, size=40)
    _draw_text(draw, "你最常点的 Top 3", 160, top_y + 28, _find_font(42, bold=True), PRIMARY, anchor="lt")
    top_products = d.get("top_products", [])[:3]
    medals = ["🥇", "🥈", "🥉"]
    for i, tp in enumerate(top_products):
        ry = top_y + 115 + i * 58
        draw_emoji(canvas, medals[i], 120, ry + 18, size=38)
        _draw_text(draw, tp.get("name", "--"), 185, ry + 12, _find_font(34), TEXT_DARK, anchor="lt")
        _draw_text(draw, f"× {tp.get('quantity', 0)}", W - 110, ry + 12, _find_font(34, bold=True), PRIMARY, anchor="rt")

    # 底部 CTA（上移到紧贴 Top 3 下方）
    bottom = top_y + 320
    _draw_text(draw, "想知道你这一年吃了多少可乐？跑一跑！", W // 2, bottom, _find_font(40, bold=True), (255,255,255,230), anchor="mt")
    _draw_text(draw, "GitHub: xiewengi/mcd-annual-report", W // 2, bottom + 55, _find_font(28), (255,255,255,180), anchor="mt")
    return canvas.convert("RGB")

# ============================================================
# 3. 热力图
# ============================================================
def make_heatmap(d):
    sa = d.get("store_analysis", {})
    canvas = _gradient_background(W, H).convert("RGBA")
    draw = ImageDraw.Draw(canvas)

    # 标题：emoji 在左，文字居中（emoji 内缩，不溢出）
    draw_emoji(canvas, "🗓️", W // 2 - 320, 125, size=44)
    _draw_text(draw, "7×24 点餐热力图", W // 2, 110, _find_font(56, bold=True), TEXT_LIGHT, anchor="mt")
    _draw_text(draw, "每格=该天某小时的下单次数", W // 2, 185, _find_font(30), (255,255,255,220), anchor="mt")

    # 黄金时间大卡
    gy = 225
    rounded_rect(draw, [80, gy, W - 80, gy + 195], 28, (255,255,255,245))
    draw_emoji(canvas, "🕐", 120, gy + 98, size=44)
    _draw_text(draw, "黄金麦门时间", 190, gy + 30, _find_font(30), TEXT_MID, anchor="lt")
    _draw_text(draw, sa.get("golden_time", "周五 18:00"), 190, gy + 68, _find_font(60, bold=True), PRIMARY, anchor="lt")
    _draw_text(draw, sa.get("golden_time_desc", ""), 190, gy + 160, _find_font(26), TEXT_DARK, anchor="lt")

    # 热力图网格（边距 100）
    hy = gy + 225
    hh = 880
    hmargin = 100
    hw = W - hmargin * 2
    cw = hw / 24
    ch = hh / 7
    days = ["周一","周二","周三","周四","周五","周六","周日"]
    hm = sa.get("heatmap", [])
    if not hm:
        hm = [{"cells":[{"hour":h,"count":0,"pct":0} for h in range(24)]} for _ in days]

    for ri, row in enumerate(hm):
        _draw_text(draw, days[ri], hmargin - 25, hy + ri * ch + ch/2, _find_font(24), (255,255,255,220), anchor="mm")
        for cell in row["cells"]:
            cnt = cell["count"]
            r = cell["pct"] / 100
            col = (255,248,225) if cnt == 0 else ((255,224,178) if r < 0.2 else (255,183,77) if r < 0.5 else (255,112,67) if r < 0.8 else (216,67,21))
            xx = hmargin + cell["hour"] * cw + 2
            yy = hy + ri * ch + 2
            rounded_rect(draw, [xx, yy, xx + cw - 4, yy + ch - 4], 3, col)

    # 图例
    ly = hy + hh + 18
    _draw_text(draw, "少", hmargin, ly + 14, _find_font(26), (255,255,255,220), anchor="mt")
    for i, c in enumerate([(255,248,225),(255,224,178),(255,183,77),(255,112,67),(216,67,21)]):
        rounded_rect(draw, [hmargin + 60 + i*78, ly + 10, hmargin + 110 + i*78, ly + 52], 8, c)
    _draw_text(draw, "多", hmargin + 470, ly + 14, _find_font(26), (255,255,255,220), anchor="mt")

    # 门店 Top
    store_y = ly + 80
    draw_emoji(canvas, "🏪", W // 2 - 290, store_y + 20, size=40)
    _draw_text(draw, "你最常去的门店", W // 2, store_y + 10, _find_font(50, bold=True), TEXT_LIGHT, anchor="mt")
    top_stores = sa.get("top_stores", [])[:3]
    for i, st in enumerate(top_stores):
        line_y = store_y + 75 + i * 50
        draw_emoji(canvas, ["🥇","🥈","🥉"][i], 110, line_y + 15, size=34)
        _draw_text(draw, st.get("name","--"), 170, line_y + 15, _find_font(28), TEXT_LIGHT, anchor="lm")
        _draw_text(draw, f'{st.get("count",0)} 单 ¥{st.get("amount",0)}', W - 110, line_y + 15, _find_font(28), (255,255,255,230), anchor="rm")

    # CTA（紧贴底部）
    cta_y = store_y + 75 + len(top_stores) * 50 + 20
    _draw_text(draw, "看看你自己的 7×24 麦门时间表", W // 2, cta_y, _find_font(36, bold=True), (255,255,255,230), anchor="mt")
    draw_emoji(canvas, "🧐", W // 2 + 240, cta_y + 10, size=32)
    return canvas.convert("RGB")

# ============================================================
# 4. 模拟器
# ============================================================
def make_simulator(d):
    health = d.get("health_assessment", {})
    sims = d.get("health_simulations", [])
    scores = health.get("scores", {})
    canvas = _gradient_background(W, H).convert("RGBA")
    draw = ImageDraw.Draw(canvas)

    draw_emoji(canvas, "💪", W // 2 - 320, 125, size=44)
    _draw_text(draw, "健康改进模拟器", W // 2, 110, _find_font(56, bold=True), TEXT_LIGHT, anchor="mt")
    _draw_text(draw, "基于你这一年的真实点餐数据", W // 2, 185, _find_font(30), (255,255,255,220), anchor="mt")

    # 健康总览卡：左侧健康分 + 右侧 4 条进度条（完全分开的两个区域）
    oy = 230
    rounded_rect(draw, [80, oy, W - 80, oy + 270], 28, (255,255,255,245))
    # 左上：健康分小区域（x:120~360, y:260~500）
    _draw_text(draw, "健康分", 120, oy + 35, _find_font(28), TEXT_MID, anchor="lt")
    _draw_text(draw, str(health.get("overall_score", "--")), 120, oy + 65, _find_font(100, bold=True), PRIMARY, anchor="lt")
    _draw_text(draw, health.get("grade","").replace("⭐","").strip(), 120, oy + 200, _find_font(28, bold=True), SECONDARY, anchor="lt")
    # 右侧：4 条进度条（x:400~1000，和左侧健康分区域完全错开）
    bar_x_start = 420
    bar_x_end = 980
    for i, (dim, sc) in enumerate(list(scores.items())):
        row_y = oy + 55 + i * 45
        ratio = min(max(sc/100, 0), 1.0)
        color = (76,175,80) if sc >= 80 else ((255,183,77) if sc >= 60 else (255,112,67))
        _draw_text(draw, f"{dim}", bar_x_start, row_y - 2, _find_font(26), TEXT_DARK, anchor="lt")
        _draw_text(draw, f"{sc}", bar_x_start + 100, row_y - 2, _find_font(26, bold=True), PRIMARY, anchor="lt")
        bar_left = bar_x_start + 150
        bar_right = bar_x_end
        rounded_rect(draw, [bar_left, row_y, bar_right, row_y + 22], 11, (255,224,178))
        rounded_rect(draw, [bar_left, row_y, bar_left + int((bar_right-bar_left)*ratio), row_y + 22], 11, color)

    # 模拟器卡片（从 oy+270+40=540 起，每条 320 高）
    cy0 = oy + 340
    card_h = 310
    n = min(len(sims), 4)
    total = n * card_h + (n - 1) * 24
    cy0 = max(cy0, (H - total) // 2 + 100)  # 垂直居中

    for i, sim in enumerate(sims[:4]):
        cy = cy0 + i * (card_h + 24)
        rounded_rect(draw, [80, cy, W - 80, cy + card_h], 24, (255,255,255,245))
        draw_emoji(canvas, sim.get("icon","💡"), 145, cy + 60, size=56)
        act = sim.get("action", "")
        _draw_text(draw, act[:38], 215, cy + 30, _find_font(34, bold=True), PRIMARY, anchor="lt")
        if len(act) > 38:
            _draw_text(draw, act[38:76], 215, cy + 65, _find_font(34, bold=True), PRIMARY, anchor="lt")
        imp = sim.get("impact", "")
        _draw_text(draw, imp[:50], 120, cy + 135, _find_font(26), TEXT_DARK, anchor="lt")
        _draw_text(draw, imp[50:100], 120, cy + 172, _find_font(26), TEXT_DARK, anchor="lt")
        _draw_text(draw, f"📈 {sim.get('score_hint','')[:36]}", 120, cy + 230, _find_font(22), SECONDARY, anchor="lt")
        _draw_text(draw, f"🎯 {sim.get('grade_hint','')[:36]}", 120, cy + 260, _find_font(22), PRIMARY, anchor="lt")
    return canvas.convert("RGB")

# ============================================================
# 5. CTA
# ============================================================
def make_cta(d):
    canvas = _gradient_background(W, H).convert("RGBA")
    draw = ImageDraw.Draw(canvas)

    circle = Image.new("RGBA", (300, 300), (0, 0, 0, 0))
    ImageDraw.Draw(circle).ellipse([0, 0, 300, 300], fill=(255, 255, 255, 30))
    canvas.paste(circle, (W // 2 - 150, 240), circle)
    draw_emoji(canvas, "🎁", W // 2, 390, size=120)

    _draw_text(draw, "想看看你自己的", W // 2, 560, _find_font(68, bold=True), TEXT_LIGHT, anchor="mt")
    _draw_text(draw, "麦门年度体检报告？", W // 2, 645, _find_font(68, bold=True), TEXT_LIGHT, anchor="mt")

    cta_y = 780
    rounded_rect(draw, [80, cta_y, W - 80, cta_y + 600], 32, (255,255,255,245))
    steps = [("申请 MCP Token", "open.mcd.cn/mcp · 手机号登录一键复制", "⚡"),
             ("克隆项目", "git clone github.com/xiewengi/mcd-annual-report", "📦"),
             ("一行命令生成", "python3 generate_report.py --token \"你的Token\" --save-json", "🚀")]
    for i, (title, desc, icon) in enumerate(steps):
        sy = cta_y + 80 + i * 170
        # 序号圆
        num_circ = Image.new("RGBA", (80, 80), (0, 0, 0, 0))
        nc = ImageDraw.Draw(num_circ)
        nc.ellipse([0, 0, 80, 80], fill=PRIMARY)
        nc.text((40, 40), str(i+1), font=_find_font(44, bold=True), fill=TEXT_LIGHT, anchor="mm")
        canvas.paste(num_circ, (120, sy - 10), num_circ)
        draw_emoji(canvas, icon, 260, sy + 30, size=40)
        _draw_text(draw, title, 320, sy + 12, _find_font(34, bold=True), TEXT_DARK, anchor="lt")
        _draw_text(draw, desc, 320, sy + 58, _find_font(24), TEXT_MID, anchor="lt")

    # 卖点（紧贴 step 3 下方）
    sell_y = cta_y + 620
    draw_emoji(canvas, "✅", 180, sell_y + 18, size=34)
    _draw_text(draw, "全程本地运行，Token 不上传，还能生成人格卡发朋友圈！", 230, sell_y + 18, _find_font(28, bold=True), (255,255,255,230), anchor="lm")

    _draw_text(draw, "github.com/xiewengi/mcd-annual-report", W // 2, H - 80, _find_font(30, bold=True), TEXT_LIGHT, anchor="mt")
    return canvas.convert("RGB")

# ============================================================
def main():
    d = load_report()
    os.makedirs(OUT, exist_ok=True)
    print("🎨 生成 v3 素材（精准 emoji 尺寸 + 布局修复）...\n")

    tasks = [
        ("1/6 封面", make_cover, f"{OUT}/01_cover.png"),
        ("3/6 关键数字", make_stats, f"{OUT}/03_stats.png"),
        ("4/6 热力图", make_heatmap, f"{OUT}/04_heatmap.png"),
        ("5/6 模拟器", make_simulator, f"{OUT}/05_simulator.png"),
        ("6/6 CTA", make_cta, f"{OUT}/06_cta.png"),
    ]
    for label, fn, path in tasks:
        print(label + "...")
        save(fn(d), path)

    print("\n2/6 人格卡...")
    generate_persona_card(d, f"{OUT}/02_persona_card.png")
    print(f"  ✅ {OUT}/02_persona_card.png")

    print(f"\n🎉 完毕 → {OUT}/")
    for f in sorted(os.listdir(OUT)):
        p = os.path.join(OUT, f)
        print(f"   {f:<30} {os.path.getsize(p)//1024} KB")

if __name__ == "__main__":
    main()
