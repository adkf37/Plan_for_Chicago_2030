"""Optional browser acceptance check; requires Playwright and Chromium.

Run: python -m scripts.check_soldier_field_map
Install browser tooling separately; it is not an analysis runtime dependency.
"""

import json
from io import BytesIO

from PIL import Image, ImageChops
from playwright.sync_api import sync_playwright

from src.config import ANALYSIS_RESULTS_DIR, SOLDIER_FIELD_MAP, SOLDIER_FIELD_SOURCE_DIR


def harbor_detail(page):
    """Sample the visible map inside today's basin to catch hidden or misordered layers."""
    x, y = page.evaluate(
        "()=>{const p=map.latLngToContainerPoint([41.8619,-87.6109]);return [p.x,p.y]}"
    )
    screenshot = Image.open(BytesIO(page.locator("#map").screenshot())).convert("RGB")
    assert 10 < x < screenshot.width - 10 and 10 < y < screenshot.height - 10
    return screenshot.crop((x - 10, y - 10, x + 10, y + 10))


def check_scenes(page):
    assert page.locator("#today").get_attribute("aria-pressed") == "true"
    assert not page.evaluate("map.hasLayer(proposals)")
    camera = "()=>[map.getCenter().lat,map.getCenter().lng,map.getZoom()]"
    start = page.evaluate(camera)
    before = harbor_detail(page)
    page.locator("#proposed").click()
    assert page.evaluate(camera) == start
    assert page.locator("#plan-legend").is_visible()
    assert page.evaluate("map.hasLayer(proposals) && map.hasLayer(district)")
    # A toggle that changes captions without painting over the water must fail.
    changed = ImageChops.difference(before, harbor_detail(page)).convert("L")
    assert sum(changed.histogram()[20:]) > 300
    page.locator("#today").click()
    assert page.evaluate(camera) == start
    assert ImageChops.difference(before, harbor_detail(page)).getbbox() is None
    page.locator("#proposed").click()
    for street in (14, 16, 18):
        marker = page.get_by_title(f"{street}th Street", exact=True)
        marker.focus()
        marker.press("Enter")
        assert f"{street}th Street" in page.locator(".leaflet-popup-content").inner_text()
        page.keyboard.press("Escape")
        page.locator(".leaflet-popup-content").wait_for(state="detached")
    page.locator("#today").click()
    assert not page.locator("#plan-legend").is_visible()
    assert page.locator(".street-tag, .leaflet-popup-content").count() == 0


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
        check_scenes(page)
        page.locator("#fit-reference").click()
        assert page.evaluate("map.getBounds().contains(comparison.getBounds())")
        page.locator("#fit-site").click()
        assert page.evaluate("map.getBounds().contains(district.getBounds())")
        page.locator("#proposed").click()
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
        page.locator("#today").click()
        page.evaluate("map.invalidateSize();fit(district)")
        check_scenes(page)
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        page.screenshot(
            path=str(SOLDIER_FIELD_SOURCE_DIR / "map_verified_mobile.png"), full_page=True
        )
        assert not errors, errors
        browser.close()
    print(
        "Browser checks passed: registered Today/Proposed views, beach street popups, benchmark, offline imagery and tile fallback on desktop and mobile."
    )


if __name__ == "__main__":
    main()
