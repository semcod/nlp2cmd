# NLP2CMD Refactoring Plan — based on benchmark results
# Generated: 2026-02-28T09:31:57.996500

## Domain Analysis
### Weak domains (accuracy < 50%) — priority for refactoring:
  - **data**: 33.3% accuracy, 0.238s avg time
    → Improve system prompts, add few-shot examples, better entity extraction
  - **rag**: 41.7% accuracy, 0.579s avg time
    → Improve system prompts, add few-shot examples, better entity extraction
### Strong domains:
  - **shell**: 66.7% accuracy, 0.196s avg time
  - **docker**: 75.0% accuracy, 0.226s avg time
  - **sql**: 50.0% accuracy, 0.357s avg time
  - **kubernetes**: 91.7% accuracy, 0.169s avg time
  - **browser**: 100.0% accuracy, 0.244s avg time
  - **git**: 91.7% accuracy, 0.203s avg time
  - **devops**: 75.0% accuracy, 0.121s avg time
  - **api**: 100.0% accuracy, 0.387s avg time
  - **ffmpeg**: 83.3% accuracy, 0.3s avg time
  - **media**: 100.0% accuracy, 0.243s avg time
  - **remote**: 75.0% accuracy, 0.26s avg time
  - **iot**: 83.3% accuracy, 0.202s avg time
  - **package_mgmt**: 75.0% accuracy, 0.117s avg time
  - **presentation**: 83.3% accuracy, 0.295s avg time

## Model Analysis
### Bielik-1.5B (PL) (1.5B)
  - Accuracy: 57.4%
  - Avg time: 0.284s
  - Errors: 16
### Qwen2.5-3B (3B)
  - Accuracy: 95.7%
  - Avg time: 0.25s
  - Errors: 0
### Gemma2-2B (2B)
  - Accuracy: 59.6%
  - Avg time: 0.238s
  - Errors: 16
### Qwen2.5-Coder-3B (3B)
  - Accuracy: 91.5%
  - Avg time: 0.236s
  - Errors: 0

## Recommendations
1. **System prompts**: Optimize per-domain prompts based on failure patterns
2. **Few-shot examples**: Add domain-specific examples to prompts (especially weak domains)
3. **Entity extraction**: Improve regex patterns for domains with low accuracy
4. **Fallback chain**: template → regex → LLM (use fastest method first)
5. **Caching**: Cache common queries to reduce LLM calls
6. **Polish language**: Add more Polish-specific patterns and keywords

## Failed Queries (for targeted improvements)
  - [shell] bielik-1.5b: "wyszukaj pliki DOCX większe niż 5MB w katalogu /home"
    Got: 
    Expected pattern: find.*\.docx.*-size
  - [shell] bielik-1.5b: "sprawdź zajętość dysku w /tmp"
    Got: 
    Expected pattern: (du|df).*(/tmp|tmp)
  - [shell] bielik-1.5b: "wyświetl 15 procesów zużywających najwięcej CPU"
    Got: 
    Expected pattern: (ps.*sort|top|ps.*cpu)
  - [docker] bielik-1.5b: "pokaż ostatnie 50 linii logów kontenera redis"
    Got: <tool_call> {"name": "docker_logs", "arguments": {"container_id": "redis:latest"
    Expected pattern: docker\s+logs.*(redis|--tail|50)
  - [sql] bielik-1.5b: "stwórz tabelę klienci z polami id, email, telefon"
    Got: CREATE TABLE klienci (id INT PRIMARY KEY AUTO_INCREMENT, email VARCHAR(255) UNIQ
    Expected pattern: CREATE\s+TABLE.*klient
  - [git] bielik-1.5b: "stwórz branch bugfix/auth-error"
    Got: git checkout bugfix/auth-error
    Expected pattern: git\s+(checkout\s+-b|branch|switch\s+-c).*bugfix.auth
  - [devops] bielik-1.5b: "sprawdź czy działa usługa postgresql"
    Got: 
    Expected pattern: (systemctl\s+status|service\s+.*status).*postgres
  - [devops] bielik-1.5b: "uruchom playbook setup.yml"
    Got: 
    Expected pattern: ansible-playbook.*setup\.yml
  - [data] bielik-1.5b: "wyświetl statystyki pliku sales.csv"
    Got: 
    Expected pattern: (csvstat|csvlook|pandas|describe|head).*sales\.csv
  - [data] bielik-1.5b: "filtruj customers.json po salary powyżej 5000"
    Got: 
    Expected pattern: jq.*select.*salary.*(>|gt).*5000
  - [data] bielik-1.5b: "policz unikalne wartości w kolumnie type z events.csv"
    Got: cut -d',' -f3 events.csv | sort | uniq -c | sort -rn
    Expected pattern: ((cut.*(type|\-f\s*2|\-f2).*events\.csv)|(awk.*type.*events\.csv)).*(sort|uniq)
  - [remote] bielik-1.5b: "zaloguj się przez SSH na 10.0.0.50 jako root"
    Got: 
    Expected pattern: ssh\s+root@10\.0\.0\.50
  - [remote] bielik-1.5b: "prześlij archive.zip na serwer do /home/user"
    Got: 
    Expected pattern: (scp|rsync).*archive\.zip.*(/home|user)
  - [remote] bielik-1.5b: "synchronizuj /opt/app na zdalną maszynę"
    Got: 
    Expected pattern: rsync.*(/opt/app|opt|app)
  - [iot] bielik-1.5b: "sprawdź temperaturę procesora Raspberry Pi"
    Got: 
    Expected pattern: (vcgencmd\s+measure_temp|temp|sensors|cpu)
  - [package_mgmt] bielik-1.5b: "wyświetl globalne pakiety yarn"
    Got: 
    Expected pattern: (yarn|npm)\s+(list|ls|global list)
  - [rag] bielik-1.5b: "przeszukaj Qdrant w poszukiwaniu 'deep learning'"
    Got: 
    Expected pattern: (qdrant|query|search).*deep.?learning
  - [rag] bielik-1.5b: "wygeneruj embeddingi przez model sentence-transformers"
    Got: 
    Expected pattern: (sentence|transform|embed|python)
  - [rag] bielik-1.5b: "zaindeksuj pliki Markdown z /content"
    Got: 
    Expected pattern: (markdown|md|langchain|load|read).*(/content|content)
  - [presentation] bielik-1.5b: "stwórz wykres liniowy z data.csv"
    Got: 
    Expected pattern: (matplotlib|plt|gnuplot|chart|plot|pandas).*data
  - [sql] qwen2.5:3b: "stwórz tabelę klienci z polami id, email, telefon"
    Got: CREATE TABLE klienci (id SERIAL PRIMARY KEY, email VARCHAR(255), telefon VARCHAR
    Expected pattern: CREATE\s+TABLE.*klient
  - [data] qwen2.5:3b: "policz unikalne wartości w kolumnie type z events.csv"
    Got: cut -d',' -f4 events.csv | sort | uniq -c | sort -nr
    Expected pattern: ((cut.*(type|\-f\s*2|\-f2).*events\.csv)|(awk.*type.*events\.csv)).*(sort|uniq)
  - [shell] gemma2:2b: "wyświetl 15 procesów zużywających najwięcej CPU"
    Got: 
    Expected pattern: (ps.*sort|top|ps.*cpu)
  - [docker] gemma2:2b: "wyświetl wszystkie zatrzymane kontenery"
    Got: 
    Expected pattern: docker\s+(ps|container\s+ls)
  - [docker] gemma2:2b: "pokaż ostatnie 50 linii logów kontenera redis"
    Got: 
    Expected pattern: docker\s+logs.*(redis|--tail|50)
  - [sql] gemma2:2b: "wybierz klientów z Krakowa"
    Got: 
    Expected pattern: SELECT.*FROM.*WHERE.*(Krak|city|miasto)
  - [sql] gemma2:2b: "policz sprzedaż pogrupowaną po tygodniu"
    Got: 
    Expected pattern: (SELECT.*COUNT|GROUP\s+BY|count)
  - [sql] gemma2:2b: "stwórz tabelę klienci z polami id, email, telefon"
    Got: 
    Expected pattern: CREATE\s+TABLE.*klient
  - [kubernetes] gemma2:2b: "wyświetl pody w namespace staging"
    Got: 
    Expected pattern: kubectl\s+get\s+pods.*(-n|namespace).*stag
  - [devops] gemma2:2b: "sprawdź czy działa usługa postgresql"
    Got: pg_ctl -d status
    Expected pattern: (systemctl\s+status|service\s+.*status).*postgres
  - [ffmpeg] gemma2:2b: "wyciągnij ścieżkę audio z recording.mkv do wav"
    Got: 
    Expected pattern: ffmpeg.*-i.*(-vn|audio|wav)
  - [ffmpeg] gemma2:2b: "zmień rozdzielczość na 1080p"
    Got: 
    Expected pattern: ffmpeg.*(-vf\s+scale|1080|-1:1080|resize)
  - [data] gemma2:2b: "wyświetl statystyki pliku sales.csv"
    Got: 
    Expected pattern: (csvstat|csvlook|pandas|describe|head).*sales\.csv
  - [data] gemma2:2b: "filtruj customers.json po salary powyżej 5000"
    Got: 
    Expected pattern: jq.*select.*salary.*(>|gt).*5000
  - [data] gemma2:2b: "policz unikalne wartości w kolumnie type z events.csv"
    Got: cut -d',' -f3 events.csv | sort | uniq -c | sort -rn
    Expected pattern: ((cut.*(type|\-f\s*2|\-f2).*events\.csv)|(awk.*type.*events\.csv)).*(sort|uniq)
  - [iot] gemma2:2b: "skanuj urządzenia I2C na szynie 0"
    Got: 
    Expected pattern: i2cdetect.*(-y\s+)?0
  - [package_mgmt] gemma2:2b: "wyświetl globalne pakiety yarn"
    Got: yarn global add
    Expected pattern: (yarn|npm)\s+(list|ls|global list)
  - [rag] gemma2:2b: "przeszukaj Qdrant w poszukiwaniu 'deep learning'"
    Got: 
    Expected pattern: (qdrant|query|search).*deep.?learning
  - [rag] gemma2:2b: "wygeneruj embeddingi przez model sentence-transformers"
    Got: 
    Expected pattern: (sentence|transform|embed|python)
  - [rag] gemma2:2b: "zaindeksuj pliki Markdown z /content"
    Got: 
    Expected pattern: (markdown|md|langchain|load|read).*(/content|content)
  - [presentation] gemma2:2b: "przekonwertuj CHANGELOG.md na PDF"
    Got: 
    Expected pattern: (pandoc|wkhtmltopdf|weasyprint|md).*CHANGELOG.*pdf
  - [sql] qwen2.5-coder:3b: "stwórz tabelę klienci z polami id, email, telefon"
    Got: CREATE TABLE klienci (id SERIAL PRIMARY KEY, email VARCHAR(255), telefon VARCHAR
    Expected pattern: CREATE\s+TABLE.*klient
  - [data] qwen2.5-coder:3b: "policz unikalne wartości w kolumnie type z events.csv"
    Got: cut -d',' -f4 events.csv | sort | uniq -c | sort -rn
    Expected pattern: ((cut.*(type|\-f\s*2|\-f2).*events\.csv)|(awk.*type.*events\.csv)).*(sort|uniq)
  - [package_mgmt] qwen2.5-coder:3b: "wyświetl globalne pakiety yarn"
    Got: yarn global ls
    Expected pattern: (yarn|npm)\s+(list|ls|global list)
  - [rag] qwen2.5-coder:3b: "przeszukaj Qdrant w poszukiwaniu 'deep learning'"
    Got: python3 -c "import qdrant_client; client = qdrant_client.QdrantClient('http://lo
    Expected pattern: (qdrant|query|search).*deep.?learning