from app import audit
from app.models.audit import AuditEntry


def test_should_log_filters_noise():
    assert audit.should_log("/clients/5")
    assert audit.should_log("/appointments/3/payments")
    assert not audit.should_log("/static/images/logo.png")
    assert not audit.should_log("/healthz")
    assert not audit.should_log("/login")
    assert not audit.should_log("/audit")  # viewing the log isn't self-logged


def test_authenticated_access_is_recorded(client, db):
    # The signed-in client fixture makes a request; it should appear in the log.
    client.get("/clients/999")  # 404, still an access attempt worth recording
    entries = db.query(AuditEntry).all()
    paths = {(e.method, e.path) for e in entries}
    assert ("GET", "/clients/999") in paths


def test_records_status_code(client, db, sample_client):
    client.get(f"/clients/{sample_client.id}")
    entry = (
        db.query(AuditEntry)
        .filter(AuditEntry.path == f"/clients/{sample_client.id}")
        .order_by(AuditEntry.id.desc())
        .first()
    )
    assert entry is not None
    assert entry.status == 200
    assert entry.actor == "user"


def test_unauthenticated_request_is_not_recorded(raw_client, db):
    from app import auth
    auth.set_password(db, "testpassword")
    before = db.query(AuditEntry).count()
    raw_client.get("/clients", follow_redirects=False)  # bounced to /login
    db.expire_all()
    assert db.query(AuditEntry).count() == before  # no PHI accessed, nothing logged


def test_audit_page_renders(client):
    assert client.get("/audit").status_code == 200
