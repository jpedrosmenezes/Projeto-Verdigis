// Formulários com data-confirmar pedem confirmação antes de enviar.
document.querySelectorAll('form[data-confirmar]').forEach(function (form) {
  form.addEventListener('submit', function (evento) {
    if (!window.confirm(form.dataset.confirmar)) evento.preventDefault();
  });
});
