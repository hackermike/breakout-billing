from fastapi.testclient import TestClient

from app import auth
from app.main import app


def _fresh_client():
    """A brand-new, unauthenticated client (separate cookie jar)."""
    return TestClient(app)


def test_unconfigured_app_is_open(raw_client):
    # With no password set, the app opens without a login.
    assert raw_client.get("/calendar", follow_redirects=False).status_code == 200


def test_login_page_redirects_when_no_password(raw_client):
    r = raw_client.get("/login", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/calendar"


def test_set_password_turns_on_login(raw_client, db):
    r = raw_client.post(
        "/security/set",
        data={"new_password": "supersecret", "confirm": "supersecret"},
        follow_redirects=False,
    )
    assert r.status_code == 303 and "sec=on" in r.headers["location"]
    assert auth.is_configured(db)
    # A different, unauthenticated browser is now gated.
    assert _fresh_client().get("/calendar", follow_redirects=False).headers["location"] == "/login"
    # The browser that set it stays signed in.
    assert raw_client.get("/clients").status_code == 200


def test_set_password_rejects_short(raw_client, db):
    r = raw_client.post("/security/set", data={"new_password": "short", "confirm": "short"},
                        follow_redirects=False)
    assert "sec=short" in r.headers["location"]
    assert not auth.is_configured(db)


def test_set_password_rejects_mismatch(raw_client, db):
    r = raw_client.post("/security/set",
                        data={"new_password": "supersecret", "confirm": "different1"},
                        follow_redirects=False)
    assert "sec=mismatch" in r.headers["location"]
    assert not auth.is_configured(db)


def test_configured_but_unauthenticated_redirects_to_login(raw_client, db):
    auth.set_password(db, "testpassword")
    r = raw_client.get("/calendar", follow_redirects=False)
    assert r.headers["location"] == "/login"


def test_wrong_password_is_rejected(raw_client, db):
    auth.set_password(db, "rightpassword")
    r = raw_client.post("/login", data={"password": "nope"})
    assert "Incorrect password" in r.text
    assert raw_client.get("/calendar", follow_redirects=False).headers["location"] == "/login"


def test_login_then_logout(raw_client, db):
    auth.set_password(db, "rightpassword")
    raw_client.post("/login", data={"password": "rightpassword"})
    assert raw_client.get("/clients").status_code == 200
    raw_client.post("/logout")
    assert raw_client.get("/calendar", follow_redirects=False).headers["location"] == "/login"


def test_change_password(client, db):
    r = client.post(
        "/security/change",
        data={"current_password": "testpassword",
              "new_password": "brandnewpass", "confirm": "brandnewpass"},
        follow_redirects=False,
    )
    assert "sec=changed" in r.headers["location"]
    assert auth.verify_password(db, "brandnewpass")
    assert not auth.verify_password(db, "testpassword")


def test_change_password_wrong_current(client, db):
    r = client.post(
        "/security/change",
        data={"current_password": "nope",
              "new_password": "brandnewpass", "confirm": "brandnewpass"},
        follow_redirects=False,
    )
    assert "sec=wrong" in r.headers["location"]
    assert auth.verify_password(db, "testpassword")


def test_remove_password_turns_off_login(client, db):
    r = client.post("/security/remove", data={"current_password": "testpassword"},
                    follow_redirects=False)
    assert "sec=off" in r.headers["location"]
    assert not auth.is_configured(db)
    # The app is open again.
    assert _fresh_client().get("/calendar", follow_redirects=False).status_code == 200


def test_remove_password_wrong_current(client, db):
    r = client.post("/security/remove", data={"current_password": "nope"},
                    follow_redirects=False)
    assert "sec=wrong" in r.headers["location"]
    assert auth.is_configured(db)  # still on


def test_password_is_hashed_not_stored_plaintext(db):
    from app.models.auth import AuthConfig
    auth.set_password(db, "plaintextpw123")
    row = db.query(AuthConfig).first()
    assert row.password_hash != "plaintextpw123"
    assert auth.verify_password(db, "plaintextpw123")
    assert not auth.verify_password(db, "wrong")
