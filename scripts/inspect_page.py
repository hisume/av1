"""Small Playwright diagnostic for inspecting public booking pages."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from playwright.sync_api import Response, sync_playwright


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("--screenshot", type=Path)
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--click-index", type=int)
    args = parser.parse_args()

    responses: list[dict[str, object]] = []
    failures: list[dict[str, object]] = []
    console_messages: list[str] = []

    def record(response: Response) -> None:
        content_type = response.headers.get("content-type", "")
        if "json" in content_type or response.request.resource_type in {"xhr", "fetch"}:
            responses.append(
                {
                    "status": response.status,
                    "method": response.request.method,
                    "resource_type": response.request.resource_type,
                    "url": response.url,
                }
            )

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=not args.headed)
        page = browser.new_page(viewport={"width": 1440, "height": 1200})
        page.on("response", record)
        page.on(
            "requestfailed",
            lambda request: failures.append(
                {"url": request.url, "failure": request.failure}
            ),
        )
        page.on(
            "console",
            lambda message: console_messages.append(
                f"{message.type}: {message.text}"
            ),
        )
        page.goto(args.url, wait_until="networkidle", timeout=90_000)

        if args.click_index is not None:
            page.locator("input, select, button, [role=button]").nth(
                args.click_index
            ).click()
            page.wait_for_timeout(1_000)

        fields = page.locator("input, select, button, [role=button]").evaluate_all(
            """elements => elements.map((element, index) => ({
                index,
                tag: element.tagName,
                type: element.getAttribute('type'),
                name: element.getAttribute('name'),
                id: element.id,
                placeholder: element.getAttribute('placeholder'),
                ariaLabel: element.getAttribute('aria-label'),
                className: element.className,
                disabled: element.disabled,
                text: (element.innerText || element.value || '').trim().slice(0, 160)
            }))"""
        )
        print(json.dumps({"title": page.title(), "url": page.url, "fields": fields}, indent=2))
        print("\nBODY\n", page.locator("body").inner_text()[:12_000])
        print("\nNETWORK\n", json.dumps(responses, indent=2))
        print("\nFAILURES\n", json.dumps(failures, indent=2))
        print("\nCONSOLE\n", json.dumps(console_messages, indent=2))

        if args.screenshot:
            args.screenshot.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=args.screenshot, full_page=True)
        browser.close()


if __name__ == "__main__":
    main()
