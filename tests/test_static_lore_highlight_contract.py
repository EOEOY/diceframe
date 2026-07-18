from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RENDERER = ROOT / "frontend-v2" / "src" / "utils" / "renderer.ts"
STYLES = ROOT / "frontend-v2" / "src" / "styles.css"
USE_GAME = ROOT / "frontend-v2" / "src" / "composables" / "useGame.ts"


def test_lore_highlight_supports_all_entry_types() -> None:
    renderer = RENDERER.read_text(encoding="utf-8")
    styles = STYLES.read_text(encoding="utf-8")

    assert "export interface LoreKeywords" in renderer
    for entry_type, css_class in {
        "npc": "kw-npc",
        "location": "kw-place",
        "item": "kw-item",
        "faction": "kw-faction",
        "event": "kw-event",
        "puzzle": "kw-puzzle",
        "other": "kw-other",
    }.items():
        assert f"{entry_type}?:string[]" in renderer
        assert f"{entry_type}:" in renderer
        assert css_class in renderer
        assert f".{css_class}" in styles


def test_lore_highlight_refreshes_after_lorebook_mutations() -> None:
    use_game = USE_GAME.read_text(encoding="utf-8")
    timeline = (ROOT / "frontend-v2" / "src" / "components" / "GameTimeline.vue").read_text(encoding="utf-8")

    assert "function buildLore(entries:LorebookResponse['entries'] = []):LoreKeywords" in use_game
    assert "/lorebook/" in use_game
    assert "lore.value=buildLore" in use_game
    assert ":lore=\"game.lore.value\"" in (ROOT / "frontend-v2" / "src" / "features" / "play" / "PlayView.vue").read_text(encoding="utf-8")
    assert "parseGMText(String(entry.gm_response), props.lore)" in timeline
