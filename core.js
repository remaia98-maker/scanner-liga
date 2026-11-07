/* Scanner Liga — lógica pura (catálogo, leitura do texto, busca e CSV).
   Sem acesso a tela ou câmera, para poder ser testada fora do navegador. */
(function (root) {
  "use strict";

  const LANGS = new Set(["PT", "EN", "JP", "JA", "ES", "FR", "DE", "IT", "KO", "BR", "ZH"]);
  const LANGMAP = { PT: "BR", BR: "BR", EN: "EN", JP: "JP", JA: "JP", ES: "ES", FR: "FR", DE: "DE", IT: "IT", KO: "KO", ZH: "TW" };
  const HEADER = '"Edicao (PTBR)","Edicao (EN)","Edicao (Sigla)","Card (PT)","Card (EN)",Quantidade,"Qualidade (M NM SP MP HP D)","Idioma (BR EN DE ES FR IT JP KO RU TW)","Raridade (C I U R H E X U P A L S)","Cor (C D O E Y F R G L M P W)",Extras,"Card #",Comentario,"# Cards na Edicao"';
  const NUM_PREFIX = /^(TG|GG|SV|RC|SH|SWSH|SM|XY|BW|H|A)(?=[0-9OILSB])/;

  const fold = s => String(s ?? "").normalize("NFD").replace(/[̀-ͯ]/g, "");
  const norm = s => fold(s).toLowerCase().replace(/[^a-z0-9 ]+/g, " ").replace(/\s+/g, " ").trim();

  /* Número comparável: "063" -> "63", "TG05" -> "TG5", "SVE003" -> "SVE3" */
  function normNum(n) {
    n = String(n ?? "").toUpperCase().replace(/\s+/g, "");
    const m = n.match(/^([A-Z]*)0*(\d+)([A-Z]*)$/);
    return m ? m[1] + m[2] + m[3] : n;
  }
  /* Número no formato da Liga: só dígitos viram 3 casas ("4" -> "004") */
  const ligaNum = n => /^\d+$/.test(n) ? n.padStart(3, "0") : String(n).toUpperCase();

  /* Corrige confusões comuns do OCR dentro da parte numérica */
  function fixDigits(tok) {
    tok = tok.toUpperCase();
    const pre = (tok.match(NUM_PREFIX) || [""])[0];
    const rest = tok.slice(pre.length).replace(/O|Q|D/g, "0").replace(/[IL|]/g, "1").replace(/S/g, "5").replace(/B/g, "8").replace(/Z/g, "2");
    return pre + rest;
  }

  /* Lê a faixa inferior: sigla, idioma, número e total */
  function parseBottom(text, sigs) {
    const out = { sig: null, lang: null, num: null, tot: null };
    const T = String(text || "").toUpperCase().replace(/[\\|]/g, "/").replace(/[^\w/\n ]+/g, " ");
    let best = null;
    for (const line of T.split(/\n+/)) {
      const re = /([A-Z]{0,4}[0-9OILSBQDZ]{1,3})\s*\/\s*([A-Z]{0,4}[0-9OILSBQDZ]{2,3})/g;
      let m;
      while ((m = re.exec(line))) {
        const num = fixDigits(m[1]), tot = fixDigits(m[2]);
        if (!/\d$/.test(num) || !/^\D*\d+$/.test(tot)) continue;
        const before = line.slice(0, m.index).trim().split(/\s+/).filter(Boolean);
        let sig = null, lang = null;
        for (let i = before.length - 1; i >= Math.max(0, before.length - 3); i--) {
          const t = before[i];
          if (!lang && LANGS.has(t)) { lang = t; continue; }
          if (!sig && sigs && sigs.has(t)) { sig = t; break; }
        }
        const nTot = parseInt(tot.replace(/\D/g, ""), 10), nNum = parseInt(num.replace(/\D/g, ""), 10);
        const score = (sig ? 4 : 0) + (lang ? 1 : 0) + (nNum <= nTot + 150 ? 1 : -2);
        if (!best || score > best.score) best = { score, sig, lang, num, tot };
      }
      /* Promos sem barra: "SVP EN 050", "MEP 012" */
      if (!best && sigs) {
        const toks = line.trim().split(/\s+/);
        for (let i = 0; i < toks.length; i++) {
          if (!sigs.has(toks[i])) continue;
          let j = i + 1, lang = null;
          if (toks[j] && LANGS.has(toks[j])) { lang = toks[j]; j++; }
          if (toks[j] && /^[0-9OILSBQDZ]{2,3}$/.test(toks[j])) {
            best = { score: 3, sig: toks[i], lang, num: fixDigits(toks[j]), tot: null };
            break;
          }
        }
      }
    }
    if (best) Object.assign(out, { sig: best.sig, lang: best.lang, num: best.num, tot: best.tot });
    out.langCode = out.lang ? LANGMAP[out.lang] : undefined;
    return out;
  }

  function lev(a, b) {
    if (a === b) return 0;
    const m = a.length, n = b.length;
    if (!m) return n; if (!n) return m;
    let prev = Array.from({ length: n + 1 }, (_, j) => j), cur = new Array(n + 1);
    for (let i = 1; i <= m; i++) {
      cur[0] = i;
      for (let j = 1; j <= n; j++) cur[j] = Math.min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
      [prev, cur] = [cur, prev];
    }
    return prev[n];
  }
  const ratio = (a, b) => (a && b) ? 1 - lev(a, b) / Math.max(a.length, b.length) : 0;

  /* Semelhança entre o texto lido no topo e um nome do catálogo (0 a 1) */
  function nameScore(readLines, name) {
    const n = norm(name);
    if (!n || !readLines.length) return 0;
    let best = 0;
    for (const line of readLines) {
      if (line === n) return 1;
      if ((" " + line + " ").includes(" " + n + " ")) best = Math.max(best, 0.88 + 0.12 * n.length / line.length);
      best = Math.max(best, ratio(line, n));
      const w = line.split(" "), k = n.split(" ").length;
      for (let i = 0; i + k <= w.length; i++) best = Math.max(best, 0.95 * ratio(w.slice(i, i + k).join(" "), n));
    }
    return best;
  }
  const readLinesOf = text => String(text || "").split(/\n+/).map(norm).filter(l => l.replace(/ /g, "").length >= 3);

  function buildIndex(cat) {
    const sets = cat.sets.map(s => ({ id: s[0], en: s[1], pt: s[2], sig: s[3], official: s[4], rel: s[5] || "", serie: s[6], ligaSig: s[7] || "" }));
    const byId = new Map(sets.map(s => [s.id, s]));
    const cards = [];
    for (const s of sets) {
      for (const c of cat.cards[s.id] || []) {
        cards.push({ key: s.id + "|" + c[0], set: s, lid: c[0], nn: normNum(c[0]), en: c[1], pt: c[2] || "", rar: c[3], cor: c[4], ne: norm(c[1]), np: norm(c[2] || "") });
      }
    }
    const sigs = new Set(sets.flatMap(s => [s.sig, s.ligaSig]).filter(Boolean));
    return { sets, byId, cards, sigs, liga: cat.liga || {}, ligaSets: cat.ligaSets || {} };
  }

  /* Ordena as cartas candidatas a partir do que o OCR leu */
  function resolve(idx, bottom, topText) {
    const lines = readLinesOf(topText);
    const num = bottom.num ? normNum(bottom.num) : null;
    const tot = bottom.tot ? parseInt(String(bottom.tot).replace(/\D/g, ""), 10) : null;
    const totPre = bottom.tot ? (String(bottom.tot).match(/^[A-Z]+/) || [""])[0] : "";
    let pool = [], base = 0;
    if (num && bottom.sig) { pool = idx.cards.filter(c => c.nn === num && (c.set.sig === bottom.sig || c.set.ligaSig === bottom.sig)); base = 3; }
    if (!pool.length && num && tot) {
      pool = idx.cards.filter(c => c.nn === num && (totPre ? c.lid.toUpperCase().startsWith(totPre) : c.set.official === tot));
      base = 2;
    }
    if (!pool.length && num && lines.length) { pool = idx.cards.filter(c => c.nn === num); base = 1; }
    if (!pool.length && lines.length) { pool = idx.cards; base = 0; }
    const ranked = pool.map(c => {
      const ns = Math.max(nameScore(lines, c.en), c.pt ? nameScore(lines, c.pt) : 0);
      return { card: c, name: ns, score: base + ns * 2 };
    }).filter(r => base > 0 || r.name >= 0.72)
      .sort((a, b) => b.score - a.score || (b.card.set.rel > a.card.set.rel ? 1 : -1))
      .slice(0, 20);
    let auto = null;
    if (ranked.length) {
      const [a, b] = ranked;
      const clearWin = !b || a.score - b.score >= 0.5;
      if (clearWin && (base >= 2 || a.name >= 0.8)) auto = a.card;
      if (base >= 2 && ranked.length === 1) auto = a.card;
    }
    return { ranked, auto, base };
  }

  /* Busca manual: "063", "MEW 063", "4/102", "charizard", "charizard base" */
  function search(idx, q, limit) {
    const toks = norm(q).split(" ").filter(Boolean);
    if (!toks.length) return [];
    let sig = null, num = null, tot = null; const words = [];
    const rawToks = String(q).toUpperCase().trim().split(/\s+/);
    for (const t of rawToks) {
      if (idx.sigs.has(t)) sig = t;
      else if (/^[A-Z]{0,4}\d+\/[A-Z]{0,4}\d+$/.test(t)) { const [a, b] = t.split("/"); num = normNum(a); tot = parseInt(b.replace(/\D/g, ""), 10); }
      else if (/^[A-Z]{0,4}\d+$/.test(t)) num = normNum(t);
      else words.push(norm(t));
    }
    const out = [];
    for (const c of idx.cards) {
      if (sig && c.set.sig !== sig && c.set.ligaSig !== sig) continue;
      if (num && c.nn !== num) continue;
      if (tot && c.set.official !== tot) continue;
      if (words.length) {
        const hay = c.ne + " " + c.np + " " + norm(c.set.en) + " " + norm(c.set.pt);
        if (!words.every(w => hay.includes(w))) continue;
      }
      out.push(c);
      if (out.length >= (limit || 40)) break;
    }
    return out;
  }

  /* Dados que vão para a linha do CSV da Liga */
  function ligaInfo(idx, card, sigOverrides) {
    const s = card.set;
    const sig = (sigOverrides && sigOverrides[s.id]) || s.ligaSig || s.sig || s.id.toUpperCase();
    const lc = idx.liga[s.id + "|" + card.nn];
    const ls = idx.ligaSets[s.id];
    return {
      sig, num: lc ? lc[4] : ligaNum(card.lid),
      ed: ls ? ls[0] : fold(s.pt || s.en).trim(), edEn: ls ? ls[1] : fold(s.en).trim(),
      pt: lc ? lc[0] : fold(card.pt || card.en), en: lc ? lc[1] : fold(card.en),
      rar: lc ? lc[2] : card.rar, cor: lc ? lc[3] : card.cor,
      tot: s.official ? String(s.official) : "",
      verified: !!lc
    };
  }

  const cell = v => { v = String(v ?? ""); return /[\s,"]/.test(v) ? '"' + v.replace(/"/g, '""') + '"' : v; };
  function buildCSV(rows) {
    const lines = [HEADER];
    for (const b of rows) lines.push([b.ed, b.edEn, b.sig, b.pt, b.en, b.qty, b.qual, b.lang, b.rar, b.cor, b.ext, b.num, "", b.tot].map(cell).join(","));
    return lines.join("\n") + "\n";
  }

  const api = { fold, norm, normNum, ligaNum, fixDigits, parseBottom, nameScore, readLinesOf, buildIndex, resolve, search, ligaInfo, buildCSV, LANGMAP };
  if (typeof module !== "undefined" && module.exports) module.exports = api; else root.LigaCore = api;
})(typeof window !== "undefined" ? window : globalThis);
