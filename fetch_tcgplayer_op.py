"""Baixa as cartas de One Piece do TCGplayer pelo TCGCSV (tcgcsv.com) e salva um resumo.

Uso: python tools/fetch_tcgplayer_op.py saida.json

Daqui só interessa o código do produto de cada carta, para mostrar a miniatura oficial
pela CDN do TCGplayer (a do site da Bandai não abre fora do site deles).
Se o TCGCSV não responder, o script avisa e termina sem erro.
"""
import json, sys, time, urllib.request

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
            return data.get("results", []) if isinstance(data, dict) else data
        except Exception:   # noqa: BLE001
            if i == tentativas - 1:
                raise
            time.sleep(2 * (i + 1))
    return []


def main(out):
    try:
        cats = get(BASE + "/categories")
    except Exception as e:   # noqa: BLE001
        print(f"AVISO: TCGCSV indisponivel ({e}). Seguindo sem as imagens do TCGplayer.")
        return
    cat = next((c for c in cats if "one piece" in " ".join(str(c.get(k, "")) for k in ("name", "displayName")).lower()), None)
    if not cat:
        print("AVISO: categoria One Piece nao encontrada no TCGCSV.")
        return
    cid = cat["categoryId"]
    print(f"Categoria: {cat.get('name')} (id {cid})")
    saida = []
    for g in get(f"{BASE}/{cid}/groups"):
        try:
            prods = get(f"{BASE}/{cid}/{g['groupId']}/products")
        except Exception as e:   # noqa: BLE001
            print(f"  pulando {g.get('name')}: {e}")
            continue
        for p in prods:
            ext = {d.get("name"): d.get("value") for d in p.get("extendedData") or []}
            num = (ext.get("Number") or "").strip().upper()
            if num:
                saida.append([g.get("name", ""), num, p.get("name", ""), p["productId"]])
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(saida, fh, ensure_ascii=False)
    print(f"TCGplayer One Piece: {len(saida)} cartas salvas em {out}")


if __name__ == "__main__":
    main(sys.argv[1])
