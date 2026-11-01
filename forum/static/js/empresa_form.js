// Cadastro da empresa: preenche o endereço pelo CEP e mostra as orientações do nicho.
(function () {
  var form = document.querySelector('[data-url-cep]');
  if (!form) return;

  var campoCep = document.getElementById('id_cep') || document.getElementById('id_empresa-cep');
  var prefixo = campoCep && campoCep.id.indexOf('empresa-') !== -1 ? 'id_empresa-' : 'id_';
  if (campoCep) {
    campoCep.addEventListener('blur', function () {
      var cep = campoCep.value.replace(/\D/g, '');
      if (cep.length !== 8) return;
      fetch(form.dataset.urlCep.replace('00000000', cep))
        .then(function (resposta) { return resposta.json(); })
        .then(function (dados) {
          if (dados.erro) return;
          ['logradouro', 'bairro', 'cidade', 'uf'].forEach(function (nome) {
            var campo = document.getElementById(prefixo + nome);
            if (campo) campo.value = dados[nome];
          });
        })
        .catch(function () {});
    });
  }

  var dadosNicho = document.getElementById('niche-info');
  var campoNicho = document.getElementById(prefixo + 'niche');
  var dica = document.getElementById('niche-dica');
  if (dadosNicho && campoNicho && dica) {
    var orientacoes = JSON.parse(dadosNicho.textContent);
    var atualizar = function () { dica.textContent = orientacoes[campoNicho.value] || ''; };
    campoNicho.addEventListener('change', atualizar);
    atualizar();
  }
})();
