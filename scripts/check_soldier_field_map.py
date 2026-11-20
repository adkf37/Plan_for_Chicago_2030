"""Optional browser acceptance check; requires Playwright and Chromium.

Run: python -m scripts.check_soldier_field_map
Install browser tooling separately; it is not an analysis runtime dependency.
"""

import json

from playwright.sync_api import sync_playwright

from src.config import ANALYSIS_RESULTS_DIR, SOLDIER_FIELD_MAP, SOLDIER_FIELD_SOURCE_DIR


def main():
    run = json.loads((ANALYSIS_RESULTS_DIR / "soldier_field_run.json").read_text())
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1080})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.route("https://**/*", lambda route: route.abort())
        page.goto(SOLDIER_FIELD_MAP.as_uri(), wait_until="networkidle")
        assert page.locator(".leaflet-image-layer").evaluate("(e)=>e.complete && e.naturalWidth>0")
        assert page.locator("input, select, #draw, #scenario-controls").count() == 0
        benchmark = run["comparator_audit"]["comparators"][0]
        assert benchmark["name"] in page.locator("#evidence").inner_text()
        assert (
            f"{benchmark['value_per_gross_acre_low'] / 1e6:.2f}"
            in page.locator("#evidence").inner_text()
        )
        assert page.evaluate("map.hasLayer(proposals) && map.hasLayer(district)")
        page.locator("#fit-reference").click()
        assert page.evaluate("map.getBounds().contains(comparison.getBounds())")
        page.locator("#fit-site").click()
        assert page.evaluate("map.getBounds().contains(district.getBounds())")
        page.evaluate("proposals.getLayers()[0].openPopup()")
        assert page.locator(".leaflet-popup-content").is_visible()
        page.evaluate("map.closePopup()")
        page.locator("#background").click()
        page.wait_for_function(
            'document.getElementById("map-status").textContent.includes("unavailable")'
        )
        page.locator("#fit-both").click()
        page.locator("#concepts").scroll_into_view_if_needed()
        page.wait_for_function(
            'Array.from(document.querySelectorAll(".concepts img")).every(e=>e.complete&&e.naturalWidth>0)'
        )
        page.evaluate("scrollTo(0,0)")
        page.screenshot(
            path=str(SOLDIER_FIELD_SOURCE_DIR / "map_verified_desktop.png"), full_page=True
        )
        page.set_viewport_size({"width": 390, "height": 844})
        page.evaluate("map.invalidateSize();fitBoth()")
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        page.screenshot(
            path=str(SOLDIER_FIELD_SOURCE_DIR / "map_verified_mobile.png"), full_page=True
        )
        assert not errors, errors
        browser.close()
    print(
        "Browser checks passed: fixed proposal, street benchmark, map navigation and feature popup, offline assets, tile fallback, desktop/mobile."
    )


if __name__ == "__main__":
    main()
