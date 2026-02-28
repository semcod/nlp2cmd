"""
Complex Query Detector for NLP2CMD.

Detects multi-step commands BEFORE the main keyword detection pipeline.
Uses only regex — zero LLM overhead (~0.1ms).

Position: Layer 0.5 — after cache lookup, before keyword detection.

Example:
    detector = ComplexQueryDetector()
    result = detector.analyze("otwórz przeglądarkę i stronę openrouter.ai, "
                              "wyciągnij klucz API i zapisz do .env")
    # result.is_complex == True
    # result.num_intents == 4
    # result.intents == ["browser:launch", "browser:navigate",
    #                     "browser:extract_data", "browser:save_file"]
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class ComplexityAnalysis:
    """Result of multi-step complexity analysis."""
    is_complex: bool              # Requires decomposition?
    num_intents: int              # How many intents detected?
    intents: list[str] = field(default_factory=list)  # Detected intent labels
    requires_llm_planning: bool = False  # Needs LLM planner? (>=3 intents)
    confidence: float = 0.0       # Analysis confidence


class ComplexQueryDetector:
    """Detects multi-step commands BEFORE the keyword detection pipeline.

    Cost: ~0.1ms (regex only, zero LLM).
    Position: Layer 0.5 — after cache, before keyword detection.
    """

    # Connectors joining multiple actions
    CHAIN_SIGNALS = [
        r"\bi\b",                    # "otwórz X i Y"
        r"\bpotem\b",               # "otwórz X, potem Y"
        r"\bnast[eę]pnie\b",        # "następnie"
        r"\ba\s+potem\b",           # "a potem"
        r"\bpo\s+czym\b",           # "po czym"
        r"\bthen\b",                # English
        r"\band\s+then\b",
    ]

    # Browser-specific intents
    BROWSER_INTENTS: dict[str, list[str]] = {
        "launch": [
            r"otw[oó]rz\s+przegl[aą]dark",
            r"uruchom\s+(?:firefox|chrome|przegl[aą]dark)",
            r"w[łl][aą]cz\s+przegl[aą]dark",
        ],
        "navigate": [
            r"(?:wejd[zź]|przejd[zź]|id[zź])\s+na\s+(?:stron|link|url)",
            r"otw[oó]rz\s+(?:stron|link|url)",
            r"otw[oó]rz\s+\S+\.\w{2,}",  # "otwórz openrouter.ai"
            r"(?:wejd[zź]|przejd[zź]|id[zź])\s+na\s+\S+\.\w{2,}",  # "wejdź na jspaint.app"
        ],
        "click": [
            r"kliknij",
            r"naci[sś]nij",
            r"wci[sś]nij\s+przycisk",
        ],
        "fill_form": [
            r"wype[lł]nij\s+(?:formularz|pole|dane)",
            r"wpisz\s+(?:dane|tekst|has[lł]o|email)",
        ],
        "extract_data": [
            r"(?:wyci[aą]gnij|skopiuj|pobierz|odczytaj)\s+(?:klucz|key|token|api|tekst|dane|kod)",
            r"(?:wyci[aą]gnij|skopiuj).+(?:ze?\s+strony|z\s+przegladarki)",
        ],
        "save_file": [
            r"zapi[sś]\s+(?:do|w)\s+(?:\.env|pliku|folderu)",
            r"(?:zapisz|eksportuj|wklej)\s+(?:do|w)\s+\S+",
        ],
        "new_tab": [
            r"(?:nowy|otw[oó]rz)\s+(?:tab|kart[eę])",
        ],
        "login": [
            r"zaloguj\s+si[eę]",
            r"(?:wpisz|podaj)\s+(?:login|has[lł]o|email|dane\s+logowania)",
        ],
        "captcha": [
            r"(?:rozwi[aą][zż]|obejd[zź]|kliknij)\s+captcha",
            r"nie\s+jestem\s+robotem",
        ],
        "screenshot": [
            r"(?:zr[oó]b|wykonaj|zapisz)\s+(?:screenshot|zrzut)",
        ],
    }

    # Canvas/drawing intents for paint applications
    CANVAS_INTENTS: dict[str, list[str]] = {
        "draw": [
            r"narysuj",
            r"rysuj",
            r"namaluj",
            r"maluj",
            r"naszkicuj",
            r"skicuj",
            r"draw",
            r"paint",
        ],
        "draw_shape": [
            r"narysuj\s+(?:ko[lł]o|kwadrat|prostok[aą]t|tr[oó]jk[aą]t|owal|lini[eę]|strza[lł]k[eę])",
            r"draw\s+(?:circle|square|rectangle|triangle|oval|line|arrow)",
        ],
        "fill": [
            r"wype[lł]nij",
            r"zamalu[jj]",
            r"fill",
            r"zafarbu[jj]",
        ],
        "select_color": [
            r"wybierz\s+kolor",
            r"kolor\s+czerwony|niebieski|zielony|ż[oó][lł]ty|czarny|bia[lł]y",
            r"select\s+color",
            r"red|blue|green|yellow|black|white\s+color",
        ],
        "clear_canvas": [
            r"wyczy[sś][ćc]\s+(?:p[lł]utno|kanw[aę]|ekran)",
            r"nowy\s+rysunek",
            r"clear\s+canvas",
            r"new\s+drawing",
        ],
        "undo": [
            r"cofnij",
            r"undo",
            r"wr[oó][ćc]",
        ],
        "save_image": [
            r"zapisz\s+(?:obraz|rysunek|obrazek|plik)",
            r"eksportuj",
            r"save\s+(?:image|drawing|file)",
            r"export",
        ],
    }

    # Desktop application intents
    DESKTOP_INTENTS: dict[str, list[str]] = {
        "email_check": [
            r"(?:sprawdz|otw[oó]rz)\s+(?:poczt|mail|email)",
            r"(?:thunderbird|evolution|outlook)",
        ],
        "email_send": [
            r"(?:wy[sś]lij|napisz)\s+(?:mail|email|wiadomo[sś][cć])",
            r"odpowiedz\s+na\s+(?:mail|wiadomo[sś][cć])",
        ],
        "app_launch": [
            r"(?:otw[oó]rz|uruchom|w[lł][aą]cz)\s+(?:terminal|edytor|vscode|libreoffice)",
        ],
    }

    def analyze(self, query: str) -> ComplexityAnalysis:
        """Analyze query complexity. Cost: ~0.1ms."""
        text = query.lower().strip()

        detected_intents: list[str] = []

        # Check browser intents
        for intent_name, patterns in self.BROWSER_INTENTS.items():
            for pattern in patterns:
                if re.search(pattern, text):
                    detected_intents.append(f"browser:{intent_name}")
                    break

        # Check canvas intents
        for intent_name, patterns in self.CANVAS_INTENTS.items():
            for pattern in patterns:
                if re.search(pattern, text):
                    detected_intents.append(f"canvas:{intent_name}")
                    break

        # Check desktop intents
        for intent_name, patterns in self.DESKTOP_INTENTS.items():
            for pattern in patterns:
                if re.search(pattern, text):
                    detected_intents.append(f"desktop:{intent_name}")
                    break

        # Count chain connectors
        chain_count = sum(
            1 for p in self.CHAIN_SIGNALS if re.search(p, text)
        )

        # Complexity analysis
        num_intents = len(detected_intents)
        is_complex = num_intents >= 2 or (num_intents >= 1 and chain_count >= 1)

        return ComplexityAnalysis(
            is_complex=is_complex,
            num_intents=num_intents,
            intents=detected_intents,
            requires_llm_planning=num_intents >= 3,  # >=3 intents → LLM
            confidence=min(0.95, 0.5 + num_intents * 0.15 + chain_count * 0.1),
        )
