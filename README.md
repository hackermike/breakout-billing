<p align="center">
  <img src="app/static/images/logo-sunburst.png" alt="Breakout Billing" width="400" />
</p>

<p align="center">
  Open-source practice management for independent therapists.<br/>
  Own your data. Run it on your laptop. No subscriptions.
</p>

---

![Calendar view](docs/screenshot-calendar.png)

## What it does (so far)

- **Calendar** — month view of all appointments, color-coded by status. Click any day to see that day's details.
- **Client list** — demographics, insurance info, and ICD-10 diagnosis codes.

Coming soon: recording payments, generating superbills (PDF), bookkeeping reports, adding/editing appointments and clients.

## Quick start (Mac)

**Requirements:** Python 3.9 or newer. Check by opening Terminal (press `Cmd+Space`, type "Terminal") and running `python3 --version`. If you don't have it, download from [python.org/downloads](https://www.python.org/downloads/).

**Option A — Download (no tools needed)**

1. On this page, click the green **Code** button → **Download ZIP**.
2. Double-click the downloaded file to unzip it.
3. In Terminal, drag the unzipped folder onto the window after typing `cd ` (note the space), then press Enter.
4. Run `./start.sh`.

**Option B — Clone with git** (if you have git installed)

```bash
git clone https://github.com/hackermike/breakout-billing.git
cd breakout-billing
./start.sh
```

Either way, your browser will open to `http://localhost:8000` with demo data loaded. Press `Ctrl+C` in the terminal to stop.

That's it. No accounts, no cloud, no subscriptions.

## Running again later

```bash
cd breakout-billing
./start.sh
```

The demo data is only created on the first run. Your real data will live in `breakout.db` in the project folder — back it up like any other file.

## HIPAA

Running locally means your data never leaves your computer. Make sure your Mac has FileVault disk encryption turned on (`System Settings → Privacy & Security → FileVault`). That satisfies the HIPAA encryption-at-rest requirement for a solo practice.

## Contributing

Pull requests welcome. This project is in early development — see open issues for what's needed next.

## License

[AGPL-3.0](LICENSE). You're free to use, modify, and self-host this software. If you run a modified version as a network service, you must make your source available under the same license. For commercial licensing options, open an issue.
