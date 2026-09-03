# Przygotowanie danych

Katalog zawiera finalny zbiór pytań oraz materiały i skrypty wykorzystane przy
jego przygotowaniu. Plik [`pytania_all.jsonl`](pytania_all.jsonl) jest wejściem
części eksperymentalnej i obejmuje 500 pytań:

- 200 pytań `general` wybranych ze zbiorów PolQA i PoQuAD;
- 200 ręcznie opracowanych pytań `polish_realia`;
- 100 pytań `global` pochodzących z TriviaQA i przetłumaczonych na język
  polski.

Każdy rekord zawiera identyfikator, kategorię, pytanie, odpowiedź wzorcową,
dopuszczalne warianty odpowiedzi, fragment referencyjny, adres źródła i datę
pozyskania materiału.

## Instalacja

Wymagane są Python 3.12 i `uv`. Z katalogu `data` uruchom:

```bash
uv sync --frozen
```

Pobieranie PolQA, PoQuAD i TriviaQA wymaga dostępu do internetu. Skrypt
tłumaczący zaakceptowane pytania TriviaQA wymaga dodatkowo zmiennej
`OPENAI_API_KEY` i wykonuje płatne wywołania API. Surowe żądania i odpowiedzi
API nie są publikowane w repozytorium.

## Zawartość

- `scripts/01_poquad_polqa_kandydaci.py` — pobranie PolQA i PoQuAD, ujednolicenie
  rekordów oraz utworzenie puli kandydatów `general`;
- `scripts/02_triviaqa_sampling.py` — deterministyczne pobranie i filtrowanie
  kandydatów TriviaQA;
- `scripts/03_selekcja_pytan.py` — interaktywna selekcja pytań oraz eksport
  decyzji do JSONL;
- `scripts/04_tlumaczenie_triviaqa.py` — tłumaczenie zaakceptowanych rekordów
  TriviaQA i odtwarzanie eksportu z archiwum odpowiedzi;
- `prompts/` — wersjonowany prompt użyty podczas tłumaczenia;
- `selekcja_general/` i `selekcja_triviaqa/` — dzienniki decyzji oraz wyniki
  kolejnych etapów selekcji;
- `pytania_pl_realia.jsonl` — ręcznie przygotowana część dotycząca polskich
  realiów;
- `pytania_all.jsonl` — finalny zbiór użyty w eksperymentach.

## Odtworzenie etapów automatycznych

Poniższe polecenia należy wykonywać z katalogu `data`.

### 1. Kandydaci z PolQA i PoQuAD

```bash
uv run python scripts/01_poquad_polqa_kandydaci.py
```

Wynik zostanie zapisany w `kandydaci_general_pelna_pula.csv`.

### 2. Kandydaci z TriviaQA

```bash
uv run python scripts/02_triviaqa_sampling.py
```

Domyślnie skrypt tworzy deterministyczną pulę 250 rekordów w
`triviaqa_kandydaci.csv`.

### 3. Selekcja pytań

Dla części `general` można użyć ustawień domyślnych:

```bash
uv run python scripts/03_selekcja_pytan.py review
```

Dla części `global` trzeba wskazać pulę TriviaQA, katalog wynikowy i kategorię:

```bash
uv run python scripts/03_selekcja_pytan.py \
  --input triviaqa_kandydaci.csv \
  --output-dir selekcja_triviaqa \
  --target 100 \
  --category global \
  review
```

Polecenia `stats`, `next`, `accept`, `reject`, `undo` i `export` umożliwiają
odpowiednio sprawdzanie postępu, obsługę pojedynczych decyzji i odtworzenie
wyników z dziennika. Szczegóły pokazuje opcja `--help`.

### 4. Tłumaczenie TriviaQA

Zaakceptowane rekordy można przetłumaczyć po ustawieniu `OPENAI_API_KEY`:

```bash
uv run python scripts/04_tlumaczenie_triviaqa.py translate
```

Surowe odpowiedzi są lokalnie dopisywane do ignorowanego przez Git pliku
`selekcja_triviaqa/tlumaczenie/surowe_odpowiedzi.jsonl`, dzięki czemu przerwany
proces można wznowić. Archiwum zawiera pełne żądania i identyfikatory API,
dlatego nie należy go publikować. Finalne, sprawdzone rekordy TriviaQA są już
częścią `pytania_all.jsonl`.

## Etapy ręczne

Skrypty nie automatyzują całego procesu powstania finalnego zbioru. Ręcznej
kontroli wymagały w szczególności:

- akceptacja i odrzucanie kandydatów;
- sprawdzenie tłumaczeń, odpowiedzi i aliasów;
- uzupełnienie pytań TriviaQA o fragmenty i adresy źródłowe, którego wynik
  zapisano w `selekcja_triviaqa/pytania_z_pasazami.jsonl`;
- opracowanie części `polish_realia`;
- połączenie trzech części w `pytania_all.jsonl`.

Z tego względu `pytania_all.jsonl` jest kanoniczną wersją danych użytych w
badaniu, a nie wyłącznie rezultatem jednego polecenia budującego.
