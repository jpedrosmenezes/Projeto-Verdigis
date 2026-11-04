// Fábrica de metas: janela de nova meta e campo de funcionário só para meta individual.
(function () {
  document.querySelectorAll('[data-abrir-modal]').forEach(function (botao) {
    botao.addEventListener('click', function () {
      document.getElementById(botao.dataset.abrirModal).showModal();
    });
  });

  document.querySelectorAll('dialog.fm-modal').forEach(function (modal) {
    // Clique fora do conteúdo (no fundo escuro) fecha a janela.
    modal.addEventListener('click', function (evento) {
      if (evento.target === modal) modal.close();
    });
    modal.querySelectorAll('[data-fechar-modal]').forEach(function (botao) {
      botao.addEventListener('click', function () { modal.close(); });
    });
    // Voltou do servidor com erro de validação: reabre para mostrar os erros.
    if (modal.hasAttribute('data-abrir')) modal.showModal();
  });

  var selectTipo = document.getElementById('id_tipo');
  var container = document.getElementById('campo-funcionario-container');
  if (!selectTipo || !container) return;
  var selectFuncionario = container.querySelector('select');

  function alternar() {
    var individual = selectTipo.value === 'INDIVIDUAL';
    container.style.display = individual ? 'flex' : 'none';
    if (selectFuncionario) {
      selectFuncionario.required = individual;
      if (!individual) selectFuncionario.value = '';
    }
  }
  selectTipo.addEventListener('change', alternar);
  alternar();
})();
