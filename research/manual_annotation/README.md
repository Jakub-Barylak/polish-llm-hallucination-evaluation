# Ręczna walidacja etykiet silver

Narzędzie przygotowuje deterministyczną próbę odpowiedzi i prowadzi
interaktywną, zaślepioną ocenę w terminalu. Źródłowe pytania, odpowiedzi modeli
i wyniki eksperymentów nie są modyfikowane.

Historia ocen jest zapisywana jako append-only JSONL. Cofnięcie decyzji dopisuje
zdarzenie `undo`; wcześniejszy wpis pozostaje dostępny do audytu.

Zależności należy wcześniej zainstalować z katalogu `research` poleceniem
`uv sync --frozen`.

## 1. Przygotowanie próby

Z katalogu `research` uruchom:

```bash
uv run python manual_annotation/manual_annotation.py prepare
```

Domyślna próba obejmuje:

- 60 pytań `general`;
- 60 pytań `polish_realia`;
- 30 pytań `global`;
- odpowiedzi wszystkich czterech modeli, czyli 600 rekordów.

Losowanie używa ziarna `20260818`. Wyniki trafiają do
`manual_annotation/artifacts`. Ponowne przygotowanie wymaga `--force` i jest
dozwolone tylko przed rozpoczęciem ocen. Po rozpoczęciu pracy należy wskazać
nowy katalog przez globalną opcję `--artifacts-dir`.

## 2. Ręczna ocena

```bash
uv run python manual_annotation/manual_annotation.py review --reviewer rater-a
uv run python manual_annotation/manual_annotation.py review --reviewer rater-b
```

Interfejs nie pokazuje nazwy modelu ani etykiet silver. Każdy oceniający
otrzymuje inną, deterministyczną kolejność zadań, a odpowiedzi na to samo
pytanie nie są wyświetlane bezpośrednio po sobie.

Skróty w interfejsie:

- `c` lub `1` — `correct`;
- `h` lub `2` — `hallucination`;
- `a` lub `3` — `abstention`;
- `u` — cofnij ostatnią aktywną ocenę;
- `p` — odłóż bieżący rekord na koniec sesji bez zapisywania decyzji;
- `?` — pokaż pełną instrukcję;
- `q` — zakończ z zachowaniem postępu.

Po wyborze etykiety można podać komentarz i dodatkowo sprawdzone źródło. Przed
zapisem skrypt prosi o potwierdzenie.

## 3. Postęp i cofanie

```bash
uv run python manual_annotation/manual_annotation.py stats --reviewer rater-a
uv run python manual_annotation/manual_annotation.py undo last --reviewer rater-a
uv run python manual_annotation/manual_annotation.py undo mv-0123456789abcdef --reviewer rater-a
```

`undo last` cofa ostatnią nadal aktywną ocenę. Cofnięty rekord ponownie pojawi
się w interaktywnej kolejce.

## 4. Eksport

Bieżący eksport jest odtwarzany automatycznie po każdej decyzji. Można go także
odtworzyć ręcznie:

```bash
uv run python manual_annotation/manual_annotation.py export --reviewer rater-a
```

Standardowy eksport pozostaje zaślepiony. Po zakończeniu ocen można jawnie
dołączyć `question_id`, `model_id` i kategorię:

```bash
uv run python manual_annotation/manual_annotation.py export \
  --reviewer rater-a \
  --with-identities \
  --output manual_annotation/artifacts/annotations/rater-a.identified.jsonl
```

## Artefakty

Pełny przebieg narzędzia tworzy w `artifacts` następujące pliki:

- `metadata.json` — konfiguracja, liczebności i skróty wejść;
- `private_manifest.jsonl` — prywatne mapowanie ślepych ID na model i pytanie;
- `tasks.jsonl` — 600 zaślepionych zadań;
- `annotations/<reviewer>.events.jsonl` — pełny dziennik decyzji;
- `annotations/<reviewer>.jsonl` — aktualny eksport ocen.

W repozytorium opublikowano przygotowane zadania, prywatny manifest potrzebny
do połączenia zaślepionych ocen z odpowiedziami oraz końcowy eksport
`annotations/human.jsonl`. Nie opublikowano pomocniczego `metadata.json` ani
dziennika zdarzeń `*.events.jsonl`, ponieważ nie są potrzebne do odtworzenia
analizy na podstawie finalnych ocen.

## Testy

Z katalogu `research`:

```bash
uv run python -m unittest manual_annotation.test_manual_annotation -v
```
