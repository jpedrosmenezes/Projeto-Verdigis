// Pilares ESG da página inicial: clicar numa letra abre a explicação dela
// e fecha as outras. Só uma fica aberta por vez.
document.addEventListener('DOMContentLoaded', function () {
    const letras = document.querySelectorAll('.esg__letra');

    letras.forEach(function (letra) {
        letra.addEventListener('click', function () {
            letras.forEach(function (outra) {
                const aberta = outra === letra;
                outra.setAttribute('aria-expanded', aberta ? 'true' : 'false');
                document.getElementById(outra.getAttribute('aria-controls')).hidden = !aberta;
            });
        });
    });
});
