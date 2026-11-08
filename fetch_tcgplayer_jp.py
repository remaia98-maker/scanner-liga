"""Baixa as cartas japonesas do TCGplayer pelo TCGCSV (tcgcsv.com) e salva um resumo.

Uso: python tools/fetch_tcgplayer_jp.py saida.json

O TCGCSV publica, uma vez por dia, os dados do TCGplayer em JSON, sem chave.
Daqui só interessa o nome em inglês de cada carta japonesa, com o número e a coleção.
Se o site não responder, o script avisa e termina sem erro: o catálogo é gerado
do mesmo jeito, só sem esses nomes.
"""
import json, re, sys, time, unicodedata, urllib.request

BASE = "https://tcgcsv.com/tcgplayer"
UA = "ScannerLiga/1.0 (catalogo pessoal; github actions)"
PAUSA = 0.25


def get(url, tentativas=3):
    for i in range(tentativas):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.loads(r.read().decode("utf-8"))
            time.sleep(PAUSA)
            if isinstance(data, dict):
                return data.get("results", [])
            return data
        except Exception as e:   # noqa: BLE001
            if i == tentativas - 1:
                raise
            time.sleep(2 * (i + 1))
    return []


def fold(t):
    return "".join(c for c in unicodedata.normalize("NFD", t or "") if unicodedata.category(c) != "Mn").lower()


def main(out):
    try:
        cats = get(BASE + "/categories")
    except Exception as e:   # noqa: BLE001
        print(f"AVISO: TCGCSV indisponivel ({e}). Seguindo sem os nomes do TCGplayer.")
        return
    cat = None
    for c in cats:
        nome = fold(" ".join(str(c.get(k, "")) for k in ("name", "displayName")))
        if "pokemon" in nome and ("japan" in nome or "japanese" in nome):
            cat = c
            break
    if not cat:
        print("AVISO: categoria Pokemon Japan nao encontrada no TCGCSV.")
        return
    cid = cat["categoryId"]
    print(f"Categoria: {cat.get('name')} (id {cid})")

    groups = get(f"{BASE}/{cid}/groups")
    saida = []
    for g in groups:
        gid = g.get("groupId")
        try:
            prods = get(f"{BASE}/{cid}/{gid}/products")
        except Exception as e:   # noqa: BLE001
            print(f"  pulando grupo {gid} ({g.get('name')}): {e}")
            continue
        cards = []
        for p in prods:
            ext = {str(x.get("name", "")).lower(): str(x.get("value", "")) for x in (p.get("extendedData") or [])}
            numero = ext.get("number", "")
            if not numero:
                continue        # produto selado (booster, caixa...)
            cards.append([numero, p.get("name", ""), ext.get("rarity", ""), p.get("productId")])
        if cards:
            saida.append({"id": gid, "name": g.get("name", ""), "abbr": g.get("abbreviation", "") or "",
                          "date": (g.get("publishedOn") or "")[:10], "cards": cards})
    json.dump({"category": cat.get("name"), "groups": saida}, open(out, "w", encoding="utf-8"),
              ensure_ascii=False, separators=(",", ":"))
    print(f"{len(saida)} colecoes japonesas, {sum(len(g['cards']) for g in saida)} cartas")


if __name__ == "__main__":
    main(sys.argv[1])
