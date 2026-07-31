from app import auth


def test_unconfigured_redirects_to_setup(raw_client):
    r = raw_client.get("/calendar", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/setup"


def test_setup_creates_password_and_signs_in(raw_client, db):
    r = raw_client.post("/setup", data={"password": "supersecret", "confirm": "supersecret"},
                        follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/calendar"
    assert auth.is_configured(db)
    assert raw_client.get("/clients").status_code == 200  # now signed in


def test_setup_rejects_short_password(raw_client):
    r = raw_client.post("/setup", data={"password": "short", "confirm": "short"})
    assert "at least 8" in r.text


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


def test_password_is_hashed_not_stored_plaintext(db):
    from app.models.auth import AuthConfig
    auth.set_password(db, "plaintextpw123")
    row = db.query(AuthConfig).first()
    assert row.password_hash != "plaintextpw123"
    assert auth.verify_password(db, "plaintextpw123")
    assert not auth.verify_password(db, "wrong")
