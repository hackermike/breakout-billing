"""Plain-English security banner printed when the server starts.

It tells the therapist, in simple terms, who can reach the app right now and
what to turn on (a login password + disk encryption) before using real client
data. The login password is optional by design — see app.auth.
"""
import sys

# Addresses that mean "only this computer can reach the app".
_LOOPBACK = {"127.0.0.1", "::1", "localhost"}


def bind_host(argv: list[str] | None = None) -> str:
    """The host uvicorn was told to listen on, read from the command line.
    Defaults to loopback, which is what `uvicorn app.main:app` uses with no
    --host (as in start.sh). The Dockerfile passes --host 0.0.0.0."""
    argv = sys.argv if argv is None else argv
    for i, arg in enumerate(argv):
        if arg == "--host" and i + 1 < len(argv):
            return argv[i + 1]
        if arg.startswith("--host="):
            return arg.split("=", 1)[1]
    return "127.0.0.1"


def is_localhost_only(host: str) -> bool:
    return host in _LOOPBACK


def security_notice(password_set: bool, host: str) -> str:
    """Build the banner text (kept pure so it can be tested)."""
    line = "-" * 62
    out = [line, " Breakout Billing - security check (plain English)", line]

    if is_localhost_only(host):
        out += [
            " Who can open this app right now:",
            "   Only THIS computer can. Other computers on your Wi-Fi or",
            "   office network cannot reach it (it listens on localhost).",
        ]
    else:
        out += [
            " *** WARNING: this app is open to your network ***",
            f"   It is listening on {host}, so OTHER computers on your",
            "   network can reach it. The connection is plain http (not",
            "   https), so anyone on the network could read the data.",
            "   Do not use real client information this way.",
        ]

    out += [
        "",
        " For real client data (HIPAA), you should have BOTH:",
        f"   [{'x' if password_set else ' '}] A login password  -- "
        + ("on. Good." if password_set
           else "OFF. Anyone who can use this"),
    ]
    if not password_set:
        out += [
            "       computer can open the app. Turn it on in",
            "       Settings > Security.",
        ]
    out += [
        "   [ ] Disk encryption -- turn on FileVault (Mac: System",
        "       Settings > Privacy & Security > FileVault) so the",
        "       files are scrambled if the laptop is lost or stolen.",
        line,
    ]
    return "\n".join(out)


def print_security_notice(password_set: bool, argv: list[str] | None = None) -> None:
    print(security_notice(password_set, bind_host(argv)), flush=True)
