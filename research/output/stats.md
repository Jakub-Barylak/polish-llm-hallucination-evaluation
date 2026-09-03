# Statystyki eksperymentów annotatora

- Ścieżka wejściowa: `research/output`
- Eksperymenty: 3 (`gold-only-v1`, `passage-v1`, `source-web-v1`)
- Przebiegi: 15
- Oczekiwane pary model–pytanie: 2 000
- Modele generujące: 4
- Pytania: 500
- Bootstrap: 10 000 powtórzeń, seed `42`
- Ręczna walidacja: 600 ocen, oceniający: `human`
- Pliki ręcznych ocen: `research/manual_annotation/artifacts/annotations/human.jsonl`
- Manifest ręcznej oceny: `research/manual_annotation/artifacts/private_manifest.jsonl`

## 1. Kompletność danych

| Eksperyment | Run | Oczekiwane | Poprawne | Braki | Kompletność | Próby API | Ponowienia | invalid_annotation | invalid_source |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gold-only-v1 | 1 | 2 000 | 2 000 | 0 | 100.00% | 2 003 | 3 | 3 | 0 |
| gold-only-v1 | 2 | 2 000 | 2 000 | 0 | 100.00% | 2 004 | 4 | 4 | 0 |
| gold-only-v1 | 3 | 2 000 | 2 000 | 0 | 100.00% | 2 007 | 7 | 7 | 0 |
| gold-only-v1 | 4 | 2 000 | 2 000 | 0 | 100.00% | 2 006 | 6 | 6 | 0 |
| gold-only-v1 | 5 | 2 000 | 2 000 | 0 | 100.00% | 2 006 | 6 | 6 | 0 |
| passage-v1 | 1 | 2 000 | 2 000 | 0 | 100.00% | 2 008 | 8 | 8 | 0 |
| passage-v1 | 2 | 2 000 | 2 000 | 0 | 100.00% | 2 007 | 7 | 7 | 0 |
| passage-v1 | 3 | 2 000 | 2 000 | 0 | 100.00% | 2 007 | 7 | 7 | 0 |
| passage-v1 | 4 | 2 000 | 2 000 | 0 | 100.00% | 2 002 | 2 | 2 | 0 |
| passage-v1 | 5 | 2 000 | 2 000 | 0 | 100.00% | 2 007 | 7 | 7 | 0 |
| source-web-v1 | 1 | 2 000 | 1 991 | 9 | 99.55% | 2 134 | 134 | 2 | 141 |
| source-web-v1 | 2 | 2 000 | 1 990 | 10 | 99.50% | 2 141 | 141 | 3 | 148 |
| source-web-v1 | 3 | 2 000 | 1 995 | 5 | 99.75% | 2 123 | 123 | 3 | 125 |
| source-web-v1 | 4 | 2 000 | 1 994 | 6 | 99.70% | 2 083 | 83 | 5 | 84 |
| source-web-v1 | 5 | 2 000 | 1 994 | 6 | 99.70% | 2 113 | 113 | 5 | 114 |

Odzyskiwanie rekordów w kolejnych batchach web:

| Eksperyment | Run | Próba | Batch ID | Wyniki | Nowe ok | invalid_annotation | invalid_source | Pozostało |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| source-web-v1 | 1 | 1 | batch_6a81ea8588c48190bc1abf6eb8396ea1 | 2000 | 1914 | 1 | 85 | 86 |
| source-web-v1 | 1 | 2 | batch_6a8210bae7888190a63e629608670105 | 86 | 64 | 1 | 21 | 22 |
| source-web-v1 | 1 | 3 | batch_6a8211696ea481909eaf3ebdbfa34b77 | 22 | 7 | 0 | 15 | 15 |
| source-web-v1 | 1 | 4 | batch_6a82123b82688190b223165b320e599b | 15 | 4 | 0 | 11 | 11 |
| source-web-v1 | 1 | 5 | batch_6a8212dabf7881909caad4ae47390300 | 11 | 2 | 0 | 9 | 9 |
| source-web-v1 | 2 | 1 | batch_6a81ea9dbcd08190ae9c3c9bc5e9dd3e | 2000 | 1908 | 3 | 89 | 92 |
| source-web-v1 | 2 | 2 | batch_6a8210dfb57c81908b37bd58e8ba5c61 | 92 | 70 | 0 | 22 | 22 |
| source-web-v1 | 2 | 3 | batch_6a82121a7f9c8190b3ee8f21538a8710 | 22 | 7 | 0 | 15 | 15 |
| source-web-v1 | 2 | 4 | batch_6a8212f375d4819087091db5a7561578 | 15 | 3 | 0 | 12 | 12 |
| source-web-v1 | 2 | 5 | batch_6a82137e98bc81909c178585fa02a3bf | 12 | 2 | 0 | 10 | 10 |
| source-web-v1 | 3 | 1 | batch_6a8169a27ab4819082ade0b678dc72fa | 2000 | 1929 | 3 | 68 | 71 |
| source-web-v1 | 3 | 2 | batch_6a81710bc32081908ff718f80512c2c1 | 71 | 42 | 0 | 29 | 29 |
| source-web-v1 | 3 | 3 | batch_6a817674bd6c8190899c057139c8f781 | 29 | 16 | 0 | 13 | 13 |
| source-web-v1 | 3 | 4 | batch_6a8178854b40819082a6711858e1bfb0 | 13 | 3 | 0 | 10 | 10 |
| source-web-v1 | 3 | 5 | batch_6a817b72ad9481908366687d596cddc9 | 10 | 5 | 0 | 5 | 5 |
| source-web-v1 | 4 | 1 | batch_6a817f14f2d481909cda3b3553114956 | 2000 | 1949 | 4 | 47 | 51 |
| source-web-v1 | 4 | 2 | batch_6a8181bc9bac8190a70ebd7d3783be3d | 51 | 35 | 1 | 15 | 16 |
| source-web-v1 | 4 | 3 | batch_6a8182d125c0819083a1d09815ac56f7 | 16 | 7 | 0 | 9 | 9 |
| source-web-v1 | 4 | 4 | batch_6a818379323c81908c3c336d56cd16a0 | 9 | 2 | 0 | 7 | 7 |
| source-web-v1 | 4 | 5 | batch_6a8186b5a1b081909a41bec2dbce92d4 | 7 | 1 | 0 | 6 | 6 |
| source-web-v1 | 5 | 1 | batch_6a81878ed6648190b323b5f9d0f3efef | 2000 | 1933 | 5 | 62 | 67 |
| source-web-v1 | 5 | 2 | batch_6a818dd71f948190a63841688f18cbf0 | 67 | 44 | 0 | 23 | 23 |
| source-web-v1 | 5 | 3 | batch_6a8190a5051c8190b9a9d652b2655d63 | 23 | 10 | 0 | 13 | 13 |
| source-web-v1 | 5 | 4 | batch_6a81931a7c4c8190b49e56fec707b8f1 | 13 | 3 | 0 | 10 | 10 |
| source-web-v1 | 5 | 5 | batch_6a81940f9a1c8190b6c308f4b489e20e | 10 | 4 | 0 | 6 | 6 |

## 2. Rozkład etykiet

| Eksperyment | N z konsensusem | correct | hallucination | abstention |
| --- | --- | --- | --- | --- |
| gold-only-v1 | 2000 | 1 235 (61.75%; 95% CI 58.80–64.60%) | 742 (37.10%; 95% CI 34.25–40.00%) | 23 (1.15%; 95% CI 0.65–1.75%) |
| passage-v1 | 1999 | 1 238 (61.93%; 95% CI 58.95–64.97%) | 741 (37.07%; 95% CI 34.13–40.00%) | 20 (1.00%; 95% CI 0.55–1.50%) |
| source-web-v1 | 1989 | 1 198 (60.23%; 95% CI 57.14–63.27%) | 758 (38.11%; 95% CI 35.12–41.13%) | 33 (1.66%; 95% CI 1.05–2.36%) |

Rozkład w poszczególnych runach:

| Eksperyment | Run | N | correct | hallucination | abstention |
| --- | --- | --- | --- | --- | --- |
| gold-only-v1 | 1 | 2000 | 1 231 (61.55%) | 746 (37.30%) | 23 (1.15%) |
| gold-only-v1 | 2 | 2000 | 1 234 (61.70%) | 740 (37.00%) | 26 (1.30%) |
| gold-only-v1 | 3 | 2000 | 1 234 (61.70%) | 741 (37.05%) | 25 (1.25%) |
| gold-only-v1 | 4 | 2000 | 1 238 (61.90%) | 736 (36.80%) | 26 (1.30%) |
| gold-only-v1 | 5 | 2000 | 1 237 (61.85%) | 740 (37.00%) | 23 (1.15%) |
| passage-v1 | 1 | 2000 | 1 236 (61.80%) | 742 (37.10%) | 22 (1.10%) |
| passage-v1 | 2 | 2000 | 1 234 (61.70%) | 745 (37.25%) | 21 (1.05%) |
| passage-v1 | 3 | 2000 | 1 235 (61.75%) | 740 (37.00%) | 25 (1.25%) |
| passage-v1 | 4 | 2000 | 1 232 (61.60%) | 745 (37.25%) | 23 (1.15%) |
| passage-v1 | 5 | 2000 | 1 242 (62.10%) | 738 (36.90%) | 20 (1.00%) |
| source-web-v1 | 1 | 1991 | 1 218 (61.18%) | 740 (37.17%) | 33 (1.66%) |
| source-web-v1 | 2 | 1990 | 1 208 (60.70%) | 742 (37.29%) | 40 (2.01%) |
| source-web-v1 | 3 | 1995 | 1 184 (59.35%) | 762 (38.20%) | 49 (2.46%) |
| source-web-v1 | 4 | 1994 | 1 209 (60.63%) | 745 (37.36%) | 40 (2.01%) |
| source-web-v1 | 5 | 1994 | 1 188 (59.58%) | 757 (37.96%) | 49 (2.46%) |

Rozkład według kategorii:

| Eksperyment | Kategoria | N | correct | hallucination | abstention |
| --- | --- | --- | --- | --- | --- |
| gold-only-v1 | general | 800 | 586 (73.25%; 95% CI 69.50–77.00%) | 211 (26.38%; 95% CI 22.75–30.12%) | 3 (0.38%; 95% CI 0.00–0.88%) |
| gold-only-v1 | global | 400 | 280 (70.00%; 95% CI 63.25–76.25%) | 119 (29.75%; 95% CI 23.25–36.50%) | 1 (0.25%; 95% CI 0.00–0.75%) |
| gold-only-v1 | polish_realia | 800 | 369 (46.12%; 95% CI 41.25–51.00%) | 412 (51.50%; 95% CI 46.75–56.25%) | 19 (2.38%; 95% CI 1.25–3.75%) |
| passage-v1 | general | 799 | 585 (73.22%; 95% CI 69.21–77.07%) | 211 (26.41%; 95% CI 22.65–30.36%) | 3 (0.38%; 95% CI 0.00–0.88%) |
| passage-v1 | global | 400 | 285 (71.25%; 95% CI 64.50–77.75%) | 114 (28.50%; 95% CI 22.00–35.25%) | 1 (0.25%; 95% CI 0.00–0.75%) |
| passage-v1 | polish_realia | 800 | 368 (46.00%; 95% CI 41.12–50.62%) | 416 (52.00%; 95% CI 47.38–56.75%) | 16 (2.00%; 95% CI 1.00–3.12%) |
| source-web-v1 | general | 799 | 565 (70.71%; 95% CI 66.71–74.56%) | 231 (28.91%; 95% CI 25.06–32.91%) | 3 (0.38%; 95% CI 0.00–0.88%) |
| source-web-v1 | global | 399 | 283 (70.93%; 95% CI 64.25–77.25%) | 115 (28.82%; 95% CI 22.50–35.50%) | 1 (0.25%; 95% CI 0.00–0.75%) |
| source-web-v1 | polish_realia | 791 | 350 (44.25%; 95% CI 39.50–49.05%) | 412 (52.09%; 95% CI 47.41–56.76%) | 29 (3.67%; 95% CI 2.26–5.32%) |

Przedziały dla konsensusu wyznaczono przez bootstrap całych pytań. Rozkład runów ma charakter opisowy i nie zawiera osobnych przedziałów.

## 3. Stabilność między runami

| Eksperyment | Runy | N ≥ 3 | Konsensus | Bez konsensusu | Jednomyślne (N ≥ 2) | Krippendorff α |
| --- | --- | --- | --- | --- | --- | --- |
| gold-only-v1 | 5 | 2000 | 2000 | 0 | 1 926 (96.30%) | 0.963 |
| passage-v1 | 5 | 2000 | 1999 | 1 | 1 912 (95.60%) | 0.957 |
| source-web-v1 | 5 | 1995 | 1989 | 11 | 1 752 (87.69%) | 0.881 |

Siła większości (liczebności etykiet, np. `4-1`):

| Eksperyment | Wzorzec | Rekordy | Odsetek |
| --- | --- | --- | --- |
| gold-only-v1 | 3-1-1 | 3 | 0.15% |
| gold-only-v1 | 3-2 | 28 | 1.40% |
| gold-only-v1 | 4-1 | 43 | 2.15% |
| gold-only-v1 | 5 | 1926 | 96.30% |
| passage-v1 | 2-2-1 | 1 | 0.05% |
| passage-v1 | 3-2 | 28 | 1.40% |
| passage-v1 | 4-1 | 59 | 2.95% |
| passage-v1 | 5 | 1912 | 95.60% |
| source-web-v1 | 2-2-1 | 3 | 0.15% |
| source-web-v1 | 3-1-1 | 3 | 0.15% |
| source-web-v1 | 3-2 | 84 | 4.20% |
| source-web-v1 | 4-1 | 140 | 7.00% |
| source-web-v1 | 5 | 1750 | 87.50% |
| source-web-v1 | 2-2 | 3 | 0.15% |
| source-web-v1 | 3-1 | 6 | 0.30% |
| source-web-v1 | 4 | 2 | 0.10% |
| source-web-v1 | 2-1 | 4 | 0.20% |
| source-web-v1 | 1-1 | 3 | 0.15% |
| source-web-v1 | 1 | 2 | 0.10% |

Zgodność parami między runami:

| Eksperyment | Run A | Run B | Wspólne N | Zgodność | Cohen κ |
| --- | --- | --- | --- | --- | --- |
| gold-only-v1 | 1 | 2 | 2000 | 98.65% | 0.972 |
| gold-only-v1 | 1 | 3 | 2000 | 98.20% | 0.963 |
| gold-only-v1 | 1 | 4 | 2000 | 98.40% | 0.967 |
| gold-only-v1 | 1 | 5 | 2000 | 98.20% | 0.963 |
| gold-only-v1 | 2 | 3 | 2000 | 98.35% | 0.966 |
| gold-only-v1 | 2 | 4 | 2000 | 98.30% | 0.965 |
| gold-only-v1 | 2 | 5 | 2000 | 97.90% | 0.956 |
| gold-only-v1 | 3 | 4 | 2000 | 97.80% | 0.954 |
| gold-only-v1 | 3 | 5 | 2000 | 98.30% | 0.965 |
| gold-only-v1 | 4 | 5 | 2000 | 97.85% | 0.955 |
| passage-v1 | 1 | 2 | 2000 | 97.75% | 0.953 |
| passage-v1 | 1 | 3 | 2000 | 97.85% | 0.955 |
| passage-v1 | 1 | 4 | 2000 | 98.30% | 0.965 |
| passage-v1 | 1 | 5 | 2000 | 97.95% | 0.957 |
| passage-v1 | 2 | 3 | 2000 | 97.65% | 0.951 |
| passage-v1 | 2 | 4 | 2000 | 97.95% | 0.957 |
| passage-v1 | 2 | 5 | 2000 | 97.80% | 0.954 |
| passage-v1 | 3 | 4 | 2000 | 98.25% | 0.964 |
| passage-v1 | 3 | 5 | 2000 | 97.75% | 0.953 |
| passage-v1 | 4 | 5 | 2000 | 98.15% | 0.961 |
| source-web-v1 | 1 | 2 | 1986 | 93.71% | 0.871 |
| source-web-v1 | 1 | 3 | 1989 | 93.82% | 0.875 |
| source-web-v1 | 1 | 4 | 1987 | 93.91% | 0.876 |
| source-web-v1 | 1 | 5 | 1987 | 94.26% | 0.884 |
| source-web-v1 | 2 | 3 | 1987 | 93.21% | 0.863 |
| source-web-v1 | 2 | 4 | 1987 | 94.06% | 0.879 |
| source-web-v1 | 2 | 5 | 1986 | 94.16% | 0.882 |
| source-web-v1 | 3 | 4 | 1991 | 95.03% | 0.900 |
| source-web-v1 | 3 | 5 | 1990 | 95.18% | 0.903 |
| source-web-v1 | 4 | 5 | 1991 | 94.83% | 0.896 |

## 4. Porównanie protokołów na podstawie konsensusu

| Para | N | Zgodność | Cohen κ | Hall. A | Hall. B | Zmiana B−A | 95% CI zmiany |
| --- | --- | --- | --- | --- | --- | --- | --- |
| gold-only-v1 → passage-v1 | 1999 | 97.60% | 0.950 | 37.07% | 37.07% | +0.00 pp | [-0.80; +0.80] pp |
| gold-only-v1 → source-web-v1 | 1989 | 95.32% | 0.904 | 37.15% | 38.11% | +0.96 pp | [-0.10; +2.01] pp |
| passage-v1 → source-web-v1 | 1988 | 95.72% | 0.912 | 37.12% | 38.08% | +0.96 pp | [+0.00; +1.96] pp |

Łączne różnice obejmują cztery odpowiedzi na pytanie, dlatego ich przedziały wyznaczono przez bootstrap całych pytań. Testy poniżej wykonywane są osobno dla każdego modelu, dzięki czemu pytanie pozostaje blokiem.

Macierz przejść `gold-only-v1` (wiersze) → `passage-v1` (kolumny), N=1999:

| A \ B | correct | hallucination | abstention |
| --- | --- | --- | --- |
| correct | 1214 | 21 | 0 |
| hallucination | 24 | 717 | 0 |
| abstention | 0 | 3 | 20 |

Macierz przejść `gold-only-v1` (wiersze) → `source-web-v1` (kolumny), N=1989:

| A \ B | correct | hallucination | abstention |
| --- | --- | --- | --- |
| correct | 1170 | 43 | 14 |
| hallucination | 28 | 709 | 2 |
| abstention | 0 | 6 | 17 |

Macierz przejść `passage-v1` (wiersze) → `source-web-v1` (kolumny), N=1988:

| A \ B | correct | hallucination | abstention |
| --- | --- | --- | --- |
| correct | 1175 | 41 | 14 |
| hallucination | 23 | 712 | 3 |
| abstention | 0 | 4 | 16 |

Zmiana pełnego rozkładu trzech etykiet — test Stuart–Maxwell:

| Model | Para protokołów | N | χ² | df | p | p Holma |
| --- | --- | --- | --- | --- | --- | --- |
| CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 | gold-only-v1 ↔ passage-v1 | 499 | 3.273 | 2 | 0.1947 | 0.1947 |
| CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 | gold-only-v1 ↔ source-web-v1 | 498 | 6.261 | 2 | 0.0437 | 0.0874 |
| CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 | passage-v1 ↔ source-web-v1 | 497 | 10.330 | 2 | 0.0057 | 0.0171 |
| meta-llama/Llama-3.1-8B-Instruct | gold-only-v1 ↔ passage-v1 | 500 | 1.000 | 2 | 0.6065 | 1.0000 |
| meta-llama/Llama-3.1-8B-Instruct | gold-only-v1 ↔ source-web-v1 | 497 | 1.352 | 2 | 0.5086 | 1.0000 |
| meta-llama/Llama-3.1-8B-Instruct | passage-v1 ↔ source-web-v1 | 497 | 3.077 | 2 | 0.2147 | 0.6441 |
| mistralai/Mistral-7B-Instruct-v0.2 | gold-only-v1 ↔ passage-v1 | 500 | 1.286 | 2 | 0.5258 | 0.5258 |
| mistralai/Mistral-7B-Instruct-v0.2 | gold-only-v1 ↔ source-web-v1 | 497 | 3.580 | 2 | 0.1669 | 0.5008 |
| mistralai/Mistral-7B-Instruct-v0.2 | passage-v1 ↔ source-web-v1 | 497 | 3.488 | 2 | 0.1748 | 0.5008 |
| speakleash/Bielik-11B-v2.3-Instruct | gold-only-v1 ↔ passage-v1 | 500 | 2.667 | 1 | 0.1025 | 0.1025 |
| speakleash/Bielik-11B-v2.3-Instruct | gold-only-v1 ↔ source-web-v1 | 497 | 10.765 | 2 | 0.0046 | 0.0138 |
| speakleash/Bielik-11B-v2.3-Instruct | passage-v1 ↔ source-web-v1 | 497 | 7.923 | 2 | 0.0190 | 0.0381 |

Porównanie binarne trzech protokołów — test Cochrana Q:

| Wynik | Model | N pytań | Q | df | p | p Holma (modele) |
| --- | --- | --- | --- | --- | --- | --- |
| hallucination | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 | 497 | 1.455 | 2 | 0.4832 | 0.9665 |
| hallucination | meta-llama/Llama-3.1-8B-Instruct | 497 | 0.261 | 2 | 0.8777 | 0.9665 |
| hallucination | mistralai/Mistral-7B-Instruct-v0.2 | 497 | 4.056 | 2 | 0.1316 | 0.3949 |
| hallucination | speakleash/Bielik-11B-v2.3-Instruct | 497 | 6.778 | 2 | 0.0337 | 0.1350 |
| correct | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 | 497 | 7.913 | 2 | 0.0191 | 0.0574 |
| correct | meta-llama/Llama-3.1-8B-Instruct | 497 | 1.280 | 2 | 0.5273 | 0.8337 |
| correct | mistralai/Mistral-7B-Instruct-v0.2 | 497 | 1.750 | 2 | 0.4169 | 0.8337 |
| correct | speakleash/Bielik-11B-v2.3-Instruct | 497 | 15.083 | 2 | 0.0005 | 0.0021 |

Porównania protokołów parami — dokładny test McNemara:

| Wynik | Model | Para protokołów | Tylko A | Tylko B | N | p | p Holma |
| --- | --- | --- | --- | --- | --- | --- | --- |
| hallucination | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 | gold-only-v1 ↔ passage-v1 | 8 | 4 | 499 | 0.3877 | 1.0000 |
| hallucination | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 | gold-only-v1 ↔ source-web-v1 | 8 | 8 | 498 | 1.0000 | 1.0000 |
| hallucination | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 | passage-v1 ↔ source-web-v1 | 6 | 10 | 497 | 0.4545 | 1.0000 |
| hallucination | meta-llama/Llama-3.1-8B-Instruct | gold-only-v1 ↔ passage-v1 | 7 | 8 | 500 | 1.0000 | 1.0000 |
| hallucination | meta-llama/Llama-3.1-8B-Instruct | gold-only-v1 ↔ source-web-v1 | 8 | 10 | 497 | 0.8145 | 1.0000 |
| hallucination | meta-llama/Llama-3.1-8B-Instruct | passage-v1 ↔ source-web-v1 | 6 | 7 | 497 | 1.0000 | 1.0000 |
| hallucination | mistralai/Mistral-7B-Instruct-v0.2 | gold-only-v1 ↔ passage-v1 | 8 | 7 | 500 | 1.0000 | 1.0000 |
| hallucination | mistralai/Mistral-7B-Instruct-v0.2 | gold-only-v1 ↔ source-web-v1 | 10 | 18 | 497 | 0.1849 | 0.4081 |
| hallucination | mistralai/Mistral-7B-Instruct-v0.2 | passage-v1 ↔ source-web-v1 | 10 | 19 | 497 | 0.1360 | 0.4081 |
| hallucination | speakleash/Bielik-11B-v2.3-Instruct | gold-only-v1 ↔ passage-v1 | 1 | 5 | 500 | 0.2188 | 0.4375 |
| hallucination | speakleash/Bielik-11B-v2.3-Instruct | gold-only-v1 ↔ source-web-v1 | 4 | 13 | 497 | 0.0490 | 0.1471 |
| hallucination | speakleash/Bielik-11B-v2.3-Instruct | passage-v1 ↔ source-web-v1 | 4 | 9 | 497 | 0.2668 | 0.4375 |
| correct | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 | gold-only-v1 ↔ passage-v1 | 3 | 8 | 499 | 0.2266 | 0.4531 |
| correct | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 | gold-only-v1 ↔ source-web-v1 | 12 | 6 | 498 | 0.2379 | 0.4531 |
| correct | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 | passage-v1 ↔ source-web-v1 | 14 | 3 | 497 | 0.0127 | 0.0382 |
| correct | meta-llama/Llama-3.1-8B-Instruct | gold-only-v1 ↔ passage-v1 | 7 | 7 | 500 | 1.0000 | 1.0000 |
| correct | meta-llama/Llama-3.1-8B-Instruct | gold-only-v1 ↔ source-web-v1 | 12 | 8 | 497 | 0.5034 | 1.0000 |
| correct | meta-llama/Llama-3.1-8B-Instruct | passage-v1 ↔ source-web-v1 | 10 | 6 | 497 | 0.4545 | 1.0000 |
| correct | mistralai/Mistral-7B-Instruct-v0.2 | gold-only-v1 ↔ passage-v1 | 6 | 8 | 500 | 0.7905 | 1.0000 |
| correct | mistralai/Mistral-7B-Instruct-v0.2 | gold-only-v1 ↔ source-web-v1 | 14 | 10 | 497 | 0.5413 | 1.0000 |
| correct | mistralai/Mistral-7B-Instruct-v0.2 | passage-v1 ↔ source-web-v1 | 16 | 10 | 497 | 0.3269 | 0.9808 |
| correct | speakleash/Bielik-11B-v2.3-Instruct | gold-only-v1 ↔ passage-v1 | 5 | 1 | 500 | 0.2188 | 0.2188 |
| correct | speakleash/Bielik-11B-v2.3-Instruct | gold-only-v1 ↔ source-web-v1 | 19 | 4 | 497 | 0.0026 | 0.0078 |
| correct | speakleash/Bielik-11B-v2.3-Instruct | passage-v1 ↔ source-web-v1 | 15 | 4 | 497 | 0.0192 | 0.0384 |

## 5. Wyniki modeli

| Eksperyment | Model | N | correct | hallucination | abstention |
| --- | --- | --- | --- | --- | --- |
| gold-only-v1 | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 | 500 | 345 (69.00%; 95% CI 64.81–72.90%) | 153 (30.60%; 95% CI 26.72–34.77%) | 2 (0.40%; 95% CI 0.11–1.45%) |
| gold-only-v1 | meta-llama/Llama-3.1-8B-Instruct | 500 | 248 (49.60%; 95% CI 45.24–53.97%) | 247 (49.40%; 95% CI 45.04–53.77%) | 5 (1.00%; 95% CI 0.43–2.32%) |
| gold-only-v1 | mistralai/Mistral-7B-Instruct-v0.2 | 500 | 231 (46.20%; 95% CI 41.88–50.58%) | 253 (50.60%; 95% CI 46.23–54.96%) | 16 (3.20%; 95% CI 1.98–5.13%) |
| gold-only-v1 | speakleash/Bielik-11B-v2.3-Instruct | 500 | 411 (82.20%; 95% CI 78.61–85.30%) | 89 (17.80%; 95% CI 14.70–21.39%) | 0 (0.00%; 95% CI 0.00–0.76%) |
| passage-v1 | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 | 499 | 350 (70.14%; 95% CI 65.98–73.99%) | 148 (29.66%; 95% CI 25.82–33.81%) | 1 (0.20%; 95% CI 0.04–1.13%) |
| passage-v1 | meta-llama/Llama-3.1-8B-Instruct | 500 | 248 (49.60%; 95% CI 45.24–53.97%) | 248 (49.60%; 95% CI 45.24–53.97%) | 4 (0.80%; 95% CI 0.31–2.04%) |
| passage-v1 | mistralai/Mistral-7B-Instruct-v0.2 | 500 | 233 (46.60%; 95% CI 42.27–50.98%) | 252 (50.40%; 95% CI 46.03–54.76%) | 15 (3.00%; 95% CI 1.83–4.89%) |
| passage-v1 | speakleash/Bielik-11B-v2.3-Instruct | 500 | 407 (81.40%; 95% CI 77.75–84.57%) | 93 (18.60%; 95% CI 15.43–22.25%) | 0 (0.00%; 95% CI 0.00–0.76%) |
| source-web-v1 | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 | 498 | 337 (67.67%; 95% CI 63.44–71.63%) | 153 (30.72%; 95% CI 26.83–34.91%) | 8 (1.61%; 95% CI 0.82–3.14%) |
| source-web-v1 | meta-llama/Llama-3.1-8B-Instruct | 497 | 244 (49.09%; 95% CI 44.72–53.48%) | 246 (49.50%; 95% CI 45.12–53.88%) | 7 (1.41%; 95% CI 0.68–2.88%) |
| source-web-v1 | mistralai/Mistral-7B-Instruct-v0.2 | 497 | 224 (45.07%; 95% CI 40.75–49.47%) | 261 (52.52%; 95% CI 48.12–56.87%) | 12 (2.41%; 95% CI 1.39–4.17%) |
| source-web-v1 | speakleash/Bielik-11B-v2.3-Instruct | 497 | 393 (79.07%; 95% CI 75.28–82.42%) | 98 (19.72%; 95% CI 16.46–23.44%) | 6 (1.21%; 95% CI 0.55–2.61%) |

Przedziały dla pojedynczego modelu są przedziałami Wilsona. W każdej grupie model ma najwyżej jedną odpowiedź na pytanie.

Ranking według odsetka `correct`:

| Eksperyment | Miejsce | Model |
| --- | --- | --- |
| gold-only-v1 | 1 | speakleash/Bielik-11B-v2.3-Instruct |
| gold-only-v1 | 2 | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 |
| gold-only-v1 | 3 | meta-llama/Llama-3.1-8B-Instruct |
| gold-only-v1 | 4 | mistralai/Mistral-7B-Instruct-v0.2 |
| passage-v1 | 1 | speakleash/Bielik-11B-v2.3-Instruct |
| passage-v1 | 2 | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 |
| passage-v1 | 3 | meta-llama/Llama-3.1-8B-Instruct |
| passage-v1 | 4 | mistralai/Mistral-7B-Instruct-v0.2 |
| source-web-v1 | 1 | speakleash/Bielik-11B-v2.3-Instruct |
| source-web-v1 | 2 | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 |
| source-web-v1 | 3 | meta-llama/Llama-3.1-8B-Instruct |
| source-web-v1 | 4 | mistralai/Mistral-7B-Instruct-v0.2 |

Stabilność rankingu w bootstrapie całych pytań:

| Eksperyment | Model | Miejsce 1 | Miejsce 2 | Miejsce 3 | Miejsce 4 | Średnia pozycja |
| --- | --- | --- | --- | --- | --- | --- |
| gold-only-v1 | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 | 0.00% | 100.00% | 0.00% | 0.00% | 2.000 |
| gold-only-v1 | meta-llama/Llama-3.1-8B-Instruct | 0.00% | 0.00% | 93.05% | 6.94% | 3.069 |
| gold-only-v1 | mistralai/Mistral-7B-Instruct-v0.2 | 0.00% | 0.00% | 6.94% | 93.05% | 3.931 |
| gold-only-v1 | speakleash/Bielik-11B-v2.3-Instruct | 100.00% | 0.00% | 0.00% | 0.00% | 1.000 |
| passage-v1 | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 | 0.00% | 100.00% | 0.00% | 0.00% | 2.000 |
| passage-v1 | meta-llama/Llama-3.1-8B-Instruct | 0.00% | 0.00% | 91.16% | 8.83% | 3.088 |
| passage-v1 | mistralai/Mistral-7B-Instruct-v0.2 | 0.00% | 0.00% | 8.83% | 91.16% | 3.912 |
| passage-v1 | speakleash/Bielik-11B-v2.3-Instruct | 100.00% | 0.00% | 0.00% | 0.00% | 1.000 |
| source-web-v1 | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 | 0.00% | 100.00% | 0.00% | 0.00% | 2.000 |
| source-web-v1 | meta-llama/Llama-3.1-8B-Instruct | 0.00% | 0.00% | 96.15% | 3.85% | 3.038 |
| source-web-v1 | mistralai/Mistral-7B-Instruct-v0.2 | 0.00% | 0.00% | 3.85% | 96.15% | 3.962 |
| source-web-v1 | speakleash/Bielik-11B-v2.3-Instruct | 100.00% | 0.00% | 0.00% | 0.00% | 1.000 |

Przy remisie masa prawdopodobieństwa jest dzielona równo między zajęte miejsca.

Wyniki model × kategoria:

| Eksperyment | Model | Kategoria | N | correct | hallucination | abstention |
| --- | --- | --- | --- | --- | --- | --- |
| gold-only-v1 | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 | general | 200 | 169 (84.50%; 95% CI 78.84–88.86%) | 31 (15.50%; 95% CI 11.14–21.16%) | 0 (0.00%; 95% CI 0.00–1.88%) |
| gold-only-v1 | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 | global | 100 | 71 (71.00%; 95% CI 61.46–78.99%) | 29 (29.00%; 95% CI 21.01–38.54%) | 0 (0.00%; 95% CI 0.00–3.70%) |
| gold-only-v1 | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 | polish_realia | 200 | 105 (52.50%; 95% CI 45.60–59.31%) | 93 (46.50%; 95% CI 39.72–53.41%) | 2 (1.00%; 95% CI 0.27–3.57%) |
| gold-only-v1 | meta-llama/Llama-3.1-8B-Instruct | general | 200 | 114 (57.00%; 95% CI 50.07–63.67%) | 86 (43.00%; 95% CI 36.33–49.93%) | 0 (0.00%; 95% CI 0.00–1.88%) |
| gold-only-v1 | meta-llama/Llama-3.1-8B-Instruct | global | 100 | 65 (65.00%; 95% CI 55.25–73.64%) | 35 (35.00%; 95% CI 26.36–44.75%) | 0 (0.00%; 95% CI 0.00–3.70%) |
| gold-only-v1 | meta-llama/Llama-3.1-8B-Instruct | polish_realia | 200 | 69 (34.50%; 95% CI 28.26–41.32%) | 126 (63.00%; 95% CI 56.12–69.39%) | 5 (2.50%; 95% CI 1.07–5.72%) |
| gold-only-v1 | mistralai/Mistral-7B-Instruct-v0.2 | general | 200 | 117 (58.50%; 95% CI 51.57–65.11%) | 80 (40.00%; 95% CI 33.46–46.92%) | 3 (1.50%; 95% CI 0.51–4.32%) |
| gold-only-v1 | mistralai/Mistral-7B-Instruct-v0.2 | global | 100 | 64 (64.00%; 95% CI 54.24–72.73%) | 35 (35.00%; 95% CI 26.36–44.75%) | 1 (1.00%; 95% CI 0.18–5.45%) |
| gold-only-v1 | mistralai/Mistral-7B-Instruct-v0.2 | polish_realia | 200 | 50 (25.00%; 95% CI 19.51–31.43%) | 138 (69.00%; 95% CI 62.28–75.00%) | 12 (6.00%; 95% CI 3.47–10.19%) |
| gold-only-v1 | speakleash/Bielik-11B-v2.3-Instruct | general | 200 | 186 (93.00%; 95% CI 88.59–95.78%) | 14 (7.00%; 95% CI 4.22–11.41%) | 0 (0.00%; 95% CI 0.00–1.88%) |
| gold-only-v1 | speakleash/Bielik-11B-v2.3-Instruct | global | 100 | 80 (80.00%; 95% CI 71.12–86.66%) | 20 (20.00%; 95% CI 13.34–28.88%) | 0 (0.00%; 95% CI 0.00–3.70%) |
| gold-only-v1 | speakleash/Bielik-11B-v2.3-Instruct | polish_realia | 200 | 145 (72.50%; 95% CI 65.93–78.22%) | 55 (27.50%; 95% CI 21.78–34.07%) | 0 (0.00%; 95% CI 0.00–1.88%) |
| passage-v1 | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 | general | 199 | 169 (84.92%; 95% CI 79.29–89.23%) | 30 (15.08%; 95% CI 10.77–20.71%) | 0 (0.00%; 95% CI 0.00–1.89%) |
| passage-v1 | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 | global | 100 | 72 (72.00%; 95% CI 62.51–79.86%) | 28 (28.00%; 95% CI 20.14–37.49%) | 0 (0.00%; 95% CI 0.00–3.70%) |
| passage-v1 | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 | polish_realia | 200 | 109 (54.50%; 95% CI 47.58–61.25%) | 90 (45.00%; 95% CI 38.26–51.92%) | 1 (0.50%; 95% CI 0.09–2.78%) |
| passage-v1 | meta-llama/Llama-3.1-8B-Instruct | general | 200 | 114 (57.00%; 95% CI 50.07–63.67%) | 86 (43.00%; 95% CI 36.33–49.93%) | 0 (0.00%; 95% CI 0.00–1.88%) |
| passage-v1 | meta-llama/Llama-3.1-8B-Instruct | global | 100 | 67 (67.00%; 95% CI 57.31–75.44%) | 33 (33.00%; 95% CI 24.56–42.69%) | 0 (0.00%; 95% CI 0.00–3.70%) |
| passage-v1 | meta-llama/Llama-3.1-8B-Instruct | polish_realia | 200 | 67 (33.50%; 95% CI 27.32–40.30%) | 129 (64.50%; 95% CI 57.65–70.80%) | 4 (2.00%; 95% CI 0.78–5.03%) |
| passage-v1 | mistralai/Mistral-7B-Instruct-v0.2 | general | 200 | 118 (59.00%; 95% CI 52.08–65.58%) | 79 (39.50%; 95% CI 32.98–46.41%) | 3 (1.50%; 95% CI 0.51–4.32%) |
| passage-v1 | mistralai/Mistral-7B-Instruct-v0.2 | global | 100 | 66 (66.00%; 95% CI 56.28–74.54%) | 33 (33.00%; 95% CI 24.56–42.69%) | 1 (1.00%; 95% CI 0.18–5.45%) |
| passage-v1 | mistralai/Mistral-7B-Instruct-v0.2 | polish_realia | 200 | 49 (24.50%; 95% CI 19.06–30.90%) | 140 (70.00%; 95% CI 63.32–75.93%) | 11 (5.50%; 95% CI 3.10–9.58%) |
| passage-v1 | speakleash/Bielik-11B-v2.3-Instruct | general | 200 | 184 (92.00%; 95% CI 87.40–95.02%) | 16 (8.00%; 95% CI 4.98–12.60%) | 0 (0.00%; 95% CI 0.00–1.88%) |
| passage-v1 | speakleash/Bielik-11B-v2.3-Instruct | global | 100 | 80 (80.00%; 95% CI 71.12–86.66%) | 20 (20.00%; 95% CI 13.34–28.88%) | 0 (0.00%; 95% CI 0.00–3.70%) |
| passage-v1 | speakleash/Bielik-11B-v2.3-Instruct | polish_realia | 200 | 143 (71.50%; 95% CI 64.88–77.30%) | 57 (28.50%; 95% CI 22.70–35.12%) | 0 (0.00%; 95% CI 0.00–1.88%) |
| source-web-v1 | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 | general | 200 | 163 (81.50%; 95% CI 75.54–86.27%) | 37 (18.50%; 95% CI 13.73–24.46%) | 0 (0.00%; 95% CI 0.00–1.88%) |
| source-web-v1 | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 | global | 100 | 72 (72.00%; 95% CI 62.51–79.86%) | 28 (28.00%; 95% CI 20.14–37.49%) | 0 (0.00%; 95% CI 0.00–3.70%) |
| source-web-v1 | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 | polish_realia | 198 | 102 (51.52%; 95% CI 44.59–58.38%) | 88 (44.44%; 95% CI 37.69–51.41%) | 8 (4.04%; 95% CI 2.06–7.77%) |
| source-web-v1 | meta-llama/Llama-3.1-8B-Instruct | general | 200 | 110 (55.00%; 95% CI 48.08–61.74%) | 90 (45.00%; 95% CI 38.26–51.92%) | 0 (0.00%; 95% CI 0.00–1.88%) |
| source-web-v1 | meta-llama/Llama-3.1-8B-Instruct | global | 99 | 68 (68.69%; 95% CI 59.00–76.98%) | 31 (31.31%; 95% CI 23.02–41.00%) | 0 (0.00%; 95% CI 0.00–3.74%) |
| source-web-v1 | meta-llama/Llama-3.1-8B-Instruct | polish_realia | 198 | 66 (33.33%; 95% CI 27.14–40.16%) | 125 (63.13%; 95% CI 56.22–69.54%) | 7 (3.54%; 95% CI 1.72–7.12%) |
| source-web-v1 | mistralai/Mistral-7B-Instruct-v0.2 | general | 200 | 114 (57.00%; 95% CI 50.07–63.67%) | 84 (42.00%; 95% CI 35.37–48.93%) | 2 (1.00%; 95% CI 0.27–3.57%) |
| source-web-v1 | mistralai/Mistral-7B-Instruct-v0.2 | global | 100 | 63 (63.00%; 95% CI 53.22–71.82%) | 36 (36.00%; 95% CI 27.27–45.76%) | 1 (1.00%; 95% CI 0.18–5.45%) |
| source-web-v1 | mistralai/Mistral-7B-Instruct-v0.2 | polish_realia | 197 | 47 (23.86%; 95% CI 18.44–30.27%) | 141 (71.57%; 95% CI 64.91–77.41%) | 9 (4.57%; 95% CI 2.42–8.45%) |
| source-web-v1 | speakleash/Bielik-11B-v2.3-Instruct | general | 199 | 178 (89.45%; 95% CI 84.41–92.99%) | 20 (10.05%; 95% CI 6.60–15.01%) | 1 (0.50%; 95% CI 0.09–2.79%) |
| source-web-v1 | speakleash/Bielik-11B-v2.3-Instruct | global | 100 | 80 (80.00%; 95% CI 71.12–86.66%) | 20 (20.00%; 95% CI 13.34–28.88%) | 0 (0.00%; 95% CI 0.00–3.70%) |
| source-web-v1 | speakleash/Bielik-11B-v2.3-Instruct | polish_realia | 198 | 135 (68.18%; 95% CI 61.40–74.27%) | 58 (29.29%; 95% CI 23.40–35.98%) | 5 (2.53%; 95% CI 1.08–5.77%) |

Ogólne porównanie czterech modeli — test Cochrana Q:

| Eksperyment | Wynik | N pytań | Q | df | p |
| --- | --- | --- | --- | --- | --- |
| gold-only-v1 | hallucination | 500 | 229.534 | 3 | 0.0000 |
| gold-only-v1 | correct | 500 | 268.530 | 3 | 0.0000 |
| passage-v1 | hallucination | 499 | 225.175 | 3 | 0.0000 |
| passage-v1 | correct | 499 | 262.530 | 3 | 0.0000 |
| source-web-v1 | hallucination | 491 | 221.938 | 3 | 0.0000 |
| source-web-v1 | correct | 491 | 240.969 | 3 | 0.0000 |

Porównania modeli parami — dokładny test McNemara:

| Eksperyment | Wynik | Para modeli | Tylko A | Tylko B | N | Zmiana B−A | p | p Holma |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gold-only-v1 | hallucination | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 ↔ meta-llama/Llama-3.1-8B-Instruct | 30 | 124 | 500 | +18.80 pp | 0.0000 | 0.0000 |
| gold-only-v1 | hallucination | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 ↔ mistralai/Mistral-7B-Instruct-v0.2 | 41 | 141 | 500 | +20.00 pp | 0.0000 | 0.0000 |
| gold-only-v1 | hallucination | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 ↔ speakleash/Bielik-11B-v2.3-Instruct | 89 | 25 | 500 | -12.80 pp | 0.0000 | 0.0000 |
| gold-only-v1 | hallucination | meta-llama/Llama-3.1-8B-Instruct ↔ mistralai/Mistral-7B-Instruct-v0.2 | 68 | 74 | 500 | +1.20 pp | 0.6749 | 0.6749 |
| gold-only-v1 | hallucination | meta-llama/Llama-3.1-8B-Instruct ↔ speakleash/Bielik-11B-v2.3-Instruct | 172 | 14 | 500 | -31.60 pp | 0.0000 | 0.0000 |
| gold-only-v1 | hallucination | mistralai/Mistral-7B-Instruct-v0.2 ↔ speakleash/Bielik-11B-v2.3-Instruct | 182 | 18 | 500 | -32.80 pp | 0.0000 | 0.0000 |
| gold-only-v1 | correct | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 ↔ meta-llama/Llama-3.1-8B-Instruct | 125 | 28 | 500 | -19.40 pp | 0.0000 | 0.0000 |
| gold-only-v1 | correct | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 ↔ mistralai/Mistral-7B-Instruct-v0.2 | 144 | 30 | 500 | -22.80 pp | 0.0000 | 0.0000 |
| gold-only-v1 | correct | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 ↔ speakleash/Bielik-11B-v2.3-Instruct | 24 | 90 | 500 | +13.20 pp | 0.0000 | 0.0000 |
| gold-only-v1 | correct | meta-llama/Llama-3.1-8B-Instruct ↔ mistralai/Mistral-7B-Instruct-v0.2 | 72 | 55 | 500 | -3.40 pp | 0.1554 | 0.1554 |
| gold-only-v1 | correct | meta-llama/Llama-3.1-8B-Instruct ↔ speakleash/Bielik-11B-v2.3-Instruct | 13 | 176 | 500 | +32.60 pp | 0.0000 | 0.0000 |
| gold-only-v1 | correct | mistralai/Mistral-7B-Instruct-v0.2 ↔ speakleash/Bielik-11B-v2.3-Instruct | 12 | 192 | 500 | +36.00 pp | 0.0000 | 0.0000 |
| passage-v1 | hallucination | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 ↔ meta-llama/Llama-3.1-8B-Instruct | 29 | 128 | 499 | +19.84 pp | 0.0000 | 0.0000 |
| passage-v1 | hallucination | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 ↔ mistralai/Mistral-7B-Instruct-v0.2 | 38 | 141 | 499 | +20.64 pp | 0.0000 | 0.0000 |
| passage-v1 | hallucination | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 ↔ speakleash/Bielik-11B-v2.3-Instruct | 81 | 26 | 499 | -11.02 pp | 0.0000 | 0.0000 |
| passage-v1 | hallucination | meta-llama/Llama-3.1-8B-Instruct ↔ mistralai/Mistral-7B-Instruct-v0.2 | 68 | 72 | 500 | +0.80 pp | 0.8000 | 0.8000 |
| passage-v1 | hallucination | meta-llama/Llama-3.1-8B-Instruct ↔ speakleash/Bielik-11B-v2.3-Instruct | 171 | 16 | 500 | -31.00 pp | 0.0000 | 0.0000 |
| passage-v1 | hallucination | mistralai/Mistral-7B-Instruct-v0.2 ↔ speakleash/Bielik-11B-v2.3-Instruct | 176 | 17 | 500 | -31.80 pp | 0.0000 | 0.0000 |
| passage-v1 | correct | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 ↔ meta-llama/Llama-3.1-8B-Instruct | 128 | 26 | 499 | -20.44 pp | 0.0000 | 0.0000 |
| passage-v1 | correct | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 ↔ mistralai/Mistral-7B-Instruct-v0.2 | 144 | 27 | 499 | -23.45 pp | 0.0000 | 0.0000 |
| passage-v1 | correct | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 ↔ speakleash/Bielik-11B-v2.3-Instruct | 25 | 81 | 499 | +11.22 pp | 0.0000 | 0.0000 |
| passage-v1 | correct | meta-llama/Llama-3.1-8B-Instruct ↔ mistralai/Mistral-7B-Instruct-v0.2 | 70 | 55 | 500 | -3.00 pp | 0.2103 | 0.2103 |
| passage-v1 | correct | meta-llama/Llama-3.1-8B-Instruct ↔ speakleash/Bielik-11B-v2.3-Instruct | 15 | 174 | 500 | +31.80 pp | 0.0000 | 0.0000 |
| passage-v1 | correct | mistralai/Mistral-7B-Instruct-v0.2 ↔ speakleash/Bielik-11B-v2.3-Instruct | 12 | 186 | 500 | +34.80 pp | 0.0000 | 0.0000 |
| source-web-v1 | hallucination | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 ↔ meta-llama/Llama-3.1-8B-Instruct | 32 | 125 | 495 | +18.79 pp | 0.0000 | 0.0000 |
| source-web-v1 | hallucination | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 ↔ mistralai/Mistral-7B-Instruct-v0.2 | 39 | 148 | 496 | +21.98 pp | 0.0000 | 0.0000 |
| source-web-v1 | hallucination | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 ↔ speakleash/Bielik-11B-v2.3-Instruct | 85 | 31 | 496 | -10.89 pp | 0.0000 | 0.0000 |
| source-web-v1 | hallucination | meta-llama/Llama-3.1-8B-Instruct ↔ mistralai/Mistral-7B-Instruct-v0.2 | 63 | 76 | 494 | +2.63 pp | 0.3088 | 0.3088 |
| source-web-v1 | hallucination | meta-llama/Llama-3.1-8B-Instruct ↔ speakleash/Bielik-11B-v2.3-Instruct | 166 | 18 | 494 | -29.96 pp | 0.0000 | 0.0000 |
| source-web-v1 | hallucination | mistralai/Mistral-7B-Instruct-v0.2 ↔ speakleash/Bielik-11B-v2.3-Instruct | 180 | 17 | 495 | -32.93 pp | 0.0000 | 0.0000 |
| source-web-v1 | correct | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 ↔ meta-llama/Llama-3.1-8B-Instruct | 124 | 31 | 495 | -18.79 pp | 0.0000 | 0.0000 |
| source-web-v1 | correct | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 ↔ mistralai/Mistral-7B-Instruct-v0.2 | 145 | 31 | 496 | -22.98 pp | 0.0000 | 0.0000 |
| source-web-v1 | correct | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 ↔ speakleash/Bielik-11B-v2.3-Instruct | 33 | 89 | 496 | +11.29 pp | 0.0000 | 0.0000 |
| source-web-v1 | correct | meta-llama/Llama-3.1-8B-Instruct ↔ mistralai/Mistral-7B-Instruct-v0.2 | 75 | 56 | 494 | -3.85 pp | 0.1155 | 0.1155 |
| source-web-v1 | correct | meta-llama/Llama-3.1-8B-Instruct ↔ speakleash/Bielik-11B-v2.3-Instruct | 17 | 166 | 494 | +30.16 pp | 0.0000 | 0.0000 |
| source-web-v1 | correct | mistralai/Mistral-7B-Instruct-v0.2 ↔ speakleash/Bielik-11B-v2.3-Instruct | 15 | 184 | 495 | +34.14 pp | 0.0000 | 0.0000 |

Różnice pomiędzy kategoriami — test chi-kwadrat:

| Eksperyment | Wynik | Model | N | χ² | df | p | p Holma (modele) | V Craméra | Min. oczekiwana |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gold-only-v1 | hallucination | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 | 500 | 45.403 | 2 | 0.0000 | 0.0000 | 0.301 | 30.60 |
| gold-only-v1 | hallucination | meta-llama/Llama-3.1-8B-Instruct | 500 | 26.372 | 2 | 0.0000 | 0.0000 | 0.230 | 49.40 |
| gold-only-v1 | hallucination | mistralai/Mistral-7B-Instruct-v0.2 | 500 | 45.815 | 2 | 0.0000 | 0.0000 | 0.303 | 49.40 |
| gold-only-v1 | hallucination | speakleash/Bielik-11B-v2.3-Instruct | 500 | 29.136 | 2 | 0.0000 | 0.0000 | 0.241 | 17.80 |
| gold-only-v1 | correct | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 | 500 | 48.107 | 2 | 0.0000 | 0.0000 | 0.310 | 31.00 |
| gold-only-v1 | correct | meta-llama/Llama-3.1-8B-Instruct | 500 | 32.110 | 2 | 0.0000 | 0.0000 | 0.253 | 49.60 |
| gold-only-v1 | correct | mistralai/Mistral-7B-Instruct-v0.2 | 500 | 61.085 | 2 | 0.0000 | 0.0000 | 0.350 | 46.20 |
| gold-only-v1 | correct | speakleash/Bielik-11B-v2.3-Instruct | 500 | 29.136 | 2 | 0.0000 | 0.0000 | 0.241 | 17.80 |
| passage-v1 | hallucination | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 | 499 | 42.980 | 2 | 0.0000 | 0.0000 | 0.293 | 29.66 |
| passage-v1 | hallucination | meta-llama/Llama-3.1-8B-Instruct | 500 | 32.270 | 2 | 0.0000 | 0.0000 | 0.254 | 49.60 |
| passage-v1 | hallucination | mistralai/Mistral-7B-Instruct-v0.2 | 500 | 52.351 | 2 | 0.0000 | 0.0000 | 0.324 | 49.60 |
| passage-v1 | hallucination | speakleash/Bielik-11B-v2.3-Instruct | 500 | 27.919 | 2 | 0.0000 | 0.0000 | 0.236 | 18.60 |
| passage-v1 | correct | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 | 499 | 44.293 | 2 | 0.0000 | 0.0000 | 0.298 | 29.86 |
| passage-v1 | correct | meta-llama/Llama-3.1-8B-Instruct | 500 | 37.230 | 2 | 0.0000 | 0.0000 | 0.273 | 49.60 |
| passage-v1 | correct | mistralai/Mistral-7B-Instruct-v0.2 | 500 | 66.737 | 2 | 0.0000 | 0.0000 | 0.365 | 46.60 |
| passage-v1 | correct | speakleash/Bielik-11B-v2.3-Instruct | 500 | 27.919 | 2 | 0.0000 | 0.0000 | 0.236 | 18.60 |
| source-web-v1 | hallucination | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 | 498 | 31.902 | 2 | 0.0000 | 0.0000 | 0.253 | 30.72 |
| source-web-v1 | hallucination | meta-llama/Llama-3.1-8B-Instruct | 497 | 29.438 | 2 | 0.0000 | 0.0000 | 0.243 | 49.00 |
| source-web-v1 | hallucination | mistralai/Mistral-7B-Instruct-v0.2 | 497 | 48.500 | 2 | 0.0000 | 0.0000 | 0.312 | 47.48 |
| source-web-v1 | hallucination | speakleash/Bielik-11B-v2.3-Instruct | 497 | 23.221 | 2 | 0.0000 | 0.0000 | 0.216 | 19.72 |
| source-web-v1 | correct | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 | 498 | 41.962 | 2 | 0.0000 | 0.0000 | 0.290 | 32.33 |
| source-web-v1 | correct | meta-llama/Llama-3.1-8B-Instruct | 497 | 37.678 | 2 | 0.0000 | 0.0000 | 0.275 | 48.60 |
| source-web-v1 | correct | mistralai/Mistral-7B-Instruct-v0.2 | 497 | 60.288 | 2 | 0.0000 | 0.0000 | 0.348 | 45.07 |
| source-web-v1 | correct | speakleash/Bielik-11B-v2.3-Instruct | 497 | 27.189 | 2 | 0.0000 | 0.0000 | 0.234 | 20.93 |

Porównania kategorii parami:

| Eksperyment | Wynik | Model | Para kategorii | Zmiana B−A | Test | p | p Holma |
| --- | --- | --- | --- | --- | --- | --- | --- |
| gold-only-v1 | hallucination | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 | general ↔ global | +13.50 pp | χ² | 0.0059 | 0.0073 |
| gold-only-v1 | hallucination | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 | general ↔ polish_realia | +31.00 pp | χ² | 0.0000 | 0.0000 |
| gold-only-v1 | hallucination | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 | global ↔ polish_realia | +17.50 pp | χ² | 0.0036 | 0.0073 |
| gold-only-v1 | hallucination | meta-llama/Llama-3.1-8B-Instruct | general ↔ global | -8.00 pp | χ² | 0.1830 | 0.1830 |
| gold-only-v1 | hallucination | meta-llama/Llama-3.1-8B-Instruct | general ↔ polish_realia | +20.00 pp | χ² | 0.0001 | 0.0001 |
| gold-only-v1 | hallucination | meta-llama/Llama-3.1-8B-Instruct | global ↔ polish_realia | +28.00 pp | χ² | 0.0000 | 0.0000 |
| gold-only-v1 | hallucination | mistralai/Mistral-7B-Instruct-v0.2 | general ↔ global | -5.00 pp | χ² | 0.4011 | 0.4011 |
| gold-only-v1 | hallucination | mistralai/Mistral-7B-Instruct-v0.2 | general ↔ polish_realia | +29.00 pp | χ² | 0.0000 | 0.0000 |
| gold-only-v1 | hallucination | mistralai/Mistral-7B-Instruct-v0.2 | global ↔ polish_realia | +34.00 pp | χ² | 0.0000 | 0.0000 |
| gold-only-v1 | hallucination | speakleash/Bielik-11B-v2.3-Instruct | general ↔ global | +13.00 pp | χ² | 0.0008 | 0.0016 |
| gold-only-v1 | hallucination | speakleash/Bielik-11B-v2.3-Instruct | general ↔ polish_realia | +20.50 pp | χ² | 0.0000 | 0.0000 |
| gold-only-v1 | hallucination | speakleash/Bielik-11B-v2.3-Instruct | global ↔ polish_realia | +7.50 pp | χ² | 0.1573 | 0.1573 |
| gold-only-v1 | correct | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 | general ↔ global | -13.50 pp | χ² | 0.0059 | 0.0059 |
| gold-only-v1 | correct | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 | general ↔ polish_realia | -32.00 pp | χ² | 0.0000 | 0.0000 |
| gold-only-v1 | correct | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 | global ↔ polish_realia | -18.50 pp | χ² | 0.0022 | 0.0043 |
| gold-only-v1 | correct | meta-llama/Llama-3.1-8B-Instruct | general ↔ global | +8.00 pp | χ² | 0.1830 | 0.1830 |
| gold-only-v1 | correct | meta-llama/Llama-3.1-8B-Instruct | general ↔ polish_realia | -22.50 pp | χ² | 0.0000 | 0.0000 |
| gold-only-v1 | correct | meta-llama/Llama-3.1-8B-Instruct | global ↔ polish_realia | -30.50 pp | χ² | 0.0000 | 0.0000 |
| gold-only-v1 | correct | mistralai/Mistral-7B-Instruct-v0.2 | general ↔ global | +5.50 pp | χ² | 0.3586 | 0.3586 |
| gold-only-v1 | correct | mistralai/Mistral-7B-Instruct-v0.2 | general ↔ polish_realia | -33.50 pp | χ² | 0.0000 | 0.0000 |
| gold-only-v1 | correct | mistralai/Mistral-7B-Instruct-v0.2 | global ↔ polish_realia | -39.00 pp | χ² | 0.0000 | 0.0000 |
| gold-only-v1 | correct | speakleash/Bielik-11B-v2.3-Instruct | general ↔ global | -13.00 pp | χ² | 0.0008 | 0.0016 |
| gold-only-v1 | correct | speakleash/Bielik-11B-v2.3-Instruct | general ↔ polish_realia | -20.50 pp | χ² | 0.0000 | 0.0000 |
| gold-only-v1 | correct | speakleash/Bielik-11B-v2.3-Instruct | global ↔ polish_realia | -7.50 pp | χ² | 0.1573 | 0.1573 |
| passage-v1 | hallucination | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 | general ↔ global | +12.92 pp | χ² | 0.0077 | 0.0090 |
| passage-v1 | hallucination | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 | general ↔ polish_realia | +29.92 pp | χ² | 0.0000 | 0.0000 |
| passage-v1 | hallucination | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 | global ↔ polish_realia | +17.00 pp | χ² | 0.0045 | 0.0090 |
| passage-v1 | hallucination | meta-llama/Llama-3.1-8B-Instruct | general ↔ global | -10.00 pp | χ² | 0.0951 | 0.0951 |
| passage-v1 | hallucination | meta-llama/Llama-3.1-8B-Instruct | general ↔ polish_realia | +21.50 pp | χ² | 0.0000 | 0.0000 |
| passage-v1 | hallucination | meta-llama/Llama-3.1-8B-Instruct | global ↔ polish_realia | +31.50 pp | χ² | 0.0000 | 0.0000 |
| passage-v1 | hallucination | mistralai/Mistral-7B-Instruct-v0.2 | general ↔ global | -6.50 pp | χ² | 0.2725 | 0.2725 |
| passage-v1 | hallucination | mistralai/Mistral-7B-Instruct-v0.2 | general ↔ polish_realia | +30.50 pp | χ² | 0.0000 | 0.0000 |
| passage-v1 | hallucination | mistralai/Mistral-7B-Instruct-v0.2 | global ↔ polish_realia | +37.00 pp | χ² | 0.0000 | 0.0000 |
| passage-v1 | hallucination | speakleash/Bielik-11B-v2.3-Instruct | general ↔ global | +12.00 pp | χ² | 0.0026 | 0.0051 |
| passage-v1 | hallucination | speakleash/Bielik-11B-v2.3-Instruct | general ↔ polish_realia | +20.50 pp | χ² | 0.0000 | 0.0000 |
| passage-v1 | hallucination | speakleash/Bielik-11B-v2.3-Instruct | global ↔ polish_realia | +8.50 pp | χ² | 0.1121 | 0.1121 |
| passage-v1 | correct | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 | general ↔ global | -12.92 pp | χ² | 0.0077 | 0.0077 |
| passage-v1 | correct | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 | general ↔ polish_realia | -30.42 pp | χ² | 0.0000 | 0.0000 |
| passage-v1 | correct | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 | global ↔ polish_realia | -17.50 pp | χ² | 0.0035 | 0.0070 |
| passage-v1 | correct | meta-llama/Llama-3.1-8B-Instruct | general ↔ global | +10.00 pp | χ² | 0.0951 | 0.0951 |
| passage-v1 | correct | meta-llama/Llama-3.1-8B-Instruct | general ↔ polish_realia | -23.50 pp | χ² | 0.0000 | 0.0000 |
| passage-v1 | correct | meta-llama/Llama-3.1-8B-Instruct | global ↔ polish_realia | -33.50 pp | χ² | 0.0000 | 0.0000 |
| passage-v1 | correct | mistralai/Mistral-7B-Instruct-v0.2 | general ↔ global | +7.00 pp | χ² | 0.2405 | 0.2405 |
| passage-v1 | correct | mistralai/Mistral-7B-Instruct-v0.2 | general ↔ polish_realia | -34.50 pp | χ² | 0.0000 | 0.0000 |
| passage-v1 | correct | mistralai/Mistral-7B-Instruct-v0.2 | global ↔ polish_realia | -41.50 pp | χ² | 0.0000 | 0.0000 |
| passage-v1 | correct | speakleash/Bielik-11B-v2.3-Instruct | general ↔ global | -12.00 pp | χ² | 0.0026 | 0.0051 |
| passage-v1 | correct | speakleash/Bielik-11B-v2.3-Instruct | general ↔ polish_realia | -20.50 pp | χ² | 0.0000 | 0.0000 |
| passage-v1 | correct | speakleash/Bielik-11B-v2.3-Instruct | global ↔ polish_realia | -8.50 pp | χ² | 0.1121 | 0.1121 |
| source-web-v1 | hallucination | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 | general ↔ global | +9.50 pp | χ² | 0.0597 | 0.0597 |
| source-web-v1 | hallucination | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 | general ↔ polish_realia | +25.94 pp | χ² | 0.0000 | 0.0000 |
| source-web-v1 | hallucination | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 | global ↔ polish_realia | +16.44 pp | χ² | 0.0060 | 0.0120 |
| source-web-v1 | hallucination | meta-llama/Llama-3.1-8B-Instruct | general ↔ global | -13.69 pp | χ² | 0.0233 | 0.0233 |
| source-web-v1 | hallucination | meta-llama/Llama-3.1-8B-Instruct | general ↔ polish_realia | +18.13 pp | χ² | 0.0003 | 0.0006 |
| source-web-v1 | hallucination | meta-llama/Llama-3.1-8B-Instruct | global ↔ polish_realia | +31.82 pp | χ² | 0.0000 | 0.0000 |
| source-web-v1 | hallucination | mistralai/Mistral-7B-Instruct-v0.2 | general ↔ global | -6.00 pp | χ² | 0.3173 | 0.3173 |
| source-web-v1 | hallucination | mistralai/Mistral-7B-Instruct-v0.2 | general ↔ polish_realia | +29.57 pp | χ² | 0.0000 | 0.0000 |
| source-web-v1 | hallucination | mistralai/Mistral-7B-Instruct-v0.2 | global ↔ polish_realia | +35.57 pp | χ² | 0.0000 | 0.0000 |
| source-web-v1 | hallucination | speakleash/Bielik-11B-v2.3-Instruct | general ↔ global | +9.95 pp | χ² | 0.0171 | 0.0342 |
| source-web-v1 | hallucination | speakleash/Bielik-11B-v2.3-Instruct | general ↔ polish_realia | +19.24 pp | χ² | 0.0000 | 0.0000 |
| source-web-v1 | hallucination | speakleash/Bielik-11B-v2.3-Instruct | global ↔ polish_realia | +9.29 pp | χ² | 0.0849 | 0.0849 |
| source-web-v1 | correct | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 | general ↔ global | -9.50 pp | χ² | 0.0597 | 0.0597 |
| source-web-v1 | correct | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 | general ↔ polish_realia | -29.98 pp | χ² | 0.0000 | 0.0000 |
| source-web-v1 | correct | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 | global ↔ polish_realia | -20.48 pp | χ² | 0.0007 | 0.0014 |
| source-web-v1 | correct | meta-llama/Llama-3.1-8B-Instruct | general ↔ global | +13.69 pp | χ² | 0.0233 | 0.0233 |
| source-web-v1 | correct | meta-llama/Llama-3.1-8B-Instruct | general ↔ polish_realia | -21.67 pp | χ² | 0.0000 | 0.0000 |
| source-web-v1 | correct | meta-llama/Llama-3.1-8B-Instruct | global ↔ polish_realia | -35.35 pp | χ² | 0.0000 | 0.0000 |
| source-web-v1 | correct | mistralai/Mistral-7B-Instruct-v0.2 | general ↔ global | +6.00 pp | χ² | 0.3192 | 0.3192 |
| source-web-v1 | correct | mistralai/Mistral-7B-Instruct-v0.2 | general ↔ polish_realia | -33.14 pp | χ² | 0.0000 | 0.0000 |
| source-web-v1 | correct | mistralai/Mistral-7B-Instruct-v0.2 | global ↔ polish_realia | -39.14 pp | χ² | 0.0000 | 0.0000 |
| source-web-v1 | correct | speakleash/Bielik-11B-v2.3-Instruct | general ↔ global | -9.45 pp | χ² | 0.0251 | 0.0501 |
| source-web-v1 | correct | speakleash/Bielik-11B-v2.3-Instruct | general ↔ polish_realia | -21.27 pp | χ² | 0.0000 | 0.0000 |
| source-web-v1 | correct | speakleash/Bielik-11B-v2.3-Instruct | global ↔ polish_realia | -11.82 pp | χ² | 0.0316 | 0.0501 |

## 6. Ręczna walidacja sędziego LLM

| Oceniający | Ocenione | Plan | Kompletność | Pytania | correct | hallucination | abstention |
| --- | --- | --- | --- | --- | --- | --- | --- |
| human | 600 | 600 | 100.00% | 150 | 361 (60.17%) | 235 (39.17%) | 4 (0.67%) |

Zgodność trójklasowa z oceną człowieka (estymata [95% CI]):

| Oceniający | Protokół | N | Pytania | Zgodność | Cohen κ |
| --- | --- | --- | --- | --- | --- |
| human | gold-only-v1 | 600 | 150 | 0.973 [0.960; 0.985] | 0.946 [0.916; 0.970] |
| human | passage-v1 | 599 | 150 | 0.972 [0.958; 0.983] | 0.942 [0.913; 0.967] |
| human | source-web-v1 | 599 | 150 | 0.968 [0.953; 0.982] | 0.935 [0.903; 0.963] |

Metryki trójklasowe według klasy (estymata [95% CI]):

| Oceniający | Protokół | Klasa | Support człowieka | Precision | Recall | F1 |
| --- | --- | --- | --- | --- | --- | --- |
| human | gold-only-v1 | correct | 361 | 0.997 [0.991; 1.000] | 0.961 [0.939; 0.980] | 0.979 [0.967; 0.989] |
| human | gold-only-v1 | hallucination | 235 | 0.943 [0.909; 0.972] | 0.991 [0.978; 1.000] | 0.967 [0.948; 0.983] |
| human | gold-only-v1 | abstention | 4 | 0.800 [0.333; 1.000] | 1.000 [1.000; 1.000] | 0.889 [0.500; 1.000] |
| human | passage-v1 | correct | 361 | 0.989 [0.977; 0.997] | 0.967 [0.946; 0.984] | 0.978 [0.966; 0.988] |
| human | passage-v1 | hallucination | 234 | 0.950 [0.919; 0.977] | 0.979 [0.959; 0.996] | 0.964 [0.945; 0.980] |
| human | passage-v1 | abstention | 4 | 0.800 [0.333; 1.000] | 1.000 [1.000; 1.000] | 0.889 [0.500; 1.000] |
| human | source-web-v1 | correct | 361 | 0.989 [0.976; 0.997] | 0.964 [0.943; 0.983] | 0.976 [0.964; 0.987] |
| human | source-web-v1 | hallucination | 234 | 0.939 [0.904; 0.969] | 0.983 [0.964; 0.996] | 0.960 [0.939; 0.978] |
| human | source-web-v1 | abstention | 4 | 1.000 [1.000; 1.000] | 0.500 [0.000; 1.000] | 0.667 [0.000; 1.000] |

Podsumowanie trójklasowe (estymata [95% CI]):

| Oceniający | Protokół | N | Macro-F1 | Balanced accuracy |
| --- | --- | --- | --- | --- |
| human | gold-only-v1 | 600 | 0.945 [0.815; 0.989] | 0.984 [0.976; 0.991] |
| human | passage-v1 | 599 | 0.944 [0.813; 0.988] | 0.982 [0.973; 0.990] |
| human | source-web-v1 | 599 | 0.868 [0.641; 0.984] | 0.816 [0.646; 0.986] |

Wartości macro są nieważoną średnią wyników trzech klas. Wyniki klasy `abstention` należy interpretować ostrożnie ze względu na bardzo małe support.

Detekcja klasy `hallucination` (estymata [95% CI]):

| Oceniający | Protokół | N | Czułość | Swoistość | Precision | F1 | Balanced accuracy | FPR | FNR |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| human | gold-only-v1 | 600 | 0.991 [0.978; 1.000] | 0.962 [0.940; 0.981] | 0.943 [0.909; 0.972] | 0.967 [0.948; 0.983] | 0.977 [0.964; 0.987] | 0.038 [0.019; 0.060] | 0.009 [0.000; 0.022] |
| human | passage-v1 | 599 | 0.979 [0.959; 0.996] | 0.967 [0.947; 0.984] | 0.950 [0.919; 0.977] | 0.964 [0.945; 0.980] | 0.973 [0.959; 0.985] | 0.033 [0.016; 0.053] | 0.021 [0.004; 0.041] |
| human | source-web-v1 | 599 | 0.983 [0.964; 0.996] | 0.959 [0.937; 0.979] | 0.939 [0.904; 0.969] | 0.960 [0.939; 0.978] | 0.971 [0.957; 0.983] | 0.041 [0.021; 0.063] | 0.017 [0.004; 0.036] |

Klasa dodatnia to `hallucination`; `correct` i `abstention` tworzą klasę ujemną. Przedziały wyznaczono przez bootstrap całych pytań.

Macierz pomyłek człowiek (wiersze) → `gold-only-v1` (kolumny), oceniający `human`, N=600:

| Człowiek \ LLM | correct | hallucination | abstention |
| --- | --- | --- | --- |
| correct | 347 | 14 | 0 |
| hallucination | 1 | 233 | 1 |
| abstention | 0 | 0 | 4 |

Macierz pomyłek człowiek (wiersze) → `passage-v1` (kolumny), oceniający `human`, N=599:

| Człowiek \ LLM | correct | hallucination | abstention |
| --- | --- | --- | --- |
| correct | 349 | 12 | 0 |
| hallucination | 4 | 229 | 1 |
| abstention | 0 | 0 | 4 |

Macierz pomyłek człowiek (wiersze) → `source-web-v1` (kolumny), oceniający `human`, N=599:

| Człowiek \ LLM | correct | hallucination | abstention |
| --- | --- | --- | --- |
| correct | 348 | 13 | 0 |
| hallucination | 4 | 230 | 0 |
| abstention | 0 | 2 | 2 |

Różnice trafności protokołów względem ręcznych etykiet (B−A):

| Oceniający | Para | Metryka | N | Różnica | 95% CI |
| --- | --- | --- | --- | --- | --- |
| human | gold-only-v1 → passage-v1 | sensitivity | 599 | -1.28 pp | [-2.88; +0.00] pp |
| human | gold-only-v1 → passage-v1 | specificity | 599 | +0.55 pp | [-0.54; +1.66] pp |
| human | gold-only-v1 → passage-v1 | precision | 599 | +0.71 pp | [-0.79; +2.31] pp |
| human | gold-only-v1 → passage-v1 | f1 | 599 | -0.25 pp | [-1.33; +0.82] pp |
| human | gold-only-v1 → passage-v1 | balanced_accuracy | 599 | -0.37 pp | [-1.30; +0.45] pp |
| human | gold-only-v1 → source-web-v1 | sensitivity | 599 | -0.85 pp | [-2.62; +0.82] pp |
| human | gold-only-v1 → source-web-v1 | specificity | 599 | -0.27 pp | [-1.94; +1.36] pp |
| human | gold-only-v1 → source-web-v1 | precision | 599 | -0.43 pp | [-2.76; +1.85] pp |
| human | gold-only-v1 → source-web-v1 | f1 | 599 | -0.63 pp | [-2.02; +0.65] pp |
| human | gold-only-v1 → source-web-v1 | balanced_accuracy | 599 | -0.56 pp | [-1.66; +0.49] pp |
| human | passage-v1 → source-web-v1 | sensitivity | 598 | +0.43 pp | [-1.40; +2.34] pp |
| human | passage-v1 → source-web-v1 | specificity | 598 | -0.82 pp | [-2.48; +0.80] pp |
| human | passage-v1 → source-web-v1 | precision | 598 | -1.15 pp | [-3.56; +1.12] pp |
| human | passage-v1 → source-web-v1 | f1 | 598 | -0.39 pp | [-1.89; +0.98] pp |
| human | passage-v1 → source-web-v1 | balanced_accuracy | 598 | -0.20 pp | [-1.36; +0.94] pp |

Formalne porównanie trafności trzech protokołów — Cochran Q:

| Oceniający | Metryka | Model | N pytań | Q | df | p | p Holma (modele) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| human | accuracy | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 | 149 | 0.667 | 2 | 0.7165 | 1.0000 |
| human | accuracy | meta-llama/Llama-3.1-8B-Instruct | 149 | 1.000 | 2 | 0.6065 | 1.0000 |
| human | accuracy | mistralai/Mistral-7B-Instruct-v0.2 | 150 | 2.000 | 2 | 0.3679 | 1.0000 |
| human | accuracy | speakleash/Bielik-11B-v2.3-Instruct | 150 | 0.667 | 2 | 0.7165 | 1.0000 |
| human | sensitivity | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 | 51 | 3.000 | 2 | 0.2231 | 0.8925 |
| human | sensitivity | meta-llama/Llama-3.1-8B-Instruct | 77 | 0.000 | 2 | 1.0000 | 1.0000 |
| human | sensitivity | mistralai/Mistral-7B-Instruct-v0.2 | 74 | 0.667 | 2 | 0.7165 | 1.0000 |
| human | sensitivity | speakleash/Bielik-11B-v2.3-Instruct | 31 | 2.000 | 2 | 0.3679 | 1.0000 |
| human | specificity | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 | 98 | 2.000 | 2 | 0.3679 | 1.0000 |
| human | specificity | meta-llama/Llama-3.1-8B-Instruct | 72 | 1.000 | 2 | 0.6065 | 1.0000 |
| human | specificity | mistralai/Mistral-7B-Instruct-v0.2 | 76 | 4.333 | 2 | 0.1146 | 0.4582 |
| human | specificity | speakleash/Bielik-11B-v2.3-Instruct | 119 | 0.000 | 2 | 1.0000 | 1.0000 |

Porównania trafności protokołów parami — dokładny McNemar:

| Oceniający | Metryka | Model | Para | Tylko A | Tylko B | N | p | p Holma |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| human | accuracy | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 | gold-only-v1 ↔ passage-v1 | 1 | 1 | 149 | 1.0000 | 1.0000 |
| human | accuracy | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 | gold-only-v1 ↔ source-web-v1 | 2 | 1 | 150 | 1.0000 | 1.0000 |
| human | accuracy | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 | passage-v1 ↔ source-web-v1 | 1 | 0 | 149 | 1.0000 | 1.0000 |
| human | accuracy | meta-llama/Llama-3.1-8B-Instruct | gold-only-v1 ↔ passage-v1 | 1 | 1 | 150 | 1.0000 | 1.0000 |
| human | accuracy | meta-llama/Llama-3.1-8B-Instruct | gold-only-v1 ↔ source-web-v1 | 0 | 1 | 149 | 1.0000 | 1.0000 |
| human | accuracy | meta-llama/Llama-3.1-8B-Instruct | passage-v1 ↔ source-web-v1 | 0 | 1 | 149 | 1.0000 | 1.0000 |
| human | accuracy | mistralai/Mistral-7B-Instruct-v0.2 | gold-only-v1 ↔ passage-v1 | 1 | 1 | 150 | 1.0000 | 1.0000 |
| human | accuracy | mistralai/Mistral-7B-Instruct-v0.2 | gold-only-v1 ↔ source-web-v1 | 5 | 2 | 150 | 0.4531 | 1.0000 |
| human | accuracy | mistralai/Mistral-7B-Instruct-v0.2 | passage-v1 ↔ source-web-v1 | 6 | 3 | 150 | 0.5078 | 1.0000 |
| human | accuracy | speakleash/Bielik-11B-v2.3-Instruct | gold-only-v1 ↔ passage-v1 | 1 | 0 | 150 | 1.0000 | 1.0000 |
| human | accuracy | speakleash/Bielik-11B-v2.3-Instruct | gold-only-v1 ↔ source-web-v1 | 1 | 1 | 150 | 1.0000 | 1.0000 |
| human | accuracy | speakleash/Bielik-11B-v2.3-Instruct | passage-v1 ↔ source-web-v1 | 1 | 2 | 150 | 1.0000 | 1.0000 |
| human | sensitivity | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 | gold-only-v1 ↔ passage-v1 | 1 | 0 | 51 | 1.0000 | 1.0000 |
| human | sensitivity | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 | gold-only-v1 ↔ source-web-v1 | 2 | 0 | 52 | 0.5000 | 1.0000 |
| human | sensitivity | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 | passage-v1 ↔ source-web-v1 | 1 | 0 | 51 | 1.0000 | 1.0000 |
| human | sensitivity | meta-llama/Llama-3.1-8B-Instruct | gold-only-v1 ↔ passage-v1 | 0 | 0 | 78 | 1.0000 | 1.0000 |
| human | sensitivity | meta-llama/Llama-3.1-8B-Instruct | gold-only-v1 ↔ source-web-v1 | 0 | 0 | 77 | 1.0000 | 1.0000 |
| human | sensitivity | meta-llama/Llama-3.1-8B-Instruct | passage-v1 ↔ source-web-v1 | 0 | 0 | 77 | 1.0000 | 1.0000 |
| human | sensitivity | mistralai/Mistral-7B-Instruct-v0.2 | gold-only-v1 ↔ passage-v1 | 1 | 0 | 74 | 1.0000 | 1.0000 |
| human | sensitivity | mistralai/Mistral-7B-Instruct-v0.2 | gold-only-v1 ↔ source-web-v1 | 1 | 1 | 74 | 1.0000 | 1.0000 |
| human | sensitivity | mistralai/Mistral-7B-Instruct-v0.2 | passage-v1 ↔ source-web-v1 | 1 | 2 | 74 | 1.0000 | 1.0000 |
| human | sensitivity | speakleash/Bielik-11B-v2.3-Instruct | gold-only-v1 ↔ passage-v1 | 1 | 0 | 31 | 1.0000 | 1.0000 |
| human | sensitivity | speakleash/Bielik-11B-v2.3-Instruct | gold-only-v1 ↔ source-web-v1 | 0 | 0 | 31 | 1.0000 | 1.0000 |
| human | sensitivity | speakleash/Bielik-11B-v2.3-Instruct | passage-v1 ↔ source-web-v1 | 0 | 1 | 31 | 1.0000 | 1.0000 |
| human | specificity | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 | gold-only-v1 ↔ passage-v1 | 0 | 1 | 98 | 1.0000 | 1.0000 |
| human | specificity | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 | gold-only-v1 ↔ source-web-v1 | 0 | 1 | 98 | 1.0000 | 1.0000 |
| human | specificity | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 | passage-v1 ↔ source-web-v1 | 0 | 0 | 98 | 1.0000 | 1.0000 |
| human | specificity | meta-llama/Llama-3.1-8B-Instruct | gold-only-v1 ↔ passage-v1 | 1 | 1 | 72 | 1.0000 | 1.0000 |
| human | specificity | meta-llama/Llama-3.1-8B-Instruct | gold-only-v1 ↔ source-web-v1 | 0 | 1 | 72 | 1.0000 | 1.0000 |
| human | specificity | meta-llama/Llama-3.1-8B-Instruct | passage-v1 ↔ source-web-v1 | 0 | 1 | 72 | 1.0000 | 1.0000 |
| human | specificity | mistralai/Mistral-7B-Instruct-v0.2 | gold-only-v1 ↔ passage-v1 | 0 | 1 | 76 | 1.0000 | 1.0000 |
| human | specificity | mistralai/Mistral-7B-Instruct-v0.2 | gold-only-v1 ↔ source-web-v1 | 4 | 1 | 76 | 0.3750 | 0.7500 |
| human | specificity | mistralai/Mistral-7B-Instruct-v0.2 | passage-v1 ↔ source-web-v1 | 5 | 1 | 76 | 0.2188 | 0.6562 |
| human | specificity | speakleash/Bielik-11B-v2.3-Instruct | gold-only-v1 ↔ passage-v1 | 0 | 0 | 119 | 1.0000 | 1.0000 |
| human | specificity | speakleash/Bielik-11B-v2.3-Instruct | gold-only-v1 ↔ source-web-v1 | 1 | 1 | 119 | 1.0000 | 1.0000 |
| human | specificity | speakleash/Bielik-11B-v2.3-Instruct | passage-v1 ↔ source-web-v1 | 1 | 1 | 119 | 1.0000 | 1.0000 |

## 7. Braki konsensusu

| Eksperyment | Przekrój | Grupa | Oczekiwane | Braki | Odsetek |
| --- | --- | --- | --- | --- | --- |
| gold-only-v1 | model | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 | 500 | 0 | 0.00% |
| gold-only-v1 | model | meta-llama/Llama-3.1-8B-Instruct | 500 | 0 | 0.00% |
| gold-only-v1 | model | mistralai/Mistral-7B-Instruct-v0.2 | 500 | 0 | 0.00% |
| gold-only-v1 | model | speakleash/Bielik-11B-v2.3-Instruct | 500 | 0 | 0.00% |
| gold-only-v1 | category | general | 800 | 0 | 0.00% |
| gold-only-v1 | category | global | 400 | 0 | 0.00% |
| gold-only-v1 | category | polish_realia | 800 | 0 | 0.00% |
| passage-v1 | model | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 | 500 | 1 | 0.20% |
| passage-v1 | model | meta-llama/Llama-3.1-8B-Instruct | 500 | 0 | 0.00% |
| passage-v1 | model | mistralai/Mistral-7B-Instruct-v0.2 | 500 | 0 | 0.00% |
| passage-v1 | model | speakleash/Bielik-11B-v2.3-Instruct | 500 | 0 | 0.00% |
| passage-v1 | category | general | 800 | 1 | 0.12% |
| passage-v1 | category | global | 400 | 0 | 0.00% |
| passage-v1 | category | polish_realia | 800 | 0 | 0.00% |
| source-web-v1 | model | CYFRAGOVPL/Llama-PLLuM-8B-instruct-2412 | 500 | 2 | 0.40% |
| source-web-v1 | model | meta-llama/Llama-3.1-8B-Instruct | 500 | 3 | 0.60% |
| source-web-v1 | model | mistralai/Mistral-7B-Instruct-v0.2 | 500 | 3 | 0.60% |
| source-web-v1 | model | speakleash/Bielik-11B-v2.3-Instruct | 500 | 3 | 0.60% |
| source-web-v1 | category | general | 800 | 1 | 0.12% |
| source-web-v1 | category | global | 400 | 1 | 0.25% |
| source-web-v1 | category | polish_realia | 800 | 9 | 1.12% |

Zależność braków od modelu lub kategorii:

| Eksperyment | Zmienna | Test | χ² | df | p | V Craméra | Min. oczekiwana |
| --- | --- | --- | --- | --- | --- | --- | --- |
| gold-only-v1 | model | — | — | 0 | — | — | — |
| gold-only-v1 | category | — | — | 0 | — | — | — |
| passage-v1 | model | Fisher–Freeman–Halton | 3.002 | 3 | 1.0000 | 0.039 | 0.25 |
| passage-v1 | category | Fisher–Freeman–Halton | 1.501 | 2 | 1.0000 | 0.027 | 0.20 |
| source-web-v1 | model | Fisher–Freeman–Halton | 0.274 | 3 | 1.0000 | 0.012 | 2.75 |
| source-web-v1 | category | Fisher–Freeman–Halton | 8.136 | 2 | 0.0217 | 0.064 | 2.20 |

Gdy minimalna oczekiwana liczebność jest mniejsza niż 5, raport podaje dokładną wartość p testu Fishera–Freemana–Haltona zamiast asymptotycznej wartości p testu chi-kwadrat. Statystykę χ² i V Craméra pozostawiono jako opis wielkości zależności.

## 8. Tokeny i wydajność

| Eksperyment | Run | Źródło usage | Wywołania | Input | Cache | Bez cache | Output | Reasoning | Total | Śr. total | Mediana | P95 | Web calls | Próby / wynik |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gold-only-v1 | 1 | archiwum (wszystkie próby) | 2003 | 3682368 | 2493696 | 1188672 | 248471 | 70708 | 3930839 | 1962.5 | 1937.0 | 2120.9 | 0 | 1.002 |
| gold-only-v1 | 2 | archiwum (wszystkie próby) | 2004 | 3684158 | 2566912 | 1117246 | 247382 | 69963 | 3931540 | 1961.8 | 1937.0 | 2117.0 | 0 | 1.002 |
| gold-only-v1 | 3 | archiwum (wszystkie próby) | 2007 | 3689749 | 2583552 | 1106197 | 249623 | 71894 | 3939372 | 1962.8 | 1938.0 | 2122.7 | 0 | 1.004 |
| gold-only-v1 | 4 | archiwum (wszystkie próby) | 2006 | 3687801 | 2585088 | 1102713 | 249597 | 72006 | 3937398 | 1962.8 | 1938.0 | 2123.0 | 0 | 1.003 |
| gold-only-v1 | 5 | archiwum (wszystkie próby) | 2006 | 3687939 | 2576896 | 1111043 | 247478 | 70342 | 3935417 | 1961.8 | 1937.0 | 2122.8 | 0 | 1.003 |
| passage-v1 | 1 | archiwum (wszystkie próby) | 2008 | 3774233 | 2576128 | 1198105 | 280266 | 90383 | 4054499 | 2019.2 | 2002.0 | 2195.6 | 0 | 1.004 |
| passage-v1 | 2 | archiwum (wszystkie próby) | 2007 | 3772519 | 2770944 | 1001575 | 280669 | 89901 | 4053188 | 2019.5 | 2002.0 | 2195.0 | 0 | 1.004 |
| passage-v1 | 3 | archiwum (wszystkie próby) | 2007 | 3772488 | 2778368 | 994120 | 281172 | 92074 | 4053660 | 2019.8 | 2001.0 | 2201.7 | 0 | 1.004 |
| passage-v1 | 4 | archiwum (wszystkie próby) | 2002 | 3762971 | 2835200 | 927771 | 274482 | 85774 | 4037453 | 2016.7 | 2000.0 | 2194.9 | 0 | 1.001 |
| passage-v1 | 5 | archiwum (wszystkie próby) | 2007 | 3772894 | 2798848 | 974046 | 276757 | 87552 | 4049651 | 2017.8 | 1999.0 | 2186.0 | 0 | 1.004 |
| source-web-v1 | 1 | archiwum (wszystkie próby) | 2134 | 21173222 | 10263040 | 10910182 | 546745 | 319955 | 21719967 | 10178.1 | 10806.0 | 17010.5 | 2795 | 1.072 |
| source-web-v1 | 2 | archiwum (wszystkie próby) | 2141 | 21554345 | 10349568 | 11204777 | 545824 | 317524 | 22100169 | 10322.4 | 10924.0 | 16965.0 | 2808 | 1.076 |
| source-web-v1 | 3 | archiwum (wszystkie próby) | 2123 | 24282279 | 10054784 | 14227495 | 531172 | 300907 | 24813451 | 11687.9 | 11123.0 | 17244.7 | 2961 | 1.064 |
| source-web-v1 | 4 | archiwum (wszystkie próby) | 2083 | 23787953 | 9875968 | 13911985 | 516278 | 291864 | 24304231 | 11667.9 | 11140.0 | 17176.9 | 2866 | 1.045 |
| source-web-v1 | 5 | archiwum (wszystkie próby) | 2113 | 23996874 | 9939968 | 14056906 | 523279 | 296051 | 24520153 | 11604.4 | 11121.0 | 17137.2 | 2896 | 1.060 |

Tokeny według statusu odpowiedzi API:

| Eksperyment | Run | Status | Wywołania | Input | Output | Total |
| --- | --- | --- | --- | --- | --- | --- |
| gold-only-v1 | 1 | invalid_annotation | 3 | 5552 | 1800 | 7352 |
| gold-only-v1 | 1 | ok | 2000 | 3676816 | 246671 | 3923487 |
| gold-only-v1 | 2 | invalid_annotation | 4 | 7342 | 2400 | 9742 |
| gold-only-v1 | 2 | ok | 2000 | 3676816 | 244982 | 3921798 |
| gold-only-v1 | 3 | invalid_annotation | 7 | 12933 | 4200 | 17133 |
| gold-only-v1 | 3 | ok | 2000 | 3676816 | 245423 | 3922239 |
| gold-only-v1 | 4 | invalid_annotation | 6 | 10985 | 3600 | 14585 |
| gold-only-v1 | 4 | ok | 2000 | 3676816 | 245997 | 3922813 |
| gold-only-v1 | 5 | invalid_annotation | 6 | 11123 | 3600 | 14723 |
| gold-only-v1 | 5 | ok | 2000 | 3676816 | 243878 | 3920694 |
| passage-v1 | 1 | invalid_annotation | 8 | 15001 | 4800 | 19801 |
| passage-v1 | 1 | ok | 2000 | 3759232 | 275466 | 4034698 |
| passage-v1 | 2 | invalid_annotation | 7 | 13287 | 4200 | 17487 |
| passage-v1 | 2 | ok | 2000 | 3759232 | 276469 | 4035701 |
| passage-v1 | 3 | invalid_annotation | 7 | 13256 | 4200 | 17456 |
| passage-v1 | 3 | ok | 2000 | 3759232 | 276972 | 4036204 |
| passage-v1 | 4 | invalid_annotation | 2 | 3739 | 1200 | 4939 |
| passage-v1 | 4 | ok | 2000 | 3759232 | 273282 | 4032514 |
| passage-v1 | 5 | invalid_annotation | 7 | 13662 | 4200 | 17862 |
| passage-v1 | 5 | ok | 2000 | 3759232 | 272557 | 4031789 |
| source-web-v1 | 1 | invalid_annotation | 2 | 18426 | 384 | 18810 |
| source-web-v1 | 1 | invalid_source | 141 | 961401 | 43554 | 1004955 |
| source-web-v1 | 1 | ok | 1991 | 20193395 | 502807 | 20696202 |
| source-web-v1 | 2 | invalid_annotation | 3 | 33587 | 1004 | 34591 |
| source-web-v1 | 2 | invalid_source | 148 | 1013229 | 45372 | 1058601 |
| source-web-v1 | 2 | ok | 1990 | 20507529 | 499448 | 21006977 |
| source-web-v1 | 3 | invalid_annotation | 3 | 29284 | 657 | 29941 |
| source-web-v1 | 3 | invalid_source | 125 | 970602 | 39010 | 1009612 |
| source-web-v1 | 3 | ok | 1995 | 23282393 | 491505 | 23773898 |
| source-web-v1 | 4 | invalid_annotation | 5 | 55852 | 1657 | 57509 |
| source-web-v1 | 4 | invalid_source | 84 | 588143 | 26899 | 615042 |
| source-web-v1 | 4 | ok | 1994 | 23143958 | 487722 | 23631680 |
| source-web-v1 | 5 | invalid_annotation | 5 | 73199 | 1517 | 74716 |
| source-web-v1 | 5 | invalid_source | 114 | 801382 | 34266 | 835648 |
| source-web-v1 | 5 | ok | 1994 | 23122293 | 487496 | 23609789 |
