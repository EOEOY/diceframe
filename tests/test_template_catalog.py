import json

from src.template_catalog import is_user_template_file, sync_template_catalog


def _write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def test_sync_refreshes_bundled_templates_and_preserves_user_templates(tmp_path):
    bundled = tmp_path / "bundle" / "rules"
    runtime = tmp_path / "data" / "templates" / "rules"
    _write(bundled / "base.json", {"rule_id": "base", "rule_version": "2"})
    _write(runtime / "base.json", {"rule_id": "base", "rule_version": "1"})
    _write(runtime / "custom_rule_home.json", {"rule_id": "custom_rule_home", "custom": True})

    stats = sync_template_catalog(bundled, runtime, "rules")

    assert stats["updated"] == 1
    assert json.loads((runtime / "base.json").read_text(encoding="utf-8"))["rule_version"] == "2"
    assert json.loads((runtime / "custom_rule_home.json").read_text(encoding="utf-8"))["custom"] is True


def test_sync_migrates_legacy_custom_templates_without_overwriting_data_copy(tmp_path):
    bundled = tmp_path / "bundle" / "worlds"
    runtime = tmp_path / "data" / "templates" / "worlds"
    _write(bundled / "custom_123.json", {"world_id": "custom_123", "world_name": "旧版本"})

    first = sync_template_catalog(bundled, runtime, "worlds")
    assert first["migrated"] == 1
    assert is_user_template_file(runtime / "custom_123.json", "worlds")

    _write(runtime / "custom_123.json", {"world_id": "custom_123", "world_name": "用户新版本", "custom": True})
    second = sync_template_catalog(bundled, runtime, "worlds")
    assert second["preserved"] == 1
    saved = json.loads((runtime / "custom_123.json").read_text(encoding="utf-8"))
    assert saved["world_name"] == "用户新版本"


def test_sync_does_not_replace_user_template_that_collides_with_bundle_name(tmp_path):
    bundled = tmp_path / "bundle" / "rules"
    runtime = tmp_path / "data" / "templates" / "rules"
    _write(bundled / "base.json", {"rule_id": "base", "rule_name": "内置"})
    _write(runtime / "base.json", {"rule_id": "base", "rule_name": "用户", "custom": True})

    stats = sync_template_catalog(bundled, runtime, "rules")

    assert stats["preserved"] == 1
    saved = json.loads((runtime / "base.json").read_text(encoding="utf-8"))
    assert saved["rule_name"] == "用户"
