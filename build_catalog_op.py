"""Gera o catalog-op.json (One Piece) do Scanner Liga.

Uso: python tools/build_catalog_op.py <pasta english do punk-records> catalog-op.json [pasta liga-op]

- Os CSVs exportados da LigaOnePiece (pasta liga-op/) são a fonte principal: edição,
  sigla, nome, raridade, cor e "Card #" saem exatamente como a Liga escreve.
- A base oficial (github.com/buhbbl/punk-records, gerada do site da Bandai) completa
  as cartas normais que ainda não aparecem nos exports. Essas entram marcadas como
  "não confirmadas" no app.
"""
import csv, glob, json, os, re, sys
from collections import Counter, defaultdict

PUNK = sys.argv[1]
OUT = sys.argv[2]
LIGA_DIR = sys.argv[3] if len(sys.argv) > 3 else "liga-op"

RARITY = {"Common": "C", "Uncommon": "U", "Rare": "R", "SuperRare": "SR", "Leader": "L",
          "SecretRare": "SCR", "Special": "SP", "Promo": "P", "TreasureRare": "TR"}
COLOR = {"Red": "R", "Green": "G", "Blue": "U", "Purple": "P", "Black": "B", "Yellow": "Y"}
BASE_RE = re.compile(r"^((?:[A-Z]+\d*|P)-\d{3})")
EVENT_RE = re.compile(r"-(PR|RE|TA|\d)$")

# Coleção da base oficial -> sigla da Liga, quando o nome não bate direto
PACK_MAP = {"PRB01": "PRB", "PRB02": "PRB2", "OP14": "OP-14", "OP15": "OP-15"}


def base_code(num):
    m = BASE_RE.match(num or "")
    return m.group(1) if m else None


def squash(s):
    return re.sub(r"[^A-Z0-9]", "", (s or "").upper())


# ---------------------------------------------------------------------------
# 1. Exports da Liga
sets, cards = {}, {}          # sigla -> [nome EN, tipo] ; (sigla, card#) -> linha
order = []
files = sorted(glob.glob(os.path.join(LIGA_DIR, "*.csv")))
for f in files:
    raw = open(f, "rb").read()
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:      # a Liga às vezes exporta em Windows-1252
        text = raw.decode("cp1252")
    if True:
        rd = csv.reader(text.splitlines())
        next(rd, None)
        for r in rd:
            if len(r) < 12 or not r[2].strip() or not r[11].strip():
                continue
            sig, ed_en, name, rar, cor, num = r[2].strip(), r[1].strip(), r[4].strip(), r[8].strip(), r[9].strip(), r[11].strip()
            if sig not in sets:
                sets[sig] = ed_en
                order.append(sig)
            key = (sig, num)
            if key not in cards:
                cards[key] = [sig, num, name, rar, cor, 1]
print(f"Liga: {len(files)} arquivo(s), {len(sets)} edições, {len(cards)} cartas")


def kind(sig, name):
    n = name.lower()
    if EVENT_RE.search(sig) and re.search(r"pre-release|release event|tournament|anniversary", n):
        return "event"
    if sig.startswith("PC-") or sig in ("OP-AS",) or "promotion" in n:
        return "promo"
    return "set"


# Edição "de origem" de cada prefixo de código (OP07 -> OP-07, ST14 -> ST14, EB04 -> EB-04)
home = {}
for sig in order:
    if kind(sig, sets[sig]) != "set":
        continue
    sq = squash(sig)
    if re.fullmatch(r"(OP|ST|EB)\d{2}", sq) and sq not in home:
        home[sq] = sig
home.setdefault("P", "PC-01")

# ---------------------------------------------------------------------------
# 2. Base oficial: completa as cartas normais que faltam
packs = json.load(open(os.path.join(PUNK, "packs.json"), encoding="utf-8"))
official = json.load(open(os.path.join(PUNK, "index", "cards_by_id.json"), encoding="utf-8"))


def pack_sig(pid):
    p = packs.get(pid)
    if not p:
        return None
    label = (p.get("title_parts") or {}).get("label") or ""
    if "promotion" in p["raw_title"].lower():
        return "PC-01"
    first = squash(label.split("-EB")[0]) if "-EB" in label else squash(label)
    if first in PACK_MAP:
        return PACK_MAP[first]
    return home.get(first)


have_base = defaultdict(set)      # sigla -> códigos-base presentes
for (sig, num) in cards:
    b = base_code(num)
    if b and num == b:
        have_base[sig].add(b)
alts = Counter()                  # código-base -> nº de artes alternativas na base oficial
added, skipped = 0, Counter()
for cid, c in official.items():
    b = cid.split("_")[0]
    if "_" in cid:
        alts[b] += 1
        continue
    sig = pack_sig(c.get("pack_id"))
    if not sig:
        skipped[packs.get(c.get("pack_id"), {}).get("raw_title", c.get("pack_id"))] += 1
        continue
    if b in have_base[sig]:
        continue
    cols = c.get("colors") or []
    cor = COLOR.get(cols[0], "") if len(cols) == 1 else ("M" if cols else "")
    rar = RARITY.get(c.get("rarity"), "")
    if c.get("category") == "Leader":
        rar = "L"
    if sig not in sets:
        sets[sig] = packs[c["pack_id"]]["raw_title"]
        order.append(sig)
    cards[(sig, b)] = [sig, b, c["name"], rar, cor, 0]
    have_base[sig].add(b)
    added += 1
print(f"Base oficial: {added} cartas acrescentadas; fora do mapa: {dict(skipped)}")

# Nome repetido na mesma edição: a Liga acrescenta o número, ex. "Boa Hancock (038)"
by_set_name = defaultdict(list)
for k, row in cards.items():
    if row[1] == base_code(row[1]):
        by_set_name[(row[0], re.sub(r" \(\d+\)$", "", row[2]))].append(row)
for (sig, name), rows in by_set_name.items():
    if len(rows) > 1:
        for row in rows:
            if not row[5]:
                row[2] = f"{name} ({row[1][-3:]})"

# ---------------------------------------------------------------------------
# 3. Saída compacta
idx = {s: i for i, s in enumerate(order)}
count = Counter(row[0] for row in cards.values())
out_sets = [[s, sets[s], kind(s, sets[s]), count[s]] for s in order]
out_cards = sorted(([idx[r[0]], r[1], r[2], r[3], r[4], r[5]] for r in cards.values()), key=lambda r: (r[0], r[1]))
out = {"game": "op", "sets": out_sets, "home": home, "cards": out_cards,
       "alts": {k: v for k, v in alts.items()}}
with open(OUT, "w", encoding="utf-8") as fh:
    json.dump(out, fh, ensure_ascii=False, separators=(",", ":"))
print(f"{OUT}: {len(out_cards)} cartas em {len(out_sets)} edições "
      f"({sum(1 for r in out_cards if r[5])} confirmadas na Liga)")
