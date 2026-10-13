"""
社交媒体素材批量生成器
从 output/report_data.json 读真实数据，生成 5 张 1080×1920 竖屏素材图：
  01_cover.png        — 封面大字 "我帮麦当劳做了个年度体检报告"
  02_persona_card.png — 人格卡（复用 personality_card.py）
  03_stats.png        — 关键数字（单数/消费/健康分/人设）
  04_heatmap.png      — 7×24 点餐热力图 + 黄金时间
  05_finale.png       — 行动号召（"你也来测测自己的麦门健康" + GitHub + MCP Token 申请链接）

纯 Pillow，无外部依赖。
"""
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from personality_card import generate_persona_card, _find_font, _gradient_background, _draw_text, EMOJI_FONT_PATH, EMOJI_SIZE

W, H = 1080, 1920
OUT = "assets/social"

# 配色
BG_TOP = (255, 193, 7)       # 麦当劳金
BG_BOT = (244, 67, 54)        # 麦当劳红
PRIMARY = (216, 67, 21)       # #d84315
SECONDARY = (255, 152, 0)     # #ff9800
TEXT_DARK = (61, 61, 61)
TEXT_MID = (117, 117, 117)
TEXT_LIGHT = (255, 255, 255)
CARD_BG = (255, 255, 255)


def rounded_rect(draw, xy, radius, fill):
    draw.rounded_rectangle(xy, radius=radius, fill=fill)


def load_report():
    json_path = os.path.join("output", "report_data.json")
    if os.path.exists(json_path):
        with open(json_path) as f:
            return json.load(f)
    print("⚠️  output/report_data.json 不存在，用示例数据")
    from generate_report import _sample_orders, _sample_nutrition
    from analyzer import AnnualAnalyzer
    return AnnualAnalyzer(_sample_orders(), _sample_nutrition()).analyze()


def draw_emoji(draw, emoji, cx, cy, size=160, color=(255, 255, 255)):
    """画彩色 emoji（用 Apple Color Emoji + embedded_color）
    Apple Color Emoji 自带颜色，不能传 fill 参数（会覆盖或导致方块）
    """
    if os.path.exists(EMOJI_FONT_PATH):
        try:
            font = ImageFont.truetype(EMOJI_FONT_PATH, 160)  # 仅 160px 可加载
            # 先在 160px 画布渲染，再 paste 到目标位置（支持任意 size）
            from PIL import Image as _Img
            patch = _Img.new("RGBA", (200, 200), (0, 0, 0, 0))
            pd = ImageDraw.Draw(patch)
            pd.text((100, 100), emoji, font=font, anchor="mm", embedded_color=True)
            # 缩放 patch 到目标 size
            scale = size / 160.0
            new_patch = patch.resize((int(200 * scale), int(200 * scale)), _Img.LANCZOS)
            draw._canvas.paste(new_patch, (int(cx - new_patch.width // 2), int(cy - new_patch.height // 2)), new_patch)
            return
        except Exception:
            pass
    # fallback：普通字体（单色）
    font = _find_font(size)
    draw.text((cx, cy), emoji, font=font, fill=color, anchor="mm")


def save(img, path):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    img.save(path, "PNG", optimize=True)
    print(f"  ✅ {path}")


# ============================================================
# 图 1：封面大字
# ============================================================
def make_cover(d):
    bg = _gradient_background(W, H)
    canvas = bg.convert("RGBA")
    draw = ImageDraw.Draw(canvas)

    # 顶部 emoji 行（Apple Color Emoji 仅 160px 可加载，贴到更大画布上）
    # 用双层：底下白圆衬底 + 160px emoji
    from PIL import Image as _Image
    bg_patch = _Image.new("RGBA", (320, 320), (255, 255, 255, 10))
    bg_canvas = ImageDraw.Draw(bg_patch)
    bg_canvas.ellipse([0, 0, 320, 320], fill=(255, 255, 255, 30))
    canvas.paste(bg_patch, (W // 2 - 160, 180), bg_patch)
    draw_emoji(draw, "🍔", W // 2, 320, size=160)

    # 主标题（3 行大字，居中）
    title_font = _find_font(80, bold=True)
    sub_font = _find_font(42)

    _draw_text(draw, "我帮麦当劳", W // 2, 480, title_font, TEXT_LIGHT, anchor="mt")
    _draw_text(draw, "做了个年度体检报告", W // 2, 580, title_font, TEXT_LIGHT, anchor="mt")

    # 副标题
    _draw_text(draw, "基于麦当劳官方 MCP API · 纯 Python · 零服务器", W // 2, 700, sub_font, (255, 255, 255, 230), anchor="mt")

    # 3 个亮点圆形
    features = [
        ("📊", "10 笔订单", "¥119.3", "佛系食客"),
        ("💪", "健康评分 81", "钠摄入最弱", "BMR 个人化"),
        ("🗓️", "7×24 热力图", "周五 18:00", "黄金麦门时间"),
    ]

    card_w = 300
    gap = 30
    total_w = len(features) * card_w + (len(features) - 1) * gap
    start_x = (W - total_w) // 2

    for i, (emoji, t1, t2, t3) in enumerate(features):
        cx = start_x + i * (card_w + gap) + card_w // 2
        cy = 950
        # 白色圆角卡片
        rounded_rect(draw, [cx - card_w // 2, cy - 140, cx + card_w // 2, cy + 140], 32, (255, 255, 255, 240))
        # emoji
        draw_emoji(draw, emoji, cx, cy - 80, size=80, color=PRIMARY)
        # 文字
        small_font = _find_font(28)
        _draw_text(draw, t1, cx, cy - 10, small_font, TEXT_DARK, anchor="mm")
        _draw_text(draw, t2, cx, cy + 30, small_font, SECONDARY, anchor="mm")
        _draw_text(draw, t3, cx, cy + 60, small_font, TEXT_MID, anchor="mm")

    # 底部行动号召
    bottom_y = 1500
    rounded_rect(draw, [120, bottom_y - 80, W - 120, bottom_y + 140], 28, (255, 255, 255, 240))
    cta_font = _find_font(48, bold=True)
    _draw_text(draw, "你的麦门年度报告", W // 2, bottom_y - 30, cta_font, PRIMARY, anchor="mt")
    _draw_text(draw, "跑一跑，看你一年吃了多少可乐", W // 2, bottom_y + 40, sub_font, TEXT_MID, anchor="mt")

    # 参赛水印
    wm_font = _find_font(28)
    _draw_text(draw, "2026 麦当劳程序员创意开发大赛参赛作品", W // 2, H - 80, wm_font, (255, 255, 255, 200), anchor="mt")

    return canvas.convert("RGB")


# ============================================================
# 图 2：关键数字页（真实数据）
# ============================================================
def make_stats(d):
    summary = d.get("summary", {})
    health = d.get("health_assessment", {})
    persona = d.get("persona", {}).get("main", {})

    bg = _gradient_background(W, H)
    canvas = bg.convert("RGBA")
    draw = ImageDraw.Draw(canvas)

    # 标题
    title_font = _find_font(64, bold=True)
    sub_font = _find_font(36)
    big_num_font = _find_font(180, bold=True)
    label_font = _find_font(36)

    _draw_text(draw, "🍔 这一年我吃了多少麦当劳？", W // 2, 100, title_font, TEXT_LIGHT, anchor="mt")
    _draw_text(draw, "真实数据 · 10 笔订单 · 209 天", W // 2, 190, sub_font, (255, 255, 255, 220), anchor="mt")

    # 4 个大号统计卡
    stats = [
        ("📋", str(summary.get("total_orders", 0)), "年度总单数", "10 笔 / 209 天"),
        ("💰", f"¥{summary.get('total_amount', 0)}", "总消费", "佛系食客"),
        ("❤️", str(health.get("overall_score", "--")), "健康评分", health.get("grade", "")[:20]),
        ("🍀", persona.get("emoji", "") + " " + persona.get("name", "--"), "麦门人设", ""),
    ]

    card_w, card_h = 460, 360
    gap = 30
    grid_w = card_w * 2 + gap
    start_x = (W - grid_w) // 2
    start_y = 280

    for idx, (emoji, num, label, sub) in enumerate(stats):
        row = idx // 2
        col = idx % 2
        cx = start_x + col * (card_w + gap)
        cy = start_y + row * (card_h + gap)
        rounded_rect(draw, [cx, cy, cx + card_w, cy + card_h], 28, (255, 255, 255, 245))

        # emoji
        draw_emoji(draw, emoji, cx + 80, cy + 80, size=80)

        if idx == 3:  # 人设卡：emoji + 名字 + breakdown 分开渲染
            p_emoji = persona.get("emoji", "")
            p_name = persona.get("name", "--")
            p_breakdown = d.get("persona", {}).get("breakdown", {})
            bd_text = " · ".join([f"{k}:{v}" for k, v in list(p_breakdown.items())[:3]])
            # 人设 emoji（大）
            if p_emoji:
                draw_emoji(draw, p_emoji, cx + 70, cy + 100, size=90)
            # 名字
            pfont = _find_font(44, bold=True)
            _draw_text(draw, p_name, cx + 140, cy + 80, pfont, PRIMARY, anchor="lt")
            # breakdown
            if bd_text:
                bdfont = _find_font(26)
                _draw_text(draw, bd_text[:36], cx + 70, cy + 190, bdfont, TEXT_DARK, anchor="lt")
        else:
            # 数字卡
            num_font = big_num_font if len(num) <= 6 else _find_font(120, bold=True)
            _draw_text(draw, num, cx + 120, cy + 60, num_font, PRIMARY, anchor="mt")

        # label + sub
        _draw_text(draw, label, cx + 80, cy + 280, label_font, TEXT_MID, anchor="mt")
        if sub and idx != 3:
            small_font = _find_font(28)
            _draw_text(draw, sub, cx + 80, cy + 315, small_font, TEXT_DARK, anchor="mt")

    # Top 3
    top_font = _find_font(44, bold=True)
    top_card_y = start_y + 2 * (card_h + gap) + 20
    rounded_rect(draw, [80, top_card_y, W - 80, top_card_y + 280], 28, (255, 255, 255, 245))
    _draw_text(draw, "⭐ 你最常点的 Top 3", 120, top_card_y + 30, top_font, PRIMARY, anchor="lt")

    top_products = d.get("top_products", [])[:3]
    medal = ["🥇", "🥈", "🥉"]
    for i, tp in enumerate(top_products):
        row_y = top_card_y + 110 + i * 55
        medal_font = _find_font(50)
        draw_emoji(draw, medal[i], 130, row_y + 22, size=50, color=SECONDARY)
        name_font = _find_font(38)
        _draw_text(draw, tp.get("name", "--"), 200, row_y + 15, name_font, TEXT_DARK, anchor="lt")
        qty_font = _find_font(38, bold=True)
        _draw_text(draw, f"× {tp.get('quantity', 0)}", W - 140, row_y + 15, qty_font, PRIMARY, anchor="rt")

    # 底部 CTA
    bottom_font = _find_font(44, bold=True)
    _draw_text(draw, "想知道你这一年吃了多少可乐？跑一跑！", W // 2, H - 180, bottom_font, (255, 255, 255, 230), anchor="mt")
    sub_cta = _find_font(32)
    _draw_text(draw, "GitHub: xiewengi/mcd-annual-report", W // 2, H - 120, sub_cta, (255, 255, 255, 200), anchor="mt")

    return canvas.convert("RGB")


# ============================================================
# 图 3：热力图 + 黄金时间页
# ============================================================
def make_heatmap(d):
    sa = d.get("store_analysis", {})
    bg = _gradient_background(W, H)
    canvas = bg.convert("RGBA")
    draw = ImageDraw.Draw(canvas)

    # 标题
    title_font = _find_font(56, bold=True)
    sub_font = _find_font(32)
    _draw_text(draw, "🗓️ 7×24 点餐热力图", W // 2, 100, title_font, TEXT_LIGHT, anchor="mt")
    _draw_text(draw, "每格=该天某小时的下单次数", W // 2, 180, sub_font, (255, 255, 255, 220), anchor="mt")

    # 黄金麦门时间大卡
    golden_y = 230
    rounded_rect(draw, [80, golden_y, W - 80, golden_y + 180], 28, (255, 255, 255, 245))
    golden_big = _find_font(72, bold=True)
    golden_sub = _find_font(34)
    _draw_text(draw, "🕐 黄金麦门时间", W // 2, golden_y + 20, golden_sub, TEXT_MID, anchor="mt")
    _draw_text(draw, sa.get("golden_time", "周五 18:00"), W // 2, golden_y + 70, golden_big, PRIMARY, anchor="mt")
    _draw_text(draw, sa.get("golden_time_desc", "你最常在周五 18 点吃麦当劳"), W // 2, golden_y + 140, golden_sub, TEXT_DARK, anchor="mt")

    # 热力图网格（1080 宽，约 24×7 格）
    hm_y = golden_y + 220
    hm_h = 900
    hm_w = W - 160
    cell_w = hm_w / 24
    cell_h = hm_h / 7

    days = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    hm_data = sa.get("heatmap", [])
    if not hm_data:
        hm_data = [{"day": d, "cells": [{"hour": h, "count": 0, "pct": 0} for h in range(24)]} for d in days]

    # 找 max count
    max_count = max(c["count"] for row in hm_data for c in row["cells"]) or 1

    # 画表头（小时）
    hour_font = _find_font(20)
    for h in range(0, 24, 2):
        x = 80 + h * cell_w + cell_w / 2
        _draw_text(draw, str(h), x, hm_y - 20, hour_font, (255, 255, 255, 200), anchor="mm")

    # 画每一格
    for row_idx, row in enumerate(hm_data):
        day_font = _find_font(24)
        _draw_text(draw, days[row_idx], 65, hm_y + row_idx * cell_h + cell_h / 2, day_font, (255, 255, 255, 220), anchor="mm")
        for cell in row["cells"]:
            cnt = cell["count"]
            ratio = cell["pct"] / 100
            # 颜色：白→浅橙→橙→深橙→红
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
            cx = 80 + cell["hour"] * cell_w + 2
            cy = hm_y + row_idx * cell_h + 2
            cw = cell_w - 4
            ch = cell_h - 4
            rounded_rect(draw, [cx, cy, cx + cw, cy + ch], 4, color)

    # 图例
    legend_y = hm_y + hm_h + 20
    legend_font = _find_font(28)
    _draw_text(draw, "少", 80, legend_y + 12, legend_font, (255, 255, 255, 220), anchor="mt")
    for i, c in enumerate([(255, 248, 225), (255, 224, 178), (255, 183, 77), (255, 112, 67), (216, 67, 21)]):
        rounded_rect(draw, [130 + i * 80, legend_y + 8, 180 + i * 80, legend_y + 50], 8, c)
    _draw_text(draw, "多", 560, legend_y + 12, legend_font, (255, 255, 255, 220), anchor="mt")

    # 门店 Top
    store_font = _find_font(40, bold=True)
    store_y = legend_y + 80
    _draw_text(draw, "🏪 你最常去的门店", W // 2, store_y, title_font, TEXT_LIGHT, anchor="mt")

    top_stores = sa.get("top_stores", [])[:3]
    row_font = _find_font(30)
    for i, st in enumerate(top_stores):
        line_y = store_y + 70 + i * 48
        medal = ["🥇", "🥈", "🥉"][i]
        draw_emoji(draw, medal, 100, line_y + 15, size=40, color=SECONDARY)
        _draw_text(draw, st.get("name", "--"), 160, line_y + 15, row_font, TEXT_LIGHT, anchor="lm")
        qty_font = _find_font(30, bold=True)
        _draw_text(draw, f'{st.get("count", 0)} 单 ¥{st.get("amount", 0)}', W - 100, line_y + 15, qty_font, (255, 255, 255, 230), anchor="rm")

    # 底部 CTA
    cta_font = _find_font(42, bold=True)
    _draw_text(draw, "看看你自己的 7×24 麦门时间表 🧐", W // 2, H - 100, cta_font, (255, 255, 255, 230), anchor="mt")

    return canvas.convert("RGB")


# ============================================================
# 图 4：健康改进模拟器
# ============================================================
def make_simulator(d):
    health = d.get("health_assessment", {})
    sims = d.get("health_simulations", [])

    bg = _gradient_background(W, H)
    canvas = bg.convert("RGBA")
    draw = ImageDraw.Draw(canvas)

    title_font = _find_font(60, bold=True)
    sub_font = _find_font(34)
    sim_title_font = _find_font(38, bold=True)
    sim_action_font = _find_font(34)
    sim_impact_font = _find_font(28)

    _draw_text(draw, "💪 健康改进模拟器", W // 2, 100, title_font, TEXT_LIGHT, anchor="mt")
    _draw_text(draw, "基于你这一年的真实点餐数据", W // 2, 180, sub_font, (255, 255, 255, 220), anchor="mt")

    # 健康总览
    overview_y = 240
    rounded_rect(draw, [80, overview_y, W - 80, overview_y + 220], 28, (255, 255, 255, 245))
    score_big = _find_font(120, bold=True)
    _draw_text(draw, "健康分", 120, overview_y + 30, sub_font, TEXT_MID, anchor="lt")
    _draw_text(draw, str(health.get("overall_score", "--")), 120, overview_y + 70, score_big, PRIMARY, anchor="lt")
    grade_font = _find_font(36, bold=True)
    _draw_text(draw, health.get("grade", ""), 120, overview_y + 170, grade_font, SECONDARY, anchor="lt")

    # 各维度条
    scores = health.get("scores", {})
    dims = [("热量", 500, 700), ("钠摄入", 700, 900), ("蛋白质", 900, 1100), ("脂肪", 1100, 1300)]
    for dim, bar_x, bar_y in dims:
        sc = scores.get(dim, 0)
        # 进度条背景
        rounded_rect(draw, [bar_x, bar_y, bar_x + 300, bar_y + 30], 15, (255, 224, 178))
        # 填充
        ratio = min(sc / 100, 1.0)
        bar_colors = [(255, 112, 67), (255, 183, 77), (76, 175, 80), (33, 150, 243)]
        color_idx = 0 if sc < 60 else (1 if sc < 80 else (2 if sc < 90 else 3))
        rounded_rect(draw, [bar_x, bar_y, bar_x + int(300 * ratio), bar_y + 30], 15, bar_colors[color_idx])
        dim_font = _find_font(28)
        _draw_text(draw, f"{dim} {sc}", bar_x, bar_y - 2, dim_font, TEXT_DARK, anchor="lb")

    # 模拟器卡片
    sim_card_y = overview_y + 260
    for i, sim in enumerate(sims[:4]):
        card_y = sim_card_y + i * 370
        rounded_rect(draw, [80, card_y, W - 80, card_y + 340], 24, (255, 255, 255, 245))
        # emoji 头
        draw_emoji(draw, sim.get("icon", "💡"), 150, card_y + 60, size=80, color=PRIMARY)
        # action
        _draw_text(draw, sim.get("action", "")[:36], 220, card_y + 30, sim_action_font, PRIMARY, anchor="lt")
        _draw_text(draw, sim.get("action", "")[36:] or "", 220, card_y + 80, sim_action_font, PRIMARY, anchor="lt")
        # impact
        _draw_text(draw, sim.get("impact", "")[:44], 120, card_y + 160, sim_impact_font, TEXT_DARK, anchor="lt")
        _draw_text(draw, sim.get("impact", "")[44:] or "", 120, card_y + 200, sim_impact_font, TEXT_DARK, anchor="lt")
        # score_hint / grade_hint
        hint_font = _find_font(26)
        _draw_text(draw, f"📈 {sim.get('score_hint', '')[:30]}", 120, card_y + 260, hint_font, SECONDARY, anchor="lt")
        _draw_text(draw, f"🎯 {sim.get('grade_hint', '')[:30]}", 120, card_y + 295, hint_font, PRIMARY, anchor="lt")

    return canvas.convert("RGB")


# ============================================================
# 图 5：行动号召页（CTA）
# ============================================================
def make_cta(d):
    bg = _gradient_background(W, H)
    canvas = bg.convert("RGBA")
    draw = ImageDraw.Draw(canvas)

    # 大 emoji（160px 彩色 + 双层放大）
    from PIL import Image as _Image2
    gift_patch = _Image2.new("RGBA", (300, 300), (0, 0, 0, 0))
    gift_draw = ImageDraw.Draw(gift_patch)
    gift_draw.ellipse([0, 0, 300, 300], fill=(255, 255, 255, 40))
    canvas.paste(gift_patch, (W // 2 - 150, 250), gift_patch)
    draw_emoji(draw, "🎁", W // 2, 400, size=160)

    title_font = _find_font(72, bold=True)
    sub_font = _find_font(36)
    step_font = _find_font(32)

    _draw_text(draw, "想看看你自己的", W // 2, 580, title_font, TEXT_LIGHT, anchor="mt")
    _draw_text(draw, "麦门年度体检报告？", W // 2, 670, title_font, TEXT_LIGHT, anchor="mt")

    # 3 步引导
    cta_y = 800
    rounded_rect(draw, [80, cta_y, W - 80, cta_y + 550], 32, (255, 255, 255, 245))

    # 1
    draw_emoji(draw, "①", 130, cta_y + 80, size=60, color=PRIMARY)
    _draw_text(draw, "申请 MCP Token（10 秒）", 220, cta_y + 50, step_font, TEXT_DARK, anchor="lt")
    _draw_text(draw, "open.mcd.cn/mcp · 手机号登录一键复制", 220, cta_y + 110, step_font, TEXT_MID, anchor="lt")

    # 2
    draw_emoji(draw, "②", 130, cta_y + 220, size=60, color=PRIMARY)
    _draw_text(draw, "克隆项目", 220, cta_y + 190, step_font, TEXT_DARK, anchor="lt")
    _draw_text(draw, "git clone github.com/xiewengi/mcd-annual-report", 220, cta_y + 250, step_font, TEXT_MID, anchor="lt")

    # 3
    draw_emoji(draw, "③", 130, cta_y + 360, size=60, color=PRIMARY)
    _draw_text(draw, "一行命令生成", 220, cta_y + 330, step_font, TEXT_DARK, anchor="lt")
    _draw_text(draw, "python3 generate_report.py --token \"你的Token\"", 220, cta_y + 390, step_font, TEXT_MID, anchor="lt")
    _draw_text(draw, "--save-json · 自动生成人格卡 PNG", 220, cta_y + 430, step_font, SECONDARY, anchor="lt")

    # 底部卖点
    sell_y = cta_y + 620
    sell_font = _find_font(36, bold=True)
    _draw_text(draw, "✅ 全程本地运行", W // 2, sell_y, sell_font, (255, 255, 255, 230), anchor="mt")
    _draw_text(draw, "✅ Token 不上传 · 隐私安全", W // 2, sell_y + 50, sell_font, (255, 255, 255, 230), anchor="mt")
    _draw_text(draw, "✅ 还能发朋友圈分享人格卡", W // 2, sell_y + 100, sell_font, (255, 255, 255, 230), anchor="mt")

    # GitHub 水印
    wm_font = _find_font(32, bold=True)
    _draw_text(draw, "github.com/xiewengi/mcd-annual-report", W // 2, H - 100, wm_font, TEXT_LIGHT, anchor="mt")

    return canvas.convert("RGB")


# ============================================================
# 主流程
# ============================================================
def main():
    print("🎨 开始生成社交媒体素材...")
    d = load_report()

    os.makedirs(OUT, exist_ok=True)
    from personality_card import generate_persona_card

    print("\n1/5 封面大字...")
    save(make_cover(d), f"{OUT}/01_cover.png")

    print("2/5 人格卡...")
    generate_persona_card(d, f"{OUT}/02_persona_card.png")
    print(f"  ✅ {OUT}/02_persona_card.png")

    print("3/5 关键数字...")
    save(make_stats(d), f"{OUT}/03_stats.png")

    print("4/5 热力图...")
    save(make_heatmap(d), f"{OUT}/04_heatmap.png")

    print("5/5 健康模拟器...")
    save(make_simulator(d), f"{OUT}/05_simulator.png")

    print("\n6/6 行动号召...")
    save(make_cta(d), f"{OUT}/06_cta.png")

    print(f"\n🎉 全部生成完毕 → {OUT}/")
    for f in sorted(os.listdir(OUT)):
        p = os.path.join(OUT, f)
        sz = os.path.getsize(p) / 1024
        print(f"   {f:<30} {sz:7.1f} KB")


if __name__ == "__main__":
    main()
