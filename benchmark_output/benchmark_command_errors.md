# NLP2CMD Benchmark — Nieprawidłowe komendy (auto-report)

Generated: `2026-02-26T21:50:06.822250`

Źródło: `examples/benchmark_nlp2cmd.py` + `benchmark_results.json`

## Summary

- Total queries: **188**
- Failed / errors: **47**

## Failures

### Model: `bielik-1.5b`

#### Domain: `api` (1)

##### 1. POST JSON

- Query: `wyślij POST z danymi JSON na /api/register`
- Error: `empty_response`
- Expected (regex): `curl.*-X\s*POST.*(Content-Type:.*json|application/json).*(-d|--data)`
- Got:

```bash

```

#### Domain: `data` (3)

##### 1. CSV stats

- Query: `wyświetl statystyki pliku sales.csv`
- Error: `empty_response`
- Expected (regex): `(csvstat|csvlook|pandas|describe|head).*sales\.csv`
- Got:

```bash

```

##### 2. jq filter

- Query: `filtruj customers.json po salary powyżej 5000`
- Error: `empty_response`
- Expected (regex): `jq.*select.*salary.*(>|gt).*5000`
- Got:

```bash

```

##### 3. Unique count

- Query: `policz unikalne wartości w kolumnie type z events.csv`
- Expected (regex): `((cut.*(type|\-f\s*2|\-f2).*events\.csv)|(awk.*type.*events\.csv)).*(sort|uniq)`
- Got:

```bash
cut -d',' -f3 events.csv | sort | uniq -c | sort -rn
```

#### Domain: `devops` (2)

##### 1. Service status

- Query: `sprawdź czy działa usługa postgresql`
- Error: `empty_response`
- Expected (regex): `(systemctl\s+status|service\s+.*status).*postgres`
- Got:

```bash

```

##### 2. Ansible playbook

- Query: `uruchom playbook setup.yml`
- Error: `empty_response`
- Expected (regex): `ansible-playbook.*setup\.yml`
- Got:

```bash

```

#### Domain: `docker` (2)

##### 1. Build image

- Query: `zbuduj obraz z tagiem webapp:v2.0`
- Expected (regex): `docker\s+build.*-t.*webapp`
- Got:

```bash
docker build -t myapp:latest .
```

##### 2. Container logs

- Query: `pokaż ostatnie 50 linii logów kontenera redis`
- Expected (regex): `docker\s+logs.*(redis|--tail|50)`
- Got:

```bash
<tool_call> {"name": "docker_logs", "arguments": {"container_id": "redis:latest", "size": 50}}</tool_call>
```

#### Domain: `git` (1)

##### 1. Create branch

- Query: `stwórz branch bugfix/auth-error`
- Expected (regex): `git\s+(checkout\s+-b|branch|switch\s+-c).*bugfix.auth`
- Got:

```bash
git checkout bugfix/auth-error
```

#### Domain: `iot` (2)

##### 1. RPi temperature

- Query: `sprawdź temperaturę procesora Raspberry Pi`
- Error: `empty_response`
- Expected (regex): `(vcgencmd\s+measure_temp|temp|sensors|cpu)`
- Got:

```bash

```

##### 2. I2C detect

- Query: `skanuj urządzenia I2C na szynie 0`
- Expected (regex): `i2cdetect.*(-y\s+)?0`
- Got:

```bash
i2cdetect -y 1
```

#### Domain: `package_mgmt` (1)

##### 1. yarn list global

- Query: `wyświetl globalne pakiety yarn`
- Error: `empty_response`
- Expected (regex): `(yarn|npm)\s+(list|ls|global list)`
- Got:

```bash

```

#### Domain: `presentation` (1)

##### 1. Line chart from CSV

- Query: `stwórz wykres liniowy z data.csv`
- Error: `empty_response`
- Expected (regex): `(matplotlib|plt|gnuplot|chart|plot|pandas).*data`
- Got:

```bash

```

#### Domain: `rag` (3)

##### 1. Qdrant query

- Query: `przeszukaj Qdrant w poszukiwaniu 'deep learning'`
- Error: `empty_response`
- Expected (regex): `(qdrant|query|search).*deep.?learning`
- Got:

```bash

```

##### 2. Sentence embeddings

- Query: `wygeneruj embeddingi przez model sentence-transformers`
- Error: `empty_response`
- Expected (regex): `(sentence|transform|embed|python)`
- Got:

```bash

```

##### 3. Index Markdown

- Query: `zaindeksuj pliki Markdown z /content`
- Error: `empty_response`
- Expected (regex): `(markdown|md|langchain|load|read).*(/content|content)`
- Got:

```bash

```

#### Domain: `remote` (3)

##### 1. SSH connect

- Query: `zaloguj się przez SSH na 10.0.0.50 jako root`
- Error: `empty_response`
- Expected (regex): `ssh\s+root@10\.0\.0\.50`
- Got:

```bash

```

##### 2. SCP upload

- Query: `prześlij archive.zip na serwer do /home/user`
- Error: `empty_response`
- Expected (regex): `(scp|rsync).*archive\.zip.*(/home|user)`
- Got:

```bash

```

##### 3. Rsync sync

- Query: `synchronizuj /opt/app na zdalną maszynę`
- Error: `empty_response`
- Expected (regex): `rsync.*(/opt/app|opt|app)`
- Got:

```bash

```

#### Domain: `shell` (3)

##### 1. Find large DOCX files

- Query: `wyszukaj pliki DOCX większe niż 5MB w katalogu /home`
- Error: `empty_response`
- Expected (regex): `find.*\.docx.*-size`
- Got:

```bash

```

##### 2. Disk usage /tmp

- Query: `sprawdź zajętość dysku w /tmp`
- Error: `empty_response`
- Expected (regex): `(du|df).*(/tmp|tmp)`
- Got:

```bash

```

##### 3. Top CPU processes

- Query: `wyświetl 15 procesów zużywających najwięcej CPU`
- Error: `empty_response`
- Expected (regex): `(ps.*sort|top|ps.*cpu)`
- Got:

```bash

```

#### Domain: `sql` (1)

##### 1. CREATE TABLE

- Query: `stwórz tabelę klienci z polami id, email, telefon`
- Expected (regex): `CREATE\s+TABLE.*klient`
- Got:

```bash
CREATE TABLE klienci (id INT PRIMARY KEY AUTO_INCREMENT, email VARCHAR(255), telefon VARCHAR(20));
```

### Model: `gemma2:2b`

#### Domain: `data` (2)

##### 1. jq filter

- Query: `filtruj customers.json po salary powyżej 5000`
- Error: `empty_response`
- Expected (regex): `jq.*select.*salary.*(>|gt).*5000`
- Got:

```bash

```

##### 2. Unique count

- Query: `policz unikalne wartości w kolumnie type z events.csv`
- Expected (regex): `((cut.*(type|\-f\s*2|\-f2).*events\.csv)|(awk.*type.*events\.csv)).*(sort|uniq)`
- Got:

```bash
cut -d',' -f3 events.csv | sort | uniq -c | sort -rn
```

#### Domain: `devops` (1)

##### 1. Service status

- Query: `sprawdź czy działa usługa postgresql`
- Expected (regex): `(systemctl\s+status|service\s+.*status).*postgres`
- Got:

```bash
pg_ctl -d status
```

#### Domain: `docker` (3)

##### 1. List containers

- Query: `wyświetl wszystkie zatrzymane kontenery`
- Error: `empty_response`
- Expected (regex): `docker\s+(ps|container\s+ls)`
- Got:

```bash

```

##### 2. Build image

- Query: `zbuduj obraz z tagiem webapp:v2.0`
- Error: `empty_response`
- Expected (regex): `docker\s+build.*-t.*webapp`
- Got:

```bash

```

##### 3. Container logs

- Query: `pokaż ostatnie 50 linii logów kontenera redis`
- Error: `empty_response`
- Expected (regex): `docker\s+logs.*(redis|--tail|50)`
- Got:

```bash

```

#### Domain: `ffmpeg` (3)

##### 1. Convert to mp4

- Query: `przekonwertuj movie.avi na format mp4`
- Error: `empty_response`
- Expected (regex): `ffmpeg.*-i.*(movie\.avi|input).*\.mp4`
- Got:

```bash

```

##### 2. Extract audio

- Query: `wyciągnij ścieżkę audio z recording.mkv do wav`
- Error: `empty_response`
- Expected (regex): `ffmpeg.*-i.*(-vn|audio|wav)`
- Got:

```bash

```

##### 3. Resize 1080p

- Query: `zmień rozdzielczość na 1080p`
- Error: `empty_response`
- Expected (regex): `ffmpeg.*(-vf\s+scale|1080|-1:1080|resize)`
- Got:

```bash

```

#### Domain: `iot` (1)

##### 1. I2C detect

- Query: `skanuj urządzenia I2C na szynie 0`
- Error: `empty_response`
- Expected (regex): `i2cdetect.*(-y\s+)?0`
- Got:

```bash

```

#### Domain: `kubernetes` (1)

##### 1. Scale deployment

- Query: `skaluj deployment api-server do 3 replik`
- Error: `empty_response`
- Expected (regex): `kubectl\s+scale.*replicas.*3`
- Got:

```bash

```

#### Domain: `rag` (3)

##### 1. Qdrant query

- Query: `przeszukaj Qdrant w poszukiwaniu 'deep learning'`
- Error: `empty_response`
- Expected (regex): `(qdrant|query|search).*deep.?learning`
- Got:

```bash

```

##### 2. Sentence embeddings

- Query: `wygeneruj embeddingi przez model sentence-transformers`
- Error: `empty_response`
- Expected (regex): `(sentence|transform|embed|python)`
- Got:

```bash

```

##### 3. Index Markdown

- Query: `zaindeksuj pliki Markdown z /content`
- Error: `empty_response`
- Expected (regex): `(markdown|md|langchain|load|read).*(/content|content)`
- Got:

```bash

```

#### Domain: `shell` (1)

##### 1. Top CPU processes

- Query: `wyświetl 15 procesów zużywających najwięcej CPU`
- Error: `empty_response`
- Expected (regex): `(ps.*sort|top|ps.*cpu)`
- Got:

```bash

```

#### Domain: `sql` (3)

##### 1. Select WHERE

- Query: `wybierz klientów z Krakowa`
- Error: `empty_response`
- Expected (regex): `SELECT.*FROM.*WHERE.*(Krak|city|miasto)`
- Got:

```bash

```

##### 2. Count GROUP BY

- Query: `policz sprzedaż pogrupowaną po tygodniu`
- Error: `empty_response`
- Expected (regex): `(SELECT.*COUNT|GROUP\s+BY|count)`
- Got:

```bash

```

##### 3. CREATE TABLE

- Query: `stwórz tabelę klienci z polami id, email, telefon`
- Error: `empty_response`
- Expected (regex): `CREATE\s+TABLE.*klient`
- Got:

```bash

```

### Model: `qwen2.5-coder:3b`

#### Domain: `data` (1)

##### 1. Unique count

- Query: `policz unikalne wartości w kolumnie type z events.csv`
- Expected (regex): `((cut.*(type|\-f\s*2|\-f2).*events\.csv)|(awk.*type.*events\.csv)).*(sort|uniq)`
- Got:

```bash
cut -d',' -f4 events.csv | sort | uniq -c | sort -rn
```

#### Domain: `rag` (1)

##### 1. Qdrant query

- Query: `przeszukaj Qdrant w poszukiwaniu 'deep learning'`
- Expected (regex): `(qdrant|query|search).*deep.?learning`
- Got:

```bash
python3 -c "import qdrant_client; client = qdrant_client.QdrantClient('http://localhost:6333'); res = client.search(collection_name='docs', query_vector=[0.1, 0.2, 0.3], limit=5); print(res)"
```

#### Domain: `sql` (1)

##### 1. CREATE TABLE

- Query: `stwórz tabelę klienci z polami id, email, telefon`
- Expected (regex): `CREATE\s+TABLE.*klient`
- Got:

```bash
CREATE TABLE klienci (id SERIAL PRIMARY KEY, email VARCHAR(255), telefon VARCHAR(15));
```

### Model: `qwen2.5:3b`

#### Domain: `data` (1)

##### 1. Unique count

- Query: `policz unikalne wartości w kolumnie type z events.csv`
- Expected (regex): `((cut.*(type|\-f\s*2|\-f2).*events\.csv)|(awk.*type.*events\.csv)).*(sort|uniq)`
- Got:

```bash
cut -d',' -f4 events.csv | sort | uniq -c | sort -nr
```

#### Domain: `package_mgmt` (1)

##### 1. yarn list global

- Query: `wyświetl globalne pakiety yarn`
- Expected (regex): `(yarn|npm)\s+(list|ls|global list)`
- Got:

```bash
yarn global:list
```

#### Domain: `sql` (1)

##### 1. CREATE TABLE

- Query: `stwórz tabelę klienci z polami id, email, telefon`
- Expected (regex): `CREATE\s+TABLE.*klient`
- Got:

```bash
CREATE TABLE klienci (id SERIAL PRIMARY KEY, email VARCHAR(255), telefon VARCHAR(20));
```
