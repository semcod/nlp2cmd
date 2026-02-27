# 08 — CAPTCHA Solver: LLM Vision Automation

Detect and solve CAPTCHAs on web pages using LLM vision (OpenRouter → Gemini 2.5 Pro).

## What it does

1. Navigates to a page with CAPTCHA
2. Detects CAPTCHA type (image, reCAPTCHA v2, hCaptcha, slider)
3. Takes screenshot of the CAPTCHA
4. Sends to Gemini 2.5 Pro via OpenRouter for analysis
5. Interacts with the page to solve (type text, click tiles, drag slider)

## Supported CAPTCHA types

- **Image CAPTCHA** — text/number recognition via LLM OCR
- **reCAPTCHA v2** — checkbox + image tile selection
- **hCaptcha** — image tile selection
- **Slider CAPTCHA** — puzzle piece drag alignment

## Prerequisites

```bash
export OPENROUTER_API_KEY="sk-or-v1-..."
pip install playwright httpx
playwright install chromium
```

## Run

```bash
cd examples/06_desktop_automation/08_captcha_solver
python3 run.py --url "https://example.com/login"
```

## Notes

- Requires `OPENROUTER_API_KEY` for LLM vision API
- Uses Gemini 2.5 Pro Preview for best accuracy
- Human-like mouse movements to avoid detection
- Not guaranteed to work on all CAPTCHA implementations
