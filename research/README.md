# Eksperymenty

Katalog zawiera kod i wyniki części eksperymentalnej: generowanie odpowiedzi
przez cztery lokalne modele językowe, automatyczną detekcję halucynacji według
trzech protokołów, ręczną weryfikację próby oraz analizę statystyczną.

## Instalacja

Wymagane są Python 3.12 i `uv`. Z katalogu `research` uruchom:

```bash
uv sync --frozen
```

Do ponownego generowania odpowiedzi wymagany jest dodatkowo plik wykonywalny
`llama-server` z projektu `llama.cpp`. Skrypt może znaleźć go w zmiennej `PATH`
albo otrzymać ścieżkę przez opcję `--llama-server`.

Polecenia wykonujące automatyczną detekcję wymagają zmiennej środowiskowej
`OPENAI_API_KEY` i mogą generować koszty. Podgląd żądań, analiza istniejących
wyników, ręczna walidacja i testy nie wymagają klucza API.

## Najważniejsze pliki

- `run_models_llamacpp.py` — uruchamianie generatorów GGUF przez
  `llama-server`;
- `odpowiedzi.jsonl` — 2 000 odpowiedzi: cztery generatory razy 500 pytań;
- `verification_experiments.toml` — wersjonowane definicje protokołów detekcji;
- `verify_answers.py` i `verification/` — budowanie żądań, komunikacja z API,
  walidacja, archiwizacja i eksport etykiet;
- `prompts/` — prompty detektora odpowiadające poszczególnym protokołom;
- `output/` — opublikowane etykiety z pięciu przebiegów każdego protokołu i
  zbiorczy raport `stats.md`;
- `manual_annotation/` — narzędzie oraz artefakty ręcznej weryfikacji;
- `silver_labels_stats.py` — odtworzenie raportu statystycznego;
- `test_silver_labels_stats.py` i `manual_annotation/test_manual_annotation.py`
  — testy automatyczne.

## Generowanie odpowiedzi

Skrypt `run_models_llamacpp.py` kolejno uruchamia cztery generatory:

- `CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412`;
- `meta-llama/Llama-3.1-8B-Instruct`;
- `speakleash/Bielik-11B-v2.3-Instruct`;
- `mistralai/Mistral-7B-Instruct-v0.2`.

Dla każdego modelu pobierany jest wariant GGUF w kwantyzacji `Q4_K_M`. Skrypt
uruchamia osobny proces `llama-server`, wysyła pytania do lokalnego API i
zapisuje odpowiedzi razem z parametrami generacji. Domyślne ustawienia użyte w
badaniu znajdują się bezpośrednio w skrypcie.

Uruchomienie z katalogu `research`:

```bash
uv run python run_models_llamacpp.py \
  --input ../data/pytania_all.jsonl \
  --output odpowiedzi.jsonl
```

Pobranie modeli wymaga dostępu do serwisu Hugging Face, a ich uruchomienie —
odpowiednich zasobów obliczeniowych. Istniejący plik wynikowy jest domyślnie
wznawiany: zapisane pary model–pytanie zostają pominięte. Opcja `--overwrite`
usuwa tę ochronę i rozpoczyna generowanie od początku.

## Protokoły detekcji

Plik `verification_experiments.toml` definiuje cztery wersjonowane protokoły:

- `original-v1` — historyczny wariant wykorzystujący odpowiedź wzorcową,
  warianty odpowiedzi i fragment referencyjny;
- `gold-only-v1` — odpowiedź wzorcowa i dopuszczalne warianty, bez fragmentu
  źródłowego i wyszukiwania internetowego;
- `passage-v1` — fragment referencyjny, bez odpowiedzi wzorcowej;
- `source-web-v1` — adres strony źródłowej oraz obowiązkowe wyszukanie i odczyt
  źródła, bez przekazania odpowiedzi wzorcowej i fragmentu.

Główne porównanie obejmuje trzy ostatnie protokoły. Każdy z nich wykorzystuje
ten sam model detektora, Responses API, niski poziom wnioskowania i ścisły
schemat odpowiedzi. Tylko `source-web-v1` korzysta z wyszukiwania sieciowego.

Kod wykonawczy jest podzielony według odpowiedzialności:

- `verification/config.py` — wczytywanie i walidacja konfiguracji TOML;
- `verification/data.py` — wczytywanie danych, filtry i budowanie wejścia;
- `verification/schema.py` — schemat i walidacja odpowiedzi detektora;
- `verification/api.py` — żądania synchroniczne, Batch API i kontrola źródeł;
- `verification/storage.py` — identyfikatory rekordów, archiwum i eksport JSONL;
- `verification/runner.py` — sterowanie przebiegiem i obsługa ponowień.

### Podgląd bez wywołania API

Pełne żądanie można sprawdzić bez wysyłania danych i bez klucza API:

```bash
uv run python verify_answers.py --experiment gold-only-v1 \
  preview --ids pl-realia-0002
uv run python verify_answers.py --experiment passage-v1 \
  preview --ids pl-realia-0002
uv run python verify_answers.py --experiment source-web-v1 \
  preview --ids pl-realia-0002
```

### Nowy przebieg

Repozytorium zawiera finalne pliki `silver_labels.jsonl`, ale nie zawiera
surowych archiwów odpowiedzi API ani plików stanu Batch API. Przed nowym
przebiegiem nie należy kierować zapisu do istniejącego katalogu
`output/<protokół>/<przebieg>`, ponieważ można w ten sposób zastąpić
opublikowany eksport wynikiem nowego uruchomienia.

Dla zwykłego wywołania API można jawnie podać nowy katalog przez ścieżki
archiwum i eksportu:

```bash
uv run python verify_answers.py \
  --experiment gold-only-v1 \
  --archive runs/gold-only-v1/1/surowe_adnotacje.jsonl \
  --output runs/gold-only-v1/1/silver_labels.jsonl \
  annotate --limit 3
```

Po sprawdzeniu próby usuń `--limit 3`, aby wykonać pełny przebieg. Dla każdego
protokołu i każdego z pięciu powtórzeń należy użyć osobnego, pustego katalogu.
Przerwany przebieg można wznowić tym samym poleceniem. Zgodne, ukończone
rekordy są odczytywane z archiwum i pomijane.

Przy odpowiedzi HTTP 429 wykonawca czeka przez czas wskazany przez API i
ponawia rekord. Domyślny limit wynosi 20 prób i można go zmienić opcją
`--max-retries`.

### Batch API

Dla Batch API katalog artefaktów ustawia pole `artifacts_dir` wybranego
protokołu w `verification_experiments.toml`. Do nowego przebiegu ustaw nową
ścieżkę, na przykład:

```toml
[experiments.source-web-v1]
artifacts_dir = "runs/source-web-v1/1"
```

Następnie przygotuj, wyślij i odbierz zadanie:

```bash
uv run python verify_answers.py --experiment source-web-v1 prepare-batch
uv run python verify_answers.py --experiment source-web-v1 submit-batch
uv run python verify_answers.py --experiment source-web-v1 batch-status
uv run python verify_answers.py --experiment source-web-v1 collect-batch
```

`submit-batch` jest operacją płatną. Stan zadania i jego identyfikator są
zapisywane w `batch_state.json`, dlatego skrypt chroni przed przypadkowym
ponownym wysłaniem tego samego przebiegu. Opcja `--resubmit` świadomie omija tę
ochronę.

W katalogu artefaktów powstają między innymi:

- `surowe_adnotacje.jsonl` — pełne żądania, odpowiedzi, błędy i dane audytowe;
- `silver_labels.jsonl` — aktualny eksport prawidłowych etykiet;
- `batch_input.jsonl`, `batch_output.jsonl` i `batch_errors.jsonl` — dane
  wymieniane z Batch API;
- `batch_state.json` — identyfikatory i stan zadania.

W protokole `source-web-v1` wynik trafia do eksportu tylko wtedy, gdy detektor
wykonał wyszukiwanie, a oczekiwany adres źródła wystąpił w wynikach albo został
bezpośrednio odwiedzony. Niepoprawne próby pozostają w archiwum i mogą zostać
ponowione.

## Wyniki i analiza statystyczna

Końcowe etykiety mają układ:

```text
output/<protokół>/<numer-przebiegu>/silver_labels.jsonl
```

Katalog `output` zawiera pięć przebiegów dla `gold-only-v1`, `passage-v1` i
`source-web-v1`. Braki w części `source-web-v1` są zachowane jawnie; nie należy
interpretować ich jako etykiety innej klasy.

Raport można odtworzyć z opublikowanych eksportów i ręcznej walidacji:

```bash
uv run python silver_labels_stats.py output stats-new.md
```

Bez drugiego argumentu raport zostanie wypisany na standardowe wyjście.
Domyślnie analiza używa 10 000 powtórzeń bootstrapu i ziarna 42. Parametry
można jawnie zmienić:

```bash
uv run python silver_labels_stats.py output stats-new.md \
  --bootstrap-repetitions 10000 \
  --bootstrap-seed 42
```

Raport obejmuje między innymi kompletność danych, rozkłady etykiet, konsensus,
stabilność ocen, zgodność z ręczną walidacją, porównania protokołów i wyniki w
podziale na generator oraz kategorię pytań.

Szczegółowy opis ręcznej walidacji znajduje się w
[`manual_annotation/README.md`](manual_annotation/README.md).

## Testy

Z katalogu `research` uruchom:

```bash
uv run python -m unittest manual_annotation.test_manual_annotation -v
uv run python -m unittest test_silver_labels_stats -v
```
