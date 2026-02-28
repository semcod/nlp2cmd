with open("src/nlp2cmd/automation/action_planner.py", "r") as f:
    text = f.read()

import re

# 1. Update SYSTEM_PROMPT to include canvas operations
old_prompt = """_SYSTEM_PROMPT = \"\"\"\\
Jesteś planistą akcji browser automation.
Dekomponujesz złożone komendy na sekwencję kroków.

Dostępne akcje:
- browser_open: Otwórz przeglądarkę
- navigate: Przejdź na URL {url}
- click: Kliknij element {selector} lub {text}
- type_text: Wpisz tekst {text} w pole {selector}
- extract_text: Wyciągnij tekst z {selector} pasujący do {pattern}
- extract_api_key: Wyciągnij API key z serwisu {service}
- save_env: Zapisz wartość do .env {var_name}={value}
- fill_form: Wypełnij formularz {fields}
- submit_form: Wyślij formularz
- screenshot: Zrób screenshot
- wait: Czekaj {ms} milisekund
- new_tab: Otwórz nowy tab
- switch_tab: Przełącz na tab {filter}
- login: Zaloguj się {email} {password}"""

new_prompt = """_SYSTEM_PROMPT = \"\"\"\\
Jesteś planistą akcji browser automation oraz rysowania na canvas (jspaint).
Dekomponujesz złożone komendy na sekwencję kroków.

Dostępne akcje:
- browser_open: Otwórz przeglądarkę
- navigate: Przejdź na URL {url}
- click: Kliknij element {selector} lub {text}
- type_text: Wpisz tekst {text} w pole {selector}
- extract_text: Wyciągnij tekst z {selector} pasujący do {pattern}
- extract_api_key: Wyciągnij API key z serwisu {service}
- save_env: Zapisz wartość do .env {var_name}={value}
- fill_form: Wypełnij formularz {fields}
- submit_form: Wyślij formularz
- screenshot: Zrób screenshot {suffix?}
- wait: Czekaj {ms} milisekund
- new_tab: Otwórz nowy tab
- switch_tab: Przełącz na tab {filter}
- login: Zaloguj się {email} {password}

Akcje rysowania (na jspaint.app):
- wait_for_canvas: Poczekaj na załadowanie canvas
- get_canvas_center: Pobierz środek canvas
- select_tool: Wybierz narzędzie {tool} (dostępne: pencil, brush, fill, ellipse, rectangle, line, text, eraser, select)
- set_color: Ustaw kolor {color} (#RRGGBB)
- draw_circle: Narysuj okrąg {radius, offset: [x, y]}
- draw_ellipse: Narysuj elipsę {rx, ry, offset: [x, y]}
- draw_filled_ellipse: Narysuj wypełnioną elipsę {rx, ry, relative_to: "center"}
- draw_rectangle: Narysuj prostokąt {width, height, offset: [x, y]}
- draw_line: Narysuj linię {from_offset: [x, y], to_offset: [x, y]}
- fill_at: Wypełnij w punkcie {offset: [x, y]}
- click_canvas: Kliknij canvas w punkcie {offset: [x, y]}"""

text = text.replace(old_prompt, new_prompt)

# 2. Fix the canvas heuristic fallback so it returns None when no template is matched
# This allows it to fall through to the LLM.

target_heuristic = """        # Generic canvas: navigate + echo instruction
        url_match = re.search(
            r'\\b([a-zA-Z0-9][\\w\\-]*\\.(?:app|com|io))\\b', text,
        )
        url = f"https://{url_match.group(1)}" if url_match else "https://jspaint.app"

        return ActionPlan(
            query=query,
            steps=[
                ActionStep(
                    action="navigate",
                    params={"url": url},
                    description=f"Otwórz {url}",
                ),
                ActionStep(
                    action="wait", params={"ms": 3000},
                    description="Poczekaj na załadowanie canvas",
                ),
                ActionStep(
                    action="echo",
                    params={"text": (
                        f"🎨 Otwarto {url}. Rysowanie wymaga adaptera canvas.\\n"
                        f"   Użyj: python3 examples/06_desktop_automation/"
                        f"09_complex_commands/run.py --query \\"{query}\\""
                    )},
                    description="Instrukcja rysowania",
                ),
            ],
            confidence=0.75,
            source="canvas_heuristic",
            estimated_time_ms=5000,
        )"""

replacement_heuristic = """        # Generic canvas: no template match, let the LLM handle it
        return None"""

text = text.replace(target_heuristic, replacement_heuristic)

with open("src/nlp2cmd/automation/action_planner.py", "w") as f:
    f.write(text)
