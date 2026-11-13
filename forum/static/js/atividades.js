/* Atividades ESG: carrossel de metas, seção de detalhes e kanban.
   Depende do template tabela_atividades.html (data-* e ids) e de js/metas.js (abrir/fechar <dialog>). */
(function () {
  'use strict';

  var pagina = document.getElementById('ca-pagina');
  var detalhe = document.getElementById('meta-detalhe');
  if (!pagina || !detalhe) return;

  var URL_ATIVIDADES = pagina.dataset.urlAtividades;
  var URL_MOVER = pagina.dataset.urlMover;
  var kanban = document.getElementById('ca-kanban');
  var reduzMovimento = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  var COLUNAS = {
    A_FAZER: 'a_fazer',
    EM_ANDAMENTO: 'em_andamento',
    REVISAO: 'revisao',
    FEITO: 'feito'
  };
  var ROTULOS_STATUS = {
    A_FAZER: 'A Fazer',
    EM_ANDAMENTO: 'Em Andamento',
    REVISAO: 'Em Revisão',
    FEITO: 'Feito'
  };
  var ROTULOS_PRIORIDADE = { BAIXA: 'Baixa', MEDIA: 'Média', ALTA: 'Alta' };

  var metaAtual = null;   // card (botão) da meta aberta
  var pedido = 0;         // descarta respostas antigas se o usuário clicar rápido em outra meta

  /* ---------- utilidades ---------- */

  function urlComId(base, id) {
    return base.replace('/0/', '/' + id + '/');
  }

  function csrf() {
    var m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
    if (m) return decodeURIComponent(m[1]);
    var campo = document.querySelector('[name=csrfmiddlewaretoken]');
    return campo ? campo.value : '';
  }

  function hojeISO() {
    var d = new Date();
    var mes = String(d.getMonth() + 1).padStart(2, '0');
    var dia = String(d.getDate()).padStart(2, '0');
    return d.getFullYear() + '-' + mes + '-' + dia;
  }

  function formatarData(iso) {
    if (!iso) return '';
    var p = iso.split('-');
    return p[2] + '/' + p[1] + '/' + p[0];
  }

  function el(tag, classe, texto) {
    var e = document.createElement(tag);
    if (classe) e.className = classe;
    if (texto !== undefined) e.textContent = texto;
    return e;
  }

  /* Preenche e com "<b>nome:</b> valor" */
  function rotulado(e, nome, valor) {
    e.textContent = '';
    e.appendChild(el('b', null, nome + ':'));
    e.appendChild(document.createTextNode(' ' + valor));
    return e;
  }

  /* Mensagem de carregamento/erro, criada uma vez acima do kanban */
  var aviso = el('p', 'fm-dica');
  aviso.setAttribute('role', 'status');
  aviso.hidden = true;
  kanban.parentNode.insertBefore(aviso, kanban);

  function mostrarAviso(texto) {
    aviso.textContent = texto;
    aviso.hidden = !texto;
  }

  function definirBotaoNova(pode) {
    detalhe.querySelectorAll('[data-abrir-modal="modal-atividade"]').forEach(function (b) {
      b.hidden = !pode;
    });
  }

  /* ---------- kanban ---------- */

  function listaDaColuna(status) {
    return kanban.querySelector('.ca-coluna[data-status="' + status + '"] .ca-coluna__lista');
  }

  function atualizarVazios() {
    kanban.querySelectorAll('.ca-coluna__lista').forEach(function (lista) {
      var vazio = lista.querySelector('.ca-coluna__vazio');
      var temCards = lista.querySelector('.ca-atividade') !== null;
      if (!temCards && !vazio) {
        lista.appendChild(el('p', 'ca-coluna__vazio', 'Nenhuma atividade.'));
      } else if (temCards && vazio) {
        vazio.remove();
      }
    });
  }

  function limparKanban() {
    kanban.querySelectorAll('.ca-coluna__lista').forEach(function (lista) {
      lista.textContent = '';
    });
  }

  function marcarAtraso(card, emAtraso) {
    var tag = card.querySelector('.ca-atividade__atraso');
    if (tag) tag.hidden = !emAtraso;
  }

  function criarCardAtividade(a, status, podeMover) {
    var card = el('article', 'ca-atividade ca-atividade--' + String(a.prioridade).toLowerCase());
    card.dataset.atividadeId = a.id;
    card.dataset.testid = 'atividade';

    card.appendChild(el('h4', 'ca-atividade__nome', a.nome));
    if (a.descricao) card.appendChild(el('p', 'fm-item', a.descricao));

    var tags = el('div', 'fm-card__tags');
    if (a.prazo) tags.appendChild(el('span', 'fm-tag', 'Prazo: ' + formatarData(a.prazo)));
    tags.appendChild(el('span', 'fm-tag', 'Prioridade: ' + (ROTULOS_PRIORIDADE[a.prioridade] || a.prioridade).toLowerCase()));
    var atraso = el('span', 'fm-tag fm-tag--atraso ca-atividade__atraso', 'Atrasada');
    atraso.hidden = !(a.prazo && status !== 'FEITO' && a.prazo < hojeISO());
    tags.appendChild(atraso);
    card.appendChild(tags);

    if (podeMover) {
      var select = el('select', 'ca-atividade__status');
      select.dataset.testid = 'atividade-status';
      select.setAttribute('aria-label', 'Mover "' + a.nome + '" para outra coluna');
      Object.keys(ROTULOS_STATUS).forEach(function (valor) {
        var op = el('option', '', ROTULOS_STATUS[valor]);
        op.value = valor;
        if (valor === status) op.selected = true;
        select.appendChild(op);
      });
      select.dataset.anterior = status;
      card.appendChild(select);
    }
    return card;
  }

  function preencherKanban(dados, podeMover) {
    limparKanban();
    Object.keys(COLUNAS).forEach(function (status) {
      var lista = listaDaColuna(status);
      (dados[COLUNAS[status]] || []).forEach(function (a) {
        lista.appendChild(criarCardAtividade(a, status, podeMover));
      });
    });
    atualizarVazios();
  }

  /* Mover atividade: muda no servidor e só então reposiciona o card */
  kanban.addEventListener('change', function (ev) {
    var select = ev.target.closest('.ca-atividade__status');
    if (!select) return;

    var card = select.closest('.ca-atividade');
    var novo = select.value;
    var anterior = select.dataset.anterior;
    var corpo = new FormData();
    corpo.append('status', novo);
    select.disabled = true;

    fetch(urlComId(URL_MOVER, card.dataset.atividadeId), {
      method: 'POST',
      headers: { 'X-CSRFToken': csrf(), 'X-Requested-With': 'XMLHttpRequest' },
      body: corpo,
      credentials: 'same-origin'
    })
      .then(function (res) {
        if (!res.ok) throw new Error('http ' + res.status);
        return res.json();
      })
      .then(function (json) {
        if (json.status !== 'sucesso') throw new Error(json.mensagem || 'erro');
        listaDaColuna(json.novo_status).appendChild(card);
        select.dataset.anterior = json.novo_status;
        marcarAtraso(card, json.em_atraso);
        atualizarVazios();
        mostrarAviso('');
      })
      .catch(function () {
        select.value = anterior;
        mostrarAviso('Não foi possível mover a atividade. Tente novamente.');
      })
      .finally(function () {
        select.disabled = false;
      });
  });

  /* ---------- seção de detalhes ---------- */

  function texto(id, valor) {
    var e = document.getElementById(id);
    if (!e) return;
    e.textContent = valor || '';
    e.hidden = !valor;
  }

  function preencherDetalhe(card) {
    var d = card.dataset;
    texto('detalhe-pilar', d.pilarNome);
    texto('detalhe-prazo', 'Prazo: ' + d.prazo);
    texto('detalhe-prioridade', 'Prioridade: ' + String(d.prioridade || '').toLowerCase());
    texto('detalhe-tipo', d.tipo);
    texto('detalhe-responsavel', d.responsavel);
    texto('detalhe-nome', d.nome);

    var situacao = document.getElementById('detalhe-situacao');
    if (d.concluida === '1') {
      situacao.textContent = 'Concluída';
      situacao.className = 'fm-tag fm-tag--ok';
      situacao.hidden = false;
    } else if (d.atrasada === '1') {
      situacao.textContent = 'Atrasada';
      situacao.className = 'fm-tag fm-tag--atraso';
      situacao.hidden = false;
    } else {
      situacao.hidden = true;
    }

    var resumo = document.getElementById('detalhe-resumo');
    resumo.textContent = '';
    (d.resumo || '').split(/\r?\n/).forEach(function (linha) {
      if (linha.trim()) resumo.appendChild(el('p', 'fm-item', linha));
    });

    /* Modal de nova atividade já sabe a qual meta pertence e sugere o pilar dela */
    var campoMeta = document.getElementById('atividade-meta-id');
    if (campoMeta) campoMeta.value = d.metaId;
    var radio = document.getElementById('ativ-esg-' + d.pilar);
    if (radio) radio.checked = true;
  }

  function abrirMeta(card) {
    if (metaAtual) {
      metaAtual.classList.remove('ca-card--ativo');
      metaAtual.setAttribute('aria-pressed', 'false');
    }
    metaAtual = card;
    card.classList.add('ca-card--ativo');
    card.setAttribute('aria-pressed', 'true');

    preencherDetalhe(card);
    limparKanban();
    definirBotaoNova(false);
    mostrarAviso('Carregando atividades…');
    detalhe.hidden = false;
    detalhe.scrollIntoView({ behavior: reduzMovimento ? 'auto' : 'smooth', block: 'start' });

    var meu = ++pedido;

    fetch(urlComId(URL_ATIVIDADES, card.dataset.metaId), {
      headers: { 'X-Requested-With': 'XMLHttpRequest' },
      credentials: 'same-origin'
    })
      .then(function (res) {
        if (!res.ok) throw new Error('http ' + res.status);
        return res.json();
      })
      .then(function (dados) {
        if (meu !== pedido) return;
        preencherKanban(dados, dados.pode_mover);
        definirBotaoNova(dados.pode_criar);
        mostrarAviso('');
      })
      .catch(function () {
        if (meu !== pedido) return;
        mostrarAviso('Não foi possível carregar as atividades desta meta.');
      });
  }

  function fecharDetalhe() {
    pedido++;
    detalhe.hidden = true;
    mostrarAviso('');
    if (metaAtual) {
      metaAtual.classList.remove('ca-card--ativo');
      metaAtual.setAttribute('aria-pressed', 'false');
      metaAtual.focus();
      metaAtual = null;
    }
  }

  document.querySelectorAll('.ca-card').forEach(function (card) {
    card.setAttribute('aria-pressed', 'false');
    card.addEventListener('click', function () {
      if (card === metaAtual) return;
      abrirMeta(card);
    });
  });

  var fechar = detalhe.querySelector('[data-fechar-detalhe]');
  if (fechar) fechar.addEventListener('click', fecharDetalhe);

  /* ---------- setas do carrossel ---------- */

  document.querySelectorAll('.ca-faixa').forEach(function (faixa) {
    var trilho = faixa.querySelector('.ca-trilho');
    faixa.querySelectorAll('[data-rolar]').forEach(function (botao) {
      botao.addEventListener('click', function () {
        trilho.scrollBy({
          left: Number(botao.dataset.rolar) * trilho.clientWidth * 0.8,
          behavior: reduzMovimento ? 'auto' : 'smooth'
        });
      });
    });
  });

  /* ---------- abrir meta vinda de ?meta= (depois de criar atividade) ---------- */

  if (pagina.dataset.metaAberta) {
    var inicial = document.querySelector('.ca-card[data-meta-id="' + pagina.dataset.metaAberta + '"]');
    if (inicial) abrirMeta(inicial);
  }
})();