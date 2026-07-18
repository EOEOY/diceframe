from src.webui.services.characters import format_attribute_map


def test_format_attribute_map_shows_chinese_and_english_names():
    text = format_attribute_map(
        {"str": 7, "con": 9, "dex": 11, "int": 14, "edu": 13, "app": 8, "pow": 9, "siz": 9},
        [
            {"key": "str", "name": "力量", "name_en": "STR"},
            {"key": "con", "name": "体质", "name_en": "CON"},
            {"key": "dex", "name": "敏捷", "name_en": "DEX"},
            {"key": "int", "name": "智力", "name_en": "INT"},
            {"key": "edu", "name": "教育", "name_en": "EDU"},
            {"key": "app", "name": "外貌", "name_en": "APP"},
            {"key": "pow", "name": "意志", "name_en": "POW"},
            {"key": "siz", "name": "体型", "name_en": "SIZ"},
        ],
    )

    assert text == "力量 (STR):7 体质 (CON):9 敏捷 (DEX):11 智力 (INT):14 教育 (EDU):13 外貌 (APP):8 意志 (POW):9 体型 (SIZ):9"
