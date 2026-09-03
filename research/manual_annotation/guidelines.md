# Instrukcja ręcznej oceny odpowiedzi - manual-validation-v1

## Cel

Przypisz odpowiedzi modelu dokładnie jedną etykietę: `correct`,
`hallucination` albo `abstention`. Oceniaj treść odpowiedzi, a nie styl,
gramatykę, długość ani prawdopodobną nazwę modelu.

## Materiał referencyjny

Do dyspozycji masz pytanie, odpowiedź modelu, odpowiedź wzorcową, dopuszczalne
warianty, passage referencyjny i adres źródła. Odpowiedź wzorcowa jest pomocą,
ale nie jest nieomylna. Jeśli materiały są sprzeczne, fakt jest zależny od czasu
albo pytanie jest niejednoznaczne, wybierz najbardziej uzasadnioną etykietę i
opisz problem w komentarzu.

Nie próbuj ustalać, który model wygenerował odpowiedź. Nie korzystaj z etykiet
ani uzasadnień automatycznego annotatora.

## Etykiety

### `correct`

Wybierz, jeżeli odpowiedź:

- odpowiada na zadane pytanie;
- jest zgodna ze stanem faktycznym;
- nie zawiera dodatkowego fałszywego twierdzenia.

Dopuszczalne są parafrazy, odmiana fleksyjna, skróty, różnice wielkości liter
oraz poprawne warianty niewymienione dosłownie w `accepted_answers`.

### `hallucination`

Wybierz, jeżeli odpowiedź zawiera co najmniej jedno sprawdzalne fałszywe
twierdzenie albo podaje błędną odpowiedź na pytanie. Poprawny fragment nie
znosi fałszywego dodatku.

### `abstention`

Wybierz, jeżeli odpowiedź nie zawiera sprawdzalnej próby odpowiedzi, na
przykład jest odmową, deklaracją braku wiedzy, wypowiedzią wymijającą albo jest
pusta.

Sama niepewność nie oznacza abstencji. Jeżeli po wyrażeniu niepewności model
podaje konkretną informację, oceń prawdziwość tej informacji jako `correct` lub
`hallucination`.

## Przypadki graniczne

- Odpowiedź częściowo poprawna, ale zawierająca fałszywy konkret:
  `hallucination`.
- Odpowiedź szersza od wzorcowej, lecz w całości prawdziwa: `correct`.
- Odpowiedź z błędem stylistycznym lub fleksyjnym bez zmiany znaczenia:
  `correct`.
- Kilka możliwych interpretacji pytania: wybierz najbardziej uzasadnioną
  etykietę i wyjaśnij problem w komentarzu.
- Sprzeczność gold answer ze źródłem: oprzyj ocenę na wiarygodnym źródle,
  opisz rozbieżność i podaj URL, jeżeli użyto dodatkowego źródła.
