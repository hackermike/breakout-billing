from app.startup_notice import bind_host, is_localhost_only, security_notice


def test_bind_host_defaults_to_loopback():
    assert bind_host(["uvicorn", "app.main:app", "--reload"]) == "127.0.0.1"


def test_bind_host_reads_flag():
    assert bind_host(["uvicorn", "app.main:app", "--host", "0.0.0.0"]) == "0.0.0.0"
    assert bind_host(["uvicorn", "app.main:app", "--host=0.0.0.0"]) == "0.0.0.0"


def test_localhost_classification():
    assert is_localhost_only("127.0.0.1")
    assert is_localhost_only("localhost")
    assert not is_localhost_only("0.0.0.0")
    assert not is_localhost_only("192.168.1.5")


def test_notice_localhost_and_no_password():
    text = security_notice(password_set=False, host="127.0.0.1")
    assert "Only THIS computer" in text
    assert "OFF" in text                 # password status
    assert "FileVault" in text


def test_notice_warns_when_network_exposed():
    text = security_notice(password_set=True, host="0.0.0.0")
    assert "WARNING" in text
    assert "network can reach it" in text
