// Botão de mostrar/ocultar senha dos campos de senha (accounts/_campo.html).
document.addEventListener('click', function (evento) {
  var botao = evento.target.closest('.btn-olho');
  if (!botao) return;
  var campo = botao.previousElementSibling;
  var oculta = campo.type === 'password';
  campo.type = oculta ? 'text' : 'password';
  botao.querySelector('img').src = oculta ? botao.dataset.olhoFechado : botao.dataset.olhoAberto;
  botao.setAttribute('aria-label', oculta ? 'Ocultar senha' : 'Mostrar senha');
});
