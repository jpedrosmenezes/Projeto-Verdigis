/**
 * Máscaras automáticas para CPF, CNPJ, telefone e CEP.
 *
 * Uso no HTML:
 *   <input data-mask="cpf">
 *   <input data-mask="cnpj">
 *   <input data-mask="cpf-cnpj">   <!-- alterna sozinho conforme a quantidade de dígitos -->
 *   <input data-mask="telefone">   <!-- fixo (10 dígitos) ou celular (11 dígitos) -->
 *   <input data-mask="cep">
 *
 *   <script src="masks.js"></script>
 */

const onlyDigits = (v) => String(v).replace(/\D/g, "");
const alnum = (v) => String(v).replace(/[^0-9A-Za-z]/g, "").toUpperCase();

const masks = {
  // 000.000.000-00
  cpf(v) {
    return onlyDigits(v)
      .slice(0, 11)
      .replace(/^(\d{3})(\d)/, "$1.$2")
      .replace(/^(\d{3})\.(\d{3})(\d)/, "$1.$2.$3")
      .replace(/\.(\d{3})(\d)/, ".$1-$2");
  },

  // 00.000.000/0000-00  (aceita letras também: novo CNPJ alfanumérico)
  cnpj(v) {
    const d = alnum(v).slice(0, 14);
    let out = d.slice(0, 2);
    if (d.length > 2) out += "." + d.slice(2, 5);
    if (d.length > 5) out += "." + d.slice(5, 8);
    if (d.length > 8) out += "/" + d.slice(8, 12);
    if (d.length > 12) out += "-" + d.slice(12, 14);
    return out;
  },

  // CPF até 11 dígitos, CNPJ acima disso (ou se tiver letras)
  "cpf-cnpj"(v) {
    const a = alnum(v);
    return a.length <= 11 && /^\d*$/.test(a) ? masks.cpf(v) : masks.cnpj(v);
  },

  // (00) 0000-0000  ou  (00) 00000-0000
  telefone(v) {
    const d = onlyDigits(v).slice(0, 11);
    if (d.length <= 2) return d.length ? `(${d}` : "";
    if (d.length <= 6) return d.replace(/^(\d{2})(\d+)/, "($1) $2");
    if (d.length <= 10) return d.replace(/^(\d{2})(\d{4})(\d+)/, "($1) $2-$3");
    return d.replace(/^(\d{2})(\d{5})(\d+)/, "($1) $2-$3");
  },

  // 00000-000
  cep(v) {
    return onlyDigits(v)
      .slice(0, 8)
      .replace(/^(\d{5})(\d)/, "$1-$2");
  },
};

function applyMask(input) {
  const type = input.dataset.mask;
  if (!masks[type]) return;

  const handler = () => {
    input.value = masks[type](input.value);
  };

  input.addEventListener("input", handler);
  input.addEventListener("paste", () => setTimeout(handler, 0));
  handler(); // formata valor já preenchido
}

function initMasks(root = document) {
  root.querySelectorAll("[data-mask]").forEach(applyMask);
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => initMasks());
} else {
  initMasks();
}

// Para enviar ao backend sem pontuação: onlyDigits(input.value)
