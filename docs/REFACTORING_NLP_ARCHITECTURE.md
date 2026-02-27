# NLP2CMD — Refactoring Plan: From Regex to Multilingual NLP Architecture

**Project**: nlp2cmd · **Version**: 1.0.84 · **Date**: 2026-02-27  
**Scope**: ~55K lines across 400+ modules  

---

## 1. Problem Statement

### Current Architecture — Fragile Regex + Hardcoded Keywords

| Metric | Value | Risk |
|--------|-------|------|
| `re.search/match/findall/sub` calls | **259** across codebase | 🔴 High |
| Hardcoded Polish strings in code | **247** occurrences | 🔴 High |
| Hardcoded keyword lists `[...]` | **23** inline lists | 🟡 Medium |
| Files >500 lines (god objects) | **14** files | 🟡 Medium |
| Largest file (pipeline_runner.py) | **2,168 lines** | 🔴 High |

### Core Issues

1. **Regex-based intent detection** — Brittle, fails on typos, unseen phrasings, different word order. Every new language or synonym requires code changes.

2. **Polish-only hardcoded keywords** — `"otwórz"`, `"zamknij"`, `"wpisz"` etc. scattered across 247 locations. No multilingual abstraction.

3. **Monolithic pipeline** — `pipeline_runner.py` (2168 ln), `keyword_detector.py` (1110 ln), `template_generator.py` (1151 ln) — too many responsibilities per file.

4. **No semantic understanding** — Keyword matching doesn't understand synonyms, context, or intent beyond exact string matches. `"uruchom przeglądarkę"` works but `"odpal mi chromka"` doesn't.

5. **No centralized language model** — Each module reimplements its own keyword lists and regex patterns independently.

---

## 2. Target Architecture

```
                    ┌─────────────────────────────────┐
                    │       NL Query (any language)     │
                    └──────────────┬──────────────────┘
                                   ▼
                    ┌─────────────────────────────────┐
                    │     1. Normalizer + Tokenizer     │
                    │  • Unicode normalization           │
                    │  • Language detection (langdetect) │
                    │  • Stemming/lemmatization          │
                    │  • Typo correction (fuzzy match)   │
                    └──────────────┬──────────────────┘
                                   ▼
                    ┌─────────────────────────────────┐
                    │     2. Intent Classifier           │
                    │  • Sentence embeddings (SBERT)     │
                    │  • Cosine similarity to prototypes │
                    │  • Fallback: keyword + regex        │
                    │  • Confidence threshold gating      │
                    └──────────────┬──────────────────┘
                                   ▼
                    ┌─────────────────────────────────┐
                    │     3. Entity Extractor            │
                    │  • NER for URLs, emails, paths     │
                    │  • App name fuzzy matching          │
                    │  • Color/shape/number extraction    │
                    │  • Slot filling from prototypes     │
                    └──────────────┬──────────────────┘
                                   ▼
                    ┌─────────────────────────────────┐
                    │     4. Intent Router               │
                    │  browser | desktop | canvas |      │
                    │  shell | docker | sql | captcha    │
                    └──────┬───┬───┬───┬───┬───┬──────┘
                           │   │   │   │   │   │
                           ▼   ▼   ▼   ▼   ▼   ▼
                    ┌─────────────────────────────────┐
                    │     5. Command Generator           │
                    │  • Template-first (fast path)      │
                    │  • LLM fallback (complex queries)  │
                    │  • Schema-driven validation        │
                    └──────────────┬──────────────────┘
                                   ▼
                    ┌─────────────────────────────────┐
                    │     6. Executor + Video Recorder   │
                    │  Playwright | xdotool | subprocess │
                    └─────────────────────────────────┘
```

---

## 3. Refactoring Phases

### Phase R1: Language Abstraction Layer (Sprint 7, ~1 week)
**Goal**: Centralize all keyword/pattern definitions in data files, not code.

#### R1.1 — Create `data/intents/` YAML schema
```yaml
# data/intents/open_app.yaml
intent: open_app
domain: desktop
labels:
  pl: ["otwórz", "uruchom", "odpal", "włącz", "wystartuj", "zapal"]
  en: ["open", "launch", "start", "run", "execute", "fire up"]
  de: ["öffne", "starte", "führe aus"]
entities:
  - name: app
    type: app_name
    required: true
examples:
  pl: ["otwórz firefox", "uruchom przeglądarkę", "odpal mi chromka"]
  en: ["open firefox", "launch the browser", "start chrome"]
```

#### R1.2 — IntentRegistry: load from YAML, not code
```python
class IntentRegistry:
    """Centralized intent definitions loaded from YAML files."""
    
    def __init__(self, intents_dir: str = "data/intents/"):
        self.intents: dict[str, IntentDef] = {}
        self._load_all(intents_dir)
    
    def match(self, text: str, lang: str = "auto") -> list[IntentMatch]:
        """Match text against all registered intents."""
        ...
```

#### R1.3 — Replace inline keyword lists
- **Before**: 247 hardcoded Polish strings in `.py` files
- **After**: 0 hardcoded strings; all in `data/intents/*.yaml`
- **Migration**: Script to extract existing keywords → YAML files

**Estimated impact**: ~500 lines removed from adapter/pipeline code

---

### Phase R2: Semantic Intent Classification (Sprint 8, ~2 weeks)
**Goal**: Replace regex matching with embedding-based similarity.

#### R2.1 — Sentence Embeddings
```python
# src/nlp2cmd/nlp/intent_classifier.py

from sentence_transformers import SentenceTransformer

class SemanticIntentClassifier:
    """Classify intents using sentence embeddings + cosine similarity."""
    
    MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    # 118M params, supports 50+ languages, 384-dim embeddings
    
    def __init__(self, registry: IntentRegistry):
        self.model = SentenceTransformer(self.MODEL)
        self._precompute_prototypes(registry)
    
    def classify(self, text: str, top_k: int = 3) -> list[IntentMatch]:
        """
        1. Encode user query → 384-dim vector
        2. Cosine similarity against precomputed intent prototypes
        3. Return top-k matches with confidence scores
        """
        embedding = self.model.encode(text)
        similarities = cosine_similarity(embedding, self._prototypes)
        return self._rank(similarities, top_k)
```

**Why this model?**
- **Multilingual**: 50+ languages (Polish, English, German, etc.)
- **Fast**: ~5ms per query on CPU
- **Small**: 118M params, ~500MB disk
- **No regex needed**: Understands synonyms, paraphrases, typos

#### R2.2 — Hybrid Pipeline (embedding + keyword fallback)
```python
class HybridIntentClassifier:
    """Semantic first, keyword fallback."""
    
    def classify(self, text: str) -> IntentMatch:
        # Tier 1: Semantic (fast, handles unseen phrasings)
        semantic = self.semantic.classify(text, top_k=1)
        if semantic and semantic[0].confidence > 0.75:
            return semantic[0]
        
        # Tier 2: Keyword (deterministic, 100% precision for known phrases)
        keyword = self.keyword.classify(text)
        if keyword and keyword.confidence > 0.6:
            return keyword
        
        # Tier 3: LLM (expensive, for truly novel queries)
        return self.llm_fallback.classify(text)
```

**Estimated impact**: 
- ~200 regex patterns can be removed
- Intent detection works for unseen phrasings
- New languages added by editing YAML, not code

---

### Phase R3: Entity Extraction Modernization (Sprint 9, ~1 week)
**Goal**: Replace regex entity extraction with NER + fuzzy matching.

#### R3.1 — URL/Email/Path extraction via NER
```python
# Instead of 30+ regex patterns for URL extraction:
# re.search(r"(https?://\S+)", text)
# re.search(r"\b([a-z0-9][a-z0-9-]*(?:\.[a-z0-9]...

# Use a lightweight NER model or rule-based tokenizer:
from nlp2cmd.nlp.entity_extractor import EntityExtractor

extractor = EntityExtractor()
entities = extractor.extract("open github.com/wronai/nlp2cmd and go to issues")
# → [Entity(type="url", value="https://github.com/wronai/nlp2cmd"),
#    Entity(type="navigation_target", value="issues")]
```

#### R3.2 — App Name Fuzzy Matching
```python
# Instead of exact match against KNOWN_APPS dict:
from rapidfuzz import fuzz, process

class AppNameResolver:
    def resolve(self, text: str) -> Optional[AppInfo]:
        """Fuzzy match app names from any language."""
        # "chromka" → "chrome" (85% match)
        # "pajton" → "python" (80% match)
        match = process.extractOne(text, self.app_names, scorer=fuzz.WRatio)
        if match and match[1] > 70:
            return self.apps[match[0]]
```

#### R3.3 — Color/Shape extraction via data tables
```python
# Instead of inline dicts in canvas.py, desktop.py, complex_planner.py:
# COLORS = {"czerwony": "#FF0000", "red": "#FF0000", ...}

# Load from YAML:
# data/entities/colors.yaml
# data/entities/shapes.yaml
# data/entities/apps.yaml
```

---

### Phase R4: Pipeline Decomposition (Sprint 10, ~1.5 weeks)
**Goal**: Break god objects into focused modules.

| File | Current | Target | Action |
|------|---------|--------|--------|
| `pipeline_runner.py` | 2,168 ln | ~800 ln | Extract video, forms, navigation into separate classes |
| `keyword_detector.py` | 1,110 ln | ~300 ln | Replace with IntentRegistry + SemanticClassifier |
| `template_generator.py` | 1,151 ln | ~400 ln | Extract per-domain generators |
| `site_explorer.py` | 1,713 ln | ~600 ln | Extract form discovery, article extraction |
| `cli/commands/run.py` | 830 ln | ~400 ln | Extract browser detection logic |
| `regex.py` | 906 ln | ~200 ln | Replace most patterns with NER |

#### R4.1 — PipelineRunner decomposition
```
pipeline_runner.py (2168 ln) → 
├── pipeline_runner.py       (~400 ln) — orchestrator only
├── execution/dom_runner.py  (~500 ln) — Playwright actions
├── execution/video.py       (~150 ln) — video recording
├── execution/forms.py       (~300 ln) — form detection/fill
└── execution/navigation.py  (~200 ln) — goto, explore, extract
```

#### R4.2 — Keyword detection → data-driven
```
keyword_detector.py (1110 ln) →
├── data/intents/*.yaml      — intent definitions
├── nlp/intent_registry.py   — load + match
└── nlp/intent_classifier.py — semantic classification
```

---

### Phase R5: Error Resilience (Sprint 11, ~1 week)
**Goal**: Graceful degradation, not crashes.

#### R5.1 — Typo tolerance
```python
class QueryNormalizer:
    """Pre-process user input for robustness."""
    
    def normalize(self, text: str) -> str:
        # 1. Unicode NFKC normalization
        text = unicodedata.normalize("NFKC", text)
        # 2. Strip diacritics for matching (keep original for display)
        # 3. Fix common typos via Levenshtein distance
        # 4. Expand abbreviations (npm → node package manager)
        return text
```

#### R5.2 — Confidence-gated execution
```python
class ConfidenceGate:
    """Only execute commands above confidence threshold."""
    
    THRESHOLDS = {
        "shell": 0.7,       # shell commands can be dangerous
        "browser": 0.5,     # browser actions are safe
        "canvas": 0.4,      # drawing is always safe
        "sql": 0.8,         # SQL can modify data
        "docker": 0.75,     # container ops need precision
    }
```

#### R5.3 — Structured error recovery
Instead of generic `except Exception: pass` (currently ~50 occurrences):
```python
class NLP2CMDError(Exception):
    """Base error with structured context."""
    def __init__(self, message: str, *, code: str, context: dict):
        self.code = code
        self.context = context
```

---

### Phase R6: Testing & Benchmarking (Sprint 12, ~1 week)
**Goal**: Automated quality gates.

#### R6.1 — Intent classification benchmark
```yaml
# tests/benchmarks/intent_classification.yaml
- query: "otwórz przeglądarkę"
  expected_intent: open_app
  expected_entities: {app: browser}
- query: "odpal mi chrome'a"   # colloquial Polish
  expected_intent: open_app
  expected_entities: {app: chrome}
- query: "open the web browser"
  expected_intent: open_app
  expected_entities: {app: browser}
- query: "starte den browser"  # German
  expected_intent: open_app
  expected_entities: {app: browser}
```

#### R6.2 — Regression test per language
```python
@pytest.mark.parametrize("lang,query,intent", [
    ("pl", "otwórz firefox", "open_app"),
    ("pl", "uruchom przeglądarkę", "open_app"),
    ("pl", "odpal mi chromka", "open_app"),  # colloquial
    ("en", "launch the browser", "open_app"),
    ("en", "fire up chrome", "open_app"),
    ("de", "öffne den browser", "open_app"),
])
def test_multilingual_intent(lang, query, intent):
    result = classifier.classify(query)
    assert result.intent == intent
```

---

## 4. New Dependencies

```toml
[project.optional-dependencies]
nlp-core = [
    "sentence-transformers>=2.2.0",  # multilingual embeddings
    "rapidfuzz>=3.0.0",               # fuzzy string matching
    "langdetect>=1.0.9",              # language detection
    "unicodedata2>=15.0.0",           # Unicode normalization
]
```

**Size impact**: ~500MB for sentence-transformers model (cached, downloaded once)
**Speed impact**: ~5ms per query for embedding (vs ~1ms for regex)

---

## 5. Migration Strategy

### Backward Compatibility
- All YAML intent files auto-generated from existing hardcoded keywords
- Hybrid classifier uses keyword fallback for 100% backward compat
- Semantic classifier only adds coverage, never removes it
- Feature flag: `NLP2CMD_USE_SEMANTIC=1` to enable/disable

### Phase Rollout
| Phase | Sprint | Duration | Risk | Backward Compat |
|-------|--------|----------|------|-----------------|
| R1 Language Abstraction | 7 | 1 week | 🟢 Low | ✅ Full |
| R2 Semantic Classification | 8 | 2 weeks | 🟡 Medium | ✅ Hybrid |
| R3 Entity Extraction | 9 | 1 week | 🟢 Low | ✅ Full |
| R4 Pipeline Decomposition | 10 | 1.5 weeks | 🟡 Medium | ✅ Full |
| R5 Error Resilience | 11 | 1 week | 🟢 Low | ✅ Full |
| R6 Testing & Benchmarks | 12 | 1 week | 🟢 Low | ✅ Full |

**Total**: ~8 weeks (Sprints 7-12)

---

## 6. Expected Outcomes

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Regex patterns in code | 259 | ~50 | -80% |
| Hardcoded Polish strings | 247 | 0 | -100% |
| Supported languages | 1 (Polish + some English) | 50+ | +4900% |
| Typo tolerance | None | Levenshtein + fuzzy | ∞ |
| Intent detection accuracy | ~85% (tested phrases only) | ~95% (semantic) | +12% |
| Unseen phrasing handling | ❌ Fails | ✅ Semantic similarity | New |
| Largest file | 2,168 lines | ~800 lines | -63% |
| New language addition | Code changes required | Edit YAML file | 0 code |

---

*Generated from project.toon v1.0.84 analysis. Plan accounts for 400+ modules and 55K lines of code.*
