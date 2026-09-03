# Polish LLM Hallucination Evaluation

Repozytorium zawiera dane i kod wykorzystane do badania metod automatycznego
wykrywania halucynacji faktograficznych w krótkich odpowiedziach generowanych
przez polskojęzyczne i wielojęzyczne modele językowe.

Badanie obejmuje 500 pytań w języku polskim oraz odpowiedzi czterech lokalnie
uruchamianych generatorów. Odpowiedzi oceniono za pomocą trzech protokołów
detekcji:

- `gold-only-v1` — na podstawie odpowiedzi wzorcowej i jej dopuszczalnych
  wariantów;
- `passage-v1` — na podstawie przekazanego fragmentu źródłowego;
- `source-web-v1` — po odczytaniu strony wskazanej adresem URL.

Każdy protokół uruchomiono pięć razy. Repozytorium zawiera również wyniki
ręcznej weryfikacji wybranej próby.

## Struktura repozytorium

- [`data`](data/README.md) — przygotowanie zbioru pytań, dane pośrednie i finalny
  zbiór `pytania_all.jsonl`;
- [`research`](research/README.md) — generowanie odpowiedzi, automatyczna
  detekcja halucynacji, ręczna weryfikacja i analiza statystyczna;
- `research/output` — końcowe etykiety z pięciu przebiegów każdego z trzech
  porównywanych protokołów oraz zbiorczy raport.

## Wymagania

Podstawowe wymagania to:

- Python 3.12;
- [uv](https://docs.astral.sh/uv/getting-started/installation/) do utworzenia
  środowisk i instalacji zależności;
- dostęp do internetu podczas pobierania zbiorów i modeli;
- `llama-server` z projektu
  [llama.cpp](https://github.com/ggml-org/llama.cpp) do ponownego wygenerowania
  odpowiedzi lokalnych modeli;
- klucz OpenAI API tylko do ponownego tłumaczenia pytań TriviaQA albo
  uruchamiania automatycznego detektora.

Ponowne wykonanie wywołań API może generować koszty. Do przeglądania danych,
analizy opublikowanych etykiet i uruchamiania testów klucz API nie jest
potrzebny.

## Instalacja

Sklonuj repozytorium:

```bash
git clone https://github.com/Jakub-Barylak/polish-llm-hallucination-evaluation.git
cd polish-llm-hallucination-evaluation
```

Katalogi `data` i `research` mają oddzielne, odtwarzalne środowiska oraz własne
pliki `uv.lock`. Zainstaluj oba zestawy zależności:

```bash
cd data
uv sync --frozen
cd ../research
uv sync --frozen
cd ..
```

Jeżeli potrzebne są operacje korzystające z OpenAI API, skopiuj przygotowany
szablon i uzupełnij lokalny plik `.env`:

```bash
cp .env.example .env
```

```dotenv
OPENAI_API_KEY=your-api-key-here
```

Plik `.env` jest automatycznie odczytywany przez skrypty tłumaczenia i
detekcji oraz ignorowany przez Git. Prawdziwego klucza nie należy wpisywać do
`.env.example` ani zapisywać w repozytorium.

Do generowania odpowiedzi modeli zainstaluj osobno `llama.cpp` zgodnie z jego
instrukcją budowania i upewnij się, że polecenie `llama-server` jest dostępne w
zmiennej `PATH`. Można również przekazać jego położenie przez opcję
`--llama-server` skryptu `research/run_models_llamacpp.py`.

## Szybka weryfikacja instalacji

Testy części badawczej można uruchomić z katalogu `research`:

```bash
cd research
uv run python -m unittest manual_annotation.test_manual_annotation -v
uv run python -m unittest test_silver_labels_stats -v
```

Podgląd przykładowego żądania detektora nie wykonuje połączenia z API:

```bash
uv run python verify_answers.py --experiment gold-only-v1 \
  preview --ids pl-realia-0002
```

Szczegółowe instrukcje odtworzenia poszczególnych etapów znajdują się w
plikach README katalogów [`data`](data/README.md) i
[`research`](research/README.md).
