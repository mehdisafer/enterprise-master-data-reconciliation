"""Real browser qualification against the running isolated Compose reference.

No token is printed or persisted to screenshots. This script is for the dedicated
synthetic CI environment; a successful result requires actual rendered state.
"""
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen

from playwright.sync_api import expect, sync_playwright


def main():
    target = "http://127.0.0.1:8000"
    actor_map = json.loads((Path(os.environ["MDM_SECRET_DIR"]) / "actors.json").read_text())
    token = next(token for token, actor in actor_map.items() if actor["role"] == "requester")
    output = Path("artifacts")
    output.mkdir(exist_ok=True)
    errors = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1100}, device_scale_factor=1)
        page.on("pageerror", lambda exc: errors.append(str(exc)))
        page.goto(target, wait_until="networkidle")
        page.get_by_label("Operator token").fill(token)
        page.get_by_role("button", name="Connect", exact=True).click()
        expect(page.locator("#actor")).to_contain_text("requester")
        expect(page.locator("#metrics")).to_contain_text("34")
        assert page.get_by_label("Operator token").input_value() == ""
        page.screenshot(path=str(output / "review-console.png"), full_page=False)
        page.locator("[data-evidence]").first.click()
        expect(page.locator("#detail")).to_be_visible()
        expect(page.locator("#detail-content")).to_contain_text("provenance")
        page.get_by_role("button", name="Close", exact=True).click()
        page.locator('[data-view="golden"]').click()
        expect(page.locator("#content")).to_contain_text("Golden records")
        page.screenshot(path=str(output / "golden-records.png"), full_page=False)
        page.locator('[data-view="consumers"]').click()
        expect(page.locator("#content")).to_contain_text("Reporting consumer")
        assert page.locator("tbody tr").count() == 34
        assert page.locator("tbody .tag.review").count() == 0
        page.screenshot(path=str(output / "consumer-corrections.png"), full_page=False)
        page.set_viewport_size({"width": 390, "height": 844})
        page.locator('[data-view="review"]').click()
        page.screenshot(path=str(output / "mobile-review.png"), full_page=False)
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        browser_version = browser.version
        browser.close()
    if errors:
        raise AssertionError(errors)
    request = Request(target + "/api/overview", headers={"Authorization": "Bearer " + token})
    with urlopen(request, timeout=10) as response:
        snapshot = json.load(response)
    report = {"passed": True, "browser": browser_version, "sources": snapshot["quality"]["sources"],
              "javascript_errors": errors, "actual_http_and_browser": True,
              "checks": ["authenticated review", "evidence dialog", "golden records", "34 aligned consumer mappings", "mobile width"]}
    (output / "browser-check.json").write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
