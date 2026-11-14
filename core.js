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
  /* Número no formato da Liga, igual ao impresso: com 3 dígitos ("004") a partir de
     Espada e Escudo (2020); antes disso, sem zeros à esquerda ("4", "32"). */
  const PAD_FROM = "2020-02-01";
  function ligaNum(n, rel) {
    n = String(n ?? "").trim().toUpperCase();
    if (!/^\d+$/.test(n)) return n;
    n = n.replace(/^0+(?=\d)/, "");
    return rel && rel >= PAD_FROM ? n.padStart(3, "0") : n;
  }

  /* Corrige confusões comuns do OCR dentro da parte numérica */
  function fixDigits(tok) {
    tok = tok.toUpperCase();
    const pre = (tok.match(NUM_PREFIX) || [""])[0];
    const rest = tok.slice(pre.length).replace(/O|Q|D/g, "0").replace(/[IL|]/g, "1").replace(/S/g, "5").replace(/B/g, "8").replace(/Z/g, "2");
    return pre + rest;
  }

  /* Reconhece a sigla num pedaço lido, tolerando o que costuma grudar nela: a marca de regulamento
     antes ("HPRE") e o idioma depois ("PREPT"). Com o total da coleção lido, aceita também uma letra
     errada ("PRER" com /131 vira PRE), desde que a coleção tenha esse total. */
  function sigOf(tok, sigs, tot, sigTot) {
    if (!tok || !sigs) return null;
    const cands = [[tok, null]];
    const lm = tok.match(/^([A-Z0-9]{2,6}?)(PT|EN|JP|ES|FR|DE|IT|KO)$/);
    if (lm) cands.push([lm[1], lm[2]]);
    if (/^[A-J][A-Z]/.test(tok)) { cands.push([tok.slice(1), null]); if (lm) cands.push([lm[1].slice(1), lm[2]]); }
    for (const [t, lang] of cands) if (t.length >= 2 && sigs.has(t)) return { sig: t, lang, fuzzy: false };
    if (tot && sigTot) {
      for (const [t, lang] of cands) {
        if (t.length < 3) continue;
        for (const [sg, tots] of sigTot) if (tots.has(tot) && Math.abs(sg.length - t.length) <= 1 && lev(sg, t) <= 1) return { sig: sg, lang, fuzzy: true };
      }
    }
    return null;
  }

  /* Lê a faixa inferior: sigla, idioma, número e total.
     sigTot (opcional): Map sigla -> Set de totais, para corrigir siglas com uma letra errada. */
  function parseBottom(text, sigs, sigTot) {
    const out = { sig: null, lang: null, num: null, tot: null, fuzzy: false, sigHint: null, bare: null };
    const T = String(text || "").toUpperCase().replace(/[\\|]/g, "/").replace(/[^\w/\n ]+/g, " ");
    let best = null;
    for (const line of T.split(/\n+/)) {
      const re = /([A-Z]{0,5}[0-9OILSBQDZ]{1,3})\s*\/\s*([A-Z]{0,4}[0-9OILSBQDZ]{2,3})/g;
      let m;
      while ((m = re.exec(line))) {
        let num = fixDigits(m[1]), tot = fixDigits(m[2]);
        if (!/\d$/.test(num) || !/^\D*\d+$/.test(tot)) continue;
        const nTot = parseInt(tot.replace(/\D/g, ""), 10);
        let sig = null, lang = null, fuzzy = false;
        /* sigla grudada no número: "PRE019/131" */
        const pm = num.match(/^([A-Z]{2,5})(\d+)$/);
        if (pm && !NUM_PREFIX.test(num)) {
          const g = sigOf(pm[1], sigs, nTot, sigTot);
          if (g) { sig = g.sig; lang = g.lang; fuzzy = g.fuzzy; num = pm[2]; }
          else num = pm[2];
        }
        const before = line.slice(0, m.index).trim().split(/\s+/).filter(Boolean);
        for (let i = before.length - 1; !sig && i >= Math.max(0, before.length - 3); i--) {
          const t = before[i];
          if (!lang && LANGS.has(t)) { lang = t; continue; }
          const g = sigOf(t, sigs, nTot, sigTot);
          if (g) { sig = g.sig; lang = lang || g.lang; fuzzy = g.fuzzy; }
        }
        const nNum = parseInt(num.replace(/\D/g, ""), 10);
        const score = (sig ? (fuzzy ? 3 : 4) : 0) + (lang ? 1 : 0) + (nNum <= nTot + 150 ? 1 : -2);
        if (!best || score > best.score) best = { score, sig, lang, num, tot, fuzzy };
      }
      /* Promos sem barra: "SVP EN 050", "MEP 012", "MEPPT 012" */
      if (sigs) {
        const toks = line.trim().split(/\s+/);
        for (let i = 0; i < toks.length; i++) {
          const g = sigOf(toks[i], sigs);
          if (!g) continue;
          let j = i + 1, lang = g.lang;
          if (!lang && toks[j] && LANGS.has(toks[j])) { lang = toks[j]; j++; }
          if (lang && !out.sigHint) out.sigHint = g.sig;      /* sigla com idioma, mesmo sem número */
          if (!best && toks[j] && /^[0-9OILSBQDZ]{2,3}$/.test(toks[j]) && /\d/.test(toks[j])) {
            best = { score: 3, sig: g.sig, lang, num: fixDigits(toks[j]), tot: null, fuzzy: false };
            break;
          }
        }
      }
    }
    /* número solto de 3 dígitos ("086"), para juntar com uma sigla lida em outro quadro */
    if (!best) {
      const b = T.split(/\s+/).find(t => /^[0-9OILSBQDZ]{3}$/.test(t) && (t.match(/\d/g) || []).length >= 2);
      if (b) out.bare = fixDigits(b);
    }
    /* Promo japonesa: "030/SV-P", "123/S-P", "045/M-P" */
    if (!best || !best.sig) {
      const m = T.match(/\b([0-9OILSBQDZ]{3})\s*\/\s*(SV|SM|S|M|XY|BW)\s*-?\s*P\b/);
      if (m && sigs && sigs.has(m[2] + "-P")) best = { score: 9, sig: m[2] + "-P", lang: "JP", num: fixDigits(m[1]), tot: null, fuzzy: false };
    }
    if (best) Object.assign(out, { sig: best.sig, lang: best.lang, num: best.num, tot: best.tot, fuzzy: !!best.fuzzy });
    out.langCode = out.lang ? LANGMAP[out.lang] : undefined;
    return out;
  }


  /* Desempata uma leitura ambígua (mesmo número e total em coleções diferentes): procura a sigla de cada
     candidata nos textos lidos há pouco, com uma letra de tolerância nas siglas de 3+ letras.
     Devolve a carta só se exatamente uma coleção aparecer. */
  function pickBySig(cands, texts) {
    const toks = new Set();
    for (const t of texts) for (const w of String(t || "").toUpperCase().split(/[^A-Z0-9]+/)) {
      if (w.length < 2) continue;
      toks.add(w);
      const lm = w.match(/^([A-Z0-9]{2,6}?)(PT|EN|JP|ES|FR|DE|IT|KO)$/); if (lm) toks.add(lm[1]);
      if (/^[A-J][A-Z]/.test(w)) { toks.add(w.slice(1)); if (lm) toks.add(lm[1].slice(1)); }
    }
    const hit = new Map();
    for (const c of cands) {
      const sgs = [c.set.sig, c.set.ligaUp].filter(Boolean);
      for (const t of toks) for (const sg of sgs) {
        if (sg.length < 3) continue;          /* siglas de 2 letras aparecem demais no ruído do OCR */
        if (t === sg || (Math.abs(t.length - sg.length) <= 1 && lev(t, sg) <= 1)) hit.set(c.set.id, c);
      }
    }
    return hit.size === 1 ? [...hit.values()][0] : null;
  }

  /* Binarização local (Sauvola) para fundos com textura, como as cartas reverse foil.
     g: tons de cinza (Uint8Array, w*h). Marca como texto o pixel mais escuro que a vizinhança
     (janela = win * altura) e entre os gp% mais escuros da faixa; depois apaga manchas grandes
     (borda, brilho holográfico) e pontinhos. Devolve Uint8Array com 0 (texto) e 255 (fundo). */
  function localBinarize(g, w, h, win, gp) {
    const W = w + 1, S = new Float64Array(W * (h + 1)), Q = new Float64Array(W * (h + 1)), hist = new Uint32Array(256);
    for (let y = 0; y < h; y++) {
      let rs = 0, rq = 0;
      for (let x = 0; x < w; x++) {
        const v = g[y * w + x]; hist[v]++; rs += v; rq += v * v;
        S[(y + 1) * W + x + 1] = S[y * W + x + 1] + rs; Q[(y + 1) * W + x + 1] = Q[y * W + x + 1] + rq;
      }
    }
    let gthr = 255;
    if (gp < 100) { let acc = 0; for (gthr = 0; gthr < 255; gthr++) { acc += hist[gthr]; if (acc >= w * h * gp / 100) break; } }
    const r = Math.max(1, Math.round(win * h / 2)), out = new Uint8Array(w * h).fill(255), mask = new Uint8Array(w * h);
    for (let y = 0; y < h; y++) {
      const y0 = Math.max(0, y - r), y1 = Math.min(h, y + r + 1);
      for (let x = 0; x < w; x++) {
        const v = g[y * w + x]; if (v > gthr) continue;
        const x0 = Math.max(0, x - r), x1 = Math.min(w, x + r + 1), n = (y1 - y0) * (x1 - x0);
        const sum = S[y1 * W + x1] - S[y0 * W + x1] - S[y1 * W + x0] + S[y0 * W + x0];
        const sq = Q[y1 * W + x1] - Q[y0 * W + x1] - Q[y1 * W + x0] + Q[y0 * W + x0];
        const m = sum / n, sd = Math.sqrt(Math.max(0, sq / n - m * m));
        if (v < m * (1 + 0.15 * (sd / 128 - 1))) mask[y * w + x] = 1;
      }
    }
    /* componentes conectados (4 vizinhos): fica só o que tem tamanho de letra */
    const stack = new Int32Array(w * h), seen = new Uint8Array(w * h), comp = new Int32Array(w * h);
    const minSz = h * h * 0.0008;
    for (let i = 0; i < w * h; i++) {
      if (!mask[i] || seen[i]) continue;
      let sp = 0, n = 0, x0 = w, x1 = 0, y0 = h, y1 = 0; stack[sp++] = i; seen[i] = 1;
      while (sp) {
        const j = stack[--sp]; comp[n++] = j;
        const x = j % w, y = (j - x) / w;
        if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y;
        if (x > 0 && mask[j - 1] && !seen[j - 1]) { seen[j - 1] = 1; stack[sp++] = j - 1; }
        if (x < w - 1 && mask[j + 1] && !seen[j + 1]) { seen[j + 1] = 1; stack[sp++] = j + 1; }
        if (y > 0 && mask[j - w] && !seen[j - w]) { seen[j - w] = 1; stack[sp++] = j - w; }
        if (y < h - 1 && mask[j + w] && !seen[j + w]) { seen[j + w] = 1; stack[sp++] = j + w; }
      }
      if (y1 - y0 + 1 <= h * 0.4 && x1 - x0 + 1 <= h * 1.2 && n >= minSz) for (let k = 0; k < n; k++) out[comp[k]] = 0;
    }
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
    const sets = cat.sets.map(s => ({ id: s[0], en: s[1], pt: s[2], sig: s[3], official: s[4], rel: s[5] || "", serie: s[6], ligaSig: s[7] || "", code: s[8] || "", jp: !!s[8] || s[6] === "Japão" }));
    const byId = new Map(sets.map(s => [s.id, s]));
    const cards = [];
    for (const s of sets) {
      for (const c of cat.cards[s.id] || []) {
        cards.push({ key: s.id + "|" + c[0], set: s, lid: c[0], nn: normNum(c[0]), en: c[1] || "", pt: c[2] || "", rar: c[3], cor: c[4], ja: c[5] || "", pid: c[6] || 0, ne: norm(c[1]), np: norm(c[2] || "") });
      }
    }
    for (const s of sets) s.ligaUp = s.ligaSig.toUpperCase();
    const sigs = new Set(sets.flatMap(s => [s.sig, s.ligaUp]).filter(Boolean));
    const sigTot = new Map();
    for (const s of sets) if (s.official) for (const g of [s.sig, s.ligaUp]) if (g) { if (!sigTot.has(g)) sigTot.set(g, new Set()); sigTot.get(g).add(s.official); }
    const byKey = new Map(cards.map(c => [c.key, c]));
    return { sets, byId, cards, byKey, sigs, sigTot, liga: cat.liga || {}, ligaSets: cat.ligaSets || {}, variants: cat.variants || {}, img: cat.img || {} };
  }

  /* Ordena as cartas candidatas a partir do que o OCR leu */
  function resolve(idx, bottom, topText) {
    const lines = readLinesOf(topText);
    const num = bottom.num ? normNum(bottom.num) : null;
    const tot = bottom.tot ? parseInt(String(bottom.tot).replace(/\D/g, ""), 10) : null;
    const totPre = bottom.tot ? (String(bottom.tot).match(/^[A-Z]+/) || [""])[0] : "";
    let pool = [], base = 0;
    if (num && bottom.sig) { pool = idx.cards.filter(c => c.nn === num && (c.set.sig === bottom.sig || c.set.ligaUp === bottom.sig)); base = 3; }
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
  /* "charizard ex 151": se o número não achar nada, tenta de novo tratando-o como parte do nome da coleção */
  /* Se nada aparecer, tenta de novo lendo números e siglas como palavras
     ("charizard ex 151": "ex" é também a sigla de Expedition, e "151" é o nome da coleção). */
  function search(idx, q, limit) {
    for (const [n, g] of [[false, false], [true, false], [false, true], [true, true]]) {
      const out = searchOnce(idx, q, limit, n, g);
      if (out.length) return out;
    }
    return [];
  }
  function searchOnce(idx, q, limit, numAsWord, sigAsWord) {
    const toks = norm(q).split(" ").filter(Boolean);
    const jpWords = String(q).trim().split(/\s+/).filter(t => /[^\x00-\x7F]/.test(t) && !norm(t));
    if (!toks.length && !jpWords.length) return [];
    let sig = null, num = null, tot = null; const words = [];
    const rawToks = String(q).toUpperCase().trim().split(/\s+/);
    for (const t of rawToks) {
      if (idx.sigs.has(t) && !sigAsWord) sig = t;
      else if (/^[A-Z]{0,4}\d+\/[A-Z]{0,4}\d+$/.test(t)) { const [a, b] = t.split("/"); num = normNum(a); tot = parseInt(b.replace(/\D/g, ""), 10); }
      else if (/^[A-Z]{0,4}\d+$/.test(t) && !(numAsWord && /^\d+$/.test(t))) num = normNum(t);
      else if (norm(t)) words.push(norm(t));
    }
    const out = [];
    for (const c of idx.cards) {
      if (sig && c.set.sig !== sig && c.set.ligaUp !== sig) continue;
      if (num && c.nn !== num) continue;
      if (tot && c.set.official !== tot) continue;
      if (words.length) {
        const hay = c.ne + " " + c.np + " " + norm(c.set.en) + " " + norm(c.set.pt);
        if (!words.every(w => hay.includes(w))) continue;
      }
      if (jpWords.length && !jpWords.every(w => c.ja.includes(w) || c.set.en.includes(w))) continue;
      out.push(c);
      if (out.length >= (limit || 40)) break;
    }
    return out;
  }

  /* Dados que vão para a linha do CSV da Liga */
  /* Número no formato da Liga. A coleção diz se usa zeros à esquerda (pad) e sufixo
     ("044JP", "077R"); números com prefixo (TG05, SWSH093, SV014) saem como impressos. */
  function formatNum(lid, info, rel, jp) {
    lid = String(lid ?? "").trim();
    const m = lid.match(/^([A-Za-z]*)(\d+)([A-Za-z]*)$/);
    const suf = (info && info.suf) || "";
    if (!m) return lid;
    if (m[1]) return lid + suf;
    const pad = info && info.pad >= 0 ? info.pad : (jp || (rel && rel >= PAD_FROM)) ? 3 : 0;
    return m[2].replace(/^0+(?=\d)/, "").padStart(pad, "0") + m[3] + suf;
  }

  /* Imagem oficial da carta: TCGdex (internacionais e japonesas) ou TCGplayer (japonesas que só ele tem) */
  function imageUrl(idx, card, high) {
    const base = idx.img[card.set.id];
    if (base) return "https://assets.tcgdex.net/" + base + "/" + encodeURIComponent(card.lid) + (high ? "/high.webp" : "/low.webp");
    if (card.pid) return "https://tcgplayer-cdn.tcgplayer.com/product/" + card.pid + (high ? "_400w.jpg" : "_200w.jpg");
    return "";
  }

  /* Versões da mesma coleção na Liga (Master Ball, Poké Ball, Equipe Rocket, coreana...) */
  function versions(idx, card) {
    const base = idx.ligaSets[card.set.id], vs = (idx.variants[card.set.id] || []).filter(v => v[5] === "ver");
    const parent = base ? base[0] : card.set.pt || card.set.en;
    return vs.map(v => {
      let label = v[1];
      if (label.toLowerCase().startsWith(parent.toLowerCase())) label = label.slice(parent.length);
      label = label.replace(/^[\s:\-–(]+|\)\s*$/g, "").trim() || v[0];
      return { sig: v[0], label };
    });
  }

  /* Dados que vão para a linha do CSV da Liga */
  function ligaInfo(idx, card, sigOverrides, verSig) {
    const s = card.set, ls = idx.ligaSets[s.id], vars = idx.variants[s.id] || [];
    let info = ls ? { pt: ls[0], en: ls[1], suf: ls[2] || "", pad: ls[3] ?? -1 } : null;
    const pre = (card.lid.match(/^[A-Za-z]+(?=\d)/) || [""])[0].toUpperCase();
    const sub = pre && vars.find(v => v[5] === "sub" && v[6] === pre);
    const ver = verSig && vars.find(v => v[5] === "ver" && v[0] === verSig);
    const v = ver || sub;
    if (v) info = { pt: v[1], en: v[2], suf: v[3] || "", pad: v[4] ?? -1 };
    /* Japonesas sem sigla confirmada: segue o padrão mais comum da Liga ("SV1V" -> "sv1V") */
    const jpGuess = s.jp && s.code ? s.code.replace(/^[A-Z]+(?=\d)/, m => m.toLowerCase()) : "";
    const sig = (v && v[0]) || (sigOverrides && sigOverrides[s.id]) || s.ligaSig || jpGuess || s.sig || (s.jp ? "" : s.id.toUpperCase());
    const lc = idx.liga[s.id + "|" + card.nn] || idx.liga[s.id + "|" + card.nn.replace(/JP$/, "")];
    const num = lc && !ver ? lc[4] : formatNum(card.lid, info, s.rel, s.jp);
    const name = s.jp ? (card.en || card.ja) : null;
    return {
      sig, num, ver: ver ? ver[0] : "",
      ed: info ? info.pt : s.jp ? "" : fold(s.pt || s.en).trim(),
      edEn: info ? info.en : s.jp ? "" : fold(s.en).trim(),
      pt: lc ? lc[0] : name ?? fold(card.pt || card.en), en: lc ? lc[1] : name ?? fold(card.en),
      rar: lc ? lc[2] : card.rar, cor: lc ? lc[3] : card.cor,
      tot: s.official ? String(s.official) : "",
      verified: !!lc || !!s.ligaSig || !!v, jpOnly: !!s.jp && !lc && !card.en
    };
  }

  const cell = v => { v = String(v ?? ""); return /[\s,"]/.test(v) ? '"' + v.replace(/"/g, '""') + '"' : v; };
  function buildCSV(rows) {
    const lines = [HEADER];
    for (const b of rows) lines.push([b.ed, b.edEn, b.sig, b.pt, b.en, b.qty, b.qual, b.lang, b.rar, b.cor, b.ext, b.num, "", b.tot].map(cell).join(","));
    return lines.join("\n") + "\n";
  }

  const api = { pickBySig, localBinarize, fold, norm, normNum, ligaNum, formatNum, versions, imageUrl, fixDigits, parseBottom, nameScore, readLinesOf, buildIndex, resolve, search, ligaInfo, buildCSV, LANGMAP };
  if (typeof module !== "undefined" && module.exports) module.exports = api; else root.LigaCore = api;
})(typeof window !== "undefined" ? window : globalThis);
