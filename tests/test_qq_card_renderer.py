from PIL import Image, ImageDraw

from src.bots.qq.card_renderer import _fit_by_pixel, _load_font, _text_width, _wrap_by_pixel


def test_wrapping_accounts_for_first_line_indent():
    font = _load_font(21)
    image = Image.new("RGB", (10, 10))
    draw = ImageDraw.Draw(image)
    content_width = 600
    indent_px = _text_width(draw, "　　", font)
    text = "尤洛沿着白马寺藏经阁外墙一路疾行，银针上残留的冷光忽明忽暗，像是在催促她立刻做出决定。"

    lines = _wrap_by_pixel(draw, text, font, content_width, first_line_max_width=content_width - indent_px)

    assert lines
    assert _text_width(draw, lines[0], font) + indent_px <= content_width
    for line in lines[1:]:
        assert _text_width(draw, line, font) <= content_width


def test_fit_by_pixel_adds_ellipsis_within_width():
    font = _load_font(19)
    image = Image.new("RGB", (10, 10))
    draw = ImageDraw.Draw(image)

    fitted = _fit_by_pixel(draw, "这是一个很长很长很长的卡片副标题", font, 120)

    assert fitted.endswith("…")
    assert _text_width(draw, fitted, font) <= 120
