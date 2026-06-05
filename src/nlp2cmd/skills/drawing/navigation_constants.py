DRAWING_SITES = {
    "jspaint": {
        "urls": ["https://jspaint.app", "https://jspaint.app/"],
        "canvas_selector": "canvas",
        "tool_selector": ".tool[title*='Pencil'], .tool[title*='pencil']",
        "fallback_order": 1,
    },
    "excalidraw": {
        "urls": ["https://excalidraw.com/", "https://excalidraw.com"],
        "canvas_selector": "canvas",
        "tool_selector": None,
        "fallback_order": 2,
    },
    "kleki": {
        "urls": ["https://kleki.com/", "https://kleki.com"],
        "canvas_selector": "canvas",
        "tool_selector": None,
        "fallback_order": 3,
    },
    "draw.chat": {
        "urls": [
            "https://draw.chat/",
            "https://draw.chat/pl/index.html",
            "https://draw.chat/en/index.html",
        ],
        "canvas_selector": "canvas",
        "tool_selector": None,
        "fallback_order": 4,
    },
}

POPUP_TEXTS = [
    "Accept", "Accept all", "Akceptuję", "Zaakceptuj wszystko",
    "Accept cookies", "Agree", "Zgadzam się", "I understand", "Rozumiem",
    "OK", "Got it", "Close", "Zamknij", "×", "Zrozumiałem",
    "Skip", "Pomiń", "No thanks", "Not now", "Później", "Nie teraz",
    "Maybe later", "Continue", "Kontynuuj", "Dalej",
]

POPUP_CSS_SELECTORS = [
    '[class*="cookie"] button', '[class*="consent"] button',
    '[id*="cookie"] button', '[id*="consent"] button',
    '[class*="gdpr"] button', '.cc-dismiss', '.cc-allow',
    '#onetrust-accept-btn-handler',
    'button[aria-label="Close"]', 'button[aria-label="close"]',
    '[class*="modal"] button[class*="close"]',
    '[role="dialog"] button[class*="close"]',
]

CANVAS_VERIFY_PROMPT = """Analyze this screenshot of a web application.

Answer these questions in JSON format:
1. Is there a drawing canvas visible? (yes/no)
2. Is the canvas ready for drawing (no popups/modals blocking it)?
3. What drawing tool is currently selected (pencil/brush/none/unknown)?
4. Are there any popups, modals, or cookie banners visible?
5. Brief description of what you see.

Respond ONLY with JSON:
{
  "has_canvas": true,
  "canvas_ready": true,
  "current_tool": "pencil",
  "has_popups": false,
  "popup_description": "",
  "description": "MS Paint clone with white canvas and tool palette on left"
}"""

FIND_POPUP_CLOSE_PROMPT = """Look at this screenshot. There are popups or modals blocking the canvas.

Find the close/dismiss/accept button for each popup. Return the approximate pixel coordinates
of each button to click, in order of priority.

Respond ONLY with JSON:
{
  "buttons": [
    {"label": "Accept cookies", "x": 500, "y": 400, "priority": 1},
    {"label": "Close modal", "x": 800, "y": 200, "priority": 2}
  ]
}"""

FIND_TOOL_PROMPT = """Look at this screenshot of a drawing application.

I need to select the pencil/freehand drawing tool. Find the button or icon
for the pencil/pen/brush/freehand tool.

Return the approximate pixel coordinates of the tool button.

Respond ONLY with JSON:
{
  "found": true,
  "tool_name": "pencil",
  "x": 50,
  "y": 200,
  "confidence": 0.9
}"""


# ── DrawNavigationSkill ───────────────────────────────────────────────────

