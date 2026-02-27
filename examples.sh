#!/bin/bash

# Lista 10 URL-i z Pomorza (główne domeny)
urls=(
  "https://pracodawcypomorza.pl"
  "https://www.ekspresowastrona.pl"
  "https://brainbox.com.pl"
  "https://rafineriagdanska.pl"
  "https://administrator.gda.pl"
  "https://axsoft.pl"
  "https://www.gdyniaprzedsiebiorcza.pl"
  "https://zielone-grabelki.pl"
  "https://projektfirmagdynia.com.pl"
  "https://sklepagd.slupsk.pl"
)

# Funkcja wyciągająca domenę (bez protokołu, ścieżek, /kontakt itp.)
extract_domain() {
  local url="$1"
  # Usuń protokół http(s)://
  url="${url#*://}"
  # Usuń wszystko od pierwszego /
  url="${url%%/*}"
  # Usuń port :XXXX
  url="${url%:*}";
  echo "$url"
}

echo "# Przykłady poleceń nlp2cmd dla Pomorza (tylko domeny główne):"
echo

# Generuj polecenia dla każdej domeny
for url in "${urls[@]}"; do
  domain=$(extract_domain "$url")
  echo "nlp2cmd -r \"wejdź na https://$domain znajdź formularz kontaktu i wypełnij formularz i wyślij\""
done
