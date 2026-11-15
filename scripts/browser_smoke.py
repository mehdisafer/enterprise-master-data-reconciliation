"""Real browser qualification against the running isolated Compose reference.

No token is printed or persisted to screenshots. This script is for the dedicated
synthetic CI environment; a successful result requires actual rendered state.
The optional lifecycle profile mutates only the two synthetic Velora identities:
merge/unmerge restores their original IDs, then merge/split exercises an explicit
new identity while retaining every source key and reconciling the consumer.
"""
import argparse
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen
from uuid import UUID

from playwright.sync_api import expect, sync_playwright

from mdm.synthetic import demo_records


TARGET = "http://127.0.0.1:8000"
VELORA_KEYS = {"ERP_ALPHA:organization:VELORA-01", "ERP_BETA:organization:VELORA-20"}


def read_overview(token):
    request = Request(TARGET + "/api/overview", headers={"Authorization": "Bearer " + token})
    with urlopen(request, timeout=10) as response:
        return json.load(response)


def mapping(snapshot, key="crosswalk"):
    return {row["source_key"]: row["golden_id"] for row in snapshot[key]
            if key != "consumer_crosswalk" or row["consumer"] == "reporting"}


def login(page, role, credentials):
    token, actor = credentials[role]
    page.get_by_label("Operator token").fill(token)
    with page.expect_response(lambda response: response.url == TARGET + "/api/overview"
                              and response.request.method == "GET") as loaded:
        page.get_by_role("button", name="Connect", exact=True).click()
    assert loaded.value.status == 200
    expect(page.locator("#actor")).to_have_text(f"{actor['name']} · {role}")
    expect(page.get_by_label("Operator token")).to_have_value("")
    expect(page.locator("#notice")).to_have_text("Loaded current source records, decisions and consumer state.")


def post_from_click(page, button, path, requests, status=200):
    """Every domain mutation must originate from a rendered console control."""
    with page.expect_response(lambda response: response.url == TARGET + path
                              and response.request.method == "POST") as pending:
        button.click()
    response = pending.value
    assert response.status == status, f"{path} returned HTTP {response.status}"
    payload = response.json()
    correlation = response.headers["x-correlation-id"]
    assert str(UUID(correlation)) == correlation
    requests.append({"path": path, "status": response.status, "correlation_id": correlation})
    expect(page.locator("#notice")).to_have_text(
        "Decision recorded. Review the ledger and consumer state for the next step.")
    expect(page.locator("#detail")).not_to_be_visible()
    return payload


def execute_decision(page, decision, credentials, requests):
    identity = decision["decision_id"]
    page.locator('[data-view="decisions"]').click()
    # The requester must not receive an approval or execution control.
    expect(page.locator(f'[data-action][data-id="{identity}"]')).to_have_count(0)
    login(page, "approver", credentials)
    approved = post_from_click(page, page.locator(f'[data-action="approve"][data-id="{identity}"]'),
                               f"/api/decisions/{identity}/approve", requests)
    assert approved["status"] == "approved"
    assert approved["requested_by"] == credentials["requester"][1]["name"]
    assert approved["approved_by"] == credentials["approver"][1]["name"]
    expect(page.locator(f'[data-action="execute"][data-id="{identity}"]')).to_have_count(0)
    login(page, "executor", credentials)
    executed = post_from_click(page, page.locator(f'[data-action="execute"][data-id="{identity}"]'),
                               f"/api/decisions/{identity}/execute", requests)
    assert executed["status"] == "executed"
    assert executed["executed_by"] == credentials["executor"][1]["name"]
    return executed


def publish_corrections(page, credentials, requests, expected_sources):
    page.locator('[data-view="consumers"]').click()
    assert page.locator("tbody .tag.review").count() > 0
    result = post_from_click(page, page.get_by_role("button", name="Apply pending corrections", exact=True),
                             "/api/consume", requests)
    assert result["caught_up"] and result["processed"] > 0
    expect(page.locator("tbody tr")).to_have_count(expected_sources)
    expect(page.locator("tbody .tag.review")).to_have_count(0)
    overview = read_overview(credentials["requester"][0])
    assert mapping(overview["snapshot"], "consumer_crosswalk") == mapping(overview["snapshot"])
    assert overview["quality"]["unconsumed_events"] == 0
    return overview


def request_merge(page, credentials, requests, reason):
    login(page, "requester", credentials)
    snapshot = read_overview(credentials["requester"][0])["snapshot"]
    pairs = [pair for pair in snapshot["candidates"] if {pair["left_key"], pair["right_key"]} == VELORA_KEYS]
    assert len(pairs) == 1, "The dedicated demo must contain one current Velora candidate"
    page.locator('[data-view="review"]').click()
    button = page.locator(f'[data-merge="{pairs[0]["candidate_id"]}"]')
    expect(button).to_be_enabled()
    button.click()
    page.locator("#reason").fill(reason)
    return post_from_click(page, page.get_by_role("button", name="Submit for approval", exact=True),
                           "/api/decisions/merge", requests, 201)


def lifecycle(page, actor_map, output):
    credentials = {}
    for role in ("requester", "approver", "executor"):
        matches = [(token, actor) for token, actor in actor_map.items() if actor["role"] == role]
        assert len(matches) == 1, f"The dedicated fixture needs exactly one {role}"
        credentials[role] = matches[0]
    assert len({actor["name"] for _, actor in credentials.values()}) == 3
    before = read_overview(credentials["requester"][0])
    baseline = before["snapshot"]
    original = mapping(baseline)
    assert set(original) == {record.key for record in demo_records()}, "Only the complete synthetic demo is supported"
    assert before["quality"]["pending_decisions"] == 0, "Resolve existing decisions before this isolated profile"
    assert mapping(baseline, "consumer_crosswalk") == original
    assert len({original[key] for key in VELORA_KEYS}) == 2
    requests = []
    page.set_viewport_size({"width": 1440, "height": 1100})

    merged = execute_decision(page, request_merge(page, credentials, requests,
        "Browser qualification: synthetic Velora merge for a reversible identity exercise."), credentials, requests)
    assert set(merged["result"]["after_memberships"]) == VELORA_KEYS
    assert len(set(merged["result"]["after_memberships"].values())) == 1
    publish_corrections(page, credentials, requests, len(original))
    page.screenshot(path=str(output / "lifecycle-merged-consumer.png"), full_page=False)

    login(page, "requester", credentials)
    page.locator('[data-view="decisions"]').click()
    page.locator(f'[data-unmerge="{merged["decision_id"]}"]').click()
    page.locator("#reason").fill("Browser qualification: undo the synthetic merge and preserve original identities.")
    undo = post_from_click(page, page.get_by_role("button", name="Submit unmerge for approval", exact=True),
                           "/api/decisions/unmerge", requests, 201)
    execute_decision(page, undo, credentials, requests)
    restored = publish_corrections(page, credentials, requests, len(original))
    assert mapping(restored["snapshot"]) == original
    page.screenshot(path=str(output / "lifecycle-unmerge-restored.png"), full_page=False)

    merged_again = execute_decision(page, request_merge(page, credentials, requests,
        "Browser qualification: second synthetic merge to exercise an explicit split."), credentials, requests)
    publish_corrections(page, credentials, requests, len(original))
    active_group = next(iter(set(merged_again["result"]["after_memberships"].values())))
    login(page, "requester", credentials)
    page.locator('[data-view="golden"]').click()
    page.locator(f'[data-split="{active_group}"]').click()
    page.locator(f'[name="split-member"][value="{sorted(VELORA_KEYS)[1]}"]').check()
    page.locator("#reason").fill("Browser qualification: explicitly separate the two synthetic source identities.")
    split = post_from_click(page, page.get_by_role("button", name="Submit split for approval", exact=True),
                            "/api/decisions/split", requests, 201)
    split_result = execute_decision(page, split, credentials, requests)
    assert len(set(split_result["result"]["after_memberships"].values())) == 2
    assert split_result["result"]["after_memberships"][sorted(VELORA_KEYS)[0]] == active_group
    final = publish_corrections(page, credentials, requests, len(original))
    after_map = mapping(final["snapshot"])
    assert set(after_map) == set(original)
    assert {key: value for key, value in after_map.items() if key not in VELORA_KEYS} == {
        key: value for key, value in original.items() if key not in VELORA_KEYS}
    assert final["snapshot"]["sources"] == baseline["sources"], "Browser decisions must not rewrite source assertions"
    assert final["quality"]["crosswalk_coverage"] == 1
    assert final["quality"]["pending_decisions"] == 0
    page.screenshot(path=str(output / "lifecycle-split-consumer.png"), full_page=False)
    login(page, "requester", credentials)
    return {"passed": True, "all_mutations_from_rendered_controls": True,
            "source_identities_preserved": len(after_map), "unmerge_restored_original_mapping": True,
            "split_preserved_unaffected_mapping": True, "source_assertions_unchanged": True,
            "consumer_alignment_verified_after_each_operation": True,
            "decision_ids": [merged["decision_id"], undo["decision_id"], merged_again["decision_id"], split["decision_id"]],
            "http_requests": requests}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exercise-lifecycle", action="store_true",
                        help="Exercise merge, unmerge and split under distinct operators on the dedicated synthetic demo")
    args = parser.parse_args()
    target = TARGET
    actor_map = json.loads((Path(os.environ["MDM_SECRET_DIR"]) / "actors.json").read_text())
    token = next(token for token, actor in actor_map.items() if actor["role"] == "requester")
    output = Path("artifacts")
    output.mkdir(exist_ok=True)
    errors = []
    lifecycle_report = None
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1100}, device_scale_factor=1)
        page.set_default_timeout(15_000)
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
        if args.exercise_lifecycle:
            lifecycle_report = lifecycle(page, actor_map, output)
        browser_version = browser.version
        browser.close()
    if errors:
        raise AssertionError(errors)
    snapshot = read_overview(token)
    report = {"passed": True, "browser": browser_version, "sources": snapshot["quality"]["sources"],
              "javascript_errors": errors, "actual_http_and_browser": True,
              "lifecycle_executed": args.exercise_lifecycle, "lifecycle": lifecycle_report,
              "checks": ["authenticated review", "evidence dialog", "golden records", "34 aligned consumer mappings", "mobile width"]}
    (output / "browser-check.json").write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
