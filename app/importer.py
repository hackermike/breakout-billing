"""Parse a client-list CSV exported from another practice-management system.

Columns are matched by name (case- and punctuation-insensitive) against an alias
table, so exports from SimplePractice, TherapyNotes, TheraNest, or a generic CSV
all map onto our Client fields without the user configuring anything. See
docs/IMPORT.md.
"""
import csv
import io
import re
from datetime import date, datetime

# Breakout field -> recognized header spellings (normalized on both sides).
FIELD_ALIASES: dict[str, set[str]] = {
    "first_name": {"firstname", "first", "clientfirstname", "givenname", "legalfirstname"},
    "last_name": {"lastname", "last", "clientlastname", "surname", "familyname",
                  "legallastname"},
    "dob": {"dateofbirth", "dob", "birthdate", "birthday", "dateofbirthmmddyyyy"},
    "email": {"email", "emailaddress", "clientemail", "primaryemail"},
    "phone": {"phone", "phonenumber", "mobile", "mobilephone", "cell", "cellphone",
              "primaryphone", "telephone", "homephone"},
    "insurance_company": {"insurance", "insurancecompany", "insurancepayer", "payer",
                          "insurancename", "primaryinsurance", "insuranceprovider"},
    "insurance_id": {"memberid", "insuranceid", "policynumber", "subscriberid",
                     "membernumber", "insurancememberid"},
    "group_number": {"groupnumber", "group", "groupid", "groupno"},
    "diagnosis_codes": {"diagnosis", "diagnosiscodes", "icd10", "icd", "dx",
                        "diagnosiscode", "icd10codes"},
}
# A single combined-name column (split into first/last when no separate columns).
FULL_NAME_ALIASES = {"clientname", "name", "fullname", "patientname", "clientfullname"}

# US month/day ordering only. A DMY format is intentionally excluded so an
# ambiguous value like 05/08/1989 is never silently reinterpreted as 8 May.
DATE_FORMATS = ["%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%m-%d-%Y", "%Y/%m/%d"]

# Guard against pathological uploads.
MAX_ROWS = 20000


class CsvImportError(ValueError):
    """Raised when a CSV can't be parsed or exceeds limits; surfaced to the user."""


def _norm(header: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (header or "").lower())


def _parse_date(value: str) -> date | None:
    value = (value or "").strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _split_name(full: str) -> tuple[str, str]:
    full = (full or "").strip()
    if "," in full:  # "Last, First"
        last, first = full.split(",", 1)
        return first.strip(), last.strip()
    parts = full.split()
    if len(parts) >= 2:  # "First Last"
        return parts[0], " ".join(parts[1:])
    return full, ""


def _build_header_map(headers: list[str]) -> tuple[dict[int, str], list[str]]:
    """Map column index -> Breakout field, plus the list of unmapped headers."""
    lookup = {alias: field for field, aliases in FIELD_ALIASES.items() for alias in aliases}
    mapping: dict[int, str] = {}
    unmapped: list[str] = []
    for i, header in enumerate(headers):
        key = _norm(header)
        if key in lookup:
            mapping[i] = lookup[key]
        elif key in FULL_NAME_ALIASES:
            mapping[i] = "_full_name"
        elif header and header.strip():
            unmapped.append(header)
    return mapping, unmapped


def parse_clients(text: str) -> tuple[list[dict], dict]:
    """Return (client dicts ready for the Client model, summary).

    summary = {rows, importable, skipped, unmapped_headers}
    """
    try:
        rows = list(csv.reader(io.StringIO(text)))
    except csv.Error as exc:
        raise CsvImportError(f"Could not read the CSV: {exc}") from exc
    if not rows:
        return [], {"rows": 0, "importable": 0, "skipped": 0, "unmapped_headers": []}
    if len(rows) - 1 > MAX_ROWS:
        raise CsvImportError(f"Too many rows ({len(rows) - 1}); limit is {MAX_ROWS}.")

    header_map, unmapped = _build_header_map(rows[0])
    clients: list[dict] = []
    skipped = 0

    for raw in rows[1:]:
        if not any(cell.strip() for cell in raw):
            continue  # blank line
        record: dict[str, str] = {}
        full_name = ""
        for i, value in enumerate(raw):
            field = header_map.get(i)
            if not field:
                continue
            value = value.strip()
            if field == "_full_name":
                full_name = value
            elif value:
                record[field] = value

        if not record.get("first_name") and not record.get("last_name") and full_name:
            record["first_name"], record["last_name"] = _split_name(full_name)

        # A client needs at least a name.
        if not (record.get("first_name") or record.get("last_name")):
            skipped += 1
            continue

        record.setdefault("first_name", "")
        record.setdefault("last_name", "")
        record["dob"] = _parse_date(record.get("dob", ""))
        clients.append(record)

    return clients, {
        "rows": len(rows) - 1,
        "importable": len(clients),
        "skipped": skipped,
        "unmapped_headers": unmapped,
    }
