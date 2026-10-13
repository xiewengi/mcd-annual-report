"""
麦门年度体检报告 - 人格卡 PNG 生成器

生成一张 1080×1920 的手机壁纸风格分享卡：
  - Hero 区：emoji 人设 + 称号 + 健康评分大字
  - 中间：3 个核心数据（年度 N 单 / ¥XXX 消费 / 健康评级）
  - 底部：Top3 最爱 + 参赛水印

纯 Pillow，无外部字体依赖（用系统字体 fallback）。
"""
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont


OUTPUT_CARD_PATH = "output/persona_card.png"

# 1080×1920 的 iPhone 壁纸比例
W, H = 1080, 1920

# macOS 彩色 emoji 字体（仅 160px 能加载，embedded_color=True 才渲染彩色）
EMOJI_FONT_PATH = "/System/Library/Fonts/Apple Color Emoji.ttc"
EMOJI_SIZE = 160

# 配色（麦当劳金红渐变系）
BG_TOP = (255, 193, 7)       # 麦当劳金
BG_BOT = (244, 67, 54)        # 麦当劳红
CARD_BG = (255, 255, 255, 250)
PRIMARY = (216, 67, 21)       # #d84315
SECONDARY = (255, 152, 0)     # #ff9800
TEXT_DARK = (61, 61, 61)
TEXT_MID = (117, 117, 117)
TEXT_LIGHT = (255, 255, 255)
ACCENT = (255, 255, 255, 230)


def _find_font(size: int, bold: bool = False, emoji: bool = False):
    """找字体。emoji=True 时优先用 Apple Color Emoji（仅 160px 可加载）"""
    if emoji:
        # Apple Color Emoji 只能 160px，按比例缩放后用 160 渲染再贴
        actual_size = 160
        if os.path.exists(EMOJI_FONT_PATH):
            try:
                return ImageFont.truetype(EMOJI_FONT_PATH, actual_size)
            except Exception:
                pass
    # 普通文字
    candidates = [
        "/System/Library/Fonts/Apple Color Emoji.ttc",  # emoji 专用（仅 160px）
        # macOS 系统字体
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/System/Library/Fonts/Helvetica.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
        # Windows fallback
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _gradient_background(w, h):
    """生成从上到下金→红的渐变背景"""
    img = Image.new("RGB", (w, h), BG_TOP)
    draw = ImageDraw.Draw(img)
    for y in range(h):
        ratio = y / h
        r = int(BG_TOP[0] + (BG_BOT[0] - BG_TOP[0]) * ratio)
        g = int(BG_TOP[1] + (BG_BOT[1] - BG_TOP[1]) * ratio)
        b = int(BG_TOP[2] + (BG_BOT[2] - BG_TOP[2]) * ratio)
        draw.line([(0, y), (w, y)], fill=(r, g, b))
    return img


def _rounded_mask(w, h, radius):
    """生成圆角蒙版"""
    mask = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([0, 0, w, h], radius=radius, fill=255)
    return mask


def _draw_rounded_card(canvas, x, y, w, h, radius=32, bg=(255, 255, 255, 240)):
    """在 canvas 上画一个圆角半透明白色卡片"""
    card = Image.new("RGBA", (w, h), bg)
    mask = _rounded_mask(w, h, radius)
    canvas.paste(card, (x, y), mask)


def _draw_text(draw, text, x, y, font, fill, anchor="lt", embedded_color=False):
    """画文字，返回 (x2, y2) 便于后续布局"""
    draw.text((x, y), text, font=font, fill=fill, anchor=anchor, embedded_color=embedded_color)
    bbox = draw.textbbox((x, y), text, font=font, anchor=anchor)
    return bbox[2], bbox[3]


def generate_persona_card(data: dict, output_path: str = OUTPUT_CARD_PATH) -> str:
    """根据 analyze() 返回的 dict 生成人格卡 PNG"""
    # === 取数据 ===
    summary = data.get("summary", {})
    persona = data.get("persona", {})
    health = data.get("health_assessment", {})
    top_products = data.get("top_products", [])
    meta = data.get("meta", {})

    main_persona = persona.get("main", {})
    persona_emoji = main_persona.get("emoji", "🍔")
    persona_name = main_persona.get("name", "麦门人")
    persona_desc = main_persona.get("desc", "") or persona.get("breakdown", {}).get("汉堡占比", "")

    total_orders = summary.get("total_orders", 0)
    total_amount = summary.get("total_amount", 0)
    avg_per_week = summary.get("avg_orders_per_week", 0)

    health_score = health.get("overall_score", 0)
    health_grade = health.get("grade", "")

    # === 画布 ===
    bg = _gradient_background(W, H)
    canvas = bg.convert("RGBA")
    draw = ImageDraw.Draw(canvas)

    # === 字体 ===
    font_big = _find_font(140, bold=True)
    font_title = _find_font(72, bold=True)
    font_sub = _find_font(44)
    font_body = _find_font(36)
    font_small = _find_font(28)
    font_number = _find_font(180, bold=True)
    font_mid_num = _find_font(100, bold=True)

    # === Hero 区 ===
    hero_top = 100
    # 大字标题：emoji + 文字分别渲染
    hero_emoji_font = _find_font(EMOJI_SIZE, emoji=True)
    _draw_text(draw, "🍔", W // 2 - 190, hero_top + 45, hero_emoji_font, TEXT_LIGHT, anchor="mm", embedded_color=True)
    _draw_text(draw, "麦门年度报告", W // 2 + 10, hero_top, font_title, TEXT_LIGHT, anchor="mt")
    # 年份
    year = meta.get("report_year", "2025")
    _draw_text(draw, year, W // 2, hero_top + 110, font_big, TEXT_LIGHT, anchor="mt")

    # 人像卡片
    card_x, card_y = 60, hero_top + 280
    card_w, card_h = W - 120, 560
    _draw_rounded_card(canvas, card_x, card_y, card_w, card_h, radius=40)

    # emoji（Apple Color Emoji 用 160px + embedded_color 才彩色）
    emoji_font = _find_font(EMOJI_SIZE, emoji=True)
    _draw_text(draw, persona_emoji, W // 2, card_y + 60, emoji_font, PRIMARY, anchor="mt", embedded_color=True)

    # 人设称号
    _draw_text(draw, persona_name, W // 2, card_y + 330, font_title, PRIMARY, anchor="mt")

    # 人设描述（breakdown 里的几个关键指标）
    breakdown = persona.get("breakdown", {})
    desc_parts = []
    if breakdown.get("汉堡占比"):
        desc_parts.append(f"汉堡 {breakdown['汉堡占比']}")
    if breakdown.get("宵夜频率"):
        desc_parts.append(f"宵夜 {breakdown['宵夜频率']}")
    if breakdown.get("鸡肉占比"):
        desc_parts.append(f"鸡肉 {breakdown['鸡肉占比']}")
    desc_text = " · ".join(desc_parts) if desc_parts else persona_desc
    _draw_text(draw, desc_text, W // 2, card_y + 420, font_body, TEXT_MID, anchor="mt")

    # === 3 个核心数据 ===
    stats_y = card_y + card_h + 40
    # 健康分级文字（去 emoji 星号，用纯文本）
    grade_text = health_grade.split("⭐")[0].strip() if health_grade else ""
    stat_labels = [
        ("年度", f"{total_orders}", "单麦当劳"),
        ("总消费", f"¥{total_amount}", "一年"),
        ("健康分", f"{health_score}", grade_text or ""),
    ]
    stat_w = (W - 120) // 3 - 12
    for i, (label, num, sub) in enumerate(stat_labels):
        sx = 60 + i * (stat_w + 18)
        _draw_rounded_card(canvas, sx, stats_y, stat_w, 200, radius=24)
        draw = ImageDraw.Draw(canvas)
        _draw_text(draw, label, sx + stat_w // 2, stats_y + 20, font_small, TEXT_MID, anchor="mt")
        _draw_text(draw, num, sx + stat_w // 2, stats_y + 55, font_mid_num, PRIMARY, anchor="mt")
        _draw_text(draw, sub, sx + stat_w // 2, stats_y + 165, font_small, TEXT_DARK, anchor="mt")

    # === Top 3 最爱 ===
    top_y = stats_y + 240
    _draw_rounded_card(canvas, 60, top_y, W - 120, 440, radius=32)
    draw = ImageDraw.Draw(canvas)
    # Top3 标题：emoji + 文字分开渲染
    top3_emoji_font = _find_font(80, emoji=True)
    # 用 mm anchor 居中对齐 emoji + 文字基线
    _draw_text(draw, "⭐", 80, top_y + 55, top3_emoji_font, PRIMARY, anchor="mm", embedded_color=True)
    _draw_text(draw, "你最常点的 Top 3", 150, top_y + 30, font_sub, PRIMARY, anchor="lt")

    for i, tp in enumerate(top_products[:3]):
        rank_emoji = ["🥇", "🥈", "🥉"][i] if i < 3 else "#"
        rank_num = "" if i < 3 else str(i+1)
        row_y = top_y + 110 + i * 95
        # 奖牌 emoji 单独渲染（用小一号 emoji 字体）
        medal_font = _find_font(80, emoji=True)
        _draw_text(draw, rank_emoji, 100 + 40, row_y + 8, medal_font, SECONDARY, anchor="mm", embedded_color=True)
        if rank_num:
            _draw_text(draw, rank_num, 100 + 80, row_y, font_body, SECONDARY, anchor="lt")
        _draw_text(draw, tp["name"], 170, row_y, font_body, TEXT_DARK, anchor="lt")
        # 数量右对齐
        qty_text = f"× {tp['quantity']}"
        _draw_text(draw, qty_text, W - 100, row_y, font_body, PRIMARY, anchor="rt")
        # 分割线
        if i < min(len(top_products), 3) - 1:
            draw.line([(100, row_y + 60), (W - 100, row_y + 60)], fill=(255, 224, 178), width=1)

    # === 参赛水印 ===
    footer_y = H - 160
    draw = ImageDraw.Draw(canvas)
    # footer emoji + 文字
    footer_emoji_font = _find_font(60, emoji=True)
    _draw_text(draw, "🍟", W // 2 - 140, footer_y + 10, footer_emoji_font, TEXT_LIGHT, anchor="mm", embedded_color=True)
    _draw_text(draw, "麦门年度体检报告", W // 2 + 20, footer_y + 15, font_sub, TEXT_LIGHT, anchor="mt")
    _draw_text(draw, "Powered by 麦当劳中国官方 MCP Server", W // 2, footer_y + 55, font_small, TEXT_LIGHT, anchor="mt")
    _draw_text(draw, "2026 麦当劳程序员创意开发大赛参赛作品", W // 2, footer_y + 95, font_small, (255, 255, 255, 200), anchor="mt")

    # === 保存 ===
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    final = canvas.convert("RGB")
    final.save(output_path, "PNG")
    return output_path


if __name__ == "__main__":
    if len(sys.argv) >= 2:
        json_path = sys.argv[1]
        with open(json_path) as f:
            data = json.load(f)
    else:
        print("❌ 需要 report_data.json 路径")
        sys.exit(1)

    out = sys.argv[2] if len(sys.argv) >= 3 else OUTPUT_CARD_PATH
    path = generate_persona_card(data, out)
    print(f"✅ 人格卡已生成: {path}")
