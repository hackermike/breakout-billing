from pathlib import Path

from app.importer import parse_clients
from app.models.client import Client

DEMO = Path("demo/patients")


def _read(name: str) -> str:
    return (DEMO / name).read_text()


def test_parse_simplepractice():
    clients, summary = parse_clients(_read("simplepractice_clients.csv"))
    assert summary["importable"] == 4
    p = clients[0]
    assert (p["first_name"], p["last_name"]) == ("Priya", "Nair")
    assert p["dob"].isoformat() == "1991-03-14"  # MM/DD/YYYY parsed
    assert p["insurance_company"] == "BlueCross BlueShield"
    assert p["insurance_id"] == "BCB771002"
    assert clients[1]["diagnosis_codes"] == "F33.1, F41.1"


def test_parse_therapynotes_splits_last_first_name():
    clients, summary = parse_clients(_read("therapynotes_clients.csv"))
    assert summary["importable"] == 3
    a = clients[0]
    assert (a["first_name"], a["last_name"]) == ("Maria", "Alvarez")
    assert a["dob"].isoformat() == "1989-08-05"
    assert a["diagnosis_codes"] == "F41.0"  # ICD-10 header mapped to diagnosis


def test_parse_theranest_ignores_do_not_contact_column():
    clients, summary = parse_clients(_read("theranest_clients.csv"))
    assert summary["importable"] == 3
    assert "Do Not Contact" in summary["unmapped_headers"]
    assert clients[0]["insurance_id"] == "CIG445120"  # Policy Number -> insurance_id


def test_parse_generic_minimal():
    clients, summary = parse_clients(_read("generic_clients.csv"))
    assert summary["importable"] == 2
    assert clients[0]["first_name"] == "Sam"


def test_parse_skips_rows_without_a_name():
    csv_text = "First Name,Email\n,nobody@example.com\nAda,ada@example.com\n"
    clients, summary = parse_clients(csv_text)
    assert summary["importable"] == 1
    assert summary["skipped"] == 1


def test_import_endpoint_creates_clients(client, db):
    csv_text = "First Name,Last Name,Email\nNina,Patel,nina@example.com\n"
    r = client.post("/import", files={"file": ("clients.csv", csv_text, "text/csv")})
    assert r.status_code == 200
    assert "Imported 1 client" in r.text
    assert db.query(Client).filter_by(last_name="Patel").count() == 1


def test_import_endpoint_with_demo_file(client, db):
    r = client.post(
        "/import",
        files={"file": ("sp.csv", _read("simplepractice_clients.csv"), "text/csv")},
    )
    assert r.status_code == 200
    assert db.query(Client).count() == 4
