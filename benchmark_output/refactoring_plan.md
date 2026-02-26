# NLP2CMD Refactoring Plan — based on benchmark results
# Generated: 2026-02-26T21:45:35.674952

## Domain Analysis
### Weak domains (accuracy < 50%) — priority for refactoring:
  - **data**: 41.7% accuracy, 0.235s avg time
    → Improve system prompts, add few-shot examples, better entity extraction
  - **rag**: 41.7% accuracy, 0.573s avg time
    → Improve system prompts, add few-shot examples, better entity extraction
### Strong domains:
  - **shell**: 66.7% accuracy, 0.218s avg time
  - **docker**: 75.0% accuracy, 0.253s avg time
  - **sql**: 50.0% accuracy, 0.343s avg time
  - **kubernetes**: 100.0% accuracy, 0.162s avg time
  - **browser**: 100.0% accuracy, 0.234s avg time
  - **git**: 91.7% accuracy, 0.192s avg time
  - **devops**: 75.0% accuracy, 0.11s avg time
  - **api**: 100.0% accuracy, 0.372s avg time
  - **ffmpeg**: 83.3% accuracy, 0.304s avg time
  - **media**: 100.0% accuracy, 0.236s avg time
  - **remote**: 75.0% accuracy, 0.246s avg time
  - **iot**: 75.0% accuracy, 0.201s avg time
  - **package_mgmt**: 75.0% accuracy, 0.127s avg time
  - **presentation**: 75.0% accuracy, 0.32s avg time

## Model Analysis
### Bielik-1.5B (PL) (1.5B)
  - Accuracy: 55.3%
  - Avg time: 0.282s
  - Errors: 14
### Qwen2.5-3B (3B)
  - Accuracy: 91.5%
  - Avg time: 0.248s
  - Errors: 0
### Gemma2-2B (2B)
  - Accuracy: 66.0%
  - Avg time: 0.235s
  - Errors: 14
### Qwen2.5-Coder-3B (3B)
  - Accuracy: 91.5%
  - Avg time: 0.235s
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
    Got: /home -type f -name '*.docx' -size +5M
    Expected pattern: find.*\.docx.*-size
  - [shell] bielik-1.5b: "sprawdź zajętość dysku w /tmp"
    Got: 
    Expected pattern: (du|df).*(/tmp|tmp)
  - [shell] bielik-1.5b: "wyświetl 15 procesów zużywających najwięcej CPU"
    Got: 
    Expected pattern: (ps.*sort|top|ps.*cpu)
  - [docker] bielik-1.5b: "pokaż ostatnie 50 linii logów kontenera redis"
    Got: <tool_call> {"name": "docker_logs", "arguments": {"container_id": "redis:1234567
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
    Got: cut -d ',' -f3 customers.json | sort | uniq -c | sort -nr
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
  - [iot] bielik-1.5b: "skanuj urządzenia I2C na szynie 0"
    Got: i2cdetect -y 1
    Expected pattern: i2cdetect.*(-y\s+)?0
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
  - [package_mgmt] qwen2.5:3b: "wyświetl globalne pakiety yarn"
    Got: yarn global:list
    Expected pattern: (yarn|npm)\s+(list|ls|global list)
  - [presentation] qwen2.5:3b: "przekonwertuj CHANGELOG.md na PDF"
    Got: markdown -f pdf --output CHANGELOG.pdf CHANGELOG.md
    Expected pattern: (pandoc|wkhtmltopdf|weasyprint|md).*CHANGELOG.*pdf
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
  - [devops] gemma2:2b: "sprawdź czy działa usługa postgresql"
    Got: pg_ctl -d status
    Expected pattern: (systemctl\s+status|service\s+.*status).*postgres
  - [ffmpeg] gemma2:2b: "wyciągnij ścieżkę audio z recording.mkv do wav"
    Got: 
    Expected pattern: ffmpeg.*-i.*(-vn|audio|wav)
  - [ffmpeg] gemma2:2b: "zmień rozdzielczość na 1080p"
    Got: 
    Expected pattern: ffmpeg.*(-vf\s+scale|1080|-1:1080|resize)
  - [data] gemma2:2b: "filtruj customers.json po salary powyżej 5000"
    Got: 
    Expected pattern: jq.*select.*salary.*(>|gt).*5000
  - [data] gemma2:2b: "policz unikalne wartości w kolumnie type z events.csv"
    Got: cut -d',' -f3 events.csv | sort | uniq -c | sort -rn
    Expected pattern: ((cut.*(type|\-f\s*2|\-f2).*events\.csv)|(awk.*type.*events\.csv)).*(sort|uniq)
  - [iot] gemma2:2b: "skanuj urządzenia I2C na szynie 0"
    Got: 
    Expected pattern: i2cdetect.*(-y\s+)?0
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