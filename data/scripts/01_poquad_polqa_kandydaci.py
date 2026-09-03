#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Krok 1: Pobranie PoQuAD (clarin-pl/poquad) i PolQA (ipipan/polqa),
        inspekcja schematu, zbudowanie wspolnej puli kandydatow,
        odfiltrowanie pytan slabo nadajacych sie na krotka, jednoznaczna
        odpowiedz i zapisanie wspolnej puli kandydatow do recznej selekcji.

Wyjscie:
  kandydaci_general_pelna_pula.csv  - wszyscy kandydaci po filtrach jakościowych,
                                      gotowi dla 03_selekcja_pytan.py
  Kolumny: zrodlo, qid, pytanie, gold_answer, aliases, passaz, passaz_url

Uruchom u siebie:  python 01_poquad_polqa_kandydaci.py
Wymaga:            pip install datasets pandas
Dostep do sieci:   huggingface.co
"""

import ast
import re
from pathlib import Path

import pandas as pd
from datasets import load_dataset

DATA_DIR = Path(__file__).resolve().parents[1]
OUT_FULL = DATA_DIR / "kandydaci_general_pelna_pula.csv"
WIKI = "https://pl.wikipedia.org/wiki/"

# --- parametry filtrow jakosciowych --------------------------------------
# Odpowiedz dluzsza niz tyle slow zwykle jest fragmentem zdania/wyliczeniem,
# a nie krotka, jednoznaczna odpowiedzia faktograficzna.
MAX_ANSWER_WORDS = 6

# Pytania zaczynajace sie tak (tak/nie, wyjasnienie przyczyny) nie dają
# krotkiej, jednoznacznej odpowiedzi faktograficznej.
BAD_PREFIXES = ("czy ", "dlaczego ")

# "Jak ..." bywa dobre ("Jak nazywal sie...") albo zle ("Jak Syria
# uzasadnila...") - akceptujemy tylko warianty z rdzeniem "nazyw".
JAK_REQUIRE_SUBSTR = "nazyw"

# Wskazniki, ze odpowiedz jest wyliczeniem/lista kilku elementow.
LIST_INDICATOR_RE = re.compile(r",|\bi\b|\boraz\b|\blub\b", re.IGNORECASE)

# W PolQA pole question_type pozwala odciac z gory pytania tak/nie,
# wybor A-czy-B, wyliczenia i uzupelnianie przyslowia (patrz analiza w
# notatkach do tego skryptu) - zostawiamy tylko typy z jednoznaczna,
# pojedyncza encja jako odpowiedzia.
ALLOWED_POLQA_QTYPES = {"SINGLE ENTITY", "OTHER NAME"}


def norm(s):
    return re.sub(r"\s+", " ", str(s)).strip()


def wiki_url(title):
    if not title:
        return ""
    return WIKI + str(title).replace(" ", "_")


def parse_polqa_answers(raw):
    """PolQA przechowuje liste odpowiedzi czasem jako liste, czasem jako
    string-reprezentacje listy (np. "['w Egipcie', 'Egipt']"). Zwraca
    (gold_answer, aliases) gdzie aliases to pozostale warianty zlaczone '|'.

    Uwaga: naiwne `raw.strip("[]'\"")` (jak w poprzedniej wersji skryptu)
    psuje ~20% odpowiedzi PolQA majacych >1 warianty (zostaje smieciowy
    fragment typu "w Egipcie', 'Egipt"), bo strip() obcina tylko krawedzie.
    """
    items = []
    if isinstance(raw, list):
        items = [norm(x) for x in raw if str(x).strip()]
    elif isinstance(raw, str):
        s = raw.strip()
        if s.startswith("[") and s.endswith("]"):
            try:
                parsed = ast.literal_eval(s)
                if isinstance(parsed, (list, tuple)):
                    items = [norm(x) for x in parsed if str(x).strip()]
            except (ValueError, SyntaxError):
                items = [norm(s.strip("[]'\""))] if s.strip("[]'\"") else []
        elif s:
            items = [norm(s)]
    if not items:
        return "", ""
    return items[0], "|".join(items[1:])


# ----------------------------------------------------------------------
# PoQuAD  (format SQuAD 2.0 + warstwa generatywna)
# ----------------------------------------------------------------------
def zbierz_poquad(limit=None):
    print("\n=== PoQuAD: pobieranie clarin-pl/poquad ===")
    ds = load_dataset("clarin-pl/poquad")
    print("Splity:", list(ds.keys()))
    przyklad = ds["train"][0]
    print("Kolumny:", list(przyklad.keys()))
    print("Przyklad rekordu:", {k: (str(v)[:120]) for k, v in przyklad.items()})

    rows = []
    seen = set()
    for split in ds.keys():
        for ex in ds[split]:
            q = norm(ex.get("question", ""))
            ctx = norm(ex.get("context", ""))
            title = ex.get("title", "")

            # answers: SQuAD-style dict {'text': [...], 'answer_start': [...], ...}
            ans = ex.get("answers", {})
            gold = ""
            if isinstance(ans, dict):
                # PoQuAD ma czasem warstwe generatywna - probujemy ja najpierw
                for key in ("generative_answer", "text"):
                    val = ans.get(key)
                    if isinstance(val, list) and val:
                        gold = norm(val[0]);  break
                    if isinstance(val, str) and val.strip():
                        gold = norm(val);  break

            # odrzucamy pytania niemozliwe (brak odpowiedzi) i puste
            if not q or not gold or not ctx:
                continue
            if q.lower() in seen:
                continue
            seen.add(q.lower())
            rows.append(dict(zrodlo="poquad", qid=f"poquad_{len(rows)}",
                             pytanie=q, gold_answer=gold, aliases="",
                             passaz=ctx[:1200], passaz_url=wiki_url(title)))
            if limit and len(rows) >= limit:
                break
        if limit and len(rows) >= limit:
            break
    print(f"PoQuAD: zebrano {len(rows)} unikalnych kandydatow")
    return rows


# ----------------------------------------------------------------------
# PolQA  (pary pytanie-passaz; wiele wierszy na pytanie)
# ----------------------------------------------------------------------
def zbierz_polqa(limit=None):
    print("\n=== PolQA: pobieranie ipipan/polqa ===")
    ds = load_dataset("ipipan/polqa")
    print("Splity:", list(ds.keys()))
    przyklad = ds["train"][0]
    cols = list(przyklad.keys())
    print("Kolumny:", cols)
    print("Przyklad rekordu:", {k: (str(v)[:120]) for k, v in przyklad.items()})

    # heurystyka nazw kolumn (dostosuj po obejrzeniu wydruku wyzej)
    col_q = next((c for c in cols if c.lower() in ("question", "pytanie")), "question")
    col_a = next((c for c in cols if c.lower() in ("answers", "answer", "odpowiedz")), None)
    col_pt = next((c for c in cols if "title" in c.lower()), None)
    col_pp = next((c for c in cols if c.lower() in ("passage_text", "passage", "context", "text")), None)
    col_rel = next((c for c in cols if c.lower() in ("relevant", "is_relevant")), None)
    col_qt = next((c for c in cols if c.lower() == "question_type"), None)
    print(f"Mapowanie -> pytanie:{col_q} odpowiedz:{col_a} passaz:{col_pp} "
          f"relevant:{col_rel} question_type:{col_qt}")

    rows = []
    seen = set()
    odrzucone_typ = 0
    for split in ds.keys():
        for ex in ds[split]:
            # bierzemy tylko passaze oznaczone jako trafne (jesli kolumna istnieje)
            if col_rel is not None:
                rv = ex.get(col_rel)
                if rv in (False, 0, "0", "False", "false", None):
                    continue
            # odcinamy z gory typy pytan bez jednoznacznej, krotkiej odpowiedzi
            # (YES/NO, ENTITY CHOICE, MULTIPLE ENTITIES, GAP FILLING - patrz
            # uzasadnienie w docstringu modulu / notatkach do tego skryptu)
            if col_qt is not None:
                if ex.get(col_qt) not in ALLOWED_POLQA_QTYPES:
                    odrzucone_typ += 1
                    continue
            q = norm(ex.get(col_q, ""))
            gold, aliasy = parse_polqa_answers(ex.get(col_a)) if col_a else ("", "")
            ctx = norm(ex.get(col_pp, "")) if col_pp else ""
            title = ex.get(col_pt, "") if col_pt else ""

            if not q or not gold:
                continue
            if q.lower() in seen:
                continue
            seen.add(q.lower())
            rows.append(dict(zrodlo="polqa", qid=f"polqa_{len(rows)}",
                             pytanie=q, gold_answer=gold, aliases=aliasy,
                             passaz=ctx[:1200], passaz_url=wiki_url(title)))
            if limit and len(rows) >= limit:
                break
        if limit and len(rows) >= limit:
            break
    print(f"PolQA: odrzucono {odrzucone_typ} przez question_type, "
          f"zebrano {len(rows)} unikalnych kandydatow")
    return rows


# ----------------------------------------------------------------------
# Filtry jakosciowe wspolne dla obu zrodel (dzialaja na polaczonym DF)
# ----------------------------------------------------------------------
def filtruj_jakosciowo(df):
    """Usuwa pytania/odpowiedzi slabo nadajace sie na krotka, jednoznaczna
    odpowiedz faktograficzna z prostym polem aliasow (patrz sekcja 4.3
    propozycji). Drukuje liczebnosci po kazdym etapie (audytowalnosc)."""
    n0 = len(df)
    print(f"\n--- filtry jakosciowe: start {n0} ---")

    ql = df["pytanie"].str.lower()
    bad_prefix = ql.str.startswith(BAD_PREFIXES)
    df = df[~bad_prefix]
    print(f"po odrzuceniu prefiksow {BAD_PREFIXES}: {len(df)}")

    ql = df["pytanie"].str.lower()
    is_jak = ql.str.startswith("jak ")
    keep_jak = ql.str.contains(JAK_REQUIRE_SUBSTR)
    df = df[~is_jak | keep_jak]
    print(f"po filtrze 'jak ...' (tylko z '{JAK_REQUIRE_SUBSTR}'): {len(df)}")

    wc = df["gold_answer"].str.split().apply(len)
    df = df[wc <= MAX_ANSWER_WORDS]
    print(f"po limicie {MAX_ANSWER_WORDS} slow w gold_answer: {len(df)}")

    df = df[~df["gold_answer"].str.contains(LIST_INDICATOR_RE, regex=True)]
    print(f"po odrzuceniu odpowiedzi-wyliczen (przecinek/i/oraz/lub): {len(df)}")

    print(f"--- filtry jakosciowe: {n0} -> {len(df)} ({len(df) / n0:.1%}) ---")
    return df.reset_index(drop=True)


if __name__ == "__main__":
    # limit = None -> wszystko; ustaw np. 2000 zeby szybciej iterowac
    wszystkie = zbierz_poquad(limit=None) + zbierz_polqa(limit=None)
    df = pd.DataFrame(wszystkie)
    print(f"\nPolaczona pula PoQuAD+PolQA: {len(df)}")

    # podstawowe filtry jakosci: krotkie, konkretne odpowiedzi
    df = df[df["gold_answer"].str.len().between(1, 80)]
    df = df[df["pytanie"].str.len().between(10, 200)]
    print(f"po filtrze dlugosci pytanie/odpowiedz: {len(df)}")

    # dedup miedzy zrodlami (PoQuAD i PolQA czasem pokrywaja te sama wiedze)
    df = df.drop_duplicates(subset=["pytanie"]).reset_index(drop=True)
    print(f"po dedupie pytan (cross-source): {len(df)}")

    df = filtruj_jakosciowo(df)

    df.to_csv(OUT_FULL, index=False, encoding="utf-8")
    print(f"\nZapisano cala przefiltrowana pule ({len(df)}) do {OUT_FULL}")

    print("\nRozkład źródeł w pełnej puli:")
    print(df["zrodlo"].value_counts())
