/* Scanner Liga — One Piece: catálogo, leitura do código impresso, versões e CSV da LigaOnePiece.
   Sem acesso a tela ou câmera, para poder ser testada fora do navegador. */
(function (root) {
  "use strict";

  /* Cabeçalho exatamente como a LigaOnePiece exporta (a coluna Raridade não lista as letras) */
  const HEADER = '"Edicao (PTBR)","Edicao (EN)","Edicao (Sigla)","Card (PT)","Card (EN)",Quantidade,"Qualidade (M NM SP MP HP D)","Idioma (BR EN DE ES FR IT JP KO RU TW)",Raridade,"Cor (C D O E Y F R G L M P W)",Extras,"Card #",Comentario,"# Cards na Edicao"';
  const BASE_RE = /^((?:[A-Z]+\d*|P)-\d{3})/;
  const COLORS = { R: "Vermelha", G: "Verde", U: "Azul", P: "Roxa", B: "Preta", Y: "Amarela", M: "Multicolor" };

  const fold = s => String(s ?? "").normalize("NFD").replace(/[̀-ͯ]/g, "");
  const norm = s => fold(s).toLowerCase().replace(/[^a-z0-9 ]+/g, " ").replace(/\s+/g, " ").trim();
  const baseOf = num => { const m = String(num || "").match(BASE_RE); return m ? m[1] : null; };
  /* "OP07" a partir de "OP07-020"; "P" para promos */
  const prefixOf = code => (String(code).match(/^([A-Z]+\d*)-/) || [, ""])[1];

  function buildIndex(cat) {
    const sets = cat.sets.map(s => ({ sig: s[0], en: s[1], kind: s[2], total: s[3], up: s[0].toUpperCase() }));
    const cards = cat.cards.map(c => {
      const set = sets[c[0]], base = baseOf(c[1]);
      return { set, num: c[1], base, name: c[2], rar: c[3], cor: c[4], ok: !!c[5], nn: norm(c[2]), key: set.sig + "|" + c[1] };
    });
    const byBase = new Map();
    for (const c of cards) if (c.base) { if (!byBase.has(c.base)) byBase.set(c.base, []); byBase.get(c.base).push(c); }
    const sigs = new Map(sets.map(s => [s.up, s]));
    const byKey = new Map(cards.map(c => [c.key, c]));
    return { sets, cards, byBase, byKey, codes: new Set(byBase.keys()), sigs, home: cat.home || {}, alts: cat.alts || {} };
  }

  /* Ordem das versões de um código: normal da coleção de origem, variantes dela,
     pré-release/eventos, reimpressões em outras coleções e, por fim, promos */
  function rank(idx, c) {
    const home = idx.home[prefixOf(c.base)];
    if (c.set.sig === home) return c.num === c.base ? 0 : 1;
    /* Sem versão normal na coleção de origem (ex.: EB04 em inglês saiu dentro da OP-14) */
    if (c.set.kind === "set" && c.num === c.base && !(idx.byBase.get(c.base) || []).some(x => x.set.sig === home && x.num === x.base)) return 0.5;
    if (c.set.kind === "event") return 2;
    if (c.set.kind === "set") return 3;
    return 4;
  }
  function candidates(idx, code) {
    const list = (idx.byBase.get(code) || []).slice();
    return list.sort((a, b) => rank(idx, a) - rank(idx, b) || (a.set.sig < b.set.sig ? -1 : a.set.sig > b.set.sig ? 1 : 0) || (a.num < b.num ? -1 : 1));
  }

  /* Corrige confusões comuns do OCR na parte numérica */
  const fixDigits = s => s.toUpperCase().replace(/[OQD]/g, "0").replace(/[IL|]/g, "1").replace(/S/g, "5").replace(/B/g, "8").replace(/Z/g, "2");
  const fixPrefix = p => p.replace(/^[O0Q]P$/, "OP").replace(/^[S5]T$/, "ST").replace(/^E[B8]$/, "EB");

  /* Procura o código impresso no canto inferior direito: OP07-020, ST14-001, EB01-012, PRB01-001, P-045 */
  function parseCode(text, codes) {
    const T = String(text || "").toUpperCase().replace(/[—–_~=:.,]/g, "-");
    const re = /(?<![A-Z])(PRB|[O0Q]P|[S5]T|E[B8]|P)\s?([0-9OILSBQDZ]{2})?\s?(-?)\s?([0-9OILSBQDZ]{3})(?![0-9])/g;
    let best = null, m;
    while ((m = re.exec(T))) {
      const pre = fixPrefix(m[1]);
      if (pre === "P" ? m[2] : !m[2]) continue;
      const code = pre === "P" ? "P-" + fixDigits(m[4]) : pre + fixDigits(m[2]) + "-" + fixDigits(m[4]);
      const score = (codes && codes.has(code) ? 10 : 0) + (m[3] ? 2 : 0) + (pre === "P" ? 0 : 1);
      if (!best || score > best.score) best = { code, score, known: !!(codes && codes.has(code)) };
    }
    return best;
  }

  /* Rótulo curto da versão, para a lista de escolha */
  function label(idx, c) {
    const tags = (c.name.match(/\(([^)]*)\)/g) || []).map(t => t.slice(1, -1)).filter(t => !/^\d+$/.test(t));
    const tag = tags.join(" · ");
    const home = idx.home[prefixOf(c.base)];
    if (c.set.sig === home) {
      if (c.num === c.base) return "Normal";
      const suf = c.num.slice(c.base.length + 1);
      return tag || (/^JP$/.test(suf) ? "Japonesa" : /-JP$/.test(suf) ? suf.replace(/-JP$/, "") + " · Japonesa" : suf);
    }
    let ev = "";
    if (c.set.kind === "event") ev = /-PR$/.test(c.set.sig) ? "Pré-release" : /-RE$/.test(c.set.sig) ? "Release Event" : "Torneio de aniversário";
    else if (c.set.kind === "promo") ev = tag ? "" : "Promo";
    else ev = c.set.en;
    return [ev, tag].filter(Boolean).join(" · ");
  }

  /* Busca manual: "OP07-020", "op07 20", "OP-07-PR luffy", "P-045", "hancock" */
  function search(idx, q, limit) {
    const raw = String(q || "").toUpperCase().trim().split(/\s+/).filter(Boolean);
    if (!raw.length) return [];
    let code = null, pre = null, sig = null, numOnly = null; const words = [];
    for (let i = 0; i < raw.length; i++) {
      const t = raw[i];
      let m;
      if ((m = t.match(/^(OP|ST|EB|PRB)(\d{2})-?(\d{1,3})$/))) code = m[1] + m[2] + "-" + m[3].padStart(3, "0");
      else if ((m = t.match(/^P-?(\d{1,3})$/))) code = "P-" + m[1].padStart(3, "0");
      else if (idx.sigs.has(t)) sig = t;
      else if (/^(OP|ST|EB|PRB)\d{2}$/.test(t)) pre = t;
      else if (/^\d{1,3}$/.test(t)) numOnly = t.padStart(3, "0");
      else if (norm(t)) words.push(norm(t));
    }
    if (pre && numOnly) { code = pre + "-" + numOnly; pre = null; numOnly = null; }
    const pool = code ? candidates(idx, code) : idx.cards;
    const out = [];
    for (const c of pool) {
      if (sig && c.set.up !== sig) continue;
      if (pre && prefixOf(c.base) !== pre) continue;
      if (numOnly && !(c.base && c.base.endsWith("-" + numOnly))) continue;
      if (words.length) { const hay = c.nn + " " + norm(c.set.en); if (!words.every(w => hay.includes(w))) continue; }
      out.push(c);
      if (out.length >= (limit || 40)) break;
    }
    return code ? out : out.sort((a, b) => rank(idx, a) - rank(idx, b));
  }

  /* Variantes da coleção de origem que a base oficial tem e o catálogo da Liga ainda não */
  function missingAlts(idx, code) {
    const n = idx.alts[code] || 0, home = idx.home[prefixOf(code)];
    const have = (idx.byBase.get(code) || []).filter(c => c.set.sig === home && c.num !== code).length;
    return Math.max(0, n - have);
  }

  /* Imagem oficial (site da Bandai). Arte alternativa da coleção de origem usa a "_p1" quando
     a carta só tem uma; nos outros casos, a arte normal, que basta para reconhecer a carta. */
  function imageUrl(idx, c) {
    if (!c || !c.base) return "";
    let id = c.base;
    if (prefixOf(c.base) !== "P" && c.set.sig === idx.home[prefixOf(c.base)] && c.num !== c.base && !/-JP$/.test(c.num) && idx.alts[c.base] === 1) id += "_p1";
    return "https://en.onepiece-cardgame.com/images/cardlist/card/" + id + ".png";
  }

  /* Linha do CSV: a LigaOnePiece deixa vazios os campos em português */
  function rowOf(c) {
    return { ed: "", edEn: c.set.en, sig: c.set.sig, pt: "", en: c.name, rar: c.rar, cor: c.cor, num: c.num, tot: "" };
  }

  const cell = v => { v = String(v ?? ""); return /[\s,"]/.test(v) ? '"' + v.replace(/"/g, '""') + '"' : v; };
  function buildCSV(rows) {
    const lines = [HEADER];
    for (const b of rows) lines.push([b.ed, b.edEn, b.sig, b.pt, b.en, b.qty, b.qual, b.lang, b.rar, b.cor, b.ext, b.num, "", b.tot].map(cell).join(","));
    return lines.join("\n") + "\n";
  }

  const api = { HEADER, COLORS, imageUrl, fold, norm, baseOf, prefixOf, buildIndex, candidates, parseCode, label, search, missingAlts, rowOf, buildCSV };
  if (typeof module !== "undefined" && module.exports) module.exports = api; else root.LigaOP = api;
})(typeof window !== "undefined" ? window : globalThis);
