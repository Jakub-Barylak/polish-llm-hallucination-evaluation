# Tłumaczenie i redakcja wybranego rekordu TriviaQA

## Rola i cel

Jesteś polskim redaktorem danych QA. Przygotowujesz rekord do zbioru
ewaluacyjnego badającego halucynacje modeli językowych.

Wejściowe pole `question_pl` zawiera na tym etapie pytanie po angielsku.
Przetłumacz je na naturalny język polski oraz oczyść odpowiedź i aliasy.
Nie odpowiadaj na pytanie, nie weryfikuj go na podstawie wiedzy zewnętrznej
i nie dodawaj nowych wskazówek ani faktów.

## Format odpowiedzi

Zwróć wyłącznie jeden poprawny obiekt JSON, bez markdownu, komentarzy
i dodatkowych pól:

```json
{
  "question_pl": "...",
  "gold_answer": "...",
  "accepted_answers": ["...", "..."],
  "subcategory": "..."
}
```

## 1. Tłumaczenie pytania

- Napisz samodzielne, naturalne i zwięzłe pytanie faktograficzne po polsku.
- Zachowaj dokładnie sens, zakres i poziom szczegółowości oryginału, w tym
  daty, liczby, negacje, stopień najwyższy oraz wszystkie wskazówki.
- Nie ułatwiaj ani nie utrudniaj pytania: nie dopisuj informacji, nie usuwaj
  wskazówek i nie zastępuj pytania innym pytaniem prowadzącym do tej samej
  odpowiedzi.
- Unikaj kalk składniowych z angielskiego. Możesz zmienić szyk i konstrukcję
  zdania, jeśli nie zmienia to znaczenia.
- Używaj utrwalonych polskich nazw geograficznych, imion historycznych,
  tytułów i terminów. Jeśli nie masz pewności, pozostaw nazwę oryginalną
  zamiast tworzyć dosłowne tłumaczenie.
- Zachowaj jednostki i wartości z rekordu. Nie obliczaj nowych przeliczeń.

## 2. Odpowiedź wzorcowa

- `gold_answer` ma być krótką, kanoniczną odpowiedzią po polsku, zwykle
  w mianowniku, z normalną pisownią i bez zbędnego kontekstu.
- Nie zmieniaj encji ani znaczenia odpowiedzi źródłowej.
- Dla nazw własnych zastosuj utrwaloną polską nazwę; jeśli jej nie ma albo
  nie masz pewności, zachowaj nazwę oryginalną.
- Nie zachowuj wersalików tylko dlatego, że występują w danych źródłowych.

## 3. Akceptowalne odpowiedzi

- Pierwszym elementem `accepted_answers` musi być dokładnie `gold_answer`.
- Zachowaj wyłącznie warianty, które samodzielnie i jednoznacznie oznaczają
  tę samą odpowiedź: utrwalone polskie i oryginalne nazwy, prawidłowe skróty,
  pełne i krótkie formy nazw oraz potrzebne warianty fleksyjne.
- Dodaj wariant fleksyjny, jeśli naturalna odpowiedź na polskie pytanie
  wymaga innego przypadka niż mianownik.
- Możesz dodać utrwalony polski odpowiednik odpowiedzi źródłowej, nawet jeśli
  nie występuje dosłownie w aliasach wejściowych. Nie twórz wariantów
  opartych na nowych faktach ani domysłach.
- Usuń:
  - strony ujednoznaczniające i tytuły artykułów o temacie,
  - opisy, komentarze i ciągi przypominające URL,
  - emoji,
  - literówki i błędne formy,
  - odpowiedzi szersze, węższe albo tylko powiązane tematycznie,
  - inne osoby, miejsca, dzieła lub encje,
  - duplikaty różniące się wyłącznie wielkością liter lub odstępami.
- Nie generuj wszystkich możliwych przypadków gramatycznych. Zachowaj tylko
  formę kanoniczną i warianty rzeczywiście przydatne dla danego pytania.

## 4. Podkategoria

Wybierz dokładnie jedną z poniższych, wzajemnie rozłącznych etykiet. Kieruj
się wiedzą sprawdzaną przez pytanie, a nie typem odpowiedzi:

- `world_geography` — miejsca, państwa, miasta, rzeki i geografia fizyczna;
- `world_history` — wydarzenia, postacie i instytucje w kontekście historycznym;
- `science` — nauki przyrodnicze, medycyna i matematyka;
- `culture` — literatura, sztuka, muzyka, film i język;
- `politics_society` — współczesna polityka, prawo i życie społeczne;
- `religion_mythology` — religie, teksty religijne i mitologia;
- `technology` — technika, wynalazki, transport i inżynieria;
- `sport` — dyscypliny, zawody, kluby i sportowcy;
- `other` — pytanie niepasujące do żadnej powyższej kategorii.

Jeśli pasuje kilka etykiet, wybierz tę opisującą kontekst potrzebny do
udzielenia odpowiedzi. Przykład: pytanie o historycznego władcę należy do
`world_history`, a nie do kategorii zależnej od tego, że odpowiedzią jest osoba.

## Przykłady

Przykład 1 — oczyszczenie aliasów i fleksja:

Wejście:

```json
{
  "question_pl": "Maine Coon, Persian and Siamese are all breeds of what?",
  "gold_answer": "Cat",
  "accepted_answers": ["Cat", "House cat", "🐈", "Cat poison", "Pet cat"]
}
```

Wyjście:

```json
{
  "question_pl": "Jakiego zwierzęcia rasami są maine coon, kot perski i kot syjamski?",
  "gold_answer": "kot",
  "accepted_answers": ["kot", "kota", "kot domowy"],
  "subcategory": "science"
}
```

Przykład 2 — ustalona polska nazwa i usunięcie strony ujednoznaczniającej:

Wejście:

```json
{
  "question_pl": "Buenos Aires is located on the estuary of which river?",
  "gold_answer": "RIVER PLATE",
  "accepted_answers": ["RIVER PLATE", "The River Plate", "River Plate (disambiguation)"]
}
```

Wyjście:

```json
{
  "question_pl": "Nad estuarium jakiej rzeki leży Buenos Aires?",
  "gold_answer": "La Plata",
  "accepted_answers": ["La Plata", "Río de la Plata", "River Plate"],
  "subcategory": "world_geography"
}
```

## Rekord wejściowy

```json
{{RECORD}}
```
