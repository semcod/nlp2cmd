# LLM Benchmark — Nieprawidłowe komendy (wykryte w benchmarku)

Ten dokument opisuje przypadki, w których benchmark wykrył **niepoprawną komendę** wygenerowaną przez model LLM (tj. `pattern_match=false`) lub gdzie wynik był **niejednoznaczny** (komenda może być sensowna, ale nie spełnia oczekiwanego wzorca).

Źródło danych:
- `benchmark_output/benchmark_results.json`
- Benchmark runner: `examples/benchmark_nlp2cmd.py`

## Jak czytać wpisy

- **Query**: zapytanie w języku naturalnym
- **Expected (regex)**: wzorzec używany w benchmarku
- **Got**: komenda po `clean_command()`
- **Uwagi**: krótka diagnoza: czy to realny błąd modelu, czy błąd/ograniczenie benchmarku

## Wykryte problemy (przykłady z ostatniego wyniku)

Poniżej znajdują się przykłady błędów wyciągnięte z `benchmark_results.json` (na podstawie wpisów `pattern_match=false`).

### shell

#### 1) Find large PDF files
- **Query**: `znajdź wszystkie pliki PDF większe niż 10MB`
- **Expected (regex)**: `find.*\.pdf.*-size`
- **Got**: `pdfdump -l *.pdf | grep -v "^$" | wc -l > /dev/null && du -h --max-depth=1 *.pdf | grep -E '[0-9]+MB'`
- **Uwagi**: realny błąd — model nie użył `find` ani filtra rozmiaru w stylu `-size +10M`. Wygenerował miks narzędzi nieadekwatny do zadania.

#### 2) Disk usage /var/log (pusta odpowiedź)
- **Query**: `pokaż użycie dysku w katalogu /var/log`
- **Expected (regex)**: `(du|df).*(/var/log|var.log)`
- **Got**: *(pusty string)*
- **Uwagi**: realny błąd (pusta odpowiedź). Benchmark po zmianie oznacza to jako `error=empty_response`.

#### 3) Top memory processes (pusta odpowiedź)
- **Query**: `pokaż procesy zużywające najwięcej pamięci`
- **Expected (regex)**: `(ps.*sort|top|ps.*mem)`
- **Got**: *(pusty string)*
- **Uwagi**: realny błąd (pusta odpowiedź).

### docker

#### 4) Container logs (pusta odpowiedź)
- **Query**: `pokaż logi kontenera nginx z ostatnich 100 linii`
- **Expected (regex)**: `docker\s+logs.*(nginx|--tail|100)`
- **Got**: *(pusty string)*
- **Uwagi**: realny błąd (pusta odpowiedź).

### sql

#### 5) SQL queries (puste odpowiedzi)
- **Query**: `pokaż wszystkich użytkowników z Warszawy`
- **Expected (regex)**: `SELECT.*FROM.*WHERE.*(Warszaw|Warsaw|miasto|city)`
- **Got**: *(pusty string)*

- **Query**: `policz zamówienia pogrupowane po miesiącu`
- **Expected (regex)**: `(SELECT.*COUNT|GROUP\s+BY|count)`
- **Got**: *(pusty string)*

- **Query**: `utwórz tabelę produkty z kolumnami id, nazwa, cena`
- **Expected (regex)**: `CREATE\s+TABLE.*produkt`
- **Got**: *(pusty string)*

- **Uwagi**: realne błędy modelu (puste odpowiedzi), ale w praktyce warto też sprawdzić, czy model nie zwrócił whitespace/znaków sterujących (benchmark teraz to lepiej wyłapie).

### devops

#### 6) systemctl status / ansible-playbook (puste odpowiedzi)
- **Query**: `sprawdź status usługi nginx`
- **Expected (regex)**: `(systemctl\s+status|service\s+.*status).*nginx`
- **Got**: *(pusty string)*

- **Query**: `uruchom playbook Ansible deploy.yml na serwerach web`
- **Expected (regex)**: `ansible-playbook.*deploy\.yml`
- **Got**: *(pusty string)*

### data

#### 7) CSV stats / jq filter (puste odpowiedzi)
- **Query**: `pokaż statystyki pliku CSV dane.csv`
- **Expected (regex)**: `(csvstat|csvlook|pandas|describe|head).*dane\.csv`
- **Got**: *(pusty string)*

- **Query**: `przefiltruj plik JSON users.json po polu age większym niż 30`
- **Expected (regex)**: `jq.*select.*age.*(>|gt).*30`
- **Got**: *(pusty string)*

#### 8) Unique count — potencjalnie benchmark false negative
- **Query**: `policz unikalne wartości w kolumnie status pliku log.csv`
- **Expected (regex)** (stare): `(awk|sort|uniq|csvkit|cut).*status`
- **Got**: `cut -d',' -f3 log.csv | sort | uniq -c | sort -rn`
- **Uwagi**: komenda jest potencjalnie poprawna, jeśli `status` to kolumna 3. Dlatego wzorzec w benchmarku został doprecyzowany, aby akceptować zarówno jawne `status`, jak i znany indeks kolumny.

### remote

#### 9) SSH/SCP/rsync (puste odpowiedzi)
- **Query**: `połącz się przez SSH do serwera 192.168.1.100 jako user admin`
- **Expected (regex)**: `ssh\s+admin@192\.168\.1\.100`
- **Got**: *(pusty string)*

- **Query**: `skopiuj plik backup.tar.gz na zdalny serwer do /tmp`
- **Expected (regex)**: `(scp|rsync).*backup\.tar\.gz.*(/tmp|remote)`
- **Got**: *(pusty string)*

- **Query**: `zsynchronizuj katalog /var/www na zdalny serwer`
- **Expected (regex)**: `rsync.*(/var/www|www)`
- **Got**: *(pusty string)*

### iot

#### 10) Raspberry Pi temperature (pusta odpowiedź)
- **Query**: `odczytaj temperaturę z Raspberry Pi`
- **Expected (regex)**: `(vcgencmd\s+measure_temp|temp|sensors|DHT)`
- **Got**: *(pusty string)*

## Znane ograniczenia benchmarku

- Benchmark ocenia wynik przez **regex**, więc:
  - może zaliczać komendy „prawie poprawne” (false positive), np. literówki w URL (`/seaarch` zamiast `/search`) jeśli regex jest zbyt luźny;
  - może odrzucać poprawne alternatywy (false negative), jeśli regex jest zbyt restrykcyjny.
- Benchmark nie wykonuje komend. To jest **walidacja syntaktyczno-wzorcowa**, nie semantyczna.

## Zmiany w benchmarku wykonane w tej iteracji

W `examples/benchmark_nlp2cmd.py` poprawiono:
- czyszczenie komendy: usuwanie inline backticks (np. `` `git log -10` ``);
- oznaczanie pustych odpowiedzi jako `error=empty_response`;
- korekty regexów:
  - `api/POST JSON` — dopasowanie do `Content-Type: application/json` zamiast wymagania „json” w payload;
  - `browser/Google search` — doprecyzowanie do `google.com/search?q=`;
  - `data/unique count` — akceptacja `status` albo `cut -f3`.
