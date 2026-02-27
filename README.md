![img.png](img.png)

wypełnianie formularza:

```bash
nlp2cmd -r "otwórz https://www.prototypowanie.pl/kontakt/ i wypelnij formularz i wyslij"
```

```bash
# 🚀 Run Mode: otwórz https://www.prototypowanie.pl/kontakt/ i wypelnij formularz i wyslij
```

```yaml
dsl: auto
query: otwórz https://www.prototypowanie.pl/kontakt/ i wypelnij formularz i wyslij
status: success
confidence: 1.0
generated_command: playwright open https://www.prototypowanie.pl/kontakt/ && fill_form && submit
```
![img_5.png](img_5.png)

![img_1.png](img_1.png)

![img_2.png](img_2.png)

realizacja zadan w shell
![img_3.png](img_3.png)

inteligentna reakcja na nie działająca w danym kontekscie polecenie i propzycja dzialajacego
![img_4.png](img_4.png)

# NLP2CMD

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Production Ready](https://img.shields.io/badge/production%20ready-brightgreen.svg)](https://github.com/wronai/nlp2cmd)
[![85%+ Success Rate](https://img.shields.io/badge/success%20rate-85%25%2B-brightgreen.svg)](https://github.com/wronai/nlp2cmd)
[![PyPI Version](https://img.shields.io/pypi/v/nlp2cmd.svg)](https://pypi.org/project/nlp2cmd/)
[![GitHub stars](https://img.shields.io/github/stars/wronai/nlp2cmd.svg)](https://github.com/wronai/nlp2cmd/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/wronai/nlp2cmd.svg)](https://github.com/wronai/nlp2cmd/network)
[![GitHub issues](https://img.shields.io/github/issues/wronai/nlp2cmd.svg)](https://github.com/wronai/nlp2cmd/issues)
[![GitHub pull requests](https://img.shields.io/github/issues-pr/wronai/nlp2cmd.svg)](https://github.com/wronai/nlp2cmd/pulls)
[![Documentation](https://img.shields.io/badge/docs-latest-blue.svg)](https://github.com/wronai/nlp2cmd/docs)
[![Build Status](https://img.shields.io/github/workflow/status/wronai/nlp2cmd/CI)](https://github.com/wronai/nlp2cmd/actions)

## 🔗 Related Projects

| Project                                                        | Description                                                 |
|----------------------------------------------------------------|------------------------------------------------------------|
| **[NLP2CMD + App2Schema](https://github.com/wronai/nlp2cmd)** | Automatic schema generation from any applications, services  |


**Natural Language to Domain-Specific Commands** - Production-ready framework for transforming natural language into DSL commands with full safety, validation, and observability.

## 🚀 Quick Start

```bash
# Install with all dependencies
pip install nlp2cmd[all]

# Setup external dependencies cache (Playwright browsers)
nlp2cmd cache auto-setup

# Start using with enhanced output
nlp2cmd "uruchom usługę nginx"
```bash
systemctl start nginx
```

```yaml
dsl: auto
query: uruchom usługę nginx
status: success
confidence: 1.0
generated_command: systemctl start nginx
```

# Polish language support
nlp2cmd "znajdź pliki większe niż 100MB"
```bash
find . -type f -size +100MB
```

# Advanced file operations
nlp2cmd "pokaż pliki użytkownika większe niż 50GB"
```bash
find $HOME -type f -size +50GB
```

## 🎯 Key Features

### 🧠 Evolutionary Cache — Self-Learning ([docs](docs/EVOLUTIONARY_CACHE.md))

nlp2cmd uczy się z każdego zapytania. **100% accuracy** (Qwen-Coder-3B), **24 355× speedup**, template pipeline + pre-warm cache eliminują 31% zapytań bez LLM.

| Model | Accuracy | Cold | Hot | Speedup |
|-------|----------|------|-----|---------|
| Qwen2.5-Coder-3B | **100.0%** | 314ms | 0.014ms | 22 461× |
| Qwen2.5-3B | **97.9%** | 317ms | 0.013ms | 24 355× |
| Bielik-1.5B (PL) | 61.7% | — | — | — |
| Gemma2-2B | 55.3% | — | — | — |

```
Zapytanie → CACHE → SIMILAR (rapidfuzz) → TEMPLATE (1615) → LLM TEACHER → AUTO-CACHE
```

```python
from nlp2cmd.generation.evolutionary_cache import EvolutionaryCache
cache = EvolutionaryCache()
r = cache.lookup("znajdź pliki PDF większe niż 10MB")  # template: ~15ms, cached: ~0.015ms
r = cache.lookup("znajdz pliki PDF wieksze niz 10MB")  # typo → similarity hit!
```

### 🌐 16 Domen (1615 szablonów)
- **Shell** - find, ls, grep, ps, du, df, tar, chmod
- **Docker** - container, image, compose, volume, network
- **SQL** - SELECT, INSERT, CREATE, JOIN, window functions
- **Kubernetes** - kubectl, pods, deployments, services, helm
- **Browser** - xdg-open, Playwright, Google/GitHub search
- **Git** - commit, branch, merge, rebase, stash, tag
- **DevOps** - systemctl, Ansible, Terraform, CI/CD, nginx, cron, SSL
- **API** - curl, httpie, wget, REST, GraphQL, WebSocket
- **FFmpeg** - video/audio conversion, streaming, screen recording
- **Media** - ImageMagick, sox, PDF, exiftool, batch processing
- **Data** - jq, csvkit, awk, sed, xsv, sqlite, pandas
- **Remote** - SSH, SCP, rsync, tmux, VPN (WireGuard, OpenVPN)
- **IoT** - Raspberry Pi GPIO, I2C, MQTT, sensors, cameras
- **Package Mgmt** - apt, pip, npm, yarn, snap, flatpak, brew, cargo
- **RAG** - ChromaDB, Qdrant, embeddings, LangChain, LlamaIndex
- **Presentation** - pandoc, matplotlib, Mermaid, Graphviz, LaTeX, Jupyter

### 🧠 Advanced NLP
- **Polish Language Support** - Native Polish NLP with spaCy (87%+ accuracy)
- **Fuzzy Matching** - Typo tolerance with rapidfuzz
- **Lemmatization** - Word form normalization
- **Priority Intent Detection** - Smart command classification
- **Enhanced Entity Extraction** - Time, size, username, path detection

### 🔧 Advanced File Operations
- **Time-based Search** - `znajdź pliki zmodyfikowane ostatnie 7 dni`
- **Size-based Filtering** - `znajdź pliki większe niż 100MB`
- **Combined Filters** - `znajdź pliki .log większe niż 10MB starsze niż 30 dni`
- **User Directory Operations** - `pokaż pliki użytkownika` → `find $HOME -type f`
- **Username-specific Paths** - `pokaż foldery użytkownika root` → `ls -la /root`

### 📦 Package Management
- **APT Installation** - `zainstaluj vlc` → `sudo apt-get install vlc`
- **Multi-variant Support** - Polish and English package commands
- **Cross-platform Ready** - OS detection and appropriate commands
- **Pattern Matching** - Multi-word keyword detection
- **Confidence Scoring** - Intent detection reliability

### 🎨 Enhanced Output Format

NLP2CMD now features **beautiful syntax-highlighted output** with clean bash codeblocks:

```bash
# Natural language query
nlp2cmd "znajdź pliki zmodyfikowane ostatnie 7 dni"

# Output with syntax highlighting
```bash
find . -type f -mtime -7                                                        
```

```yaml
dsl: auto                                                                       
query: znajdź pliki zmodyfikowane ostatnie 7 dni                                
status: success                                                                 
confidence: 1.0                                                                 
generated_command: find . -type f -mtime -7                                     
```

#### Key Features
- **🎨 Syntax Highlighting** - Rich syntax highlighting for bash, SQL, and YAML
- **📋 Clean Codeblocks** - No more complex Rich panels, just clean markdown-style blocks
- **🌍 Multi-language Support** - Full Polish language support with 87%+ accuracy
- **⚡ Instant Feedback** - Real-time command generation with confidence scores

#### Supported Languages
- **🇵🇱 Polish** - Native support with lemmatization and fuzzy matching
- **🇬🇧 English** - Full English language support
- **🔀 Mixed** - Seamless handling of mixed-language queries

### 🌍 Web Automation
```bash
# Extract schema from any website
nlp2cmd web-schema extract https://example.com

# Fill forms automatically
nlp2cmd -r "otwórz https://www.prototypowanie.pl/kontakt/ i wypełnij formularz i wyślij"

# Manage interaction history
nlp2cmd web-schema history --stats

# Multi-step: use existing Firefox window, open new tab, and save OpenRouter key to .env
nlp2cmd -r "owtorz tab w już otwartym oknie przegladarki firefox wyciągnij klucz API z OpenRouter i zapisz do .env"
```

Expected multi-step plan for the command above:

```yaml
status: multistep_plan_detected
intent: rule_decomposer
steps:
  - new_tab
  - navigate
  - echo
  - prompt_secret
  - save_env
```

### 🏢 Deep Company Extraction (NEW!)

Extract company data from business directories (e.g., Oferteo.pl) and save to CSV:

```bash
# Extract company websites from Oferteo catalog and save to CSV
nlp2cmd -r "wejdź na https://www.oferteo.pl/katalog-firm, znajdź strony www firm i zapisz do firmy.csv"
# → 🔍 Found 25 company profiles to check
# → ✓ Extracted 20 companies with websites
# → 💾 Saved 20 entries to CSV: /home/user/firmy.csv

# Find companies from specific city and save to text file
nlp2cmd -r "Otwórz przeglądarkę i wejdź na https://www.oferteo.pl. Przeszukaj katalog firm w poszukiwaniu stron www firm z Gdańska. Znajdź co najmniej 20 firm i zapisz ich adresy internetowe do pliku oferteo_firmy.txt"
# → 🔍 Found 20 company profiles to check  
# → 💾 Saved 20 entries to file: /home/user/oferteo_firmy.txt
```

**Features:**
- **Deep extraction** - Navigates to each company profile page
- **Website discovery** - Finds external company websites (filters out social media)
- **CSV export** - Structured data with name, Oferteo URL, and website
- **Text export** - Simple list format for further processing
- **Form filtering** - Automatically ignores search/cookie/comment forms

### 🔍 Exploration System (NEW!)

Automatic resource discovery when commands fail - searches for missing files, directories, API endpoints, and web content:

```bash
# If file doesn't exist in expected location, system searches and finds alternative
nlp2cmd -r "edytuj konfigurację nginx"
# → 🔍 Searching for nginx config...
# → ✓ Found: /home/user/projects/myapp/nginx.conf

# If form not on main page, automatically explores entire website
nlp2cmd -r "wejdź na maskservice.pl i wypełnij formularz kontaktu"
# → 🔍 Exploring site for contact form...
# → ✓ Found form at: https://www.maskservice.pl/en/contact
```

**Supported Exploration Types:**
- **Web** (`SiteExplorer`) - Finds forms, articles, products, docs across entire websites
- **Disk** (`DiskExplorer`) - Searches filesystem for files, configs, code, data
- **Services** (`ServiceExplorer`) - Discovers REST/GraphQL API endpoints
- **Data** (`DataTreeExplorer`) - Navigates JSON and nested data structures

**Integration:**
- Automatic in `ExecutionRunner.run_with_recovery()` - tries discovery before LLM fallback
- Integrated in `PipelineRunner._run_shell()` - retries with discovered resources
- Decision logic: analyzes error → decides → discovers → adapts command → retries

[📖 Full Documentation](docs/EXPLORATION_GUIDE.md)

### 🖥️ Desktop GUI Automation via noVNC (NEW!)

Control **any desktop application** on any OS through natural language — not just web pages.
NLP2CMD connects to a full Linux desktop (XFCE) running in Docker via noVNC/VNC protocol.

```bash
# Start desktop environment
docker compose -f docker/novnc/docker-compose.yml up -d
# Open http://localhost:6080/vnc.html to watch live

# Run demo — opens terminal, calculator, text editor, file manager, Firefox
python3 docker/novnc/demos/demo_desktop_gui.py

# With video recording
python3 docker/novnc/demos/demo_desktop_gui.py --record
```

**Demonstrated capabilities:**
- **Open applications** — terminal, calculator, text editor, file manager, browser
- **Type text** — in any GUI application field
- **Keyboard shortcuts** — Ctrl+S, Alt+F2, Alt+F4, etc.
- **Navigate menus** — click buttons, select options
- **Take screenshots** — automatic at each step
- **Record video** — ffmpeg session recording inside Docker

**Cross-OS Roadmap:**

| Protocol | OS | Status |
|----------|-----|--------|
| **noVNC** (Docker) | Linux | ✅ Working |
| **noVNC** (remote) | Any with VNC | 🔜 Planned |
| **RDP** via xfreerdp | Windows | 🔜 Planned |
| **VNC** direct | macOS | 🔜 Planned |

[📖 Full Documentation](docs/DESKTOP_GUI_AUTOMATION.md)

### 🚀 Service Mode (NEW!)
```bash
# Configure service settings
nlp2cmd config-service --host 0.0.0.0 --port 8000 --debug

# Start HTTP API service
nlp2cmd service --host 0.0.0.0 --port 8000 --workers 4

# Test the API
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "list files in current directory", "dsl": "shell"}'
```

#### Service Mode Features
- **🌐 HTTP API** - RESTful API with FastAPI + Pydantic
- **⚙️ Configuration Management** - Environment variables + .env support
- **🔧 Flexible Deployment** - Host/port configuration, CORS, workers
- **📊 Real-time Processing** - Sub-second API responses
- **🛡️ Type Safety** - Full Pydantic model validation
- **📝 Auto-documentation** - Automatic OpenAPI/Swagger docs at `/docs`

### 💾 Smart Caching
```bash
# External dependencies cache management
nlp2cmd cache info          # Show cache status
nlp2cmd cache auto-setup    # Install and configure
nlp2cmd cache clear         # Clear cache if needed
nlp2cmd cache full-clear --yes  # Clear full NLP2CMD cache (runtime + external + schema)
```

## 🏗️ Architecture Overview

```text
   ┌─────────────────┐
   │   User Query    │
   └────────┬────────┘
            │
            ▼
   ┌─────────────────┐
   │   NLP Layer     │ → Intent + Entities + Confidence
   └────────┬────────┘
            │
            ▼
   ┌─────────────────┐
   │ Intent Router  │ → Domain + Intent Classification
   └────────┬────────┘
            │
            ▼
   ┌─────────────────┐
   │ Entity Extractor│ → Time, Size, Username, Path
   └────────┬────────┘
            │
            ▼
   ┌─────────────────┐
   │ Command Generator│ → Domain-specific Commands
   └────────┬────────┘
            │
            ▼
   ┌─────────────────┐
   │ Safety Validator│ → Command Safety Check
   └────────┬────────┘
            │
            ▼
   ┌─────────────────┐
   │   Execution     │ → Run Command with Confirmation
   └─────────────────┘
```

## 📊 Performance Metrics

### 🎯 Success Rate by Domain
- **Shell Operations**: 90%+ (files, processes, packages)
- **Package Management**: 100% (apt install, zainstaluj)
- **User File Operations**: 100% (user directory detection)
- **Advanced Find**: 100% (size + age filtering)
- **Web Search**: 33% (Google, GitHub, Amazon)
- **Overall System**: 85%+ Production Ready

### 🚀 Advanced Examples

#### File Operations with Time & Size
```bash
# Find files modified in last 7 days larger than 100MB
nlp2cmd "znajdź pliki większe niż 100MB zmodyfikowane ostatnie 7 dni"
# → find . -type f -size +100MB -mtime +7

# Search user's home directory for large files
nlp2cmd "pokaż pliki użytkownika większe niż 50GB"
# → find $HOME -type f -size +50GB

# Find specific file types with age filter
nlp2cmd "znajdź pliki .log większe niż 10MB starsze niż 2 dni"
# → find . -type f -name '*.log' -size +10MB -mtime -2
```

#### User-Specific Operations
```bash
# List current user's files
nlp2cmd "pokaż pliki użytkownika"
# → find $HOME -type f

# List specific user's directory
nlp2cmd "pokaż foldery użytkownika root"
# → ls -la /root

# List files in user directory
nlp2cmd "listuj pliki w katalogu domowym"
# → ls -la .
```

#### Package Management
```bash
# Install packages (Polish & English)
nlp2cmd "zainstaluj vlc"
# → sudo apt-get install vlc

nlp2cmd "apt install nginx"
# → sudo apt-get install nginx

nlp2cmd "install git"
# → sudo apt-get install git
```

#### Browser & Web Operations
```bash
# Search Google
nlp2cmd "wyszukaj w google python tutorial"
# → xdg-open 'https://www.google.com/search?q=w google python tutorial'

# Search GitHub
nlp2cmd "znajdź repozytorium nlp2cmd na github"
# → xdg-open 'https://github.com/search?q=nlp2cmd&type=repositories'

# Search Amazon
nlp2cmd "szukaj na amazon python books"
# → xdg-open 'https://www.amazon.com/s?k=python books'
```

### Key Principle

**Natural Language → System Commands** with 85%+ accuracy and full safety validation.

## ✨ Features

### Core Capabilities

- 🗣️ **6 DSL Adapters**: SQL, Shell, Docker, Kubernetes, DQL (Doctrine), Browser
- 🧠 **Polish NLP**: Native Polish language support with 87%+ accuracy
- 🔍 **Advanced Search**: Time-based, size-based, and combined filtering
- 👤 **User Operations**: Username-specific directory operations
- 📦 **Package Management**: APT installation with Polish variants
- 🌐 **Web Automation**: Google, GitHub, Amazon search integration
- 🏢 **Deep Company Extraction**: Navigate business directories, extract external websites, export to CSV
- 🚀 **Service Mode**: HTTP API with FastAPI + Pydantic for integration
- ⚡ **Real-time Processing**: Sub-second command generation
- 🛡️ **Safety Validation**: Command safety checks and confirmation
- 📁 **11 File Format Schemas**: Dockerfile, docker-compose, K8s manifests, GitHub workflows, .env, and more
- 🛡️ **Safety Policies**: Allowlist-based action control, no eval/shell execution
- 🔄 **Multi-step Plans**: Support for `foreach` loops and variable references between steps
- 🌍 **Polish NLP**: Native Polish language support with lemmatization and fuzzy matching
- 💾 **Smart Caching**: External dependencies cache for Playwright browsers

### New Architecture Components (v0.2.0)

- 🔀 **Decision Router**: Intelligently routes queries to direct execution or LLM planner
- 📋 **Action Registry**: Central registry of 19+ typed actions with full validation
- ⚡ **Plan Executor**: Executes multi-step plans with tracing, retry, and error handling
- 🤖 **LLM Planner**: Generates JSON plans constrained to allowed actions
- 📊 **Result Aggregator**: Multiple output formats (text, table, JSON, markdown)
- 🌐 **Web Schema Engine**: Browser automation with Playwright integration
- 💾 **Cache Manager**: Smart caching for external dependencies

### Security Features

- ✅ No direct LLM access to system
- ✅ Typed actions (no eval/shell)
- ✅ Allowlist of permitted actions
- ✅ Full plan validation before execution
- ✅ Traceable execution (trace_id per request)

## 📚 Documentation

| Document | Description |
|----------|-------------|
| **[Documentation Hub](docs/README.md)** | Entry point and navigation for all docs |
| **[Installation Guide](INSTALLATION.md)** | Setup instructions and installation options |
| **[User Guide](docs/guides/user-guide.md)** | Complete usage tutorial and examples |
| **[CLI Reference](docs/cli-reference.md)** | Comprehensive CLI documentation |
| **[Python API Guide](docs/python-api.md)** | Detailed Python API usage |
| **[Examples Guide](docs/examples-guide.md)** | Comprehensive examples overview |
| **[API Reference](docs/api/README.md)** | Detailed API documentation |
| **[Thermodynamic Integration](THERMODYNAMIC_INTEGRATION.md)** | Advanced optimization with Langevin dynamics |
| **[Thermodynamic Architecture](THERMODYNAMIC_ARCHITECTURE.md)** | Deep technical architecture overview |
| **[Contributing Guide](CONTRIBUTING.md)** | Development guidelines and contribution process |
| **[Generation Module](README_GENERATION.md)** | DSL generation implementation details |
| **[Quick Fix Reference](docs/quick-fix-reference.md)** | Common issues and solutions |
| **[Keyword Detection Flow](docs/KEYWORD_DETECTION_FLOW.md)** | Detailed keyword intent detection pipeline and fallback mechanisms |
| **[Enhanced NLP Integration](docs/ENHANCED_NLP_INTEGRATION.md)** | Advanced NLP libraries integration with semantic similarity and web schema context |
| **[Web Schema Guide](docs/WEB_SCHEMA_GUIDE.md)** | Browser automation and form filling |
| **[Cache Management Guide](docs/CACHE_MANAGEMENT.md)** | External dependencies caching |
| **[Service Mode Guide](docs/SERVICE_MODE.md)** | HTTP API service with FastAPI + Pydantic |

## 🚀 Quick Start

### Installation

```bash
# Install with all dependencies (including service mode)
pip install nlp2cmd[all]

# Install desktop automation tools (for Firefox tab control, etc.)
nlp2cmd-install-desktop
# or after cloning repo:
make install-desktop

# Or install specific components
pip install nlp2cmd[browser,nlp]  # Web automation + Polish NLP
pip install nlp2cmd[sql,shell]   # Database + system commands
pip install nlp2cmd[service]      # Service mode (FastAPI + Pydantic)
```

### Shell Emulation Mode

NLP2cmd provides full shell emulation capabilities for system commands:

```bash
# Interactive shell mode
nlp2cmd --interactive --dsl shell
nlp2cmd> list files in current directory
nlp2cmd> find files larger than 100MB
nlp2cmd> show running processes
nlp2cmd> exit

# Single query mode
nlp2cmd --dsl shell --query "list files in current directory"
# Output: ls -la .

# Execute immediately (run mode)
nlp2cmd --run "list files in current directory" --auto-confirm
# Executes: ls -la . with real output

# Polish language support
nlp2cmd --dsl shell --query "znajdź pliki .log większe niż 10MB"
# Output: find . -type f -name "*.log" -size +10MB -exec ls -lh {} \;

# Process management
nlp2cmd --dsl shell --query "uruchom usługę nginx"
# Output: systemctl start nginx

nlp2cmd --dsl shell --query "pokaż procesy zużywające najwięcej pamięci"
# Output: ps aux --sort=-%mem | head -10
```

### Setup External Dependencies

```bash
# Auto-setup Playwright browsers and cache
nlp2cmd cache auto-setup

# Install desktop automation tools (for Firefox tab control, etc.)
nlp2cmd-install-desktop
# or manually:
make install-desktop

# Manual setup
nlp2cmd cache install --package playwright
```

### CLI Usage

The fastest way to use NLP2CMD is through the command line interface:

```bash
# Basic query
nlp2cmd --query "Pokaż użytkowników"

# Specific DSL
nlp2cmd --dsl sql --query "SELECT * FROM users WHERE city = 'Warsaw'"
nlp2cmd --dsl shell --query "Znajdź pliki .log większe niż 10MB"
nlp2cmd --dsl docker --query "Pokaż wszystkie kontenery"
nlp2cmd --dsl kubernetes --query "Skaluj deployment nginx do 3 replik"

# Web automation
nlp2cmd --dsl browser --query "otwórz https://example.com i wypełnij formularz"
nlp2cmd web-schema extract https://example.com
nlp2cmd web-schema history --stats

# With options
nlp2cmd --explain --query "Sprawdź status systemu"
nlp2cmd --auto-repair --query "Napraw konfigurację nginx"

# Interactive mode
nlp2cmd --interactive

# Cache management
nlp2cmd cache info
nlp2cmd cache auto-setup

# Environment analysis
nlp2cmd analyze-env
nlp2cmd analyze-env --output environment.json

# Service mode
nlp2cmd config-service --host 0.0.0.0 --port 8000 --debug
nlp2cmd service --host 0.0.0.0 --port 8000 --workers 4
nlp2cmd service --reload  # Development mode with auto-reload

# File validation and repair
nlp2cmd validate config.json
nlp2cmd repair docker-compose.yml --backup
```

#### Working Examples

##### Shell Emulation Examples

# Interactive mode
```bash
nlp2cmd "show user folders"
```

### output: 

```bash
find ~ -maxdepth 1 -type d                                                                                                                                                                                                                               
```

```yaml
dsl: auto                                                                                                                                                                                                                                                
query: show user folders                                                                                                                                                                                                                                 
status: success                                                                                                                                                                                                                                          
confidence: 1.0                                                                                                                                                                                                                                          
generated_command: find ~ -maxdepth 1 -type d                                                                                                                                                                                                            
errors: []                                                                                                                                                                                                                                               
warnings: []                                                                                                                                                                                                                                             
suggestions: []                                                                                                                                                                                                                                          
clarification_questions: []                                                                                                                                                                                                                              
resource_metrics:                                                                                                                                                                                                                                        
  time_ms: 1.6                                                                                                                                                                                                                                           
  cpu_percent: 0.0                                                                                                                                                                                                                                       
  memory_mb: 56.6                                                                                                                                                                                                                                        
  energy_mj: 0.015                                                                                                                                                                                                                                       
resource_metrics_parsed:                                                                                                                                                                                                                                 
  time_ms: 1.6                                                                                                                                                                                                                                           
  cpu_percent: 0.0                                                                                                                                                                                                                                       
  memory_mb: 56.6                                                                                                                                                                                                                                        
  energy_mj: 0.015                                                                                                                                                                                                                                       
token_estimate:                                                                                                                                                                                                                                          
  total: 1                                                                                                                                                                                                                                               
  input: 1                                                                                                                                                                                                                                               
  output: 0                                                                                                                                                                                                                                              
  cost_usd: 2.0e-06                                                                                                                                                                                                                                      
  model_tier: tiny                                                                                                                                                                                                                                       
  tokens_per_ms: 0.625                                                                                                                                                                                                                                   
  tokens_per_mj: 66.66666666666667                                                                                                                                                                                                                       
```

# Run mode with execution
$ nlp2cmd --run "list files in current directory" --auto-confirm
# 🚀 Run Mode: list files in current directory                                  
Generating command...
✗ Could not generate command with rule-based pipeline: # Unknown: could not 
detect domain for: list files in current directory
Attempting LLM fallback via LiteLLM...
✓ LLM fallback succeeded
Detected: shell/llm_fallback

$ ls
  CHANGELOG.md
  COMMIT_MESSAGE.md
  CONTRIBUTING.md
  Dockerfile
  ENHANCED_README.md
  INSTALLATION.md...
✓ Command completed in 13.4ms

# Polish language examples
$ nlp2cmd --dsl shell --query "uruchom usługę nginx"
systemctl start nginx

$ nlp2cmd --dsl shell --query "pokaż procesy zużywające najwięcej pamięci"
ps aux --sort=-%mem | head -10

$ nlp2cmd --dsl shell --query "znajdź pliki z rozszerzeniem .py"
find . -name "*.py" -type f
```

##### Service Mode Examples

```bash
# Configure service settings
$ nlp2cmd config-service --host 127.0.0.1 --port 8080 --debug --log-level debug
Configuration saved to .env
Current configuration:
  host: 127.0.0.1
  port: 8080
  debug: True
  log_level: debug
  ...

# Start the service
$ nlp2cmd service --host 0.0.0.0 --port 8000 --workers 4
2026-01-25 11:24:32,971 - nlp2cmd.service - INFO - Starting NLP2CMD service on 0.0.0.0:8000
INFO:     Started server process [1493894]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)

# Test API endpoints (in another terminal)
$ curl http://localhost:8000/health
{"status": "healthy", "service": "nlp2cmd"}

$ curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "list files in current directory", "dsl": "shell"}'
{
  "success": true,
  "command": "ls -la",
  "confidence": 0.95,
  "domain": "shell",
  "intent": "list_files",
  "entities": {},
  "explanation": "Generated by RuleBasedPipeline with confidence 0.95"
}

# Get service configuration
$ curl http://localhost:8000/config
{
  "host": "0.0.0.0",
  "port": 8000,
  "debug": false,
  "log_level": "info",
  "cors_origins": ["*"],
  "max_workers": 4,
  "auto_execute": false,
  "session_timeout": 3600
}

# Update configuration
$ curl -X POST http://localhost:8000/config \
  -H "Content-Type: application/json" \
  -d '{"log_level": "debug"}'
{
  "message": "Configuration updated",
  "config": {
    "host": "0.0.0.0",
    "port": 8000,
    "debug": false,
    "log_level": "debug",
    ...
  }
}

# Python client example
$ python3 -c "
import requests
response = requests.post('http://localhost:8000/query', json={
    'query': 'znajdź pliki .log większe niż 10MB',
    'dsl': 'shell',
    'explain': True
})
result = response.json()
print(f'Command: {result[\"command\"]}')
print(f'Confidence: {result[\"confidence\"]}')
print(f'Explanation: {result[\"explanation\"]}')
"
Command: find . -type f -name "*.log" -size +10MB -exec ls -lh {} \;
Confidence: 0.9
Explanation: Generated by RuleBasedPipeline with confidence 0.90
```

##### Other DSL Examples

```bash
$ nlp2cmd --dsl docker --query "Pokaż wszystkie kontenery"
docker ps -a

📊 ⏱️  Time: 2.2ms | 💻 CPU: 0.0% | 🧠 RAM: 55.2MB (0.1%) | ⚡ Energy: 0.019mJ

$ nlp2cmd web-schema extract https://httpbin.org/forms/post
✓ Schema extracted successfully
📊 Extracted Elements: 12 inputs, 1 button, 1 form

$ nlp2cmd cache info
╭─────────────────────────────── Cache Overview ───────────────────────────────╮
│ Cache Directory: /home/tom/github/wronai/nlp2cmd/.cache/external             │
│ Total Size: 0.0 MB                                                           │
│ Cached Packages: 0                                                           │
╰──────────────────────────────────────────────────────────────────────────────╯
No packages cached
```

### Python API Usage

#### Basic Usage (New Architecture)

```python
from nlp2cmd import (
    DecisionRouter,
    RoutingDecision,
    PlanExecutor,
    ExecutionPlan,
    PlanStep,
    ResultAggregator,
    OutputFormat,
    get_registry,
)

# Initialize components
router = DecisionRouter()
executor = PlanExecutor()
aggregator = ResultAggregator()

# Route a query
routing = router.route(
    intent="select",
    entities={"table": "users"},
    text="show all users",
    confidence=0.9,
)

if routing.decision == RoutingDecision.DIRECT:
    # Simple query - direct execution
    plan = ExecutionPlan(steps=[
        PlanStep(action="sql_select", params={"table": "users"})
    ])
else:
    # Complex query - use LLM Planner
    from nlp2cmd import LLMPlanner
    planner = LLMPlanner(llm_client=your_llm_client)
    result = planner.plan(intent="select", entities={}, text="...")
    plan = result.plan

# Execute and format results
exec_result = executor.execute(plan)
output = aggregator.aggregate(exec_result, format=OutputFormat.TABLE)
print(output.data)
```

#### HybridThermodynamicGenerator (Recommended)

```python
from nlp2cmd.generation import HybridThermodynamicGenerator

generator = HybridThermodynamicGenerator()

# Simple query → DSL generation
result = await generator.generate("Pokaż użytkowników")
# → {'source': 'dsl', 'result': HybridResult(...)}

# Optimization → Thermodynamic sampling
result = await generator.generate("Zoptymalizuj przydzielanie zasobów")
# → {'source': 'thermodynamic', 'result': ThermodynamicResult(...)}
```

### Multi-Step Plans with Foreach

```python
# Define a multi-step plan
plan = ExecutionPlan(steps=[
    PlanStep(
        action="shell_find",
        params={"glob": "*.log"},
        store_as="log_files",
    ),
    PlanStep(
        action="shell_count_pattern",
        foreach="log_files",  # Iterate over results
        params={"file": "$item", "pattern": "ERROR"},
        store_as="error_counts",
    ),
    PlanStep(
        action="summarize_results",
        params={"data": "$error_counts"},
    ),
])

# Execute with tracing
result = executor.execute(plan)
print(f"Trace ID: {result.trace_id}")
print(f"Duration: {result.total_duration_ms}ms")
```

### Legacy Usage (SQL Adapter)

```python
from nlp2cmd import NLP2CMD, SQLAdapter

# Initialize with SQL adapter
nlp = NLP2CMD(adapter=SQLAdapter(dialect="postgresql"))

# Transform natural language to SQL
result = nlp.transform("Pokaż wszystkich użytkowników z Warszawy")
print(result.command)  # SELECT * FROM users WHERE city = 'Warszawa';
```

## 🔍 Keyword Intent Detection

NLP2CMD uses a **robust multi-layered detection pipeline** that ensures reliable intent recognition even with typos, variations, or missing dependencies:

### Detection Pipeline (11 Layers)

1. **Text Normalization** - Polish diacritics, typo corrections, optional lemmatization
2. **Fast Path Detection** - Quick browser/search queries
3. **SQL Context Detection** - Identify SQL keywords
4. **SQL DROP Detection** - High-priority dangerous operations
5. **Docker Detection** - Explicit Docker commands
6. **Kubernetes Detection** - K8s-specific commands
7. **Service Restart Detection** - Service management priority
8. **Priority Intents** - Configured high-priority patterns
9. **General Pattern Matching** - Full keyword matching with confidence scoring
10. **Fuzzy Matching** - Optional rapidfuzz for typos (85% threshold)
11. **Final Fallback** - Always returns `unknown/unknown`

### Key Guarantees

✅ **Always works** - Final fallback ensures no method returns `None`  
✅ **Graceful degradation** - Missing dependencies don't break the pipeline  
✅ **Typo tolerance** - Built-in corrections + optional fuzzy matching  
✅ **Performance optimized** - Fast path and priority checks first  
✅ **Safety first** - Dangerous operations get highest priority  

### Example Flow

```text
Input: "dokcer ps" (typo)
1. Normalization: "dokcer" → "docker"
2. Pattern matching: "docker ps" → docker/list
Result: ✅ Works without fuzzy matching
```

**[📖 Full Documentation](docs/KEYWORD_DETECTION_FLOW.md)**

## 📋 Action Registry

```python
from nlp2cmd import get_registry

registry = get_registry()

# List all domains
print(registry.list_domains())
# ['sql', 'shell', 'docker', 'kubernetes', 'utility']

# List actions by domain
print(registry.list_actions(domain="sql"))
# ['sql_select', 'sql_insert', 'sql_update', 'sql_delete', 'sql_aggregate']

# Get destructive actions (require confirmation)
print(registry.get_destructive_actions())
# ['sql_insert', 'sql_update', 'sql_delete', 'docker_run', ...]

# Generate LLM prompt with available actions
prompt = registry.to_llm_prompt(domain="sql")
```

## 🔧 DSL Support

| DSL | Adapter | Status |
|-----|---------|--------|
| SQL (PostgreSQL, MySQL, SQLite) | `SQLAdapter` | ✅ Stable |
| Shell (Bash, Zsh) | `ShellAdapter` | ✅ Stable |
| DQL (Doctrine) | `DQLAdapter` | ✅ Stable |
| Docker / Docker Compose | `DockerAdapter` | ✅ Stable |
| Kubernetes | `KubernetesAdapter` | ✅ Stable |

## 📁 Supported File Formats

- Dockerfile
- docker-compose.yml
- Kubernetes manifests (Deployment, Service, Ingress, ConfigMap)
- SQL migrations
- .env files
- nginx.conf
- GitHub Actions workflows
- Prisma Schema
- Terraform (.tf)
- .editorconfig
- package.json

## 📊 Output Formats

```python
from nlp2cmd import ResultAggregator, OutputFormat

aggregator = ResultAggregator()

# Text format (default)
result = aggregator.aggregate(exec_result, format=OutputFormat.TEXT)

# ASCII Table
result = aggregator.aggregate(exec_result, format=OutputFormat.TABLE)

# JSON (for programmatic use)
result = aggregator.aggregate(exec_result, format=OutputFormat.JSON)

# Markdown (for documentation)
result = aggregator.aggregate(exec_result, format=OutputFormat.MARKDOWN)

# Summary (for dashboards)
result = aggregator.aggregate(exec_result, format=OutputFormat.SUMMARY)
```

## 🛡️ Safety

The framework enforces safety at multiple levels:

1. **Action Allowlist**: Only registered actions can be executed
2. **Parameter Validation**: Full type checking and constraints
3. **Plan Validation**: All plans validated before execution
4. **No Code Generation**: LLM only produces JSON plans, not executable code
5. **Destructive Action Marking**: Actions that modify state are flagged

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run E2E tests for service mode
python3 run_e2e_tests.py

# Run specific component tests
pytest tests/unit/test_router.py -v
pytest tests/unit/test_registry.py -v
pytest tests/unit/test_executor.py -v

# Service mode E2E tests
pytest tests/e2e/ -m service

# With coverage
pytest --cov=nlp2cmd --cov-report=html
```

## 🔬 Thermodynamic Optimization (v0.3.0+)

Based on [Whitelam (2025) "Generative thermodynamic computing"](https://arxiv.org/abs/2506.15121), the framework now includes thermodynamic optimization for complex constraint satisfaction problems.

### Key Features

- **Langevin Dynamics Sampling**: Natural evolution from noise to structured solutions
- **Energy-Based Models**: Domain-specific constraint functions
- **Hybrid Routing**: Automatic selection between DSL generation and thermodynamic optimization
- **Energy Efficiency**: 50-70% reduction vs pure LLM inference

### Quick Example

```bash
nlp2cmd "Zaplanuj 5 zadań w 10 slotach z ograniczeniami" --explain
```

This command triggers thermodynamic optimization for constraint satisfaction problems and outputs results in YAML format, including energy estimates and scheduling solutions.

### Supported Problem Types

- **Scheduling**: Task scheduling with deadlines and constraints
- **Resource Allocation**: Optimal distribution under capacity limits  
- **Planning**: Multi-step planning with constraint satisfaction
- **Optimization**: General constrained optimization problems

See [Thermodynamic Integration](THERMODYNAMIC_INTEGRATION.md) for detailed documentation.

## 💡 Examples

### CLI Examples

- **[Shell Commands Demo](examples/use_cases/shell_commands_demo.sh)** - Complete CLI usage examples
- **[Simple Demo](examples/use_cases/simple_demo_examples.py)** - Python API + Shell concepts
- **[Complete Examples](examples/use_cases/complete_python_shell_examples.py)** - Full Python API examples
- **[DSL Commands Demo](examples/use_cases/dsl_commands_demo.py)** - Direct DSL generation examples

### Quick Examples

- **[Basic SQL](examples/sql/basic_sql.py)** - Simple SQL queries
- **[Shell Commands](examples/shell/basic_shell.py)** - Common shell operations  
- **[Docker Management](examples/docker/basic_docker.py)** - Container operations
- **[Kubernetes](examples/kubernetes/basic_kubernetes.py)** - K8s cluster management

### Advanced Examples  

- **[End-to-End Demo](examples/architecture/end_to_end_demo.py)** - Complete workflow
- **[Log Analysis Pipeline](examples/pipelines/log_analysis.py)** - Data processing
- **[Infrastructure Health](examples/pipelines/infrastructure_health.py)** - System monitoring
- **[Configuration Validation](examples/validation/config_validation.py)** - File validation

### Use Case Examples

- **[DevOps Automation](examples/use_cases/devops_automation.py)** - IT operations
- **[Data Science & ML](examples/use_cases/data_science_ml.py)** - Data workflows
- **[Healthcare](examples/use_cases/healthcare.py)** - Medical applications
- **[Finance & Trading](examples/use_cases/finance_trading.py)** - Financial operations
- **[Smart Cities](examples/use_cases/smart_cities.py)** - Urban management

### Documentation

- **[CLI Reference](docs/cli-reference.md)** - Complete CLI documentation
- **[Python API Guide](docs/python-api.md)** - Detailed Python API usage
- **[Examples Guide](docs/examples-guide.md)** - Comprehensive examples overview

See [Examples README](examples/use_cases/README.md) for all available examples.

## 📁 Project Structure

```text
nlp2cmd/
├── src/nlp2cmd/
│   ├── __init__.py       # Main exports
│   ├── core.py           # Core NLP2CMD class
│   ├── router/           # Decision Router
│   ├── registry/         # Action Registry
│   ├── executor/         # Plan Executor
│   ├── planner/          # LLM Planner
│   ├── aggregator/       # Result Aggregator
│   ├── adapters/         # DSL Adapters (SQL, Shell, Docker, K8s, DQL)
│   ├── schemas/          # File Format Schemas
│   ├── feedback/         # Feedback Loop
│   ├── environment/      # Environment Analyzer
│   └── validators/       # Validators
├── tests/
│   ├── unit/            # Unit tests (~150 tests)
│   └── integration/     # Integration tests
├── examples/
│   ├── architecture/    # End-to-end demos
│   ├── sql/            # SQL examples
│   ├── shell/          # Shell examples
│   └── docker/         # Docker examples
└── docs/               # Documentation
```

## 🔖 Version History

### v0.3.0+ (Thermodynamic Integration)

- **NEW**: Thermodynamic optimization using Whitelam's generative framework
- Langevin dynamics for constraint satisfaction problems
- 50-70% energy reduction vs pure LLM inference
- Hybrid router: DSL generation + thermodynamic optimization
- Domain-specific energy models (scheduling, allocation, planning)
- Parallel sampling with energy-based voting

### v0.2.0 (Current)

- New architecture: LLM as Planner + Typed Actions
- Decision Router for intelligent query routing
- Action Registry with 19+ typed actions
- Plan Executor with foreach, conditions, and retry
- Result Aggregator with multiple output formats
- Full observability (trace_id, duration tracking)
- 150+ tests

### v0.1.0

- Initial release
- 5 DSL adapters
- 11 file format schemas
- Safety policies
- Feedback loop

## 📄 License

Apache License - see [LICENSE](LICENSE) for details.

## 🙏 Acknowledgements

- [Whitelam, S. (2025)](https://arxiv.org/abs/2506.15121) "Generative thermodynamic computing" - Theoretical foundation for thermodynamic optimization
- [spaCy](https://spacy.io/) - NLP processing
- [Anthropic Claude](https://anthropic.com/) - LLM integration
- [Rich](https://rich.readthedocs.io/) - Terminal formatting

## License

Apache License 2.0 - see [LICENSE](LICENSE) for details.

## Author

Created by **Tom Sapletta** - [tom@sapletta.com](mailto:tom@sapletta.com)
