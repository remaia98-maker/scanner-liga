"""Gera o catalog-op.json (One Piece) do Scanner Liga.

Uso: python tools/build_catalog_op.py <pasta english do punk-records> catalog-op.json [pasta liga-op] [tcgplayer-op.json]

- Os CSVs exportados da LigaOnePiece (pasta liga-op/) são a fonte principal: edição,
  sigla, nome, raridade, cor e "Card #" saem exatamente como a Liga escreve.
- A base oficial (github.com/buhbbl/punk-records, gerada do site da Bandai) completa
  as cartas normais que ainda não aparecem nos exports. Essas entram marcadas como
  "não confirmadas" no app.
"""
import csv, glob, html, json, os, re, sys
from collections import Counter, defaultdict

PUNK = sys.argv[1]
OUT = sys.argv[2]
LIGA_DIR = sys.argv[3] if len(sys.argv) > 3 else "liga-op"
TCGP = sys.argv[4] if len(sys.argv) > 4 else None

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
    if first in home:
        return home[first]
    # Coleção nova, que ainda não está nos exports da Liga: usa o padrão de sigla da Liga
    # (OP-18, EB-05, ST30). As cartas entram como "conferir na Liga" até virem num export.
    m = re.fullmatch(r"(OP|EB|ST)(\d{2})", first)
    if not m:
        return None
    sig = f"{m.group(1)}{m.group(2)}" if m.group(1) == "ST" and int(m.group(2)) >= 14 else f"{m.group(1)}-{m.group(2)}"
    title = html.unescape((p.get("title_parts") or {}).get("title") or p["raw_title"])
    if title.isupper():       # "THE DOMINANCE OF GOD" -> "The Dominance of God"
        words = title.title().split()
        title = " ".join(w.lower() if i and w in ("Of", "The", "In", "And", "To", "A") else w for i, w in enumerate(words))
    new_sets[sig] = title
    home[first] = sig
    return sig


new_sets = {}                     # coleções novas criadas a partir da base oficial
have_base = defaultdict(set)      # sigla -> códigos-base presentes
for (sig, num) in cards:
    b = base_code(num)
    if b and num == b:
        have_base[sig].add(b)
alts = Counter()                  # código-base -> nº de artes alternativas na base oficial
alt_packs = defaultdict(list)     # código-base -> [(sufixo da arte "_p2", sigla da edição onde saiu)]
added, skipped = 0, Counter()
for cid, c in official.items():
    b = cid.split("_")[0]
    if "_" in cid:
        alts[b] += 1
        alt_packs[b].append(("_" + cid.split("_", 1)[1], pack_sig(c.get("pack_id"))))
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
        sets[sig] = new_sets.get(sig) or html.unescape(packs[c["pack_id"]]["raw_title"])
        order.append(sig)
    cards[(sig, b)] = [sig, b, c["name"], rar, cor, 0]
    have_base[sig].add(b)
    added += 1
print(f"Base oficial: {added} cartas acrescentadas; fora do mapa: {dict(skipped)}")
if new_sets:
    print("Coleções novas (sigla provisória, conferir na Liga):", new_sets)

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
# 3a. Arte de cada versão: a arte alternativa oficial (OP07-038_p2) que saiu na mesma edição da
#     versão na Liga (ex.: a SPR da EB-02). Na edição de origem, se a carta só tem uma arte
#     alternativa, é ela (_p1). Promos (PC-01) ficam de fora: lá a mesma carta tem várias versões
#     de evento com a mesma arte, e a base oficial não diz qual é qual.
arts = {}
for key, row in cards.items():
    sig, num = row[0], row[1]
    b = base_code(num)
    if not b or sig == "PC-01" or not alt_packs.get(b):
        continue
    is_home = sig == home.get(b.split("-")[0])
    if num == b and is_home:
        continue                                  # a carta normal da edição de origem
    same = [suf for suf, s in alt_packs[b] if s == sig]
    if len(same) == 1:
        arts[key] = same[0]
    elif not same and is_home and num != b and alts[b] == 1:
        arts[key] = alt_packs[b][0][0]
# Promos: só o caso seguro, uma única versão "Alternate Art" na Liga e uma única arte alternativa
# oficial lançada fora das coleções (promo ou "Other Product Card").
promo_aa = defaultdict(list)
for key, row in cards.items():
    b = base_code(row[1])
    if row[0] == "PC-01" and b and row[1] != b and (row[1].endswith("-AA") or "alternate art" in row[2].lower()):
        promo_aa[b].append(key)
for b, keys in promo_aa.items():
    offs = [suf for suf, sg in alt_packs.get(b, []) if sg in (None, "PC-01")]
    if len(keys) == 1 and len(offs) == 1:
        arts[keys[0]] = offs[0]
print(f"Artes alternativas oficiais ligadas às versões: {len(arts)}")

# ---------------------------------------------------------------------------
# 3b. Miniaturas: código do produto no TCGplayer (a imagem da Bandai não abre fora do site deles).
#    Cada carta pega o produto com o mesmo código impresso cujas etiquetas entre parênteses
#    (Parallel, Manga, SP, Pre-Release...) mais se parecem com as do nome da Liga.
TAG_RE = re.compile(r"\(([^)]*)\)")
SUFFIX_TAGS = {"PA": "parallel", "AA": "parallel", "MA": "manga", "SP": "sp", "PR": "pre-release"}


def tags_of(name, num=""):
    t = {x.strip().lower() for x in TAG_RE.findall(name or "") if x.strip() and not x.strip().isdigit()}
    suf = num[len(base_code(num) or num):].strip("-")
    for part in suf.split("-"):
        if part in SUFFIX_TAGS:
            t.add(SUFFIX_TAGS[part])
    # palavras soltas, sem pontuação: "Mini Case Set Vol. 3 Ryuda Artwork" -> mini, case, set, vol, 3, ryuda...
    words = {w for x in t for w in re.findall(r"[a-z0-9]+", x)}
    return words - {"op", "p"}


pids = {}
if TCGP and os.path.exists(TCGP):
    by_num = defaultdict(list)
    for gname, num, pname, pid in json.load(open(TCGP, encoding="utf-8")):
        by_num[num].append((tags_of(pname), pid))
    hits = 0
    for key, row in cards.items():
        b = base_code(row[1])
        cands = by_num.get(b) or []
        if not cands:
            continue
        want = tags_of(row[2], row[1])
        best = max(cands, key=lambda c: (len(want & c[0]) * 2 - len(c[0] - want), -c[1]))
        pids[key] = best[1]
        hits += 1
    print(f"TCGplayer: miniatura para {hits} de {len(cards)} cartas")
else:
    print("TCGplayer: sem o arquivo do TCGCSV, as cartas ficam sem código de produto")

# ---------------------------------------------------------------------------
# 4. Saída compacta
idx = {s: i for i, s in enumerate(order)}
count = Counter(row[0] for row in cards.values())
out_sets = [[s, sets[s], kind(s, sets[s]), count[s]] for s in order]
def out_row(k, r):
    row = [idx[r[0]], r[1], r[2], r[3], r[4], r[5]]
    if k in arts:
        row += [pids.get(k, 0), arts[k]]          # [..., código TCGplayer, arte "_p2"]
    elif k in pids:
        row += [pids[k]]
    return row


out_cards = sorted((out_row(k, r) for k, r in cards.items()), key=lambda r: (r[0], r[1]))
out = {"game": "op", "sets": out_sets, "home": home, "cards": out_cards,
       "alts": {k: v for k, v in alts.items()}}
with open(OUT, "w", encoding="utf-8") as fh:
    json.dump(out, fh, ensure_ascii=False, separators=(",", ":"))
print(f"{OUT}: {len(out_cards)} cartas em {len(out_sets)} edições "
      f"({sum(1 for r in out_cards if r[5])} confirmadas na Liga)")
