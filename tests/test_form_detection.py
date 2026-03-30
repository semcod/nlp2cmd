#!/usr/bin/env python3
"""
Test script to check form field detection on prototypowanie.pl
"""

import asyncio
import pytest

try:
    from playwright.async_api import async_playwright
except ImportError:
    async_playwright = None


pytestmark = [pytest.mark.integration, pytest.mark.slow]

async def test_form_detection():
    if async_playwright is None:
        pytest.skip("Playwright is not installed")

    from nlp2cmd.utils import is_playwright_browsers_installed

    if not is_playwright_browsers_installed():
        pytest.skip("Playwright Chromium browser is not installed")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        # Go to the contact page
        await page.goto("https://www.prototypowanie.pl/kontakt/")
        await page.wait_for_load_state('networkidle')
        
        # Debug: Check all input elements manually
        all_inputs = await page.query_selector_all('input')
        print(f"Found {len(all_inputs)} total input elements")
        
        visible_inputs = await page.query_selector_all('input:not([type="hidden"]):not([type="submit"]):not([type="button"])')
        print(f"Found {len(visible_inputs)} visible input fields")
        
        textareas = await page.query_selector_all('textarea')
        print(f"Found {len(textareas)} textarea fields")
        
        content_editables = await page.query_selector_all('[contenteditable="true"]')
        print(f"Found {len(content_editables)} contenteditable fields")
        
        div_inputs = await page.query_selector_all('div[role="textbox"], div[data-input], div[data-field]')
        print(f"Found {len(div_inputs)} div-based input fields")
        
        # Check details for each input
        for i, inp in enumerate(visible_inputs):
            inp_type = await inp.get_attribute('type') or 'text'
            name = await inp.get_attribute('name')
            inp_id = await inp.get_attribute('id')
            placeholder = await inp.get_attribute('placeholder')
            print(f"Input {i+1}: type={inp_type}, name={name}, id={inp_id}, placeholder={placeholder}")
        
        # Check details for each textarea
        for i, ta in enumerate(textareas):
            name = await ta.get_attribute('name')
            ta_id = await ta.get_attribute('id')
            placeholder = await ta.get_attribute('placeholder')
            print(f"Textarea {i+1}: name={name}, id={ta_id}, placeholder={placeholder}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_form_detection())
