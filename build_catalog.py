"""Gera o catalog.json do Scanner Liga.

Uso: python tools/build_catalog.py <pasta data do tcgdex/cards-database> catalog.json [pasta liga] [tcgplayer-jp.json]

Os CSVs exportados da LigaPokemon (pasta liga/) servem para usar os nomes e siglas
exatos da Liga nas cartas que aparecem neles.
"""
import csv, glob, html, io, json, os, re, sys

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
images = {}  # id da coleção -> caminho das imagens oficiais em assets.tcgdex.net ("en/sv/sv03.5")


def serie_id(path, fallback):
    try:
        m = re.search(r"^\tid:\s*[\"']([^\"']+)", open(path, encoding="utf-8").read(), re.M)
        return m.group(1) if m else fallback
    except OSError:
        return fallback
intl = []   # (set_id, numero, dexIds, nome_en, categoria) para traduzir as cartas japonesas
DEX_RE = re.compile(r"dexId\s*:\s*\[([\d,\s]+)\]")
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
            dm = DEX_RE.search(csrc)
            intl.append((sid, lid, tuple(int(x) for x in dm.group(1).split(",") if x.strip()) if dm else (), cen, cat))
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
        images[sid] = "en/%s/%s" % (serie_id(os.path.join(ROOT, serie + ".ts"), serie), sid)
        cards_out[sid] = cards


# ---------------------------------------------------------------------------
# Coleções japonesas (data-asia do TCGdex), da era Black & White em diante,
# que imprimem o código da coleção na carta (ex.: "SV2a 063/165").
# O TCGdex só tem os nomes em japonês; o nome em inglês é montado aqui.
# ---------------------------------------------------------------------------
from collections import Counter, defaultdict

ASIA = os.path.join(os.path.dirname(os.path.abspath(ROOT)), "data-asia")
JP_SERIES = ["BW", "XY", "SM", "S", "SV", "M"]

SUFFIX_EN = r"(?:\s+(?:ex|EX|GX|V|VMAX|VSTAR|V-UNION|BREAK|LV\.X|Lv\.X|Prime|LEGEND|δ|☆|◇|Star)|-EX|-GX)$"
SKIP_PREFIX = ("Mega ", "Dark ", "Light ", "Radiant ", "Alolan ", "Galarian ", "Hisuian ", "Paldean ", "Shining ", "Shadow ")
species = defaultdict(Counter)
owner_en = defaultdict(Counter)   # dexId -> dono em inglês ("Ethan")
for _sid, _lid, dex, en, cat in intl:
    if cat != "Pokemon" or len(dex) != 1:
        continue
    m = re.match(r"^(.+?)'s (.+)$", en)
    if m:
        owner_en[dex[0]][m.group(1)] += 1
        continue
    if en.startswith(SKIP_PREFIX) or "&" in en:
        continue
    base = en
    while True:
        nb = re.sub(SUFFIX_EN, "", base).strip()
        if nb == base:
            break
        base = nb
    species[dex[0]][base] += 1
SPECIES = {d: c.most_common(1)[0][0] for d, c in species.items()}

JP_PREFIX = [("かがやく", "Radiant "), ("メガ", "Mega "), ("アローラ", "Alolan "), ("ガラル", "Galarian "),
             ("ヒスイ", "Hisuian "), ("パルデア", "Paldean ")]
JP_SUFFIX = [("VSTAR", " VSTAR"), ("VMAX", " VMAX"), ("VUNION", " V-UNION"), ("BREAK", " BREAK"),
             ("ex", " ex"), ("EX", " EX"), ("GX", " GX"), ("V", " V"), ("◇", " ◇")]
ENERGY = {"草": "Grass", "炎": "Fire", "水": "Water", "雷": "Lightning", "超": "Psychic", "闘": "Fighting",
          "悪": "Darkness", "鋼": "Metal", "フェアリー": "Fairy"}
JP_RARITY = {"Common": "C", "Uncommon": "U"}

jp_cards = []   # (set_id, numero, dexIds, ja, categoria)
jp_sets = []
for serie in JP_SERIES:
    sdir = os.path.join(ASIA, serie)
    if not os.path.isdir(sdir):
        continue
    for f in sorted(os.listdir(sdir)):
        if not f.endswith(".ts"):
            continue
        code = f[:-3]
        cdir = os.path.join(sdir, code)
        if not os.path.isdir(cdir):
            continue
        src = open(os.path.join(sdir, f), encoding="utf-8").read()
        nb = block(src, "name")
        sname = langval(nb, "ja") or langval(nb, "en") or code
        cc = re.search(r"official\s*:\s*(\d+)", block(src, "cardCount"))
        rb = block(src, "releaseDate")
        rel = langval(rb, "ja") or langval(rb, "id") or langval(rb, "th") or scalar(src, "releaseDate") or ""
        sid = "jp-" + code
        rows = []
        for cf in os.listdir(cdir):
            if not cf.endswith(".ts"):
                continue
            csrc = open(os.path.join(cdir, cf), encoding="utf-8").read()
            ja = langval(block(csrc, "name"), "ja")
            if not ja:
                continue
            cat = scalar(csrc, "category") or ""
            dm = DEX_RE.search(csrc)
            dex = tuple(int(x) for x in dm.group(1).split(",") if x.strip()) if dm else ()
            tm = re.search(r"types\s*:\s*\[\s*[\"'](\w+)", csrc)
            col = "E" if cat == "Energy" else "C" if cat == "Trainer" else (COLOR.get(tm.group(1), "") if tm else "")
            rows.append([cf[:-3], ja, cat, dex, JP_RARITY.get(scalar(csrc, "rarity") or "", ""), col])
            jp_cards.append((sid, cf[:-3], dex, ja, cat))
        if rows:
            jp_sets.append((sid, code, sname, int(cc.group(1)) if cc else 0, rel, rows))
            images[sid] = "ja/%s/%s" % (serie_id(os.path.join(ASIA, serie + ".ts"), serie), code)

# Dono ("ヒビキの" -> "Ethan's"): cruza cartas com o mesmo dexId nos dois idiomas
owner_votes = defaultdict(Counter)
for _s, _n, dex, ja, cat in jp_cards:
    m = re.match(r"^(.+?)の(.+)$", ja)
    if cat == "Pokemon" and len(dex) == 1 and m and dex[0] in owner_en:
        for o, n in owner_en[dex[0]].items():
            owner_votes[m.group(1)][o] += n
OWNERS = {"ロケット団": "Team Rocket"}
for ja_o, c in owner_votes.items():
    OWNERS.setdefault(ja_o, c.most_common(1)[0][0])

# Treinadores mais comuns. A numeração das coleções japonesas não bate com a das
# internacionais nos treinadores, então os nomes vêm desta lista (complete à vontade).
TRAINER = {
    "ポケモンいれかえ": "Switch", "ハイパーボール": "Ultra Ball", "ふしぎなアメ": "Rare Candy",
    "博士の研究": "Professor's Research", "ボスの指令": "Boss's Orders", "ネストボール": "Nest Ball",
    "ジャッジマン": "Judge", "ポケモンキャッチャー": "Pokémon Catcher", "リーリエ": "Lillie",
    "ポケギア3.0": "Pokégear 3.0", "改造ハンマー": "Enhanced Hammer", "ネモ": "Nemona",
    "なかよしポフィン": "Buddy-Buddy Poffin", "あなぬけのヒモ": "Escape Rope", "カウンターゲイン": "Counter Gain",
    "ダブル無色エネルギー": "Double Colorless Energy", "こだわりハチマキ": "Choice Band", "ペパー": "Arven",
    "ナンジャモ": "Iono", "アカマツ": "Crispin", "なぞの化石": "Mysterious Fossil", "クラッシュハンマー": "Crushing Hammer",
    "キバナ": "Raihan", "夜のタンカ": "Night Stretcher", "エリカの招待": "Erika's Invitation",
    "サカキのカリスマ": "Giovanni's Charisma", "ナナミの手助け": "Daisy's Help", "マサキの転送": "Bill's Transfer",
    "サイクリングロード": "Cycling Road", "たべのこし": "Leftovers", "ガチガチバンド": "Extra-tight Band",
    "大きなふうせん": "Big Balloon", "安全ゴーグル": "Protective Goggles", "スナッチアーム": "Grabber",
    "エネルギーシール": "Energy Sticker", "古びたかいの化石": "Antique Helix Fossil", "古びたこうらの化石": "Antique Dome Fossil",
}

def jp_to_en(ja, cat, dex):
    if ja in TRAINER:
        return TRAINER[ja]
    m = re.match(r"^基本(.+)エネルギー$", ja)
    if m and m.group(1) in ENERGY:
        return ENERGY[m.group(1)] + " Energy"
    if cat != "Pokemon" or not dex or any(d not in SPECIES for d in dex):
        return None
    name, pre, suf = ja, "", ""
    m = re.match(r"^(.+?)の(.+)$", name)
    if m:
        if m.group(1) not in OWNERS:
            return None
        pre, name = OWNERS[m.group(1)] + "'s ", m.group(2)
    for j, e in JP_PREFIX:
        if name.startswith(j):
            pre, name = pre + e, name[len(j):]
            break
    for j, e in JP_SUFFIX:
        if name.endswith(j):
            suf, name = e, name[: -len(j)]
            break
    return pre + " & ".join(SPECIES[d] for d in dex) + suf

jp_total = jp_named = 0
taken = {s[3] for s in sets_out if s[3]}
for sid, code, sname, official, rel, rows in jp_sets:
    out = []
    for lid, ja, cat, dex, rar, col in rows:
        en = jp_to_en(ja, cat, dex)
        jp_total += 1
        jp_named += 1 if en else 0
        out.append([lid, en or "", "", rar, col, ja])
    out.sort(key=lambda r: (int(re.sub(r"\D", "", r[0]) or 9999), r[0]))
    sig = code.upper()
    sets_out.append([sid, sname, "", sig if sig not in taken else "", official, rel, "Japão", "", code])
    cards_out[sid] = out
print(f"japonesas: {len(jp_sets)} colecoes, {jp_total} cartas, {jp_named} com nome em ingles")

# ---------------------------------------------------------------------------
# Nomes em inglês das japonesas pelo TCGplayer (arquivo gerado por
# tools/fetch_tcgplayer_jp.py). Substitui a tradução automática e acrescenta
# coleções japonesas que o TCGdex não tem.
# ---------------------------------------------------------------------------
TCGP = sys.argv[4] if len(sys.argv) > 4 else ""
if TCGP and os.path.exists(TCGP):
    tdata = json.load(open(TCGP, encoding="utf-8"))

    def tkey(t):
        return re.sub(r"[^a-z0-9]", "", (t or "").lower())

    def tnum(n):
        first = (n or "").split("/")[0].strip()
        m = re.match(r"^([A-Za-z-]*?)0*(\d+)([A-Za-z]*)$", first)
        return (m.group(1).replace("-", "").upper() + m.group(2) + m.group(3).upper()) if m else first.upper()

    def tclean(name):
        name = re.sub(r"\s+-\s+[A-Za-z0-9]*\d+/[A-Za-z0-9-]+$", "", name or "")
        while True:
            n2 = re.sub(r"\s*\([^()]*\)\s*$", "", name)
            if n2 == name or not n2:
                break
            name = n2
        return name.strip()

    jp_by_code = {tkey(s2[8]): s2 for s2 in sets_out if len(s2) > 8 and s2[8]}
    jp_list = [s2 for s2 in sets_out if s2[6] == "Japão"]
    existing_sigs = {s2[3] for s2 in sets_out if s2[3]}
    replaced = matched = added = 0
    for g in tdata.get("groups", []):
        m = re.match(r"^([A-Za-z0-9.+-]{2,10})\s*:\s*(.+)$", g["name"])
        code = (g.get("abbr") or (m.group(1) if m else "")).strip()
        title = m.group(2).strip() if m else g["name"]
        names = {}
        tots = Counter()
        for numero, nome, rar, _pid in g["cards"]:
            k = tnum(numero)
            limpo = tclean(nome)
            if k not in names or len(limpo) < len(names[k]):
                names[k] = limpo
            if "/" in numero and numero.split("/")[1].strip().isdigit():
                tots[int(numero.split("/")[1])] += 1
        total = tots.most_common(1)[0][0] if tots else 0
        target = jp_by_code.get(tkey(code)) if code else None
        if target is None:
            best, bscore = None, 0.0
            for s2 in jp_list:
                if total and s2[4] and s2[4] != total:
                    continue
                pairs = [(c[1], names.get(tnum(c[0]))) for c in cards_out[s2[0]] if c[1] and names.get(tnum(c[0]))]
                if len(pairs) < 5:
                    continue
                score = sum(1 for a, b in pairs if tkey(a) == tkey(b)) / len(pairs)
                if score > bscore:
                    best, bscore = s2, score
            if best and bscore >= 0.6:
                target = best
        if target is not None:
            matched += 1
            for c in cards_out[target[0]]:
                en = names.get(tnum(c[0]))
                if en and en != c[1]:
                    c[1] = en
                    replaced += 1
            continue
        # Coleção japonesa que o TCGdex não tem
        sid = "tcgp-" + str(g["id"])
        rows = []
        for numero, nome, rar, _pid in g["cards"]:
            lid = numero.split("/")[0].strip()
            if any(r[0] == lid for r in rows):
                continue
            rows.append([lid, tclean(nome), "", JP_RARITY.get(rar, ""), "", "", _pid])
        rows.sort(key=lambda r: (int(re.sub(r"\D", "", r[0]) or 9999), r[0]))
        sig = code.upper() if code and code.upper() not in existing_sigs else ""
        if sig:
            existing_sigs.add(sig)
        sets_out.append([sid, title, "", sig, total, g.get("date", ""), "Japão", "", code])
        cards_out[sid] = rows
        added += 1
    print(f"TCGplayer: {matched} colecoes japonesas com nome em ingles atualizado ({replaced} cartas), {added} colecoes novas")
elif TCGP:
    print("TCGplayer: arquivo nao encontrado, seguindo sem os nomes do TCGplayer")

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
liga_rows = {}          # sigla da Liga (maiúsculas) -> dados da coleção
manual = {}             # sigla da Liga -> id do catálogo (liga/mapa-colecoes.csv)


def read_csv_rows(path):
    """Lê o CSV aceitando UTF-8 e linhas em Windows-1252 (arquivos salvos no Excel)."""
    data = open(path, "rb").read()
    if data.startswith(b"\xef\xbb\xbf"):
        data = data[3:]
    lines = []
    for ln in data.split(b"\n"):
        try:
            lines.append(ln.decode("utf-8"))
        except UnicodeDecodeError:
            lines.append(ln.decode("cp1252"))
    return [r for r in csv.reader(io.StringIO("\n".join(lines))) if r]


NUM_RE = re.compile(r"^([A-Za-z]*)(\d+)([A-Za-z]*)$")


def num_format(nums):
    """Descobre como a Liga escreve os números de uma coleção: zeros à esquerda e sufixo."""
    parts = [NUM_RE.match(n) for n in nums]
    parts = [m for m in parts if m]
    suffix = ""
    sufs = {m.group(3) for m in parts}
    if parts and len(sufs) == 1:
        suffix = sufs.pop()
    plain = [m.group(2) for m in parts if not m.group(1)]
    lz = [len(d) for d in plain if len(d) > 1 and d[0] == "0"]
    if lz:
        pad = max(lz)
    elif any(len(d) <= 2 for d in plain):
        pad = 0
    else:
        pad = -1
    return suffix, pad


if liga_dir:
    for path in sorted(glob.glob(os.path.join(liga_dir, "*.csv"))):
        rows = read_csv_rows(path)
        if not rows:
            continue
        if os.path.basename(path).lower().startswith("mapa"):
            for r in rows[1:]:
                if len(r) >= 2 and r[0].strip() and r[1].strip():
                    manual[r[0].strip().upper()] = (r[0].strip(), r[1].strip())
            continue
        for r in rows[1:]:
            if len(r) < 14 or not r[2].strip() or not r[11].strip():
                continue
            raw = r[2].strip()          # a Liga diferencia maiúsculas: "sv1V", "SVPJp"
            sig = raw.upper()
            r = [fold(html.unescape(x)).strip() for x in r]
            st = liga_rows.setdefault(sig, {"raw": raw, "pt": r[0], "en": r[1] or r[0], "tot": r[13], "cards": {}, "nums": []})
            if r[0] and not st["pt"]:
                st["pt"] = r[0]
            st["nums"].append(r[11])
            st["cards"][r[11]] = [r[3] or r[4], r[4] or r[3], r[8], r[9], r[11]]

for st in liga_rows.values():
    st["suffix"], st["pad"] = num_format(st["nums"])
    # chave de cada carta: número sem o sufixo da coleção ("044JP" -> "44")
    suf = st["suffix"]
    st["cards"] = {nnum(n[: len(n) - len(suf)] if suf and n.endswith(suf) else n): c for n, c in st["cards"].items()}


def tot_int(t):
    return int(t) if t.isdigit() else 0


by_id = {s[0]: s for s in sets_out}
by_name = {}
for s in sets_out:
    by_name.setdefault(key(s[1]), s)
by_sig = defaultdict(list)
for s in sets_out:
    if s[3]:
        by_sig[s[3]].append(s)
    if len(s) > 8 and s[8] and s[8].upper() != s[3]:
        by_sig[s[8].upper()].append(s)      # código japonês original, mesmo se a sigla foi apagada

# Ligação Liga -> catálogo em três passadas, sem deixar duas siglas na mesma coleção:
# 1) mapa manual e nome em inglês idêntico, 2) sigla, 3) nome aproximado + total.
assign, how_of, used = {}, {}, set()
for sig, st in sorted(liga_rows.items()):
    t = None
    if sig in manual and manual[sig][1] in by_id:
        t, h = by_id[manual[sig][1]], "mapa"
    elif key(st["en"]) in by_name and by_name[key(st["en"])][0] not in used:
        t, h = by_name[key(st["en"])], "nome"
        lt = tot_int(st["tot"])
        if lt and t[4] and abs(lt - t[4]) > max(10, 0.3 * t[4]):
            t = None    # mesmo nome, mas outra coleção (ex.: versão japonesa com outro tamanho)
    if t is not None and t[0] not in used:
        assign[sig], how_of[sig] = t, h
        used.add(t[0])
for sig, st in sorted(liga_rows.items()):
    if sig in assign:
        continue
    lt = tot_int(st["tot"])
    for t in by_sig.get(sig, []):
        if t[0] in used:
            continue
        if lt and t[4] and abs(lt - t[4]) > max(10, 0.3 * t[4]):
            continue    # mesma sigla, mas tamanho de coleção muito diferente
        assign[sig], how_of[sig] = t, "sigla"
        used.add(t[0])
        break
for sig, st in sorted(liga_rows.items()):
    if sig in assign or re.search(r"\((JP|Japanese|Chinese|Coreano|Korean)\)$", st["en"]):
        continue
    lt, ltok = tot_int(st["tot"]), tokens(st["en"])
    best, bscore = None, 0.0
    for s2 in sets_out:
        if s2[0] in used or s2[6] == "Japão":
            continue
        tt = tokens(s2[1])
        if not ltok or not tt:
            continue
        score = len(ltok & tt) / len(ltok | tt) + (0.25 if lt and s2[4] == lt else 0)
        if score > bscore:
            best, bscore = s2, score
    if best and bscore >= 0.75:
        assign[sig], how_of[sig] = best, "aproximado"
        used.add(best[0])

# Coleções que só existem na Liga. Algumas são partes ou versões de outra coleção:
#  - "sub": subcoleção com prefixo no número (Galeria de Treinadores TG, Galarian Gallery GG, Shiny Vault SV)
#  - "ver": a mesma coleção com outro padrão (Master Ball, Poké Ball, Equipe Rocket, coreana...)
variants = defaultdict(list)
unassigned = {sig: st for sig, st in liga_rows.items() if sig not in assign}
parents = {sig: st for sig, st in liga_rows.items()}
for sig, st in sorted(unassigned.items()):
    en = st["en"]
    if re.search(r"\((JP|Japanese|Chinese)\)$", en):
        continue
    m = re.match(r"^([A-Za-z]+)\d+$", st["tot"])
    best = None
    for psig, pst in parents.items():
        pen = pst["en"]
        if psig == sig or not pen or len(pen) >= len(en):
            continue
        if en.startswith(pen) and en[len(pen):][:2] in (": ", " -", " (") and (not best or len(pen) > len(parents[best]["en"])):
            best = psig
    if m:
        prefix = m.group(1).upper()
        parent_set = assign.get(best) if best else None
        if parent_set is None:
            owners = [sid for sid, cards in cards_out.items() if any(c[0].upper().startswith(prefix) and re.match(r"^[A-Z]+\d+$", c[0].upper()) for c in cards)]
            owners = [o for o in owners if any(c[0].upper() == st["tot"].upper() for c in cards_out[o])] or owners
            parent_set = by_id[owners[0]] if len(owners) == 1 else None
        if parent_set is not None:
            variants[parent_set[0]].append([st["raw"], st["pt"] or st["en"], st["en"], st["suffix"], st["pad"], "sub", prefix])
            assign[sig], how_of[sig] = parent_set, "subcolecao " + prefix
            st["sub"] = True
        continue
    if best and tot_int(st["tot"]) and tot_int(st["tot"]) == tot_int(parents[best]["tot"]):
        st["ver_of"] = best

liga, liga_sets, report = {}, {}, []
for sig, st in sorted(liga_rows.items()):
    if st.get("ver_of"):
        continue
    target = assign.get(sig)
    how = how_of.get(sig, "")
    if target is None:
        # Coleção que só existe na Liga: entra com os dados dela
        sid = "liga-" + sig.lower()
        cards = []
        for nn, c in st["cards"].items():
            cards.append([c[4], fold(c[1] or c[0]), fold(c[0]) if c[0] != c[1] else "", c[2], c[3]])
        cards.sort(key=lambda r: (int(re.sub(r"\D", "", r[0]) or 9999), r[0]))
        sets_out.append([sid, fold(st["en"] or st["pt"]), fold(st["pt"]) if st["pt"] != st["en"] else "", sig, tot_int(st["tot"]), "", "Liga"])
        cards_out[sid] = cards
        by_id[sid] = sets_out[-1]
        target, how = sets_out[-1], "so na Liga"
    else:
        # Cartas que a Liga tem e o catálogo não tem nessa coleção
        have = {nnum(c[0]) for c in cards_out[target[0]]}
        for nn, c in st["cards"].items():
            if nn not in have:
                cards_out[target[0]].append([c[4], fold(c[1] or c[0]), fold(c[0]) if c[0] != c[1] else "", c[2], c[3]])
                have.add(nn)
    sid = target[0]
    for nn, c in st["cards"].items():
        liga[sid + "|" + nn] = c
    if st.get("sub"):
        report.append(f"{st['raw']:8} -> {sid:16} ({how}) total {st['tot']}")
        continue
    while len(target) < 8:
        target.append("")
    target[7] = st["raw"]
    liga_sets[sid] = [st["pt"] or st["en"], st["en"], st["suffix"], st["pad"]]
    report.append(f"{st['raw']:8} -> {sid:16} ({how}) total Liga {st['tot']} / catalogo {target[4]} | {st['en']} = {target[1]}")

for sig, st in sorted(liga_rows.items()):
    if st.get("ver_of"):
        parent = parents[st["ver_of"]]
        psid = (assign.get(st["ver_of"]) or by_id.get("liga-" + st["ver_of"].lower()))[0]
        variants[psid].append([st["raw"], st["pt"] or st["en"], st["en"], st["suffix"], st["pad"], "ver", ""])
        report.append(f"{st['raw']:8} -> {psid:16} (versao de {parent['raw']}) {st['en']}")

# Siglas do mapa que não apareceram em nenhum export: aplica só a sigla
done = {r.split()[0].upper() for r in report}
for sig, (raw, sid) in sorted(manual.items()):
    if sig in done:
        continue
    if sid not in by_id:
        report.append(f"{sig:8} -> {sid:16} (mapa) id nao encontrado")
        continue
    t = by_id[sid]
    while len(t) < 8:
        t.append("")
    t[7] = raw
    report.append(f"{raw:8} -> {sid:16} (mapa)")

# Sigla do TCGdex que a Liga usa para outra coleção (ex.: TR = Team Rocket na Liga,
# mas Team Rocket Returns no TCGdex): apaga a do TCGdex para não exportar errado
claimed = {t[7].upper(): t[0] for t in sets_out if len(t) > 7 and t[7]}
for t in sets_out:
    if t[3] in claimed and claimed[t[3]] != t[0]:
        report.append(f"{t[3]:8} removida de {t[0]} ({t[1]}): na Liga e de {claimed[t[3]]}")
        t[3] = ""

# Só aponta imagens de coleções que o TCGdex tem (lista em assets.tcgdex.net/datas.json)
DATAS = sys.argv[5] if len(sys.argv) > 5 else ""
if DATAS and os.path.exists(DATAS):
    try:
        datas = json.load(open(DATAS, encoding="utf-8"))
        kept = {}
        for sid, base in images.items():
            lang, ser, st = base.split("/", 2)
            if datas.get(lang, {}).get(ser, {}).get(st):
                kept[sid] = base
        print(f"imagens: {len(kept)} de {len(images)} colecoes com imagem oficial")
        images = kept
    except (ValueError, AttributeError) as e:
        print(f"imagens: datas.json ilegivel ({e}), mantendo todas")

json.dump({"v": 4, "sets": sets_out, "cards": cards_out, "ligaSets": liga_sets, "liga": liga, "variants": variants, "img": images}, open(OUT, "w", encoding="utf-8"),
          ensure_ascii=False, separators=(",", ":"))
print(len(sets_out), "colecoes", sum(len(v) for v in cards_out.values()), "cartas")
print(len(liga), "cartas com dados da Liga")
print("\n".join(report))
