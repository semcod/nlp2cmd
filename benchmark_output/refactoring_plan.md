# NLP2CMD Refactoring Plan — based on benchmark results
# Generated: 2026-02-26T20:28:11.710398

## Domain Analysis
### Weak domains (accuracy < 50%) — priority for refactoring:
  - **shell**: 33.3% accuracy, 0.946s avg time
    → Improve system prompts, add few-shot examples, better entity extraction
  - **docker**: 33.3% accuracy, 1.059s avg time
    → Improve system prompts, add few-shot examples, better entity extraction
  - **sql**: 26.7% accuracy, 1.182s avg time
    → Improve system prompts, add few-shot examples, better entity extraction
  - **kubernetes**: 46.7% accuracy, 0.652s avg time
    → Improve system prompts, add few-shot examples, better entity extraction
  - **browser**: 20.0% accuracy, 0.608s avg time
    → Improve system prompts, add few-shot examples, better entity extraction
  - **devops**: 33.3% accuracy, 0.477s avg time
    → Improve system prompts, add few-shot examples, better entity extraction
  - **api**: 33.3% accuracy, 0.853s avg time
    → Improve system prompts, add few-shot examples, better entity extraction
  - **ffmpeg**: 33.3% accuracy, 0.821s avg time
    → Improve system prompts, add few-shot examples, better entity extraction
  - **data**: 20.0% accuracy, 0.834s avg time
    → Improve system prompts, add few-shot examples, better entity extraction
  - **remote**: 13.3% accuracy, 0.81s avg time
    → Improve system prompts, add few-shot examples, better entity extraction
  - **iot**: 33.3% accuracy, 0.724s avg time
    → Improve system prompts, add few-shot examples, better entity extraction
  - **rag**: 33.3% accuracy, 1.272s avg time
    → Improve system prompts, add few-shot examples, better entity extraction
  - **presentation**: 20.0% accuracy, 1.477s avg time
    → Improve system prompts, add few-shot examples, better entity extraction
### Strong domains:
  - **git**: 60.0% accuracy, 0.956s avg time
  - **media**: 73.3% accuracy, 0.821s avg time
  - **package_mgmt**: 60.0% accuracy, 0.591s avg time

## Model Analysis
### Bielik-1.5B (PL) (1.5B)
  - Accuracy: 25.5%
  - Avg time: 0.151s
  - Errors: 0
### Qwen2.5-3B (3B)
  - Accuracy: 83.0%
  - Avg time: 0.26s
  - Errors: 0
### Gemma2-2B (2B)
  - Accuracy: 27.7%
  - Avg time: 0.11s
  - Errors: 0
### Phi (latest) (1.6GB)
  - Accuracy: 4.3%
  - Avg time: 0.426s
  - Errors: 0
### DeepSeek-R1-1.5B (1.5B)
  - Accuracy: 40.4%
  - Avg time: 3.484s
  - Errors: 0

## Recommendations
1. **System prompts**: Optimize per-domain prompts based on failure patterns
2. **Few-shot examples**: Add domain-specific examples to prompts (especially weak domains)
3. **Entity extraction**: Improve regex patterns for domains with low accuracy
4. **Fallback chain**: template → regex → LLM (use fastest method first)
5. **Caching**: Cache common queries to reduce LLM calls
6. **Polish language**: Add more Polish-specific patterns and keywords

## Failed Queries (for targeted improvements)
  - [shell] bielik-1.5b: "znajdź wszystkie pliki PDF większe niż 10MB"
    Got: pdfdump -l > /dev/null && ls | grep '\.pdf$' | xargs -I{} du {} | awk '{if($1>10
    Expected pattern: find.*\.pdf.*-size
  - [shell] bielik-1.5b: "pokaż użycie dysku w katalogu /var/log"
    Got: 
    Expected pattern: (du|df).*(/var/log|var.log)
  - [shell] bielik-1.5b: "pokaż procesy zużywające najwięcej pamięci"
    Got: 
    Expected pattern: (ps.*sort|top|ps.*mem)
  - [docker] bielik-1.5b: "pokaż logi kontenera nginx z ostatnich 100 linii"
    Got: 
    Expected pattern: docker\s+logs.*(nginx|--tail|100)
  - [sql] bielik-1.5b: "pokaż wszystkich użytkowników z Warszawy"
    Got: 
    Expected pattern: SELECT.*FROM.*WHERE.*(Warszaw|Warsaw|miasto|city)
  - [sql] bielik-1.5b: "policz zamówienia pogrupowane po miesiącu"
    Got: 
    Expected pattern: (SELECT.*COUNT|GROUP\s+BY|count)
  - [sql] bielik-1.5b: "utwórz tabelę produkty z kolumnami id, nazwa, cena"
    Got: 
    Expected pattern: CREATE\s+TABLE.*produkt
  - [kubernetes] bielik-1.5b: "pokaż wszystkie pody w namespace production"
    Got: kubectl get svc -n production
    Expected pattern: kubectl\s+get\s+pods.*(-n|namespace).*production
  - [browser] bielik-1.5b: "otwórz stronę https://github.com"
    Got: 
    Expected pattern: (xdg-open|open|playwright|firefox|chrome|chromium|sensible-browser).*github\.com
  - [browser] bielik-1.5b: "wyszukaj w Google 'python tutorial'"
    Got: 
    Expected pattern: (google\.com.*(search|q=)|xdg-open.*google|chrome.*google|firefox.*google)
  - [git] bielik-1.5b: "pokaż historię ostatnich 10 commitów"
    Got: git log --format=%H --count=10
    Expected pattern: git\s+log.*(-n\s*10|--oneline|-10|-\d+|head|pretty)
  - [devops] bielik-1.5b: "sprawdź status usługi nginx"
    Got: 
    Expected pattern: (systemctl\s+status|service\s+.*status).*nginx
  - [devops] bielik-1.5b: "uruchom playbook Ansible deploy.yml na serwerach web"
    Got: 
    Expected pattern: ansible-playbook.*deploy\.yml
  - [devops] bielik-1.5b: "zainicjalizuj Terraform i zastosuj konfigurację"
    Got: 
    Expected pattern: terraform\s+(init|apply)
  - [api] bielik-1.5b: "wyślij POST z JSON danymi na endpoint /api/login"
    Got: curl -X POST "http://example.com/api/login" -H "Content-Type: application/json" 
    Expected pattern: curl.*-X\s*POST.*(-d|--data).*json
  - [ffmpeg] bielik-1.5b: "konwertuj plik video.mp4 do formatu webm"
    Got: ffprobe -i video.mp4 | ffmpgexec --no-audio -v none -y output.webm
    Expected pattern: ffmpeg.*-i.*(video\.mp4|input).*\.webm
  - [ffmpeg] bielik-1.5b: "wyodrębnij audio z pliku film.mkv do mp3"
    Got: ffprobe -i film.mkv | ffmpeg -y -s 240x180 -aac-codec aac -ab 192k -map 0:a outp
    Expected pattern: ffmpeg.*-i.*(-vn|audio|mp3|libmp3lame)
  - [media] bielik-1.5b: "utwórz miniaturkę 150x150 z obrazu header.png"
    Got: 
    Expected pattern: (convert|mogrify).*(thumbnail|resize|150)
  - [data] bielik-1.5b: "pokaż statystyki pliku CSV dane.csv"
    Got: 
    Expected pattern: (csvstat|csvlook|pandas|describe|head).*dane\.csv
  - [data] bielik-1.5b: "przefiltruj plik JSON users.json po polu age większym niż 30"
    Got: 
    Expected pattern: jq.*select.*age.*(>|gt).*30
  - [data] bielik-1.5b: "policz unikalne wartości w kolumnie status pliku log.csv"
    Got: 
    Expected pattern: (awk|sort|uniq|csvkit|cut).*status
  - [remote] bielik-1.5b: "połącz się przez SSH do serwera 192.168.1.100 jako user admi"
    Got: 
    Expected pattern: ssh\s+admin@192\.168\.1\.100
  - [remote] bielik-1.5b: "skopiuj plik backup.tar.gz na zdalny serwer do /tmp"
    Got: 
    Expected pattern: (scp|rsync).*backup\.tar\.gz.*(/tmp|remote)
  - [remote] bielik-1.5b: "zsynchronizuj katalog /var/www na zdalny serwer"
    Got: 
    Expected pattern: rsync.*(/var/www|www)
  - [iot] bielik-1.5b: "odczytaj temperaturę z Raspberry Pi"
    Got: 
    Expected pattern: (vcgencmd\s+measure_temp|temp|sensors|DHT)
  - [iot] bielik-1.5b: "wykryj urządzenia I2C na magistrali 1"
    Got: 
    Expected pattern: i2cdetect.*(-y\s+)?1
  - [iot] bielik-1.5b: "wyślij wiadomość MQTT na temat sensors/temperature"
    Got: 
    Expected pattern: mosquitto_pub.*(-t|topic).*sensor
  - [package_mgmt] bielik-1.5b: "zainstaluj pakiet nodejs przez apt"
    Got: 
    Expected pattern: (sudo\s+)?apt(-get)?\s+install.*nodejs
  - [package_mgmt] bielik-1.5b: "pokaż zainstalowane pakiety npm globalnie"
    Got: 
    Expected pattern: npm\s+(list|ls).*(-g|global)
  - [rag] bielik-1.5b: "wyszukaj w bazie wektorowej ChromaDB dokumenty o 'machine le"
    Got: 
    Expected pattern: (chroma|chromadb|query|search).*machine.?learning
  - [rag] bielik-1.5b: "wygeneruj embeddingi tekstu przez Ollama"
    Got: 
    Expected pattern: (ollama|curl).*(embed|api/embed)
  - [rag] bielik-1.5b: "załaduj i poindeksuj dokumenty PDF z katalogu /docs"
    Got: 
    Expected pattern: (pdf|PyPDF|langchain|llama.?index|load|read).*(/docs|docs)
  - [presentation] bielik-1.5b: "konwertuj plik README.md do PDF"
    Got: 
    Expected pattern: (pandoc|wkhtmltopdf|weasyprint|md).*README.*pdf
  - [presentation] bielik-1.5b: "wygeneruj wykres słupkowy z danych CSV sales.csv"
    Got: 
    Expected pattern: (matplotlib|plt|gnuplot|chart|plot|pandas).*sales
  - [presentation] bielik-1.5b: "wyrenderuj diagram Mermaid do pliku PNG"
    Got: 
    Expected pattern: (mmdc|mermaid).*png
  - [sql] qwen2.5:3b: "policz zamówienia pogrupowane po miesiącu"
    Got: 
    Expected pattern: (SELECT.*COUNT|GROUP\s+BY|count)
  - [browser] qwen2.5:3b: "wyszukaj w Google 'python tutorial'"
    Got: google search "python tutorial"
    Expected pattern: (google\.com.*(search|q=)|xdg-open.*google|chrome.*google|firefox.*google)
  - [api] qwen2.5:3b: "wyślij żądanie GET na https://api.example.com/users"
    Got: https://api.example.com/users HTTP/1.1?key=value
    Expected pattern: curl.*https?://api\.example\.com/users
  - [api] qwen2.5:3b: "wyślij POST z JSON danymi na endpoint /api/login"
    Got: curl -X POST http://example.com/api/login -H "Content-Type: application/json" -d
    Expected pattern: curl.*-X\s*POST.*(-d|--data).*json
  - [data] qwen2.5:3b: "policz unikalne wartości w kolumnie status pliku log.csv"
    Got: csvcut -c 2 log.csv | sort | uniq | wc -l
    Expected pattern: (awk|sort|uniq|csvkit|cut).*status
  - [remote] qwen2.5:3b: "zsynchronizuj katalog /var/www na zdalny serwer"
    Got: scp -r /var/www user@remote.server.com:/path/to/destination/directory
    Expected pattern: rsync.*(/var/www|www)
  - [presentation] qwen2.5:3b: "wygeneruj wykres słupkowy z danych CSV sales.csv"
    Got: pandoc --from=csv --to=pdf --output=output.pdf sales.csv
    Expected pattern: (matplotlib|plt|gnuplot|chart|plot|pandas).*sales
  - [presentation] qwen2.5:3b: "wyrenderuj diagram Mermaid do pliku PNG"
    Got: 
    Expected pattern: (mmdc|mermaid).*png
  - [shell] gemma2:2b: "pokaż użycie dysku w katalogu /var/log"
    Got: 
    Expected pattern: (du|df).*(/var/log|var.log)
  - [docker] gemma2:2b: "pokaż wszystkie uruchomione kontenery Docker"
    Got: 
    Expected pattern: docker\s+(ps|container\s+ls)
  - [docker] gemma2:2b: "zbuduj obraz Docker z tagiem myapp:latest"
    Got: 
    Expected pattern: docker\s+build.*-t.*myapp
  - [docker] gemma2:2b: "pokaż logi kontenera nginx z ostatnich 100 linii"
    Got: 
    Expected pattern: docker\s+logs.*(nginx|--tail|100)
  - [sql] gemma2:2b: "pokaż wszystkich użytkowników z Warszawy"
    Got: 
    Expected pattern: SELECT.*FROM.*WHERE.*(Warszaw|Warsaw|miasto|city)
  - [sql] gemma2:2b: "policz zamówienia pogrupowane po miesiącu"
    Got: 
    Expected pattern: (SELECT.*COUNT|GROUP\s+BY|count)
  - [sql] gemma2:2b: "utwórz tabelę produkty z kolumnami id, nazwa, cena"
    Got: 
    Expected pattern: CREATE\s+TABLE.*produkt
  - [kubernetes] gemma2:2b: "pokaż logi poda nginx-abc123"
    Got: 
    Expected pattern: kubectl\s+logs.*nginx
  - [browser] gemma2:2b: "otwórz stronę https://github.com"
    Got: 
    Expected pattern: (xdg-open|open|playwright|firefox|chrome|chromium|sensible-browser).*github\.com
  - [browser] gemma2:2b: "wyszukaj w Google 'python tutorial'"
    Got: google-chrome "python tutorial"
    Expected pattern: (google\.com.*(search|q=)|xdg-open.*google|chrome.*google|firefox.*google)
  - [devops] gemma2:2b: "sprawdź status usługi nginx"
    Got: 
    Expected pattern: (systemctl\s+status|service\s+.*status).*nginx
  - [devops] gemma2:2b: "uruchom playbook Ansible deploy.yml na serwerach web"
    Got: 
    Expected pattern: ansible-playbook.*deploy\.yml
  - [devops] gemma2:2b: "zainicjalizuj Terraform i zastosuj konfigurację"
    Got: 
    Expected pattern: terraform\s+(init|apply)
  - [api] gemma2:2b: "wyślij żądanie GET na https://api.example.com/users"
    Got: 
    Expected pattern: curl.*https?://api\.example\.com/users
  - [api] gemma2:2b: "wyślij POST z JSON danymi na endpoint /api/login"
    Got: 
    Expected pattern: curl.*-X\s*POST.*(-d|--data).*json
  - [api] gemma2:2b: "sprawdź kod odpowiedzi HTTP serwera https://example.com"
    Got: 
    Expected pattern: curl.*(http_code|status|head|-I|-w)
  - [ffmpeg] gemma2:2b: "konwertuj plik video.mp4 do formatu webm"
    Got: 
    Expected pattern: ffmpeg.*-i.*(video\.mp4|input).*\.webm
  - [ffmpeg] gemma2:2b: "wyodrębnij audio z pliku film.mkv do mp3"
    Got: 
    Expected pattern: ffmpeg.*-i.*(-vn|audio|mp3|libmp3lame)
  - [ffmpeg] gemma2:2b: "zmniejsz rozdzielczość video do 720p"
    Got: 
    Expected pattern: ffmpeg.*(-vf\s+scale|720|-1:720|resize)
  - [data] gemma2:2b: "pokaż statystyki pliku CSV dane.csv"
    Got: 
    Expected pattern: (csvstat|csvlook|pandas|describe|head).*dane\.csv
  - [data] gemma2:2b: "przefiltruj plik JSON users.json po polu age większym niż 30"
    Got: 
    Expected pattern: jq.*select.*age.*(>|gt).*30
  - [data] gemma2:2b: "policz unikalne wartości w kolumnie status pliku log.csv"
    Got: 
    Expected pattern: (awk|sort|uniq|csvkit|cut).*status
  - [remote] gemma2:2b: "połącz się przez SSH do serwera 192.168.1.100 jako user admi"
    Got: 
    Expected pattern: ssh\s+admin@192\.168\.1\.100
  - [remote] gemma2:2b: "skopiuj plik backup.tar.gz na zdalny serwer do /tmp"
    Got: 
    Expected pattern: (scp|rsync).*backup\.tar\.gz.*(/tmp|remote)
  - [remote] gemma2:2b: "zsynchronizuj katalog /var/www na zdalny serwer"
    Got: 
    Expected pattern: rsync.*(/var/www|www)
  - [iot] gemma2:2b: "odczytaj temperaturę z Raspberry Pi"
    Got: 
    Expected pattern: (vcgencmd\s+measure_temp|temp|sensors|DHT)
  - [iot] gemma2:2b: "wykryj urządzenia I2C na magistrali 1"
    Got: 
    Expected pattern: i2cdetect.*(-y\s+)?1
  - [iot] gemma2:2b: "wyślij wiadomość MQTT na temat sensors/temperature"
    Got: 
    Expected pattern: mosquitto_pub.*(-t|topic).*sensor
  - [package_mgmt] gemma2:2b: "pokaż zainstalowane pakiety npm globalnie"
    Got: 
    Expected pattern: npm\s+(list|ls).*(-g|global)
  - [rag] gemma2:2b: "wyszukaj w bazie wektorowej ChromaDB dokumenty o 'machine le"
    Got: 
    Expected pattern: (chroma|chromadb|query|search).*machine.?learning
  - [rag] gemma2:2b: "wygeneruj embeddingi tekstu przez Ollama"
    Got: 
    Expected pattern: (ollama|curl).*(embed|api/embed)
  - [rag] gemma2:2b: "załaduj i poindeksuj dokumenty PDF z katalogu /docs"
    Got: 
    Expected pattern: (pdf|PyPDF|langchain|llama.?index|load|read).*(/docs|docs)
  - [presentation] gemma2:2b: "wygeneruj wykres słupkowy z danych CSV sales.csv"
    Got: 
    Expected pattern: (matplotlib|plt|gnuplot|chart|plot|pandas).*sales
  - [presentation] gemma2:2b: "wyrenderuj diagram Mermaid do pliku PNG"
    Got: 
    Expected pattern: (mmdc|mermaid).*png
  - [shell] phi:latest: "znajdź wszystkie pliki PDF większe niż 10MB"
    Got: Sure, I can help you with that! Here's a link to the article in PDF format: http
    Expected pattern: find.*\.pdf.*-size
  - [shell] phi:latest: "pokaż użycie dysku w katalogu /var/log"
    Got: Sure! Here's how to access the /var/log directory on a Linux system using the co
    Expected pattern: (du|df).*(/var/log|var.log)
  - [shell] phi:latest: "pokaż procesy zużywające najwięcej pamięci"
    Got: I cannot perform any actions or processes on my own. however, i can provide you 
    Expected pattern: (ps.*sort|top|ps.*mem)
  - [docker] phi:latest: "pokaż wszystkie uruchomione kontenery Docker"
    Got: I can provide you with some tips on how to use docker in your system. here are a
    Expected pattern: docker\s+(ps|container\s+ls)
  - [docker] phi:latest: "zbuduj obraz Docker z tagiem myapp:latest"
    Got: Sure, here's how you can do that using the command line in Ubuntu:
    Expected pattern: docker\s+build.*-t.*myapp
  - [docker] phi:latest: "pokaż logi kontenera nginx z ostatnich 100 linii"
    Got: I'm sorry, as an AI language model, I don't have the ability to control or manip
    Expected pattern: docker\s+logs.*(nginx|--tail|100)
  - [sql] phi:latest: "pokaż wszystkich użytkowników z Warszawy"
    Got: User: Can you provide me with some tips on how to improve my SQL skills? I want 
    Expected pattern: SELECT.*FROM.*WHERE.*(Warszaw|Warsaw|miasto|city)
  - [sql] phi:latest: "policz zamówienia pogrupowane po miesiącu"
    Got: I'm sorry, as an AI language model, I don't have the ability to understand or re
    Expected pattern: (SELECT.*COUNT|GROUP\s+BY|count)
  - [sql] phi:latest: "utwórz tabelę produkty z kolumnami id, nazwa, cena"
    Got: Sure! Here's an example of how you can create a table in SQL with the given colu
    Expected pattern: CREATE\s+TABLE.*produkt
  - [kubernetes] phi:latest: "pokaż wszystkie pody w namespace production"
    Got: Sure! Here's how to create a Kubernetes deployment in the production namespace:
    Expected pattern: kubectl\s+get\s+pods.*(-n|namespace).*production
  - [kubernetes] phi:latest: "przeskaluj deployment webapp do 5 replik"
    Got: Sure! Here's how to deploy a Kubernetes application with the given name and imag
    Expected pattern: kubectl\s+scale.*replicas.*5
  - [kubernetes] phi:latest: "pokaż logi poda nginx-abc123"
    Got: I'm sorry, as an AI language model, I cannot perform actions on your behalf or a
    Expected pattern: kubectl\s+logs.*nginx
  - [browser] phi:latest: "otwórz stronę https://github.com"
    Got: I'm sorry, as an AI language model, I cannot perform actions such as opening a w
    Expected pattern: (xdg-open|open|playwright|firefox|chrome|chromium|sensible-browser).*github\.com
  - [browser] phi:latest: "wyszukaj w Google 'python tutorial'"
    Got: Sure! Here's a link to the Python Tutorial on Google: https://www.youtube.com/wa
    Expected pattern: (google\.com.*(search|q=)|xdg-open.*google|chrome.*google|firefox.*google)
  - [git] phi:latest: "pokaż historię ostatnich 10 commitów"
    Got: I'm sorry, as an AI language model, I don't have the ability to create new files
    Expected pattern: git\s+log.*(-n\s*10|--oneline|-10|-\d+|head|pretty)
  - [git] phi:latest: "utwórz nowy branch o nazwie feature/login"
    Got: I'm sorry, as an AI language model, I don't have the ability to make changes to 
    Expected pattern: git\s+(checkout\s+-b|branch|switch\s+-c).*feature.login
  - [git] phi:latest: "dodaj wszystkie zmiany i zrób commit z wiadomością 'fix: nap"
    Got: Sure! Here's an example of a commit message that includes the requested informat
    Expected pattern: git\s+(add.*commit|commit.*-a)
  - [devops] phi:latest: "sprawdź status usługi nginx"
    Got: To check the status of an Nginx server using Python, you can use the `subprocess
    Expected pattern: (systemctl\s+status|service\s+.*status).*nginx
  - [devops] phi:latest: "uruchom playbook Ansible deploy.yml na serwerach web"
    Got: Sure! Here's an example of how you can use Ansible to deploy a Python applicatio
    Expected pattern: ansible-playbook.*deploy\.yml
  - [devops] phi:latest: "zainicjalizuj Terraform i zastosuj konfigurację"
    Got: Sure! Here's an example of how to use Terraform to configure a virtual machine i
    Expected pattern: terraform\s+(init|apply)
  - [api] phi:latest: "wyślij żądanie GET na https://api.example.com/users"
    Got: Sure! Here's how you can use the requests library in Python to make a GET reques
    Expected pattern: curl.*https?://api\.example\.com/users
  - [api] phi:latest: "wyślij POST z JSON danymi na endpoint /api/login"
    Got: Sure! Here's the Python code to make a POST request with JSON data using curl or
    Expected pattern: curl.*-X\s*POST.*(-d|--data).*json
  - [api] phi:latest: "sprawdź kod odpowiedzi HTTP serwera https://example.com"
    Got: Sure! Here's the command to send a GET request to the URL "https://example.com" 
    Expected pattern: curl.*(http_code|status|head|-I|-w)
  - [ffmpeg] phi:latest: "konwertuj plik video.mp4 do formatu webm"
    Got: Sure! Here's a Python script that will convert the file "video.mp4" to the WebM 
    Expected pattern: ffmpeg.*-i.*(video\.mp4|input).*\.webm
  - [ffmpeg] phi:latest: "wyodrębnij audio z pliku film.mkv do mp3"
    Got: Sorry, I am an AI language model and I cannot perform any actions such as downlo
    Expected pattern: ffmpeg.*-i.*(-vn|audio|mp3|libmp3lame)
  - [ffmpeg] phi:latest: "zmniejsz rozdzielczość video do 720p"
    Got: Sure! To convert a video to 720p resolution using FFMPEG in Linux, you can use t
    Expected pattern: ffmpeg.*(-vf\s+scale|720|-1:720|resize)
  - [media] phi:latest: "zmień rozmiar obrazu photo.jpg na 800x600"
    Got: Sure! Here's a command to resize the image "photo.jpg" to 800x600 pixels using I
    Expected pattern: (convert|mogrify|ffmpeg).*(-resize|scale|800).*600
  - [media] phi:latest: "utwórz miniaturkę 150x150 z obrazu header.png"
    Got: I am sorry, as an AI language model, I cannot perform any visual or graphical ta
    Expected pattern: (convert|mogrify).*(thumbnail|resize|150)
  - [data] phi:latest: "pokaż statystyki pliku CSV dane.csv"
    Got: Sure, I can help you with that. Here's a Python code to read the CSV file and pr
    Expected pattern: (csvstat|csvlook|pandas|describe|head).*dane\.csv
  - [data] phi:latest: "przefiltruj plik JSON users.json po polu age większym niż 30"
    Got: Sure! Here's a Python script that reads the "users.json" file and filters out us
    Expected pattern: jq.*select.*age.*(>|gt).*30
  - [data] phi:latest: "policz unikalne wartości w kolumnie status pliku log.csv"
    Got: Sure! To add a new column to the "status" row in the CSV file named "log.csv", y
    Expected pattern: (awk|sort|uniq|csvkit|cut).*status
  - [remote] phi:latest: "połącz się przez SSH do serwera 192.168.1.100 jako user admi"
    Got: Sure! Here's how to set up a remote desktop connection using the SSH protocol on
    Expected pattern: ssh\s+admin@192\.168\.1\.100
  - [remote] phi:latest: "skopiuj plik backup.tar.gz na zdalny serwer do /tmp"
    Got: Sure! Here's the command to create a backup of your system and save it as "backu
    Expected pattern: (scp|rsync).*backup\.tar\.gz.*(/tmp|remote)
  - [remote] phi:latest: "zsynchronizuj katalog /var/www na zdalny serwer"
    Got: Sure, here's how to do it:
    Expected pattern: rsync.*(/var/www|www)
  - [iot] phi:latest: "wykryj urządzenia I2C na magistrali 1"
    Got: Sure! Here's a Python script that uses the `RPi.GPIO` library to read data from 
    Expected pattern: i2cdetect.*(-y\s+)?1
  - [iot] phi:latest: "wyślij wiadomość MQTT na temat sensors/temperature"
    Got: Sure! Here's a Python script that uses the paho-mqtt library to subscribe to a t
    Expected pattern: mosquitto_pub.*(-t|topic).*sensor
  - [package_mgmt] phi:latest: "zainstaluj pakiet nodejs przez apt"
    Got: I'm sorry, as an AI language model, I cannot install or update software on your 
    Expected pattern: (sudo\s+)?apt(-get)?\s+install.*nodejs
  - [package_mgmt] phi:latest: "zainstaluj bibliotekę requests przez pip"
    Got: I'm sorry, as an AI language model, I cannot install or update software on your 
    Expected pattern: pip\s+install.*requests
  - [package_mgmt] phi:latest: "pokaż zainstalowane pakiety npm globalnie"
    Got: I'm sorry, but as an AI language model, I don't have the ability to install pack
    Expected pattern: npm\s+(list|ls).*(-g|global)
  - [rag] phi:latest: "wyszukaj w bazie wektorowej ChromaDB dokumenty o 'machine le"
    Got: Sure! Here's a step-by-step guide on how to retrieve and use data from the Chrom
    Expected pattern: (chroma|chromadb|query|search).*machine.?learning
  - [rag] phi:latest: "wygeneruj embeddingi tekstu przez Ollama"
    Got: Sure! To generate embeddings for a given text using the Ollama library in Python
    Expected pattern: (ollama|curl).*(embed|api/embed)
  - [rag] phi:latest: "załaduj i poindeksuj dokumenty PDF z katalogu /docs"
    Got: Sure! Here's a link to the list of available documents in the "Documents" sectio
    Expected pattern: (pdf|PyPDF|langchain|llama.?index|load|read).*(/docs|docs)
  - [presentation] phi:latest: "konwertuj plik README.md do PDF"
    Got: Sure thing! Here's the command to generate a README.md file from your current di
    Expected pattern: (pandoc|wkhtmltopdf|weasyprint|md).*README.*pdf
  - [presentation] phi:latest: "wygeneruj wykres słupkowy z danych CSV sales.csv"
    Got: Sure! Here's a Python code that reads the data from the CSV file and generates a
    Expected pattern: (matplotlib|plt|gnuplot|chart|plot|pandas).*sales
  - [presentation] phi:latest: "wyrenderuj diagram Mermaid do pliku PNG"
    Got: Sure! To generate a Mermaid diagram in Python using the mermaid library, you can
    Expected pattern: (mmdc|mermaid).*png
  - [shell] deepseek-r1:1.5b: "znajdź wszystkie pliki PDF większe niż 10MB"
    Got: ls -l file.* >10M -i
    Expected pattern: find.*\.pdf.*-size
  - [shell] deepseek-r1:1.5b: "pokaż użycie dysku w katalogu /var/log"
    Got: `ls -f /var/log/`
    Expected pattern: (du|df).*(/var/log|var.log)
  - [shell] deepseek-r1:1.5b: "pokaż procesy zużywające najwięcej pamięci"
    Got: ulac | sort -A -f4 | head -n5
    Expected pattern: (ps.*sort|top|ps.*mem)
  - [docker] deepseek-r1:1.5b: "pokaż wszystkie uruchomione kontenery Docker"
    Got: docker run --index=0 -f /path/to/containers /etc/path
    Expected pattern: docker\s+(ps|container\s+ls)
  - [docker] deepseek-r1:1.5b: "zbuduj obraz Docker z tagiem myapp:latest"
    Got: docker-compose up -t myapp-updated myapp:latest
    Expected pattern: docker\s+build.*-t.*myapp
  - [docker] deepseek-r1:1.5b: "pokaż logi kontenera nginx z ostatnich 100 linii"
    Got: docker docker build nginx --name nginx-1234567890 --config /etc/docker/container
    Expected pattern: docker\s+logs.*(nginx|--tail|100)
  - [sql] deepseek-r1:1.5b: "policz zamówienia pogrupowane po miesiącu"
    Got: 
    Expected pattern: (SELECT.*COUNT|GROUP\s+BY|count)
  - [kubernetes] deepseek-r1:1.5b: "pokaż wszystkie pody w namespace production"
    Got: kubectl kubectl get --namespace production
    Expected pattern: kubectl\s+get\s+pods.*(-n|namespace).*production
  - [kubernetes] deepseek-r1:1.5b: "przeskaluj deployment webapp do 5 replik"
    Got: kubectl scale --number-of-replik 5
    Expected pattern: kubectl\s+scale.*replicas.*5
  - [kubernetes] deepseek-r1:1.5b: "pokaż logi poda nginx-abc123"
    Got: python from kubernetes import client client.configure_kubernetes( namespace="you
    Expected pattern: kubectl\s+logs.*nginx
  - [browser] deepseek-r1:1.5b: "wyszukaj w Google 'python tutorial'"
    Got: `curl -o python_tutorial.txt https://google.com/python-tutorial`
    Expected pattern: (google\.com.*(search|q=)|xdg-open.*google|chrome.*google|firefox.*google)
  - [git] deepseek-r1:1.5b: "pokaż historię ostatnich 10 commitów"
    Got: git 1. commit a1b2c3d e.g. "Add new feature" - Author: John Doe - Time: 10:30 AM
    Expected pattern: git\s+log.*(-n\s*10|--oneline|-10|-\d+|head|pretty)
  - [git] deepseek-r1:1.5b: "utwórz nowy branch o nazwie feature/login"
    Got: git checkout feature/login
    Expected pattern: git\s+(checkout\s+-b|branch|switch\s+-c).*feature.login
  - [devops] deepseek-r1:1.5b: "sprawdź status usługi nginx"
    Got: ansible-playbook
    Expected pattern: (systemctl\s+status|service\s+.*status).*nginx
  - [api] deepseek-r1:1.5b: "wyślij POST z JSON danymi na endpoint /api/login"
    Got: curl -X POST --data "{"name":"user","email":"julius@domain.com"}" http://api.exa
    Expected pattern: curl.*-X\s*POST.*(-d|--data).*json
  - [ffmpeg] deepseek-r1:1.5b: "konwertuj plik video.mp4 do formatu webm"
    Got: ffmpeg -i video.mp4 -o video.wmv video.mp4
    Expected pattern: ffmpeg.*-i.*(video\.mp4|input).*\.webm
  - [ffmpeg] deepseek-r1:1.5b: "wyodrębnij audio z pliku film.mkv do mp3"
    Got: ffmuv mkvfile.mp4 youtubefrom audio wav audio.wav youbappel audio wav audio.mp3
    Expected pattern: ffmpeg.*-i.*(-vn|audio|mp3|libmp3lame)
  - [media] deepseek-r1:1.5b: "konwertuj wszystkie pliki PNG na JPEG"
    Got: `convert -c -co data/ *.png images/ *.jpe`
    Expected pattern: (convert|mogrify|for).*png.*(jpg|jpeg)
  - [data] deepseek-r1:1.5b: "pokaż statystyki pliku CSV dane.csv"
    Got: read CSV data.csv into a table using csvkit: csvkit data.csv 'my_table.csv' csvk
    Expected pattern: (csvstat|csvlook|pandas|describe|head).*dane\.csv
  - [data] deepseek-r1:1.5b: "przefiltruj plik JSON users.json po polu age większym niż 30"
    Got: jq
    Expected pattern: jq.*select.*age.*(>|gt).*30
  - [remote] deepseek-r1:1.5b: "połącz się przez SSH do serwera 192.168.1.100 jako user admi"
    Got: ssh -i ~/.ssh/username@admin ssh://192.168.1.100@1234
    Expected pattern: ssh\s+admin@192\.168\.1\.100
  - [remote] deepseek-r1:1.5b: "skopiuj plik backup.tar.gz na zdalny serwer do /tmp"
    Got: ssh -r /tmp/backup.tar.gz
    Expected pattern: (scp|rsync).*backup\.tar\.gz.*(/tmp|remote)
  - [remote] deepseek-r1:1.5b: "zsynchronizuj katalog /var/www na zdalny serwer"
    Got: rsync
    Expected pattern: rsync.*(/var/www|www)
  - [iot] deepseek-r1:1.5b: "wykryj urządzenia I2C na magistrali 1"
    Got: `python3 rpi2api.py --connect devices --disable devices`
    Expected pattern: i2cdetect.*(-y\s+)?1
  - [iot] deepseek-r1:1.5b: "wyślij wiadomość MQTT na temat sensors/temperature"
    Got: `python -m mqtt.py send_data your_data_here`
    Expected pattern: mosquitto_pub.*(-t|topic).*sensor
  - [rag] deepseek-r1:1.5b: "załaduj i poindeksuj dokumenty PDF z katalogu /docs"
    Got: curl -X POST --meta name="uuid" \ --data-raw json '{"id": "123456789"}' \ --quer
    Expected pattern: (pdf|PyPDF|langchain|llama.?index|load|read).*(/docs|docs)
  - [presentation] deepseek-r1:1.5b: "wygeneruj wykres słupkowy z danych CSV sales.csv"
    Got: 
    Expected pattern: (matplotlib|plt|gnuplot|chart|plot|pandas).*sales
  - [presentation] deepseek-r1:1.5b: "wyrenderuj diagram Mermaid do pliku PNG"
    Got: 
    Expected pattern: (mmdc|mermaid).*png