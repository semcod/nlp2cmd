# NLP2CMD Debug Log

**Generated:** 2026-02-28T09:55:37.796959

**Query:** `wejdź na jspaint.app i narysuj biedronkę`

# Decision Tree for Query: "wejdź na jspaint.app i narysuj biedronkę"

## Step 1: Intent Detection

### Top Intent Matches:
1. 🟢 **draw** (confidence: 0.95)
   - Domain: `canvas`
   - Method: `keyword`
   - Matched label: `narysuj` (pl)

2. 🟢 **navigate** (confidence: 0.95)
   - Domain: `browser`
   - Method: `keyword`
   - Matched label: `wejdz na` (pl)

3. 🟡 **close_app** (confidence: 0.77)
   - Domain: `desktop`
   - Method: `fuzzy`
   - Matched label: `zamknij` (pl)

4. 🟡 **email_compose** (confidence: 0.77)
   - Domain: `desktop`
   - Method: `fuzzy`
   - Matched label: `napisz maila` (pl)

5. 🟡 **minimize_all** (confidence: 0.77)
   - Domain: `desktop`
   - Method: `fuzzy`
   - Matched label: `schowaj okna` (pl)

## Step 2: Pipeline Processing

### Detection Result:
- **Domain:** `multi_step`
- **Intent:** `cached_plan`
- **Detection Confidence:** 0.85
- **Source:** `multistep_cache`

## Step 3: Entity Extraction

🔴 **No entities extracted!**

## Step 4: Command Generation

- **Template Used:** `N/A`
- **Final Confidence:** 0.85

## Step 5: Final Result

✅ **Success!** Generated command:
```bash

```

## Metadata

- **Latency:** 0.6 ms

## Multi-Step Action Plan

- **Steps:** 1
- **Plan Source:** `cache`
- **Plan Confidence:** 0.85
