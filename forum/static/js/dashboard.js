// Avisos do dashboard: o "x" fecha e o aviso não volta a aparecer neste navegador.
document.querySelectorAll('.dash-aviso').forEach(function (aviso) {
  var chave = 'aviso-fechado-' + (aviso.classList.contains('dash-aviso--ok') ? 'ok' : 'atraso');
  try {
    if (localStorage.getItem(chave)) { aviso.remove(); return; }
  } catch (e) { /* armazenamento bloqueado: o aviso só não fica lembrado */ }

  aviso.querySelector('.dash-aviso__fechar').addEventListener('click', function () {
    try { localStorage.setItem(chave, '1'); } catch (e) {}
    aviso.classList.add('some');
    setTimeout(function () { aviso.remove(); }, 300);
  });
});

// Seletor de empresa do consultor: troca assim que muda (o botão continua para quem não usa JS).
document.querySelectorAll('[data-enviar-ao-mudar]').forEach(function (campo) {
  campo.addEventListener('change', function () { campo.form.submit(); });
});
