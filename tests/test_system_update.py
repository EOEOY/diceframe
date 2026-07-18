from src.webui.services.system import is_newer_version


def test_is_newer_version_compares_numeric_segments():
    assert is_newer_version("v0.10.0", "0.9.9")
    assert is_newer_version("1.0", "0.10.0")
    assert not is_newer_version("0.9.9", "0.10.0")


def test_is_newer_version_ignores_prerelease_suffix_for_basic_comparison():
    assert is_newer_version("1.2.0-beta.1", "1.1.9")
    assert not is_newer_version("1.2.0-beta.1", "1.2.0")


def test_is_newer_version_returns_false_for_unknown_formats():
    assert not is_newer_version("nightly", "0.1.0")
    assert not is_newer_version("0.2.0", "local-dev")
