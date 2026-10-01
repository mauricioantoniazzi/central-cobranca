/* Central de Crédito e Cobrança — comportamento das telas (sem biblioteca, sem rede além da própria Central).
   Regra de ouro: a página já nasce completa e legível SEM este arquivo. Aqui só entram conveniências:
   busca/filtro/ordem da fila, "já liguei", modo telão, contagem animada do número grande, régua (lista + texto), copiar.
   No arquivo único (window.CENTRAL_ARQUIVO = true) nada vai para servidor: as marcações ficam só neste navegador. */
(function () {
  'use strict';
  var ARQUIVO = !!window.CENTRAL_ARQUIVO;
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var REDUZ = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;

  function guardar(chave, valor) { try { localStorage.setItem('central.' + chave, JSON.stringify(valor)); } catch (e) { /* sem armazenamento: segue sem lembrar */ } }
  function ler(chave, padrao) { try { var v = localStorage.getItem('central.' + chave); return v === null ? padrao : JSON.parse(v); } catch (e) { return padrao; } }
  function sem(s) { return (s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase(); }
  function reais(n) { return 'R$ ' + Math.round(n).toLocaleString('pt-BR'); }

  var temporizador;
  function aviso(texto, desfazer) {
    var t = $('#toast'); if (!t) return;
    t.textContent = texto + ' ';
    if (desfazer) {
      var b = document.createElement('button'); b.type = 'button'; b.className = 'btn suave'; b.textContent = 'Desfazer';
      b.onclick = function () { t.classList.remove('on'); desfazer(); };
      t.appendChild(b);
    }
    t.classList.add('on'); clearTimeout(temporizador);
    temporizador = setTimeout(function () { t.classList.remove('on'); }, desfazer ? 9000 : 3500);
  }
  window.CentralAviso = aviso;

  function iniciarPagina() {
  /* ---------------------------------------------------------------- número grande: cabe na caixa, qualquer que seja o tamanho do valor */
  var cabe = function () {
    $$('.grande').forEach(function (el) {
      el.style.fontSize = '';
      var fs = parseFloat(getComputedStyle(el).fontSize);
      while (el.scrollWidth > el.clientWidth && fs > 22) { fs -= 2; el.style.fontSize = fs + 'px'; }
    });
  };
  cabe();
  if (!window.__cabeLigado) { window.__cabeLigado = true; window.addEventListener('resize', function () { $$('.grande').forEach(function (el) { el.style.fontSize = ''; }); cabe(); }); }
  if (document.fonts && document.fonts.load) { document.fonts.load('700 1em Unbounded').then(cabe, function () {}); }
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(cabe);
  window.addEventListener('load', cabe);

  /* ---------------------------------------------------------------- número grande: sobe até o valor (o texto final já está na página) */
  $$('[data-conta]').forEach(function (el) {
    var alvo = parseInt(el.getAttribute('data-conta'), 10), final = el.textContent;
    if (REDUZ || !isFinite(alvo) || alvo < 1000) return;
    var ini = performance.now(), dur = 900;
    function passo(t) {
      var k = Math.min(1, (t - ini) / dur), e = 1 - Math.pow(1 - k, 3);
      el.textContent = k >= 1 ? final : reais(alvo * (0.7 + 0.3 * e));
      if (k < 1) requestAnimationFrame(passo);
    }
    requestAnimationFrame(passo);
    setTimeout(function () { el.textContent = final; }, dur + 400); // se a animação não rodar, o número certo aparece do mesmo jeito
  });

  /* ---------------------------------------------------------------- Hoje: busca, filtro, ordem e "já liguei" */
  var fila = $('#fila');
  if (fila) {
    var cartoes = $$('.cartao', fila), filtro = 'todos';
    var FATOR = parseFloat(fila.getAttribute('data-fator') || '0.35');
    var ligados = ler('ligados', {});      // {codigo: marca de tempo}; só vale no arquivo único ou até recarregar
    var registros = {};                     // codigo -> id do registro na Central (para desfazer)
    var agora = function () { return Date.now(); };
    function efetivo(c) {
      var cod = c.getAttribute('data-cod'), base = parseFloat(c.getAttribute('data-base') || '0');
      var recente = c.getAttribute('data-recente') === '1';
      var meu = ARQUIVO && ligados[cod] && agora() - ligados[cod] < 48 * 3600e3;
      var nesta = !ARQUIVO && registros[cod];
      return (recente || meu || nesta) ? base * FATOR : base;
    }
    function foiLigado(c) {
      var cod = c.getAttribute('data-cod');
      return c.getAttribute('data-recente') === '1' || !!registros[cod] || (ARQUIVO && ligados[cod] && agora() - ligados[cod] < 48 * 3600e3);
    }
    function aplicar() {
      var q = sem(($('#busca') || {}).value || ''), ordem = ($('#ordem') || {}).value || 'fila';
      var lista = cartoes.slice();
      var chaves = {
        fila: function (a, b) { return efetivo(b) - efetivo(a) || num(a, 'pos') - num(b, 'pos'); },
        valor: function (a, b) { return num(b, 'valor') - num(a, 'valor'); },
        dias: function (a, b) { return num(b, 'dias') - num(a, 'dias'); },
        indice: function (a, b) { return num(b, 'indice') - num(a, 'indice'); },
        nome: function (a, b) { return a.getAttribute('data-nome').localeCompare(b.getAttribute('data-nome'), 'pt-BR'); }
      };
      lista.sort(chaves[ordem] || chaves.fila);
      var visiveis = 0, n = 0, k = 0;
      lista.forEach(function (c) {
        fila.appendChild(c);
        var bate = (!q || sem(c.getAttribute('data-nome')).indexOf(q) >= 0) &&
          (filtro === 'todos' || (filtro === 'alto' && c.getAttribute('data-risco') === 'alto') || (filtro === 'livre' && !foiLigado(c)));
        c.classList.toggle('escondido', !bate);
        c.classList.toggle('ligado', foiLigado(c));
        if (bate) {
          visiveis++;
          var cheio = k < 3;          // os três primeiros cartões visíveis: frase em duas linhas e botões; os demais, uma linha e só links
          c.classList.toggle('simples', !cheio);
          var l2 = $('.l2', c); if (l2) l2.textContent = cheio ? (c.getAttribute('data-l2') || '') : '';
          k++;
        }
      });
      if (ordem === 'fila') {           // na ordem da fila, a posição e o "comece por aqui" acompanham quem foi marcado
        lista.forEach(function (c) { n++; var p = $('.pos', c); if (p) p.textContent = n; c.classList.toggle('primeiro', n === 1); });
      }
      var vazio = $('#vazio'); if (vazio) vazio.classList.toggle('escondido', visiveis > 0);
      var ct = $('#contagem'); if (ct) ct.textContent = visiveis + ' de ' + cartoes.length + (cartoes.length === 1 ? ' cliente' : ' clientes');
    }
    function num(c, k) { return parseFloat(c.getAttribute('data-' + k)) || 0; }
    var busca = $('#busca'); if (busca) busca.addEventListener('input', aplicar);
    var ord = $('#ordem'); if (ord) ord.addEventListener('change', aplicar);
    $$('[data-filtro]').forEach(function (b) {
      b.addEventListener('click', function () {
        filtro = b.getAttribute('data-filtro');
        $$('[data-filtro]').forEach(function (x) { x.setAttribute('aria-pressed', x === b ? 'true' : 'false'); });
        aplicar();
      });
    });
    fila.addEventListener('click', function (e) {
      var b = e.target.closest('.js-liguei'); if (!b) return;
      var c = b.closest('.cartao'), cod = c.getAttribute('data-cod'), nome = b.getAttribute('data-nome');
      function marcar() { aplicar(); }
      if (ARQUIVO) {
        ligados[cod] = agora(); guardar('ligados', ligados); marcar();
        aviso('Marcado: você ligou para ' + nome + '. Ele desce na fila (só neste computador).', function () { delete ligados[cod]; guardar('ligados', ligados); marcar(); });
        return;
      }
      b.disabled = true;
      fetch('/regua/registrar', { method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cliente: cod, canal: 'Telefone', ligacao: true, mensagem: 'Ligação marcada na fila de Hoje.' }) })
        .then(function (r) { return r.json(); })
        .then(function (j) {
          b.disabled = false;
          if (!j.ok) { aviso(j.erro || 'Não foi possível registrar.'); return; }
          registros[cod] = j.id; marcar();
          aviso('Registrado: você ligou para ' + nome + '. Ele desce na fila por 48 horas.', function () {
            fetch('/cobrancas/desfazer', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id: j.id }) })
              .then(function () { delete registros[cod]; marcar(); aviso('Registro desfeito.'); });
          });
        })
        .catch(function () { b.disabled = false; aviso('Não consegui falar com a Central. Nada foi registrado.'); });
    });
    aplicar();
  }

  /* ---------------------------------------------------------------- Risco: busca, filtro e ordem da lista */
  var tab = $('#tabela-risco');
  if (tab) {
    var linhas = $$('tbody tr', tab), filtroR = 'todos', corpo = $('tbody', tab);
    var nn = function (l, k) { return parseFloat(l.getAttribute('data-' + k)) || 0; };
    var ordens = {
      valor: function (a, b) { return nn(b, 'valor') - nn(a, 'valor'); },
      indice: function (a, b) { return nn(b, 'indice') - nn(a, 'indice'); },
      saldo: function (a, b) { return nn(b, 'saldo') - nn(a, 'saldo'); },
      nome: function (a, b) { return a.getAttribute('data-nome').localeCompare(b.getAttribute('data-nome'), 'pt-BR'); }
    };
    var aplicarR = function () {
      var q = sem(($('#busca') || {}).value || ''), o = ($('#ordem') || {}).value || 'valor', vis = 0;
      linhas.sort(ordens[o] || ordens.valor);
      linhas.forEach(function (l, i) {
        corpo.appendChild(l);
        var bate = (!q || sem(l.getAttribute('data-nome')).indexOf(q) >= 0) &&
          (filtroR === 'todos' || (filtroR === 'alerta' && l.getAttribute('data-alerta') === '1') || l.getAttribute('data-risco') === filtroR);
        l.classList.toggle('escondido', !bate);
        if (bate) vis++;
        if (o === 'valor') l.cells[0].textContent = i + 1;
      });
      var v = $('#vazio'); if (v) v.classList.toggle('escondido', vis > 0);
      var ct = $('#contagem'); if (ct) ct.textContent = vis + ' de ' + linhas.length + ' clientes';
    };
    var b2 = $('#busca'); if (b2) b2.addEventListener('input', aplicarR);
    var o2 = $('#ordem'); if (o2) o2.addEventListener('change', aplicarR);
    $$('[data-filtro]').forEach(function (b) {
      b.addEventListener('click', function () {
        filtroR = b.getAttribute('data-filtro');
        $$('[data-filtro]').forEach(function (x) { x.setAttribute('aria-pressed', x === b ? 'true' : 'false'); });
        aplicarR();
      });
    });
    aplicarR();
  }

  /* ---------------------------------------------------------------- Régua: lista de um lado, texto de um cliente do outro */
  var regua = $('#regua');
  if (regua) {
    regua.classList.add('mestre');
    var itens = $$('.item', regua), paineis = $$('.regua-painel', regua);
    var escolher = function (cod, rolar) {
      var achou = false;
      itens.forEach(function (i) { var on = i.getAttribute('data-cod') === String(cod); i.setAttribute('aria-selected', on ? 'true' : 'false'); if (on) achou = true; });
      if (!achou) return;
      paineis.forEach(function (p) { p.classList.toggle('ativo', p.getAttribute('data-cod') === String(cod)); });
      if (rolar && window.innerWidth < 1100) { var p = $('.regua-painel.ativo', regua); if (p) p.scrollIntoView({ behavior: REDUZ ? 'auto' : 'smooth', block: 'start' }); }
    };
    var doHash = function () { var m = /c(\d+)$/.exec(location.hash || ''); return m ? m[1] : null; };
    itens.forEach(function (i) {
      i.addEventListener('click', function (e) {
        e.preventDefault();
        var cod = i.getAttribute('data-cod');
        history.replaceState(null, '', (ARQUIVO ? '#/regua/c' : '#c') + cod);
        escolher(cod, true);
      });
    });
    if (window.__hc) window.removeEventListener('hashchange', window.__hc);
    window.__hc = function () { var c = doHash(); if (c && $('#regua')) escolher(c, false); };
    window.addEventListener('hashchange', window.__hc);
    escolher(doHash() || (itens[0] && itens[0].getAttribute('data-cod')), false);
    var br = $('#busca-regua');
    if (br) br.addEventListener('input', function () {
      var q = sem(br.value);
      itens.forEach(function (i) { i.classList.toggle('escondido', !!q && sem(i.getAttribute('data-nome')).indexOf(q) < 0); });
    });

    var parametros = function (p) {
      return { cliente: p.getAttribute('data-cod'), tom: $('.tom', p).value, canal: $('.canal', p).value,
               titulos: $$('.tit:checked', p).map(function (x) { return x.value; }) };
    };
    var reescrever = function (p) {
      var q = parametros(p), ta = $('textarea', p), bts = $$('.js-copiar,.js-registrar', p);
      if (!q.titulos.length) { ta.value = 'Escolha ao menos um título.'; bts.forEach(function (b) { b.disabled = true; }); return Promise.resolve(); }
      bts.forEach(function (b) { b.disabled = ARQUIVO && b.classList.contains('js-registrar'); });
      if (ARQUIVO) {
        var t = ((window.CENTRAL_TEXTOS || {})[q.cliente] || {})[q.tom];
        if (t && t[q.canal]) { ta.value = t[q.canal].texto; if (t[q.canal].porque) $('.porque', p).innerHTML = t[q.canal].porque; }
        return Promise.resolve();
      }
      var qs = new URLSearchParams({ cliente: q.cliente, tom: q.tom, canal: q.canal, titulos: q.titulos.join(',') });
      return fetch('/regua/texto?' + qs).then(function (r) { return r.json(); }).then(function (j) {
        ta.value = j.texto; $('.porque', p).innerHTML = j.porque_html; $('.valor', p).textContent = j.total;
      });
    };
    regua.addEventListener('change', function (e) {
      var p = e.target.closest('.regua-painel');
      if (p && e.target.matches('.tom,.canal,.tit')) reescrever(p);
    });
    regua.addEventListener('click', function (e) {
      var p = e.target.closest('.regua-painel'); if (!p) return;
      var cp = e.target.closest('.js-copiar');
      if (cp) {
        var ta = $('textarea', p); ta.select();
        var fim = function () { var t = cp.textContent; cp.textContent = 'Copiado'; setTimeout(function () { cp.textContent = t; }, 1500); };
        if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(ta.value).then(fim, function () { document.execCommand('copy'); fim(); });
        else { document.execCommand('copy'); fim(); }
        return;
      }
      if (e.target.closest('.js-registrar') && !ARQUIVO) {
        var q = parametros(p);
        if (!confirm('Registrar que você cobrou ' + p.getAttribute('data-nome') + ' por ' + q.canal + ' agora? Isso desce o cliente na fila de Hoje.')) return;
        fetch('/regua/registrar', { method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ cliente: q.cliente, tom: q.tom, canal: q.canal, titulos: q.titulos, mensagem: $('textarea', p).value }) })
          .then(function (r) { return r.json(); })
          .then(function (j) { if (j.ok) location.href = '/regua?registrado=' + j.id + '#c' + q.cliente; else aviso(j.erro || 'Não foi possível registrar.'); });
      }
    });
    var sa = $('#salvar-assinatura');
    if (sa && !ARQUIVO) sa.addEventListener('click', function () {
      fetch('/regua/assinatura', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ assinatura: $('#assinatura').value }) })
        .then(function () { return Promise.all(paineis.map(reescrever)); })
        .then(function () { $('#ass-ok').textContent = 'Salvo.'; });
    });
    if (ARQUIVO) {
      $$('.tit', regua).forEach(function (c) { c.disabled = true; });
      $$('.js-registrar', regua).forEach(function (b) { b.disabled = true; });
      var sv = $('#salvar-assinatura'); if (sv) sv.disabled = true;
    }
  }

  }
  window.CentralIniciar = iniciarPagina;
  iniciarPagina();

  /* ---------------------------------------------------------------- Cobranças feitas: desfazer um registro da Central */
  document.addEventListener('click', function (e) {
    var d = e.target.closest('.js-desfazer'); if (!d || ARQUIVO) return;
    if (!confirm('Apagar este registro? O cliente volta na fila de Hoje como se a cobrança não tivesse sido feita.')) return;
    fetch('/cobrancas/desfazer', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id: parseInt(d.getAttribute('data-id'), 10) }) })
      .then(function () { location.reload(); });
  });
})();
