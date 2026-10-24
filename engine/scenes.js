/* videomotiondeck — scene engine (by AbdoulayeXYZ)
 * Deterministic, time-based motion design scenes rendered frame by frame.
 * Contract:  VMD.build({scene, data, dur, brand, transparent}) -> Promise
 *            VMD.render(t)   (t in seconds, 0..dur)
 *            VMD.events()    -> [{t, kind, ...}] used by the sound designer
 */
(function () {
  const W = 1920, H = 1080;
  const cl = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x));
  const lerp = (a, b, u) => a + (b - a) * u;
  const eo = x => 1 - Math.pow(1 - cl(x), 3);
  const ex = x => { x = cl(x); return x === 1 ? 1 : 1 - Math.pow(2, -10 * x); };
  const eio = x => { x = cl(x); return x < .5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2; };
  const fr1 = x => x - Math.floor(x);

  // ---------- DOM helpers
  function h(parent, tag, cls, style, html) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (style) e.style.cssText = style;
    if (html != null) e.innerHTML = html;
    if (parent) parent.appendChild(e);
    return e;
  }
  const esc = s => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  // rich text: **accent**  __accent2__  !!alert!!  final "." coloured
  // French typography: non-breaking space before ? ! : ; » % and after « (no orphan "?" on a new line)
  // UI words by language (cfg.lang): add yours here
  const L10N = {
    fr: { answer: 'Notre réponse.', stamp: 'Notre réponse', kicker: 'Problématique', source: 'Source : ', th: '\u202F', dec: ',' },
    en: { answer: 'Our answer.', stamp: 'Our answer', kicker: 'Challenge', source: 'Source: ', th: ',', dec: '.' },
    es: { answer: 'Nuestra respuesta.', stamp: 'Nuestra respuesta', kicker: 'Desafío', source: 'Fuente: ', th: '.', dec: ',' },
    pt: { answer: 'A nossa resposta.', stamp: 'A nossa resposta', kicker: 'Desafio', source: 'Fonte: ', th: '.', dec: ',' }
  };
  let LANG = L10N.fr;
  const typo = s => String(s == null ? '' : s).replace(/ +([?!:;»%])/g, '\u00A0$1').replace(/« +/g, '«\u00A0');
  function rt(s, dot = true) {
    let x = esc(typo(s));
    x = x.replace(/\*\*(.+?)\*\*/g, '<span class="acc">$1</span>')
         .replace(/__(.+?)__/g, '<span class="acc2">$1</span>')
         .replace(/!!(.+?)!!/g, '<span class="alert">$1</span>');
    if (dot) x = x.replace(/([.?!])(\s*)$/, '<span class="acc">$1</span>$2');
    return x;
  }
  function fit(el, maxW, size, min = 18) {
    el.style.fontSize = size + 'px';
    let guard = 0;
    while (el.scrollWidth > maxW && size > min && guard++ < 200) { size -= 2; el.style.fontSize = size + 'px'; }
    return size;
  }
  // a masked line that slides up; returns the inner element
  function maskLine(parent, x, y, w, size, html, cls = 'big', extra = '') {
    const m = h(parent, 'div', 'mask', `left:${x}px;top:${y}px;width:${w}px`);
    const inner = h(m, 'div', 'in ' + cls, `font-size:${size}px;${extra}`, html);
    const s = fit(inner, w - 10, size);
    m.style.height = Math.ceil(s * 1.18) + 'px';
    inner.style.transform = `translateY(${s * 1.4}px)`;
    return inner;
  }
  function maskIn(inner, t, a, d = 0.8, out = null) {
    const Hh = inner.parentNode.offsetHeight + 12;
    const i = ex((t - a) / d), u = out == null ? 0 : eio((t - out) / 0.45);
    inner.style.transform = `translateY(${(Hh * (1 - i) - Hh * u).toFixed(1)}px)`;
  }
  function fadeUp(el, t, a, { dy = 24, d = 0.6, sc = 0, out = null } = {}) {
    const i = ex((t - a) / d), u = out == null ? 0 : eio((t - out) / 0.4);
    el.style.opacity = (cl((t - a) / d * 1.4) * (1 - u)).toFixed(3);
    el.style.transform = `translateY(${(dy * (1 - i)).toFixed(1)}px) scale(${(1 - sc * (1 - i)).toFixed(4)})`;
  }
  function popIn(el, t, a, { d = 0.5, from = 0.85, base = '' } = {}) {
    const u = ex((t - a) / d);
    el.style.opacity = cl((t - a) / 0.22).toFixed(3);
    const bump = 0.04 * Math.sin(cl((t - a) / d) * Math.PI);
    el.style.transform = `${base} scale(${(from + (1 - from) * u + bump).toFixed(4)})`;
  }
  const spread = (n, a, b) => Array.from({ length: n }, (_, i) => n === 1 ? a : a + (b - a) * i / (n - 1));
  // voice sync: data.sync = {index: seconds} (filled automatically from voice lines with "reveal")
  const syncT = (times, d) => {
    if (!d.sync) return times;
    const o = times.slice(), fixed = new Set();
    for (const k in d.sync) { const i = +k; if (i >= 0 && i < o.length) { o[i] = +d.sync[k]; fixed.add(i); } }
    for (let i = 1; i < o.length; i++) if (!fixed.has(i) && o[i] < o[i - 1] + 0.25) o[i] = o[i - 1] + 0.25;
    return o;
  };
  const nf = (v, dec = 0) => {
    const s = Number(v).toFixed(dec).split('.');
    s[0] = s[0].replace(/\B(?=(\d{3})+(?!\d))/g, LANG.th || '\u202F');
    return s.join(LANG.dec || ',');
  };
  const img = (parent, src, style) => { const i = h(parent, 'img', null, style); i.src = src; return i; };

  const ICONS = {
    car: '<path d="M8 30 L12 18 Q14 13 20 13 L36 13 Q42 13 44 18 L48 30 L48 40 L8 40 Z M14 40 v5 M42 40 v5" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linejoin="round"/><circle cx="17" cy="32" r="3" fill="currentColor"/><circle cx="39" cy="32" r="3" fill="currentColor"/>',
    flag: '<path d="M14 46 V8 M14 10 H42 L36 19 L42 28 H14" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linejoin="round"/>',
    building: '<path d="M6 46 H50 M10 46 V22 M46 46 V22 M8 22 H48 L28 9 Z M19 46 V28 M28 46 V28 M37 46 V28" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linejoin="round"/>',
    truck: '<path d="M4 14 H32 V38 H4 Z M32 22 H43 L50 30 V38 H32" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linejoin="round"/><circle cx="14" cy="41" r="4.5" fill="none" stroke="currentColor" stroke-width="3"/><circle cx="42" cy="41" r="4.5" fill="none" stroke="currentColor" stroke-width="3"/>',
    star: '<path d="M28 6 L34 21 L50 22 L37.5 32 L42 47 L28 38.5 L14 47 L18.5 32 L6 22 L22 21 Z" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linejoin="round"/>',
    user: '<circle cx="28" cy="18" r="9" fill="none" stroke="currentColor" stroke-width="3.5"/><path d="M10 46 Q10 30 28 30 Q46 30 46 46" fill="none" stroke="currentColor" stroke-width="3.5"/>',
    users: '<circle cx="20" cy="18" r="7" fill="none" stroke="currentColor" stroke-width="3.2"/><circle cx="38" cy="20" r="6" fill="none" stroke="currentColor" stroke-width="3.2"/><path d="M6 44 Q6 30 20 30 Q34 30 34 44 M32 31 Q48 30 50 44" fill="none" stroke="currentColor" stroke-width="3.2"/>',
    shield: '<path d="M28 6 L46 13 V26 Q46 40 28 48 Q10 40 10 26 V13 Z M20 27 L26 33 L37 21" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linejoin="round"/>',
    wrench: '<path d="M38 8 A11 11 0 0 0 30 24 L10 44 L14 48 L34 28 A11 11 0 0 0 48 18 L41 21 L36 16 Z" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linejoin="round"/>',
    chart: '<path d="M8 46 H50 M14 40 V28 M24 40 V18 M34 40 V24 M44 40 V10" fill="none" stroke="currentColor" stroke-width="4" stroke-linecap="round"/>',
    bolt: '<path d="M32 4 L12 30 H26 L22 50 L44 22 H30 Z" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linejoin="round"/>',
    globe: '<circle cx="28" cy="27" r="20" fill="none" stroke="currentColor" stroke-width="3.5"/><path d="M8 27 H48 M28 7 Q16 27 28 47 Q40 27 28 7" fill="none" stroke="currentColor" stroke-width="3"/>',
    phone: '<rect x="17" y="5" width="22" height="44" rx="5" fill="none" stroke="currentColor" stroke-width="3.5"/><path d="M25 42 H31" stroke="currentColor" stroke-width="3.5"/>',
    heart: '<path d="M28 46 L10 28 Q4 18 12 12 Q20 7 28 16 Q36 7 44 12 Q52 18 46 28 Z" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linejoin="round"/>',
    leaf: '<path d="M10 46 Q10 10 46 8 Q46 44 10 46 Z M10 46 L34 22" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linejoin="round"/>',
    home: '<path d="M6 26 L28 8 L50 26 M12 22 V46 H44 V22 M23 46 V32 H33 V46" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linejoin="round"/>',
    school: '<path d="M4 20 L28 8 L52 20 L28 32 Z M14 26 V38 Q28 46 42 38 V26" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linejoin="round"/>',
    hospital: '<rect x="8" y="8" width="40" height="40" rx="6" fill="none" stroke="currentColor" stroke-width="3.5"/><path d="M28 17 V39 M17 28 H39" stroke="currentColor" stroke-width="4.5"/>',
    money: '<rect x="4" y="14" width="48" height="28" rx="5" fill="none" stroke="currentColor" stroke-width="3.5"/><circle cx="28" cy="28" r="7" fill="none" stroke="currentColor" stroke-width="3.5"/>',
    camera: '<rect x="5" y="15" width="46" height="30" rx="6" fill="none" stroke="currentColor" stroke-width="3.5"/><circle cx="28" cy="30" r="9" fill="none" stroke="currentColor" stroke-width="3.5"/><path d="M19 15 L23 8 H33 L37 15" fill="none" stroke="currentColor" stroke-width="3.5"/>',
    cloud: '<path d="M16 42 Q4 42 6 31 Q8 22 18 23 Q21 11 33 12 Q45 14 45 26 Q53 27 52 35 Q51 42 42 42 Z" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linejoin="round"/>',
    check: '<circle cx="28" cy="27" r="21" fill="none" stroke="currentColor" stroke-width="3.5"/><path d="M18 28 L25 35 L39 20" fill="none" stroke="currentColor" stroke-width="4" stroke-linejoin="round"/>',
    pin: '<path d="M28 50 Q10 30 10 21 A18 18 0 0 1 46 21 Q46 30 28 50 Z" fill="none" stroke="currentColor" stroke-width="3.5"/><circle cx="28" cy="21" r="6" fill="none" stroke="currentColor" stroke-width="3.5"/>'
  };
  const icon = (name, size = 52, color = 'var(--accent)') =>
    `<svg width="${size}" height="${size * 52 / 56}" viewBox="0 0 56 52" style="color:${color}">${ICONS[name] || ICONS.check}</svg>`;
  const colorVar = c => ({ accent: 'var(--accent)', accent2: 'var(--accent2)', alert: 'var(--alert)', text: 'var(--text)', muted: 'var(--muted)' }[c] || c || 'var(--accent)');

  // ---------- background
  let BG = null;
  function background(root, d, ctx) {
    if (ctx.transparent) return null;
    const b = h(root, 'div', 'full', 'background:var(--bg)');
    let im = null;
    if (d.bg_image) {
      im = img(b, d.bg_image, `position:absolute;left:0;top:0;width:${W}px;height:${H}px;object-fit:cover;opacity:${d.bg_opacity == null ? 0.28 : d.bg_opacity};filter:${d.bg_blur ? `blur(${d.bg_blur}px)` : 'none'}`);
    }
    const g = d.grid === false ? null : h(b, 'div', 'grid');
    h(b, 'div', 'glow');
    if (d.bg_image) h(b, 'div', 'full', 'background:linear-gradient(90deg,color-mix(in srgb,var(--bg) 94%,transparent) 0%,color-mix(in srgb,var(--bg) 70%,transparent) 38%,transparent 70%)');
    h(b, 'div', 'full', 'background:radial-gradient(ellipse at 50% 50%,transparent 55%,rgba(0,0,0,.45) 100%)');
    return t => {
      if (g) g.style.transform = `translate(${(-t * 6).toFixed(1)}px,${(-t * 2.5).toFixed(1)}px)`;
      if (im) im.style.transform = `scale(${(1.08 - 0.06 * cl(t / Math.max(1, ctx.dur))).toFixed(4)})`;
    };
  }

  // ---------- scenes
  const SC = {};

  // TITLE / STATEMENT
  SC.title = (root, d, ctx) => {
    const lines = d.lines || [d.title || ''];
    const center = d.align === 'center';
    const size = d.size || (lines.length > 2 ? 104 : 128);
    const x = center ? 160 : 126, w = center ? 1600 : (d.width || 1500);
    const lh = size * 1.12;
    const blockH = (d.eyebrow ? 60 : 0) + lines.length * lh + (d.sub ? 90 : 0);
    let y = d.y != null ? d.y : (d.valign === 'bottom' ? 1000 - blockH : (H - blockH) / 2);
    const eb = d.eyebrow ? h(root, 'div', 'a eyebrow', `left:${x}px;top:${y}px;${center ? `width:${w}px;text-align:center` : ''}`, esc(d.eyebrow)) : null;
    if (eb) y += 60;
    const ins = lines.map((ln, i) => {
      const e = maskLine(root, x, y + i * lh, w, size, rt(ln, d.dot !== false && i === lines.length - 1));
      if (center) { e.parentNode.style.textAlign = 'center'; }
      return e;
    });
    const sub = d.sub ? h(root, 'div', 'a sub', `left:${x + 4}px;top:${y + lines.length * lh + 24}px;width:${w}px;${center ? 'text-align:center' : ''}`, rt(d.sub, false)) : null;
    const st = d.start || 0.15;
    return {
      events: [{ t: 0, kind: 'in' }],
      update(t) {
        if (eb) fadeUp(eb, t, st - 0.05, { dy: 10 });
        ins.forEach((e, i) => maskIn(e, t, st + 0.1 + i * 0.13));
        if (sub) fadeUp(sub, t, st + 0.35 + lines.length * 0.13, { dy: 16 });
      }
    };
  };

  // STAT (animated counter)
  SC.stat = (root, d, ctx) => {
    const x = d.align === 'center' ? 0 : 118, w = d.align === 'center' ? W : 1500;
    const ta = d.align === 'center' ? 'text-align:center;' : '';
    const size = d.size || 230;
    const y0 = d.y != null ? d.y : 300;
    const eb = d.eyebrow ? h(root, 'div', 'a eyebrow', `left:${x + 8}px;top:${y0}px;width:${w}px;${ta}`, esc(d.eyebrow)) : null;
    const col = colorVar(d.color || 'accent');
    const num = h(root, 'div', 'a big', `left:${x}px;top:${y0 + 44}px;width:${w}px;${ta}font-size:${size}px;letter-spacing:-0.045em;font-variant-numeric:tabular-nums`);
    const pre = esc(d.prefix || ''), suf = d.suffix ? `<span style="color:${col}">${esc(d.suffix)}</span>` : '';
    const cap = d.caption ? h(root, 'div', 'a sub', `left:${x + 10}px;top:${y0 + 44 + size * 1.08}px;width:${w - 20}px;${ta}color:var(--text);font-weight:700;font-size:${d.caption_size || 42}px`, rt(d.caption, false)) : null;
    const src = d.source ? h(root, 'div', 'a src', `left:${x + 10}px;top:${y0 + 44 + size * 1.08 + 80}px;width:${w}px;${ta}`, LANG.source + esc(d.source)) : null;
    const [c0, c1] = d.count || [0.35, 0.35 + (d.count_dur || 1.7)];
    const from = d.from || 0, to = Number(d.value), dec = d.decimals || 0;
    const steps = Math.min(36, Math.max(8, Math.round((c1 - c0) * 18)));
    return {
      events: [{ t: 0, kind: 'in' }, { t: c0, kind: 'counter', t1: c1, n: steps }, { t: c1, kind: 'hit', strength: 0.5 }],
      update(t) {
        if (eb) fadeUp(eb, t, 0.05, { dy: 10 });
        const u = eo((t - c0) / (c1 - c0));
        num.innerHTML = `${pre}${nf(lerp(from, to, u), dec)}${suf}`;
        num.style.color = t >= c0 ? 'var(--text)' : 'var(--text)';
        fadeUp(num, t, c0 - 0.15, { dy: 30, d: 0.5 });
        if (cap) fadeUp(cap, t, c1 - 0.4, { dy: 18 });
        if (src) fadeUp(src, t, c1, { dy: 8 });
      }
    };
  };

  // QUESTION / QUOTE (word by word)
  SC.question = (root, d, ctx) => {
    const size = d.size || 76;
    const box = h(root, 'div', 'a big', `left:160px;width:1600px;top:0;text-align:center;font-size:${size}px;line-height:1.25;white-space:normal;letter-spacing:-0.02em`);
    // keep **accent** / __accent2__ / !!alert!! spans across word boundaries
    const words = []; let mode = '';
    typo(d.text || '').split(/[ \t\n]+/).filter(Boolean).forEach(w => {
      let cls = mode, raw = w;
      for (const [mk, c] of [['**', 'acc'], ['__', 'acc2'], ['!!', 'alert']]) {
        if (raw.startsWith(mk)) { raw = raw.slice(2); cls = c; if (!raw.includes(mk)) mode = c; }
        if (raw.includes(mk)) { raw = raw.replace(mk, ''); mode = ''; cls = cls || c; }
      }
      words.push({ w: raw, cls });
    });
    box.innerHTML = words.map(o => `<span class="${o.cls}" style="display:inline-block;margin:0 .03em;opacity:0">${esc(o.w)}</span>`).join(' ');
    box.style.textWrap = 'balance';                      // no orphan word on the last line
    let fs = size;                                       // shrink until it fits on 2 lines (max_lines)
    while (box.offsetHeight > fs * 1.25 * (d.max_lines || 2) + 4 && fs > 44) { fs -= 4; box.style.fontSize = fs + 'px'; }
    box.style.top = ((H - box.offsetHeight) / 2 - (d.sub ? 40 : 0)) + 'px';
    const sub = d.sub ? h(root, 'div', 'a sub', `left:160px;width:1600px;text-align:center;top:${(H + box.offsetHeight) / 2 + 10}px`, rt(d.sub, false)) : null;
    const ws = [...box.children];
    const a = d.start || 0.3, span = d.words_dur || Math.min(1.6, 0.18 * ws.length);
    return {
      events: [{ t: 0, kind: 'in_soft' }].concat(d.swell === false ? [] : [{ t: ctx.dur + (ctx.pre || 0), kind: 'swell_end', len: Math.min(1.6, ctx.dur * 0.4) }]),
      update(t) {
        ws.forEach((w, i) => { const s = a + span * i / Math.max(1, ws.length - 1); w.style.opacity = cl((t - s) / 0.35).toFixed(3); w.style.transform = `translateY(${(10 * (1 - ex((t - s) / 0.5))).toFixed(1)}px)`; });
        box.style.transform = `scale(${(1 + 0.025 * cl(t / ctx.dur)).toFixed(4)})`;
        if (sub) fadeUp(sub, t, a + span + 0.3, { dy: 12 });
      }
    };
  };

  // BRIEF (document card -> our answer)
  SC.brief = (root, d, ctx) => {
    const c = d.card || {};
    const ans = d.answer || null;
    const sw = ans ? (ans.at || Math.max(2.5, ctx.dur - 2.0)) : 1e9;
    const hl = d.highlight_at || Math.min(sw - 1.0, ctx.dur * 0.5);
    const eb = h(root, 'div', 'a eyebrow', 'left:126px;top:300px', esc(d.eyebrow || 'Le brief'));
    const t1 = maskLine(root, 112, 350, 860, d.title_size || 140, rt(d.title || ''));
    const t2 = d.subtitle ? maskLine(root, 118, 350 + (d.title_size || 140) * 1.22, 860, 40, esc(d.subtitle), 'sub', 'color:var(--text);font-weight:700') : null;
    const a1 = ans ? maskLine(root, 112, 360, 880, ans.size || 108, rt(ans.title || LANG.answer)) : null;
    const alogo = ans && ans.logo ? img(root, ans.logo, 'position:absolute;left:118px;top:540px;height:200px;opacity:0;object-fit:contain') : null;
    const card = h(root, 'div', 'card', 'left:1010px;top:200px;width:780px;height:640px;overflow:hidden;opacity:0');
    const hc = c.header_color || 'var(--accent2)';
    h(card, 'div', 'a', `left:0;top:0;width:780px;height:150px;background:${hc}`);
    if (c.logo) img(card, c.logo, 'position:absolute;left:36px;top:15px;height:120px;max-width:380px;object-fit:contain');
    if (c.tag) h(card, 'div', 'a', 'right:40px;top:58px;font-size:22px;font-weight:800;letter-spacing:4px;color:#121212;white-space:nowrap', esc(c.tag));
    h(card, 'div', 'a eyebrow', 'left:52px;top:196px;font-size:22px', esc(c.kicker || LANG.kicker));
    h(card, 'div', 'a', 'left:52px;top:244px;width:680px;font-size:46px;font-weight:800;line-height:1.15', esc(c.heading || ''));
    h(card, 'div', 'a', 'left:52px;top:380px;width:680px;height:1px;background:rgba(255,255,255,.14)');
    const body = String(c.body || '');
    const bodyHtml = esc(body).replace(/\[\[(.+?)\]\]/, '<span style="position:relative;color:var(--text);font-weight:700">$1<span class="hlb" style="position:absolute;left:-4px;bottom:2px;height:14px;width:0;background:color-mix(in srgb,var(--accent) 45%,transparent);z-index:-1"></span></span>');
    h(card, 'div', 'a', 'left:52px;top:414px;width:680px;font-size:34px;font-weight:500;line-height:1.45;color:var(--muted)', bodyHtml);
    const hlb = card.querySelector('.hlb');
    const stamp = ans ? h(card, 'div', 'a eyebrow', 'left:52px;top:584px;font-size:22px;letter-spacing:5px;opacity:0', '→ ' + esc(ans.stamp || LANG.stamp)) : null;
    return {
      events: [{ t: 0, kind: 'in' }, { t: 0.35, kind: 'pop' }, { t: hl, kind: 'scan' }].concat(ans ? [{ t: sw - 0.1, kind: 'whoosh' }, { t: sw + 0.25, kind: 'hit', strength: 0.4, shimmer: true }] : []),
      update(t) {
        fadeUp(eb, t, 0.1, { dy: 10 });
        maskIn(t1, t, 0.2, 0.8, ans ? sw : null);
        if (t2) maskIn(t2, t, 0.55, 0.8, ans ? sw : null);
        if (a1) maskIn(a1, t, sw + 0.25);
        if (alogo) fadeUp(alogo, t, sw + 0.6, { dy: 20, sc: 0.06 });
        const k = ex((t - 0.3) / 0.9), out = eio((t - sw) / 0.7);
        card.style.opacity = cl((t - 0.3) / 0.4);
        card.style.transform = `perspective(1800px) rotateY(${(-16 * (1 - k) - 5 + 3 * cl(t / ctx.dur)).toFixed(2)}deg) translateY(${(70 * (1 - k)).toFixed(1)}px) translateX(${(40 * out).toFixed(1)}px) scale(${(1 - 0.06 * out).toFixed(4)})`;
        if (hlb) hlb.style.width = `calc(${(eio((t - hl) / 0.9) * 100).toFixed(1)}% + 8px)`;
        if (stamp) fadeUp(stamp, t, sw + 0.4, { dy: 12 });
      }
    };
  };

  // FEATURES (product image + callouts)
  SC.features = (root, d, ctx) => {
    const items = d.items || [];
    const times = syncT(d.times || spread(items.length, 0.9, Math.max(1.0, ctx.dur - 1.6)), d);
    const eb = d.eyebrow ? h(root, 'div', 'a eyebrow', 'left:126px;top:150px', esc(d.eyebrow)) : null;
    const tt = d.title ? maskLine(root, 112, 196, 900, d.title_size || 92, rt(d.title)) : null;
    const pic = d.image ? img(root, d.image, 'position:absolute;left:960px;top:150px;width:860px;height:780px;object-fit:contain;filter:drop-shadow(0 40px 80px rgba(0,0,0,.6));opacity:0') : null;
    const top0 = d.title ? 380 : 260, gap = Math.min(150, (900 - top0) / Math.max(1, items.length));
    const rows = items.map((it, i) => {
      const r = h(root, 'div', 'a', `left:126px;top:${top0 + i * gap}px;width:800px;opacity:0`);
      h(r, 'div', 'a', `left:0;top:6px;width:6px;height:${gap - 40}px;border-radius:3px;background:var(--accent)`);
      const l = h(r, 'div', 'a big', 'left:30px;top:0;font-size:44px;letter-spacing:-0.02em', rt(it.label || '', false)); fit(l, 760, 44);
      if (it.sub) { const s = h(r, 'div', 'a sub', 'left:32px;top:58px;font-size:27px;white-space:nowrap', esc(it.sub)); fit(s, 760, 27); }
      return r;
    });
    return {
      events: [{ t: 0, kind: 'in' }].concat(times.map(t => ({ t, kind: 'pop' }))),
      update(t) {
        if (eb) fadeUp(eb, t, 0.05, { dy: 10 });
        if (tt) maskIn(tt, t, 0.15);
        if (pic) { const k = ex((t - 0.2) / 1.0); pic.style.opacity = cl((t - 0.2) / 0.5); pic.style.transform = `translateY(${(50 * (1 - k) + 8 * Math.sin(t * 1.2)).toFixed(1)}px) scale(${(0.94 + 0.06 * k + 0.02 * cl(t / ctx.dur)).toFixed(4)})`; }
        rows.forEach((r, i) => {
          const a = times[i]; const nxt = times[i + 1];
          fadeUp(r, t, a, { dy: 20, d: 0.5 });
          if (nxt != null && t > nxt) r.style.opacity = (lerp(1, 0.5, cl((t - nxt) / 0.4))).toFixed(3);
        });
      }
    };
  };

  // LOOP (value cycle)
  SC.loop = (root, d, ctx) => {
    const nodes = d.nodes || [];
    const n = nodes.length || 1;
    const times = syncT(d.times || spread(n, 0.6, Math.max(1, ctx.dur * 0.62)), d);
    const CX = 1430, CY = 540, R = 290;
    const eb = d.eyebrow ? h(root, 'div', 'a eyebrow', 'left:126px;top:330px', esc(d.eyebrow)) : null;
    const L = (d.lines || []).map((ln, i) => maskLine(root, 112, 390 + i * 86, 860, 66, rt(ln, i === (d.lines.length - 1))));
    const svg = h(root, 'div', 'full', '');
    svg.innerHTML = `<svg width="${W}" height="${H}"><circle cx="${CX}" cy="${CY}" r="${R}" fill="none" stroke="color-mix(in srgb,var(--accent) 14%,transparent)" stroke-width="3"/><circle class="ring" cx="${CX}" cy="${CY}" r="${R}" fill="none" stroke="var(--accent)" stroke-width="4" stroke-linecap="round" pathLength="1" stroke-dasharray="1" stroke-dashoffset="1" transform="rotate(-90 ${CX} ${CY})"/><circle class="sp" r="11" fill="#ffffff" opacity="0"/><circle class="spg" r="30" fill="color-mix(in srgb,var(--accent) 25%,transparent)" opacity="0"/></svg>`;
    const ring = svg.querySelector('.ring'), sp = svg.querySelector('.sp'), spg = svg.querySelector('.spg');
    const hub = h(root, 'div', 'a', `left:${CX - 100}px;top:${CY - 50}px;width:200px;height:100px;border-radius:18px;overflow:hidden;display:flex;align-items:center;justify-content:center;background:${d.center && d.center.bg ? d.center.bg : 'var(--bg2)'};box-shadow:0 0 0 8px color-mix(in srgb,var(--accent2) 14%,transparent),0 20px 60px rgba(0,0,0,.6);opacity:0`);
    if (d.center && d.center.logo) img(hub, d.center.logo, 'width:200px;height:100px;object-fit:contain');
    else h(hub, 'div', null, 'font-size:28px;font-weight:800;text-align:center;padding:0 10px', esc((d.center && d.center.text) || ''));
    const els = nodes.map((nd, i) => {
      const ang = -Math.PI / 2 + i * 2 * Math.PI / n;
      const x = CX + R * Math.cos(ang), y = CY + R * Math.sin(ang);
      const e = h(root, 'div', 'node', `left:${x}px;top:${y}px;opacity:0;${nd.color ? `border-color:${colorVar(nd.color)}` : ''}`);
      h(e, 'div', 'n', nd.color ? `color:${colorVar(nd.color)}` : '', esc(nd.num || String(i + 1).padStart(2, '0')));
      const tt = h(e, 'div', 't', '', esc(nd.title || '')); fit(tt, 258, 27);
      if (nd.sub) { const s = h(e, 'div', 's', '', esc(nd.sub)); fit(s, 258, 21, 15); }
      return e;
    });
    const fracAt = t => { if (t < times[0]) return 0; for (let i = 0; i < n - 1; i++) if (t < times[i + 1]) return (i + eio((t - times[i]) / (times[i + 1] - times[i]))) / n; return Math.min(1, (n - 1 + eio((t - times[n - 1]) / 1.2)) / n); };
    return {
      events: [{ t: 0, kind: 'in' }].concat(times.map(t => ({ t, kind: 'pop' }))),
      update(t) {
        if (eb) fadeUp(eb, t, 0.1, { dy: 10 });
        L.forEach((e, i) => maskIn(e, t, 0.25 + i * (d.line_gap || 1.2)));
        const f = fracAt(t);
        ring.setAttribute('stroke-dashoffset', (1 - f).toFixed(4));
        const th = -Math.PI / 2 + f * 2 * Math.PI; const sx = CX + R * Math.cos(th), sy = CY + R * Math.sin(th);
        [sp, spg].forEach(e => { e.setAttribute('cx', sx.toFixed(1)); e.setAttribute('cy', sy.toFixed(1)); e.setAttribute('opacity', (cl((t - times[0]) / 0.3) * (f < 1 ? 1 : 0.4)).toFixed(2)); });
        popIn(hub, t, 0.2, { from: 0.8 });
        els.forEach((e, i) => popIn(e, t, times[i]));
      }
    };
  };

  // NETWORK (hub and spokes)
  SC.network = (root, d, ctx) => {
    const items = d.items || []; const n = items.length;
    const badges = d.badges || [];
    const times = syncT(d.times || spread(n, 1.0, Math.max(1.5, ctx.dur * 0.55)), d);
    const btimes = d.badge_times || spread(badges.length, Math.max(1.2, ctx.dur * 0.68), Math.max(1.5, ctx.dur * 0.85));
    const HX = 1430, HY = 540;
    const eb = d.eyebrow ? h(root, 'div', 'a eyebrow', 'left:126px;top:330px', esc(d.eyebrow)) : null;
    const L = (d.lines || []).map((ln, i) => maskLine(root, 112, 390 + i * 86, 860, 66, rt(ln, i === (d.lines.length - 1))));
    const svgw = h(root, 'div', 'full');
    const hub = h(root, 'div', 'a', `left:${HX - 100}px;top:${HY - 50}px;width:200px;height:100px;border-radius:18px;overflow:hidden;display:flex;align-items:center;justify-content:center;background:${d.hub && d.hub.bg ? d.hub.bg : 'var(--bg2)'};box-shadow:0 0 0 8px color-mix(in srgb,var(--accent2) 14%,transparent),0 20px 60px rgba(0,0,0,.6);opacity:0`);
    if (d.hub && d.hub.logo) img(hub, d.hub.logo, 'width:200px;height:100px;object-fit:contain');
    else h(hub, 'div', null, 'font-size:28px;font-weight:800;text-align:center', esc((d.hub && d.hub.text) || ''));
    const pills = items.map((it, i) => {
      const p = h(root, 'div', 'pill', 'opacity:0', icon(it.icon || 'check') + esc(it.label || ''));
      return p;
    });
    let s = '';
    const pos = items.map((it, i) => {
      const ang = -Math.PI / 2 + i * 2 * Math.PI / Math.max(n, 1);
      let x = HX + 400 * Math.cos(ang), y = HY + 335 * Math.sin(ang);
      const w = pills[i].offsetWidth;
      let left = Math.max(990, Math.min(1880 - w, x - w / 2));
      pills[i].style.left = left + 'px'; pills[i].style.top = y + 'px';
      const ex2 = left + w / 2;
      s += `<line class="spk" x1="${HX}" y1="${HY}" x2="${ex2}" y2="${y}" stroke="color-mix(in srgb,var(--accent) 55%,transparent)" stroke-width="3" pathLength="1" stroke-dasharray="1" stroke-dashoffset="1"/><circle class="pk" r="7" fill="var(--accent2)" opacity="0"/>`;
      return [ex2, y];
    });
    svgw.innerHTML = `<svg width="${W}" height="${H}">${s}</svg>`;
    const spk = [...svgw.querySelectorAll('.spk')], pks = [...svgw.querySelectorAll('.pk')];
    const bels = badges.map((b, i) => {
      const c = colorVar(b.color || (i % 2 ? 'accent2' : 'accent'));
      return h(root, 'div', 'badge', `left:118px;top:${620 + i * 96}px;opacity:0;background:color-mix(in srgb,${c} 14%,transparent);border:1.5px solid ${c}`, rt(b.text || '', false));
    });
    return {
      events: [{ t: 0, kind: 'in' }].concat(times.map(t => ({ t, kind: 'pop' })), btimes.map(t => ({ t, kind: 'pop_hi' }))),
      update(t) {
        if (eb) fadeUp(eb, t, 0.1, { dy: 10 });
        L.forEach((e, i) => maskIn(e, t, 0.25 + i * (d.line_gap || 1.2)));
        popIn(hub, t, 0.3, { from: 0.8 });
        pos.forEach(([x, y], i) => {
          const a = times[i];
          spk[i].setAttribute('stroke-dashoffset', (1 - eio((t - a + 0.25) / 0.45)).toFixed(4));
          popIn(pills[i], t, a, { from: 0.86 });
          const ph = fr1((t - a - 0.6) / 1.3); const on = t > a + 0.6;
          pks[i].setAttribute('opacity', on ? Math.sin(ph * Math.PI).toFixed(2) : 0);
          pks[i].setAttribute('cx', (HX + (x - HX) * (1 - ph)).toFixed(1)); pks[i].setAttribute('cy', (HY + (y - HY) * (1 - ph)).toFixed(1));
        });
        bels.forEach((b, i) => fadeUp(b, t, btimes[i], { dy: 18 }));
      }
    };
  };

  // STEPS (timeline / roadmap / pilot)
  SC.steps = (root, d, ctx) => {
    const st = d.steps || []; const n = st.length || 1;
    const times = syncT(d.times || spread(n, 0.9, Math.max(1, ctx.dur * 0.62)), d);
    const xs = spread(n, 330, 1590);
    if (d.bg_image) { /* handled by background */ }
    const eb = d.eyebrow ? h(root, 'div', 'a eyebrow', 'left:126px;top:150px', esc(d.eyebrow)) : null;
    const tt = maskLine(root, 112, 196, 1700, d.title_size || 104, rt(d.title || ''));
    const line = h(root, 'div', 'full');
    line.innerHTML = `<svg width="${W}" height="${H}"><line x1="${xs[0]}" y1="480" x2="${xs[n - 1]}" y2="480" stroke="rgba(255,255,255,.12)" stroke-width="4"/><line class="pg" x1="${xs[0]}" y1="480" x2="${xs[n - 1]}" y2="480" stroke="var(--accent)" stroke-width="4" stroke-linecap="round" pathLength="1" stroke-dasharray="1" stroke-dashoffset="1"/></svg>`;
    const pg = line.querySelector('.pg');
    const last = n - 1;
    const colW = Math.min(470, 1660 / n - 20);
    const dots = [], cols = [], lineEls = [];
    st.forEach((s, i) => {
      const c = i === last ? 'var(--accent2)' : 'var(--accent)';
      dots.push(h(root, 'div', 'dot', `left:${xs[i]}px;top:480px;opacity:0;border-color:${c};color:${c};background:var(--bg)`, String(i + 1)));
      const col = h(root, 'div', 'a', `left:${xs[i] - (n === 1 ? 0 : (i === 0 ? 204 : (i === last ? colW - 204 : colW / 2)))}px;top:560px;width:${colW}px;opacity:0`);
      h(col, 'div', null, `font-size:22px;font-weight:800;letter-spacing:6px;color:${c};text-transform:uppercase`, esc(s.key || ''));
      const ttl = h(col, 'div', null, 'font-size:46px;font-weight:800;margin-top:10px;letter-spacing:-1px;white-space:nowrap', esc(s.title || '')); fit(ttl, colW, 46);
      const ls = (s.lines || []).map(l => h(col, 'div', null, 'font-size:30px;font-weight:700;margin-top:14px;color:var(--text);opacity:0', esc(l)));
      cols.push(col); lineEls.push(ls);
    });
    const ltimes = d.line_times || st.map((s, i) => (s.lines || []).map((_, k) => times[i] + 0.45 + k * 0.8));
    return {
      events: [{ t: 0, kind: 'in' }].concat(times.map(t => ({ t, kind: 'pop' })), ltimes.flat().map(t => ({ t, kind: 'tick' }))),
      update(t) {
        if (eb) fadeUp(eb, t, 0.1, { dy: 10 });
        maskIn(tt, t, 0.2);
        let pr = 0; for (let i = 1; i < n; i++) if (t > times[i]) pr = (i - 1 + eio((t - times[i]) / 0.9)) / (n - 1);
        pg.setAttribute('stroke-dashoffset', (1 - pr).toFixed(4));
        dots.forEach((e, i) => { popIn(e, t, times[i], { from: 0.6 }); const on = t > times[i] + 0.3; e.style.background = on ? (i === last ? 'var(--accent2)' : 'var(--accent)') : 'var(--bg)'; e.style.color = on ? 'var(--bg)' : (i === last ? 'var(--accent2)' : 'var(--accent)'); });
        cols.forEach((c, i) => fadeUp(c, t, times[i] + 0.1, { dy: 24 }));
        lineEls.forEach((ls, i) => ls.forEach((e, k) => fadeUp(e, t, ltimes[i][k], { dy: 16, d: 0.5 })));
      }
    };
  };

  // TEAM (portrait panels — keep >= 10 s so names can be read)
  SC.team = (root, d, ctx) => {
    const m = d.members || []; const n = Math.max(1, m.length);
    const gap = 6, pw = (W - gap * (n - 1)) / n;
    const panels = m.map((p, i) => {
      const x = i * (pw + gap);
      const pan = h(root, 'div', 'a', `left:${x}px;top:0;width:${pw}px;height:${H}px;overflow:hidden;background:linear-gradient(180deg,var(--bg2),var(--bg));opacity:0`);
      if (p.bg) img(pan, p.bg, `position:absolute;left:0;top:0;width:${pw}px;height:${H}px;object-fit:cover;opacity:.35`);
      const ph = p.photo ? img(pan, p.photo, `position:absolute;left:0;top:${d.photo_top || 60}px;width:${pw}px;height:${H - 200}px;object-fit:cover;object-position:50% ${p.focus || '18%'}`) : null;
      h(pan, 'div', 'a', `left:0;top:${H - 430}px;width:${pw}px;height:430px;background:linear-gradient(180deg,transparent 0%,color-mix(in srgb,var(--bg) 88%,transparent) 45%,var(--bg) 100%)`);
      h(pan, 'div', 'a', `left:${pw / 2 - 22}px;top:${H - 182}px;width:44px;height:3px;background:var(--accent)`);
      const nm = h(pan, 'div', 'a', `left:10px;width:${pw - 20}px;top:${H - 160}px;text-align:center;font-size:36px;font-weight:800;white-space:nowrap`, esc(p.name || '')); fit(nm, pw - 24, 36, 20);
      const rl = h(pan, 'div', 'a', `left:10px;width:${pw - 20}px;top:${H - 108}px;text-align:center;font-size:23px;font-weight:500;color:var(--accent);white-space:nowrap;letter-spacing:.5px`, esc(p.role || '')); fit(rl, pw - 24, 23, 14);
      return { pan, ph, nm, rl };
    });
    const eb = d.eyebrow ? h(root, 'div', 'a eyebrow', `left:0;width:${W}px;text-align:center;top:44px;text-shadow:0 2px 12px rgba(0,0,0,.6)`, esc(d.eyebrow)) : null;
    const st = d.start || 0.2, stag = d.stagger || 0.14;
    return {
      events: [{ t: 0, kind: 'in_soft' }].concat(panels.map((_, i) => ({ t: st + i * stag, kind: 'swoosh' }))),
      update(t) {
        if (eb) fadeUp(eb, t, st + 0.3, { dy: 10 });
        panels.forEach((p, i) => {
          const a = st + i * stag; const k = ex((t - a) / 0.8);
          p.pan.style.opacity = cl((t - a) / 0.35);
          p.pan.style.transform = `translateY(${(80 * (1 - k)).toFixed(1)}px)`;
          if (p.ph) p.ph.style.transform = `scale(${(1.0 + 0.045 * cl(t / ctx.dur)).toFixed(4)})`;
          fadeUp(p.nm, t, a + 0.45, { dy: 14 }); fadeUp(p.rl, t, a + 0.6, { dy: 10 });
        });
      }
    };
  };

  // LOGO end card / sting
  SC.logo = (root, d, ctx) => {
    const a = d.start || 0.3;
    const hasP = !!d.partner_logo;
    // logos in a centred row: any aspect ratio, never colliding with the connector
    const row = h(root, 'div', 'a', `left:0;top:${d.row_top || 250}px;width:${W}px;height:300px;display:flex;align-items:center;justify-content:center;gap:56px`);
    const lg = img(row, d.logo, `position:relative;width:auto;height:auto;max-width:${hasP ? 620 : 900}px;max-height:${hasP ? 250 : 300}px;opacity:0`);
    const x = hasP ? h(row, 'div', 'big', 'position:relative;font-size:90px;color:var(--muted);opacity:0', esc(d.connector || '×')) : null;
    const pl = hasP ? img(row, d.partner_logo, 'position:relative;width:auto;height:auto;max-width:440px;max-height:190px;opacity:0') : null;
    const ring = h(root, 'div', 'a', 'left:960px;top:400px;width:0;height:0;border-radius:50%;border:3px solid var(--accent);opacity:0');
    const nm = d.name ? h(root, 'div', 'a', `left:0;width:${W}px;top:580px;text-align:center;font-size:40px;font-weight:800`, esc(d.name)) : null;
    const tg = d.tagline ? h(root, 'div', 'a sub', `left:160px;width:1600px;top:${d.name ? 640 : 600}px;text-align:center;color:var(--text);font-weight:700;font-size:40px`, rt(d.tagline, false)) : null;
    const fin = d.final ? h(root, 'div', 'a big', `left:0;width:${W}px;top:${d.tagline ? 720 : 660}px;text-align:center;font-size:${d.final_size || 96}px`, rt(d.final)) : null;
    const fa = d.final_at || a + 1.6;
    let cx = null;
    return {
      events: [{ t: a, kind: 'sting' }].concat(fin ? [{ t: fa, kind: 'pop_hi' }] : []),
      update(t) {
        if (cx === null) { const r = lg.getBoundingClientRect(); cx = r.left + r.width / 2; }
        const k = ex((t - a) / 0.9);
        lg.style.opacity = cl((t - a) / 0.3); lg.style.transform = `scale(${(0.7 + 0.3 * k + 0.012 * Math.sin(t * 1.6) * cl((t - a) / 1)).toFixed(4)})`;
        const rp = cl((t - a) / 1.1); const R = 40 + rp * 520;
        ring.style.opacity = (rp > 0 && rp < 1 ? (1 - rp) * 0.8 : 0).toFixed(3); ring.style.width = ring.style.height = (2 * R) + 'px'; ring.style.left = cx - R + 'px'; ring.style.top = 400 - R + 'px';
        if (x) { x.style.opacity = cl((t - a - 0.5) / 0.4); x.style.transform = `scale(${(0.7 + 0.3 * ex((t - a - 0.5) / 0.6)).toFixed(4)})`; }
        if (pl) { pl.style.opacity = cl((t - a - 0.7) / 0.4); pl.style.transform = `scale(${(0.88 + 0.12 * ex((t - a - 0.7) / 0.7)).toFixed(4)})`; }
        if (nm) fadeUp(nm, t, a + 0.7, { dy: 14 });
        if (tg) fadeUp(tg, t, a + 1.0, { dy: 14 });
        if (fin) fadeUp(fin, t, fa, { dy: 18, sc: 0.04 });
      }
    };
  };

  // TRIO (three panels with one strong word each)
  SC.trio = (root, d, ctx) => {
    const it = d.items || []; const n = Math.max(1, it.length);
    const times = syncT(d.times || spread(n, 0.15, Math.max(0.3, ctx.dur * 0.45)), d);
    const gap = 8, pw = (W - gap * (n - 1)) / n;
    const P = it.map((p, i) => {
      const pan = h(root, 'div', 'a', `left:${i * (pw + gap)}px;top:0;width:${pw}px;height:${H}px;overflow:hidden;background:var(--bg2);opacity:0`);
      const im = p.image ? img(pan, p.image, `position:absolute;left:0;top:0;width:${pw}px;height:${H}px;object-fit:cover`) : null;
      h(pan, 'div', 'a', `left:0;top:${H * 0.45}px;width:${pw}px;height:${H * 0.55}px;background:linear-gradient(180deg,transparent,color-mix(in srgb,var(--bg) 92%,transparent))`);
      const eb = p.eyebrow ? h(pan, 'div', 'a eyebrow', `left:40px;top:${H - 210}px;font-size:20px`, esc(p.eyebrow)) : null;
      const w = maskLine(pan, 32, H - 175, pw - 50, p.size || 84, rt(p.word || ''));
      return { pan, im, eb, w };
    });
    return {
      events: times.map(t => ({ t, kind: 'swoosh' })),
      update(t) {
        P.forEach((p, i) => {
          const a = times[i]; p.pan.style.opacity = cl((t - a) / 0.3);
          if (p.im) p.im.style.transform = `scale(${(1.1 - 0.08 * cl((t - a) / Math.max(1, ctx.dur))).toFixed(4)})`;
          if (p.eb) fadeUp(p.eb, t, a + 0.3, { dy: 8 });
          maskIn(p.w, t, a + 0.25);
        });
      }
    };
  };

  // SCREEN (product / platform screenshot in a floating window)
  SC.screen = (root, d, ctx) => {
    const right = d.side !== 'left';
    const win = h(root, 'div', 'a', `left:${right ? 760 : 120}px;top:150px;width:1040px;height:${d.height || 660}px;border-radius:18px;overflow:hidden;background:#fff;box-shadow:0 60px 140px rgba(0,0,0,.6),0 0 0 1px rgba(255,255,255,.08);opacity:0`);
    h(win, 'div', 'a', 'left:0;top:0;width:1040px;height:38px;background:#E9EEF3', '<div style="position:absolute;left:16px;top:13px;width:12px;height:12px;border-radius:50%;background:#FF5F57;box-shadow:20px 0 0 #FEBC2E,40px 0 0 #28C840"></div>');
    if (d.image) img(win, d.image, `position:absolute;left:0;top:38px;width:1040px;height:${(d.height || 660) - 38}px;object-fit:cover;object-position:${d.focus || '50% 0%'}`);
    const eb = d.eyebrow ? h(root, 'div', 'a eyebrow', `left:${right ? 126 : 1240}px;top:${d.caption_y || 840}px`, esc(d.eyebrow)) : null;
    const tt = d.title ? maskLine(root, right ? 112 : 1226, (d.caption_y || 840) + 44, 680, d.title_size || 72, rt(d.title)) : null;
    const tilt = d.tilt == null ? -9 : d.tilt;
    return {
      events: [{ t: 0, kind: 'in' }],
      update(t) {
        const k = ex((t - 0.1) / 1.0);
        win.style.opacity = cl((t - 0.1) / 0.4);
        win.style.transform = `perspective(2200px) rotateY(${((right ? 1 : -1) * (tilt * (1 - 0.35 * cl(t / ctx.dur)))).toFixed(2)}deg) translateY(${(60 * (1 - k)).toFixed(1)}px) scale(${(0.94 + 0.06 * k).toFixed(4)})`;
        if (eb) fadeUp(eb, t, 0.4, { dy: 10 });
        if (tt) maskIn(tt, t, 0.5);
      }
    };
  };

  // CAPTION (transparent overlay for footage / stills)
  SC.caption = (root, d, ctx) => {
    const pos = d.position || 'bl';
    const top = pos[0] === 't';
    if (d.scrim !== false) h(root, 'div', 'full', top ? 'background:radial-gradient(ellipse at 8% 4%,rgba(2,10,20,.85) 0%,rgba(2,10,20,.5) 30%,transparent 60%)' : 'background:radial-gradient(ellipse at 6% 96%,rgba(2,10,20,.9) 0%,rgba(2,10,20,.6) 32%,transparent 64%)');
    const size = d.size || 96;
    const lines = d.lines || (d.title ? [d.title] : []);
    const lh = size * 1.1;
    const y0 = top ? 110 : 1000 - lines.length * lh;
    const eb = d.eyebrow ? h(root, 'div', 'a eyebrow', `left:126px;top:${y0 - 52}px;font-size:24px;text-shadow:0 2px 14px rgba(0,0,0,.5)`, esc(d.eyebrow)) : null;
    const L = lines.map((ln, i) => maskLine(root, 112, y0 + i * lh, d.width || 1300, size, rt(ln, i === lines.length - 1), 'big', 'text-shadow:0 4px 30px rgba(0,0,0,.45)'));
    const a = d.start || 0.25;
    const out = d.out;   // optional exit time
    return {
      events: [],
      update(t) {
        if (eb) fadeUp(eb, t, a - 0.1, { dy: 10, out });
        L.forEach((e, i) => maskIn(e, t, a + i * 0.12, 0.8, out));
      }
    };
  };

  // ---------- public API
  let CUR = null, CTX = null, CAM = null, PRE = 0;
  window.VMD = {
    scenes: Object.keys(SC),
    async build(cfg) {
      const r = document.documentElement.style;
      const b = cfg.brand || {};
      for (const [k, v] of Object.entries({ bg: b.bg, bg2: b.bg2, accent: b.accent, accent2: b.accent2, alert: b.alert, text: b.text, muted: b.muted }))
        if (v) r.setProperty('--' + k, v);
      if (b.font) r.setProperty('--font', b.font);
      document.body.style.background = cfg.transparent ? 'transparent' : (b.bg || '');
      try { await Promise.all(['500', '700', '800'].map(w => document.fonts.load(w + ' 100px VMD'))); } catch (e) { }
      await document.fonts.ready;
      const stage = document.getElementById('stage'); stage.innerHTML = '';
      CTX = { dur: cfg.dur || 5, transparent: !!cfg.transparent };
      PRE = cfg.transparent ? 0 : (cfg.preroll == null ? 0.3 : +cfg.preroll);   // start mid-entrance: no empty frame at the cut
      CTX.pre = PRE;
      LANG = L10N[String(cfg.lang || 'fr').slice(0, 2)] || L10N.en;
      const d = cfg.data || {};
      BG = background(stage, d, CTX);
      const layer = h(stage, 'div', 'full');
      // living picture: a slow camera push on every opaque scene (data.camera = 0 to disable, 0.05 for more)
      CAM = { el: layer, amt: CTX.transparent ? 0 : (d.camera == null ? 0.03 : +d.camera) };
      layer.style.transformOrigin = d.camera_origin || '50% 50%';
      const fn = SC[cfg.scene];
      if (!fn) throw new Error('Unknown scene: ' + cfg.scene + ' (available: ' + Object.keys(SC).join(', ') + ')');
      CUR = fn(layer, d, CTX);
      await Promise.all([...document.images].map(i => i.decode().catch(() => { console.warn('image failed: ' + i.src); })));
      return true;
    },
    render(t) {
      if (BG) BG(t);
      if (CAM && CAM.amt) CAM.el.style.transform = `scale(${(1 + CAM.amt * Math.min(1, Math.max(0, t / CTX.dur))).toFixed(5)})`;
      CUR.update(t + PRE);
    },
    events() {   // scene time -> segment time (minus preroll)
      return ((CUR && CUR.events) || []).map(e => Object.assign({}, e, { t: Math.max(0, e.t - PRE) }, e.t1 != null ? { t1: Math.max(0, e.t1 - PRE) } : {}));
    },
    preroll() { return PRE; }
  };
})();
