import hashlib

import pytest

from scripts import build_portable


def test_verify_sha256_accepts_expected_content(tmp_path):
    payload = b"portable-runtime"
    target = tmp_path / "runtime.zip"
    target.write_bytes(payload)

    build_portable.verify_sha256(target, hashlib.sha256(payload).hexdigest())


def test_verify_sha256_rejects_tampered_content(tmp_path):
    target = tmp_path / "runtime.zip"
    target.write_bytes(b"tampered")

    with pytest.raises(RuntimeError, match="SHA-256 mismatch"):
        build_portable.verify_sha256(target, "0" * 64)


def test_download_rechecks_cached_file(tmp_path):
    target = tmp_path / "cached.zip"
    target.write_bytes(b"stale-cache")

    with pytest.raises(RuntimeError, match="SHA-256 mismatch"):
        build_portable.download("https://example.invalid/runtime.zip", target, "0" * 64)


def test_remove_generated_tree_removes_nested_content(tmp_path):
    target = tmp_path / "build" / "nested"
    target.mkdir(parents=True)
    (target / "artifact.txt").write_text("generated", encoding="utf-8")

    build_portable.remove_generated_tree(tmp_path / "build")

    assert not (tmp_path / "build").exists()
