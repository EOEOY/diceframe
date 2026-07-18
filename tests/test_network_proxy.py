from src.network_proxy import effective_proxy_url, is_supported_proxy_url, mask_proxy_url


def test_supported_proxy_url_accepts_http_and_https():
    assert is_supported_proxy_url("http://127.0.0.1:7890")
    assert is_supported_proxy_url("https://proxy.example.com:8443")


def test_supported_proxy_url_rejects_socks_for_builtin_aiohttp_proxy():
    assert not is_supported_proxy_url("socks5://127.0.0.1:1080")
    assert not is_supported_proxy_url("127.0.0.1:7890")


def test_mask_proxy_url_hides_password():
    masked = mask_proxy_url("http://alice:secret@127.0.0.1:7890")
    assert masked == "http://alice:***@127.0.0.1:7890"
    assert "secret" not in masked


def test_effective_proxy_url_respects_enabled_flag():
    assert effective_proxy_url(False, "http://127.0.0.1:7890") == ""
    assert effective_proxy_url(True, "http://127.0.0.1:7890") == "http://127.0.0.1:7890"
