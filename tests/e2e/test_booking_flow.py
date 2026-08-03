"""End-to-end booking + payment flow through a real browser."""
import pytest

playwright_sync = pytest.importorskip("playwright.sync_api")
sync_playwright = playwright_sync.sync_playwright

pytestmark = pytest.mark.e2e


def test_book_and_pay(live_server):
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except Exception as exc:  # browsers not installed
            pytest.skip(f"chromium unavailable: {exc}")
        page = browser.new_page()
        page.goto(f"{live_server}/calendar")

        # First run requires setting a password (the scratch DB is unconfigured).
        page.wait_for_load_state("networkidle")
        if "/setup" in page.url:
            page.fill('input[name="password"]', "e2epassword1")
            page.fill('input[name="confirm"]', "e2epassword1")
            page.click('button:has-text("Set password")')
            page.wait_for_url("**/calendar")

        # The demo data is July 2026; go there explicitly (the calendar otherwise
        # defaults to the current month).
        page.goto(f"{live_server}/calendar?year=2026&month=7")

        # Open an empty day and add an appointment.
        page.click('div[hx-get="/calendar/day/2026-07-05"]')
        page.wait_for_selector("text=+ Add appointment")
        page.click("text=+ Add appointment")
        page.wait_for_selector('select[name="client_id"]')
        page.fill('input[name="time"]', "11:00")
        page.click('button:has-text("Save")')

        # The new chip appears live in the calendar cell (out-of-band swap).
        page.wait_for_selector("#chips-2026-07-05 .truncate", timeout=5000)

        # Record a payment on the newly created appointment.
        page.click('button:has-text("+ Record payment")')
        page.wait_for_selector('input[name="amount"]')
        page.click('button:has-text("Save payment")')
        page.wait_for_selector("text=Paid in full", timeout=5000)

        browser.close()
