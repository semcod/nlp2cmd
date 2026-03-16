# Web Schema Guide

## Overview

The Web Schema system enables NLP2CMD to understand and interact with real websites by extracting their UI structure and converting natural language commands into browser automation actions.

## Architecture

### Web Schema Extraction

The system uses Playwright to extract interactive elements from websites:

```bash
nlp2cmd web-schema extract https://github.com --headless
```

### Schema Structure

Extracted schemas contain:

- **Actions**: Interactive elements (inputs, buttons, links)
- **Metadata**: Element selectors and types
- **Examples**: Natural language command patterns

## Supported Websites

### Currently Supported

1. **GitHub** (`github.com`)
   - Repository search
   - User lookup
   - Code navigation
   - Form interactions

2. **Google** (`google.com`)
   - Search interface
   - Application navigation
   - Form filling

3. **Amazon** (`amazon.com`)
   - Product search
   - Shopping cart
   - Form interactions

### Adding New Websites

```bash
# Extract schema from any website
nlp2cmd web-schema extract https://example.com --headless

# The schema will be saved to:
# command_schemas/sites/example.com.json
```

## Site Explorer (Automatic Form Discovery)

The `SiteExplorer` provides automatic discovery of forms and content across entire websites, even when they're not on the initially loaded page.

### How It Works

1. **Crawl website** - Follows links from navigation, sitemap.xml
2. **Analyze pages** - Detects forms, content types
3. **Score relevance** - Matches pages to search intent
4. **Navigate automatically** - Goes to best matching page

### Usage

```python
from nlp2cmd.web_schema import SiteExplorer

explorer = SiteExplorer(max_depth=2, max_pages=10)

# Find contact forms
result = explorer.find_form("https://example.com", intent="contact")
if result.success:
    print(f"Found form at: {result.form_url}")
    # Automatically navigated to contact page

# Find content pages
result = explorer.find_content(
    "https://example.com",
    content_type="article"  # or "product", "docs"
)

# Universal exploration with intent detection
result = explorer.explore(
    "https://example.com",
    "find pricing information"  # Auto-detects "product" intent
)
```

### Automatic Form Discovery in Browser Commands

When using CLI with `-r` flag, form discovery happens automatically:

```bash
# If form not on main page, SiteExplorer searches the site
nlp2cmd -r "wejdź na maskservice.pl i wypełnij formularz kontaktu"

# Output:
# 🔍 Exploring site for contact form...
# ✓ Found form at: https://www.maskservice.pl/en/contact
# Form submitted via: input[type="submit"]
```

### Supported Intents

- **contact** - Contact forms, support pages
- **article** - Blog posts, news, publications  
- **product** - Product pages, pricing, catalogs
- **docs** - Documentation, guides, FAQ

### Features

- **Sitemap parsing** - Reads sitemap.xml for efficient crawling
- **Cookie consent handling** - Auto-dismisses common popups
- **Iframe support** - Detects forms inside iframes
- **Multi-language** - Polish and English keyword support
- **Depth control** - Configurable crawl depth and page limits

### Configuration

```python
from nlp2cmd.web_schema import SiteExplorer

explorer = SiteExplorer(
    max_depth=2,           # How many levels deep to crawl
    max_pages=10,          # Maximum pages to visit
    headless=True,         # Run browser headless
    timeout_ms=15000,      # Page load timeout
    dynamic_wait_ms=3000,  # Wait for JS frameworks
)
```

## Browser Domain Integration

### Browser Intents

The browser domain supports four main intents:

#### 1. Web Action
General web interactions including typing, clicking, and navigating.

```python
# Examples
"wpisz tekst w wyszukiwarce google" → browser/web_action
"kliknij przycisk sign in" → browser/web_action
"wypełnij formularz rejestracji" → browser/web_action
```

#### 2. Navigate
Page navigation and URL opening.

```python
# Examples
"przejdź do github" → browser/navigate
"otwórz stronę google" → browser/navigate
"idź na stronę główną" → browser/navigate
```

#### 3. Click
Button and link clicking.

```python
# Examples
"kliknij przycisk" → browser/click
"wybierz opcję" → browser/click
"aktywuj link" → browser/click
```

#### 4. Fill Form
Form filling and data entry.

```python
# Examples
"wypełnij formularz" → browser/fill_form
"podaj dane kontaktowe" → browser/fill_form
"zarejestruj się" → browser/fill_form
```

## Usage Examples

### Basic Web Interactions

```bash
# Search on Google
nlp2cmd --query "wyszukaj python tutorial w google"

# Navigate to GitHub
nlp2cmd --query "przejdź do github"

# Fill form on website
nlp2cmd --query "wypełnij formularz kontaktowy"

# Click button
nlp2cmd --query "kliknij przycisk submit"
```

### Site-Specific Commands

#### GitHub Commands

```bash
# Search repositories
nlp2cmd --query "znajdź repozytorium nlp2cmd na github"

# User lookup
nlp2cmd --query "wyszukaj użytkownika tomek na github"

# Code navigation
nlp2cmd --query "przejdź do kodu projektu"
```

#### Google Commands

```bash
# Search queries
nlp2cmd --query "wyszukaj najlepsze kursy python w google"

# Application navigation
nlp2cmd --query "otwórz aplikacje google"

# Form interactions
nlp2cmd --query "wyczyść wyszukiwarkę google"
```

#### Amazon Commands

```bash
# Product search
nlp2cmd --query "znajdź książki o nlp na amazon"

# Shopping cart
nlp2cmd --query "dodaj do koszyka amazon"

# Form filling
nlp2cmd --query "wypełnij dane wysyłki amazon"
```

## Configuration

### Browser Patterns

Add to `data/patterns.json`:

```json
{
  "browser": {
    "web_action": [
      "wpisz tekst", "type text", "wypełnij pole", "fill field",
      "kliknij przycisk", "click button", "wypełnij formularz", "fill form",
      "wyszukaj w google", "google search", "znajdź repozytorium na github",
      "szukaj na amazon", "amazon search"
    ],
    "navigate": [
      "przejdź do", "go to", "otwórz stronę", "open website",
      "nawiguj do", "navigate to", "idź do", "visit"
    ],
    "click": [
      "kliknij", "click", "naciśnij", "press", "wybierz", "select"
    ],
    "fill_form": [
      "wypełnij formularz", "fill form", "wypełlij dane", "fill data"
    ]
  }
}
```

### Domain Configuration

Update `keyword_intent_detector_config.json`:

```json
{
  "domain_boosters": {
    "browser": ["przeglądark", "browser", "strona", "website", "kliknij", "click",
                "formularz", "form", "przycisk", "button", "link", "url",
                "google", "github", "amazon", "szukaj", "wyszukaj", "wpisz", "type"]
  },
  "priority_intents": {
    "browser": ["web_action", "navigate", "click", "fill_form"]
  }
}
```

## Schema Management

### Extracting Schemas

```bash
# Basic extraction
nlp2cmd web-schema extract https://example.com

# With headless mode
nlp2cmd web-schema extract https://example.com --headless

# Specify output directory
nlp2cmd web-schema extract https://example.com --output-dir ./schemas
```

### Schema Structure

```json
{
  "app_name": "example.com",
  "app_version": "1.0",
  "description": "Web interface for example.com",
  "actions": [
    {
      "id": "type_search",
      "name": "search",
      "description": "Type text into input field",
      "parameters": [
        {
          "name": "text",
          "type": "string",
          "description": "Text to type",
          "required": true
        }
      ],
      "examples": [
        "wpisz tekst w search",
        "type text in search"
      ],
      "metadata": {
        "selector": "#search-input",
        "element_type": "input",
        "input_type": "text"
      }
    }
  ],
  "metadata": {
    "url": "https://example.com",
    "title": "Example Domain",
    "extracted_at": "2026-01-24T21:15:22.864128",
    "total_inputs": 5,
    "total_buttons": 12,
    "total_links": 8
  }
}
```

### Managing Multiple Schemas

```bash
# List all extracted schemas
ls command_schemas/sites/

# View specific schema
cat command_schemas/sites/github.com.json

# Remove schema
rm command_schemas/sites/example.com.json

# Update schema (re-extract)
nlp2cmd web-schema extract https://example.com --headless --force
```

## Advanced Features

### Enhanced Context Detection

The system uses semantic similarity to match queries with web actions:

```python
from nlp2cmd.generation.enhanced_context import get_enhanced_detector

detector = get_enhanced_detector()
match = detector.get_best_match("znajdź repozytorium nlp2cmd na github")

# Returns browser/web_action with high confidence
# Uses GitHub schema for enhanced understanding
```

### Multi-Language Support

The system supports both Polish and English:

```bash
# Polish queries
nlp2cmd --query "znajdź repozytorium na github"
nlp2cmd --query "wyszukaj produkty na amazon"

# English queries
nlp2cmd --query "find repository on github"
nlp2cmd --query "search products on amazon"
```

### Entity Extraction

The system extracts entities from queries:

```python
# Query: "znajdź książki o nlp na amazon"
# Entities:
# - "książki" (book) - product type
# - "nlp" - topic
# - "amazon" - site
# - Language: polish
```

## Troubleshooting

### Common Issues

#### 1. Schema Extraction Failed

**Problem**: Unable to extract schema from website

**Solution**: Check website accessibility and Playwright installation:

```bash
# Check Playwright installation
npx playwright --version

# Install browsers
npx playwright install

# Test extraction with verbose output
nlp2cmd web-schema extract https://example.com --headless --verbose
```

#### 2. Low Browser Detection Rate

**Problem**: Queries detected as shell instead of browser

**Solution**: Verify browser patterns and domain boosters:

```bash
# Check browser patterns
grep -A 20 '"browser"' data/patterns.json

# Check domain boosters
grep -A 5 '"browser"' data/keyword_intent_detector_config.json
```

#### 3. Missing Web Actions

**Problem**: Web actions not recognized for specific sites

**Solution**: Ensure schema is properly extracted and loaded:

```bash
# Check if schema exists
ls command_schemas/sites/

# Verify schema content
cat command_schemas/sites/github.com.json | jq '.actions | length'

# Test enhanced context detection
python -c "
from nlp2cmd.generation.enhanced_context import get_enhanced_detector
detector = get_enhanced_detector()
print('Browser schemas loaded:', 'browser' in detector.schemas)
"
```

#### 4. Intent Disambiguation Issues

**Problem**: Wrong intent detected (click vs web_action vs navigate)

**Solution**: Review intent priorities and patterns:

```json
{
  "priority_intents": {
    "browser": ["web_action", "navigate", "click", "fill_form"]
  }
}
```

### Debug Mode

Enable debug mode for detailed detection information:

```bash
# Run with explain flag
nlp2cmd --query "wyszukaj w google" --explain

# Check detection reasoning
python -c "
from nlp2cmd.generation.enhanced_context import get_enhanced_detector
detector = get_enhanced_detector()
explanation = detector.explain_detection('wyszukaj w google')
print(explanation)
"
```

## Performance Optimization

### Schema Caching

Schemas are cached in memory for fast access:

```python
# Schemas loaded once at initialization
detector = get_enhanced_detector()

# Multiple queries use cached schemas
for query in queries:
    match = detector.get_best_match(query)
```

### Semantic Index Precomputation

Semantic embeddings are precomputed for patterns:

```python
# Built during initialization
detector._build_semantic_index()

# Fast similarity lookup during queries
similarity = detector._calculate_semantic_similarity(query, domain, intent)
```

### Batch Processing

Process multiple queries efficiently:

```python
# Batch intent detection
queries = ["wyszukaj w google", "znajdź na github", "szukaj na amazon"]
results = [detector.get_best_match(q) for q in queries]
```

## Security Considerations

### Safe Web Automation

The system includes safety measures:

- **Headless Mode**: Default browser execution without UI
- **Selector Validation**: Safe CSS selectors only
- **Input Sanitization**: Clean text input for forms
- **Timeout Protection**: Prevent hanging operations

### Privacy Protection

- **Local Processing**: No external API calls for detection
- **Schema Storage**: Schemas stored locally
- **No Data Transmission**: Queries processed locally
- **Optional Telemetry**: Usage tracking disabled by default

## Future Enhancements

### Planned Features

1. **Dynamic Schema Updates**: Real-time schema refresh
2. **Custom Schema Upload**: User-defined website schemas
3. **Visual Context**: Screenshot-based UI understanding
4. **Form Intelligence**: Smart form filling with saved data
5. **Multi-step Workflows**: Complex web task automation

### Extension Points

The system is designed for extensibility:

```python
# Custom web schema extractor
class CustomSchemaExtractor:
    def extract_schema(self, url: str) -> dict:
        # Custom extraction logic
        pass

# Enhanced context detector extension
class CustomContextDetector(EnhancedContextDetector):
    def _calculate_custom_score(self, query: str) -> float:
        # Custom scoring logic
        pass
```

## Best Practices

### Schema Management

1. **Regular Updates**: Re-extract schemas when websites change
2. **Version Control**: Track schema changes in git
3. **Testing**: Validate schemas with test queries
4. **Documentation**: Document custom schemas

### Query Design

1. **Be Specific**: Include website names when possible
2. **Use Natural Language**: Write queries as you would speak
3. **Include Context**: Mention specific actions or elements
4. **Test Variations**: Try different phrasings for the same intent

### Performance Optimization

1. **Cache Schemas**: Load schemas once per session
2. **Batch Processing**: Process multiple queries together
3. **Limit Scope**: Use specific patterns for better accuracy
4. **Monitor Performance**: Track detection times and accuracy

## Conclusion

The Web Schema system enables NLP2CMD to understand and interact with real websites, providing:

- **Natural Language Web Automation**: Convert speech to browser actions
- **Multi-Site Support**: Work with GitHub, Google, Amazon, and more
- **Context-Aware Detection**: Understand site-specific interactions
- **Enhanced NLP Integration**: Semantic similarity and entity extraction
- **Extensible Architecture**: Easy to add new websites and features

This represents a significant advancement in making web automation accessible through natural language interfaces.
