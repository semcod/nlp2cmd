# Keyword Intent Detection Flow

## Overview

The `KeywordIntentDetector` uses a multi-layered approach to detect domain and intent from natural language input. Each layer acts as a fallback mechanism, ensuring robust detection even when some methods fail or dependencies are missing.

## Detection Pipeline

The detection process follows this exact order:

### 1. Text Normalization (`_normalize_text_lower`)
**Always active** - No dependencies

```python
def _normalize_text_lower(self, text_lower: str) -> str:
```

**Steps:**
- Polish diacritic normalization (`ł` → `l`, `ą` → `a`, etc.)
- Common typo corrections (`doker` → `docker`, `dokcer` → `docker`)
- Verb normalization (`startuj` → `uruchom`)
- Optional spaCy lemmatization (if Polish model available)

**Fallback behavior:** Always works, gracefully handles missing spaCy

---

### 2. Fast Path Detection (`_detect_fast_path`)
**Always active** - No dependencies

```python
def _detect_fast_path(self, text_lower: str) -> Optional[DetectionResult]:
```

**Purpose:** Quick detection of browser and search queries
**Patterns:**
- Browser: `przeglądark`, `browser`, `otwórz stronę`, `open url`
- Search: `szukaj w google`, `wyszukaj w google`, `search web`

**Fallback behavior:** Returns `None` if no match, continues to next step

---

### 3. SQL Context Detection (`_compute_sql_context`)
**Always active** - No dependencies

```python
def _compute_sql_context(self, text_lower: str) -> tuple[bool, bool]:
```

**Purpose:** Determine if text contains SQL keywords
**Returns:** `(sql_context, sql_explicit)`

**Fallback behavior:** Always works, returns `(False, False)` if no SQL context

---

### 4. SQL DROP Table Detection (`_detect_sql_drop_table`)
**Conditional** - Requires SQL context

```python
def _detect_sql_drop_table(self, text_lower: str, *, sql_context: bool, sql_explicit: bool) -> Optional[DetectionResult]:
```

**Purpose:** High-priority detection of dangerous SQL DROP operations
**Activation:** Only runs if `sql_context` is `True`

**Fallback behavior:** Returns `None` if no DROP pattern, continues to next step

---

### 5. Explicit Docker Detection (`_detect_explicit_docker`)
**Always active** - No dependencies

```python
def _detect_explicit_docker(self, text_lower: str) -> Optional[DetectionResult]:
```

**Purpose:** High-priority detection of Docker commands
**Patterns:** `docker run`, `docker stop`, `docker-compose`, etc.

**Fallback behavior:** Returns `None` if no Docker pattern, continues to next step

---

### 6. Explicit Kubernetes Detection (`_detect_explicit_kubernetes`)
**Always active** - No dependencies

```python
def _detect_explicit_kubernetes(self, text_lower: str) -> Optional[DetectionResult]:
```

**Purpose:** High-priority detection of Kubernetes commands
**Patterns:** `kubectl`, `k8s`, `pod`, `deployment`, etc.

**Fallback behavior:** Returns `None` if no K8s pattern, continues to next step

---

### 7. Explicit Service Restart Detection (`_detect_explicit_service_restart`)
**Always active** - No dependencies

```python
def _detect_explicit_service_restart(self, text_lower: str) -> Optional[DetectionResult]:
```

**Purpose:** High-priority detection of service restart commands
**Patterns:** `restartuj usługę`, `systemctl restart`, etc.

**Fallback behavior:** Returns `None` if no restart pattern, continues to next step

---

### 8. Priority Intents Detection (`_detect_best_from_priority_intents`)
**Always active** - No dependencies

```python
def _detect_best_from_priority_intents(self, text_lower: str, *, sql_context: bool, sql_explicit: bool) -> Optional[DetectionResult]:
```

**Purpose:** Check high-priority intents first (configured in `keyword_intent_detector_config.json`)
**Priority Order (Shell):** `service_start`, `service_restart`, `service_stop`, `service_status`, then others

**Fallback behavior:** Returns `None` if no priority intent matches, continues to next step

---

### 9. General Pattern Matching (`_detect_best_from_patterns`)
**Always active** - No dependencies

```python
def _detect_best_from_patterns(self, text_lower: str, *, sql_context: bool, sql_explicit: bool) -> Optional[DetectionResult]:
```

**Purpose:** General keyword matching across all domains and intents
**Process:**
1. Iterate through all domains/intents
2. Check domain scan permissions (domain boosters required for Docker/K8s)
3. Match keywords using `_match_keyword`
4. Calculate confidence scores with bonuses
5. Return best match above threshold

**Fallback behavior:** Returns `None` if no pattern matches confidence threshold, continues to next step

---

### 10. Fuzzy Matching Fallback (`_detect_best_from_fuzzy`)
**Conditional** - Requires `rapidfuzz` library

```python
def _detect_best_from_fuzzy(self, text_lower: str) -> Optional[DetectionResult]:
```

**Purpose:** Handle typos and variations using fuzzy string matching
**Activation:** Only runs if `rapidfuzz` is installed
**Threshold:** 85% similarity minimum

**Fallback behavior:** Returns `None` if rapidfuzz not installed or no good matches, continues to next step

---

### 11. Final Fallback (`unknown` intent)
**Always active** - No dependencies

```python
return DetectionResult(
    domain='unknown',
    intent='unknown', 
    confidence=0.0,
    matched_keyword=None,
)
```

**Purpose:** Guaranteed return value when all detection methods fail

---

## Dependency Matrix

| Method | Dependencies | Always Works? | Fallback |
|--------|--------------|---------------|----------|
| Text Normalization | None (optional spaCy) | ✅ Yes | Regex-only normalization |
| Fast Path Detection | None | ✅ Yes | Returns `None` |
| SQL Context Detection | None | ✅ Yes | Returns `(False, False)` |
| SQL DROP Detection | SQL context only | ✅ Yes | Returns `None` |
| Docker Detection | None | ✅ Yes | Returns `None` |
| Kubernetes Detection | None | ✅ Yes | Returns `None` |
| Service Restart Detection | None | ✅ Yes | Returns `None` |
| Priority Intents | None | ✅ Yes | Returns `None` |
| Pattern Matching | None | ✅ Yes | Returns `None` |
| Fuzzy Matching | `rapidfuzz` library | ❌ No | Skipped if missing |
| Final Fallback | None | ✅ Yes | Always returns result |

## Failure Scenarios

### Scenario 1: Missing spaCy Model
```
Input: "restartuj usługę nginx"
1. Text normalization: Uses regex only (no lemmatization)
2. Fast path: No match
3. SQL context: No SQL keywords
4. Pattern matching: Finds "restartuj usługę" → service_restart
Result: ✅ Works correctly
```

### Scenario 2: Missing rapidfuzz Library
```
Input: "dokcer ps" (typo)
1. Text normalization: "dokcer" → "docker"
2. Pattern matching: "docker ps" → docker/list
Result: ✅ Works correctly (fuzzy not needed)
```

### Scenario 3: No Dependencies Available
```
Input: "unknown command xyz"
1. All detection methods return None
2. Final fallback: unknown/unknown
Result: ✅ Always returns something
```

### Scenario 4: Domain Booster Missing
```
Input: "ps" (no docker keyword)
1. Domain scan for Docker: Requires booster → fails
2. Shell pattern matching: "ps" → list_processes
Result: ✅ Falls back to shell
```

## Confidence Scoring

- **Base confidence:** 0.70 for pattern matches
- **Priority intents:** 0.85 base confidence
- **Keyword length bonus:** Up to +0.20 for longer keywords
- **Service intent bonus:** +0.05 for service_* intents
- **Domain boost:** +0.05 per matching domain booster (max +0.15)
- **Position bonus:** +0.05 for early keyword matches
- **Maximum confidence:** 0.95

## Configuration

### Priority Intents (`keyword_intent_detector_config.json`)
```json
{
  "priority_intents": {
    "shell": ["service_start", "service_restart", "service_stop", "service_status", ...]
  }
}
```

### Domain Boosters
```json
{
  "domain_boosters": {
    "docker": ["docker", "doker", "dokcer", "kontener", ...],
    "shell": ["plik", "file", "katalog", "directory", ...]
  }
}
```

### Fast Path Keywords
```json
{
  "fast_path": {
    "browser_keywords": ["przeglądark", "browser", ...],
    "search_keywords": ["szukaj w google", "search web", ...]
  }
}
```

## Guarantees

1. **Always returns a result** - The final fallback ensures no method returns `None`
2. **Graceful degradation** - Missing dependencies don't break the pipeline
3. **Deterministic behavior** - Same input always produces same output
4. **Performance optimization** - Fast path and priority checks first
5. **Safety first** - Dangerous operations (SQL DROP) get highest priority

## Testing

The system is tested with:
- **Exact matches:** Standard keyword detection
- **Typos:** Fuzzy matching and normalization
- **Word order variations:** Pattern flexibility
- **Missing dependencies:** Graceful fallback behavior
- **Edge cases:** Empty input, special characters, mixed languages

All tests pass regardless of optional dependencies being available.
