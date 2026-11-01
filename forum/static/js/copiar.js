// Botões "Copiar": copiam o texto de data-copiar para a área de transferência.
document.querySelectorAll('[data-copiar]').forEach(function (botao) {
  botao.addEventListener('click', function () {
    var texto = botao.dataset.copiar;
    var original = botao.textContent;
    function avisar(mensagem) {
      botao.textContent = mensagem;
      setTimeout(function () { botao.textContent = original; }, 2000);
    }
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(texto).then(function () { avisar('Copiado!'); }, function () { avisar(texto); });
    } else {
      avisar(texto);
    }
  });
});
