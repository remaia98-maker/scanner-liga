"""Gera o catalog.json do Scanner Liga.

Uso: python tools/build_catalog.py <pasta data do tcgdex/cards-database> catalog.json [pasta com exports da Liga]

Os CSVs exportados da LigaPokemon (pasta liga/) servem para usar os nomes e siglas
exatos da Liga nas cartas que aparecem neles.
"""
import csv, glob, json, os, re, sys

ROOT = sys.argv[1]
OUT = sys.argv[2]
SKIP_SERIES = {"Pokémon TCG Pocket", "Trainer kits", "McDonald's Collection"}

COLOR = {"Colorless": "C", "Darkness": "D", "Dragon": "O", "Fighting": "F", "Fire": "R",
         "Grass": "G", "Lightning": "L", "Metal": "M", "Psychic": "P", "Water": "W", "Fairy": "Y"}
RARITY = {"Common": "C", "Uncommon": "U"}


def block(src, key):
    m = re.search(r"\b" + key + r"\s*:\s*\{(.*?)\}", src, re.S)
    return m.group(1) if m else ""


def langval(blk, lang):
    m = re.search(r"\b" + lang + r"\s*:\s*([\"'])(.*?)(?<!\\)\1", blk, re.S)
    return m.group(2).replace("\\'", "'").replace('\\"', '"') if m else None


def scalar(src, key):
    m = re.search(r"\b" + key + r"\s*:\s*([\"'])(.*?)\1", src)
    return m.group(2) if m else None


sets_out, cards_out = [], {}
for serie in sorted(os.listdir(ROOT)):
    sdir = os.path.join(ROOT, serie)
    if not os.path.isdir(sdir) or serie in SKIP_SERIES:
        continue
    for f in sorted(os.listdir(sdir)):
        if not f.endswith(".ts"):
            continue
        setname = f[:-3]
        cdir = os.path.join(sdir, setname)
        if not os.path.isdir(cdir):
            continue
        src = open(os.path.join(sdir, f), encoding="utf-8").read()
        sid = scalar(src, "id")
        nm = block(src, "name")
        en = langval(nm, "en") or setname
        pt = langval(nm, "pt") or ""
        cc = re.search(r"official\s*:\s*(\d+)", block(src, "cardCount"))
        official = int(cc.group(1)) if cc else 0
        abbr = langval(block(src, "abbreviations"), "official")
        tcgo = scalar(src, "tcgOnline")
        sig = (abbr or tcgo or "").upper()
        rel = scalar(src, "releaseDate") or ""
        cards = []
        for cf in os.listdir(cdir):
            if not cf.endswith(".ts"):
                continue
            lid = cf[:-3]
            csrc = open(os.path.join(cdir, cf), encoding="utf-8").read()
            cn = block(csrc, "name")
            cen = langval(cn, "en")
            if not cen:
                continue
            cpt = langval(cn, "pt") or ""
            rar = RARITY.get(scalar(csrc, "rarity") or "", "")
            cat = scalar(csrc, "category") or ""
            tm = re.search(r"types\s*:\s*\[\s*[\"'](\w+)", csrc)
            col = COLOR.get(tm.group(1), "") if tm else ""
            if cat == "Energy":
                col = "E"
            elif cat == "Trainer":
                col = "C"
            row = [lid, cen]
            row.append(cpt if cpt and cpt != cen else "")
            row += [rar, col]
            cards.append(row)
        if not cards:
            continue
        def keyf(r):
            d = re.sub(r"\D", "", r[0])
            return (int(d) if d else 9999, r[0])
        cards.sort(key=keyf)
        sets_out.append([sid, en, pt if pt != en else "", sig, official, rel, serie])
        cards_out[sid] = cards

sets_out.sort(key=lambda s: s[5], reverse=True)

# ---------------------------------------------------------------------------
# Dados da Liga: cada CSV exportado da LigaPokemon (pasta liga/) corrige siglas,
# nomes e números das coleções que aparecem nele. Coleções que não existem no
# TCGdex entram no catálogo só com os dados da Liga.
# ---------------------------------------------------------------------------
import unicodedata


def fold(t):
    return "".join(ch for ch in unicodedata.normalize("NFD", t or "") if unicodedata.category(ch) != "Mn")


def key(t):
    t = fold(t).lower().replace("&", " and ")
    return re.sub(r"[^a-z0-9]+", "", t)


def tokens(t):
    t = fold(t).lower().replace("&", " and ")
    return set(w for w in re.split(r"[^a-z0-9]+", t) if w and w not in {"and", "the", "of", "pokemon", "tcg", "set"})


def nnum(n):
    n = (n or "").upper().replace(" ", "")
    m = re.match(r"^([A-Z]*)0*(\d+)([A-Z]*)$", n)
    return m.group(1) + m.group(2) + m.group(3) if m else n


liga_dir = sys.argv[3] if len(sys.argv) > 3 else None
liga_rows = {}          # sigla da Liga -> {"pt","en","tot","cards": {nnum: row}}
manual = {}             # sigla da Liga -> id do TCGdex (liga/mapa-colecoes.csv)
if liga_dir:
    for path in sorted(glob.glob(os.path.join(liga_dir, "*.csv"))):
        with open(path, encoding="utf-8-sig") as fh:
            rows = list(csv.reader(fh))
        if not rows:
            continue
        if os.path.basename(path).lower().startswith("mapa"):
            for r in rows[1:]:
                if len(r) >= 2 and r[0].strip() and r[1].strip():
                    manual[r[0].strip().upper()] = r[1].strip()
            continue
        for r in rows[1:]:
            if len(r) < 14 or not r[2].strip() or not r[11].strip():
                continue
            sig = r[2].strip().upper()
            st = liga_rows.setdefault(sig, {"pt": r[0], "en": r[1], "tot": r[13], "cards": {}})
            st["cards"][nnum(r[11])] = [r[3], r[4], r[8], r[9], r[11].strip()]

by_id = {s[0]: s for s in sets_out}
by_name = {}
for s in sets_out:
    by_name.setdefault(key(s[1]), s)
by_sig = {}
for s in sets_out:
    if s[3]:
        by_sig.setdefault(s[3], s)

liga, liga_sets, report = {}, {}, []
for sig, st in sorted(liga_rows.items()):
    tot = int(st["tot"]) if st["tot"].isdigit() else 0
    target, how = None, ""
    if sig in manual and manual[sig] in by_id:
        target, how = by_id[manual[sig]], "mapa"
    elif key(st["en"]) in by_name:
        target, how = by_name[key(st["en"])], "nome"
    elif sig in by_sig:
        target, how = by_sig[sig], "sigla"
    else:
        lt = tokens(st["en"])
        best, bscore = None, 0.0
        for s in sets_out:
            tt = tokens(s[1])
            if not lt or not tt:
                continue
            score = len(lt & tt) / len(lt | tt)
            if tot and s[4] == tot:
                score += 0.25
            if score > bscore:
                best, bscore = s, score
        if best and bscore >= 0.6:
            target, how = best, "aproximado"

    if target is None:
        # Coleção que só existe na Liga: entra com os dados dela
        sid = "liga-" + sig.lower()
        cards = []
        for nn, c in st["cards"].items():
            cards.append([c[4], fold(c[1] or c[0]), fold(c[0]) if c[0] != c[1] else "", c[2], c[3]])
        cards.sort(key=lambda r: (int(re.sub(r"\D", "", r[0]) or 9999), r[0]))
        sets_out.append([sid, fold(st["en"] or st["pt"]), fold(st["pt"]) if st["pt"] != st["en"] else "", sig, tot, "", "Liga"])
        cards_out[sid] = cards
        target, how = sets_out[-1], "so na Liga"
    else:
        # Cartas que a Liga tem e o TCGdex não tem nessa coleção
        have = {nnum(c[0]) for c in cards_out[target[0]]}
        for nn, c in st["cards"].items():
            if nn not in have:
                cards_out[target[0]].append([c[4], fold(c[1] or c[0]), fold(c[0]) if c[0] != c[1] else "", c[2], c[3]])

    sid = target[0]
    while len(target) < 8:
        target.append("")
    target[7] = sig
    liga_sets[sid] = [st["pt"], st["en"]]
    for nn, c in st["cards"].items():
        liga[sid + "|" + nn] = c
    report.append(f"{sig:8} -> {sid:16} ({how}) {len(st['cards'])} cartas")

# Siglas do mapa que não apareceram em nenhum export: aplica só a sigla
done = {r.split()[0] for r in report}
for sig, sid in sorted(manual.items()):
    if sig in done:
        continue
    if sid not in by_id:
        report.append(f"{sig:8} -> {sid:16} (mapa) id nao encontrado no TCGdex")
        continue
    t = by_id[sid]
    while len(t) < 8:
        t.append("")
    t[7] = sig
    report.append(f"{sig:8} -> {sid:16} (mapa)")

# Sigla do TCGdex que a Liga usa para outra coleção (ex.: TR = Team Rocket na Liga,
# mas Team Rocket Returns no TCGdex): apaga a do TCGdex para não exportar errado
claimed = {t[7]: t[0] for t in sets_out if len(t) > 7 and t[7]}
for t in sets_out:
    if t[3] in claimed and claimed[t[3]] != t[0]:
        report.append(f"{t[3]:8} removida de {t[0]} ({t[1]}): na Liga e de {claimed[t[3]]}")
        t[3] = ""

json.dump({"v": 2, "sets": sets_out, "cards": cards_out, "ligaSets": liga_sets, "liga": liga}, open(OUT, "w", encoding="utf-8"),
          ensure_ascii=False, separators=(",", ":"))
print(len(sets_out), "colecoes", sum(len(v) for v in cards_out.values()), "cartas")
print(len(liga), "cartas com dados da Liga")
print("\n".join(report))
