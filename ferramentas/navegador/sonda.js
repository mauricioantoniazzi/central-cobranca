(function () {
  const W = window.innerWidth, out = { largura: W, problemas: [] };
  const add = (tipo, el, detalhe) => out.problemas.push({ tipo, el: desc(el), detalhe });
  function desc(el) {
    let s = el.tagName.toLowerCase();
    if (el.id) s += '#' + el.id;
    if (el.className && typeof el.className === 'string') s += '.' + el.className.trim().split(/\s+/).join('.');
    const t = (el.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 50);
    return s + ' "' + t + '"';
  }
  const de = document.documentElement;
  out.scrollWidth = de.scrollWidth; out.scrollHeight = de.scrollHeight;
  if (de.scrollWidth > W + 1) add('pagina-com-rolagem-horizontal', de, 'scrollWidth=' + de.scrollWidth + ' > ' + W);
  const dentroDeRolagem = el => { for (let p = el.parentElement; p; p = p.parentElement) { const o = getComputedStyle(p).overflowX; if (o === 'auto' || o === 'scroll') return p; } return null; };
  document.querySelectorAll('body *').forEach(el => {
    const cs = getComputedStyle(el); if (cs.display === 'none' || cs.visibility === 'hidden') return;
    const r = el.getBoundingClientRect(); if (r.width === 0 && r.height === 0) return;
    if (el.closest('svg') && el.tagName.toLowerCase() !== 'svg') return;
    if (r.right > W + 1 && !dentroDeRolagem(el)) add('saiu-da-tela', el, 'right=' + Math.round(r.right) + ' W=' + W);
    if (r.left < -1 && !dentroDeRolagem(el)) add('saiu-pela-esquerda', el, 'left=' + Math.round(r.left));
    if ((cs.overflowX === 'hidden' || cs.overflow === 'hidden' || cs.textOverflow === 'ellipsis') && el.scrollWidth > el.clientWidth + 1)
      add('texto-cortado', el, 'scrollWidth=' + el.scrollWidth + ' clientWidth=' + el.clientWidth);
    if (el.tagName === 'BUTTON' || el.tagName === 'A' && el.classList.contains('bt')) {
      const lh = parseFloat(cs.lineHeight) || parseFloat(cs.fontSize) * 1.2;
      if (r.height > lh * 1.9 + parseFloat(cs.paddingTop) + parseFloat(cs.paddingBottom)) add('botao-quebrou-de-linha', el, 'altura=' + Math.round(r.height));
    }
    if ((el.tagName === 'TD' || el.tagName === 'TH') && r.width < 52 && (el.textContent || '').trim().length > 6)
      add('coluna-espremida', el, 'largura=' + Math.round(r.width));
  });
  // valores R$ quebrados entre linhas em células de tabela
  document.querySelectorAll('td, .kpi b, .h b, .ind .v, .din').forEach(el0 => {
    const el = el0.querySelector && el0.querySelector('.din') ? el0.querySelector('.din') : el0;
    const t = el.textContent || ''; const m = t.match(/R\$\s*[\d.]+(,\d\d)?/);
    if (!m) return; const rg = document.createRange(); rg.selectNodeContents(el);
    const rects = Array.from(rg.getClientRects());
    const tops = new Set(rects.map(x => Math.round(x.top)));
    if (t.trim().length < 18 && tops.size > 1) add('valor-quebrado-em-linhas', el, 'linhas=' + tops.size);
  });
  // rótulos de SVG sobrepostos
  document.querySelectorAll('svg').forEach(svg => {
    const ts = Array.from(svg.querySelectorAll('text')).map(t => ({ t, r: t.getBoundingClientRect(), s: t.textContent }));
    for (let i = 0; i < ts.length; i++) for (let j = i + 1; j < ts.length; j++) {
      const a = ts[i].r, b = ts[j].r; if (!a.width || !b.width) continue;
      const ix = Math.min(a.right, b.right) - Math.max(a.left, b.left), iy = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
      if (ix > 2 && iy > 6) out.problemas.push({ tipo: 'rotulo-svg-sobreposto', el: 'svg', detalhe: '"' + ts[i].s + '" x "' + ts[j].s + '"' });
    }
    const sr = svg.getBoundingClientRect();
    ts.forEach(o => { if (o.r.right > sr.right + 1 || o.r.left < sr.left - 1 || o.r.top < sr.top - 1 || o.r.bottom > sr.bottom + 1) out.problemas.push({ tipo: 'rotulo-svg-fora-do-quadro', el: 'svg', detalhe: '"' + o.s + '"' }); });
    out.svgs = (out.svgs || 0) + 1;
  });
  // fonte muito pequena
  let minimo = 99; document.querySelectorAll('body *').forEach(el => { if (el.children.length === 0 && (el.textContent || '').trim()) { const f = parseFloat(getComputedStyle(el).fontSize); if (f < minimo) minimo = f; } });
  out.menor_fonte = minimo;
  // contagem de elementos com mesma classe usada em contextos distintos (pista de colisão de nomes)
  return JSON.stringify(out);
})()
