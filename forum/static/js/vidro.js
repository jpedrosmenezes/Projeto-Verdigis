
(function () {
    
    const INTENSIDADE = 1.4;

    const ehChromium = /Chrome\/|Chromium\//.test(navigator.userAgent);
    const menosTransparencia = window.matchMedia('(prefers-reduced-transparency: reduce)').matches;
    if (!ehChromium || menosTransparencia) return;

    const NS = 'http://www.w3.org/2000/svg';
    const svg = document.createElementNS(NS, 'svg');
    svg.setAttribute('width', '0');
    svg.setAttribute('height', '0');
    svg.setAttribute('aria-hidden', 'true');
    svg.style.position = 'absolute';
    document.body.appendChild(svg);

    
    function criarMapa(largura, altura, borda, raio) {
        const raioInterno = Math.max(raio - borda, 0);
        const mapa =
            `<svg xmlns="http://www.w3.org/2000/svg" width="${largura}" height="${altura}">` +
              '<defs>' +
                '<linearGradient id="r"><stop offset="0" stop-color="#f00"/><stop offset="1" stop-color="#000"/></linearGradient>' +
                '<linearGradient id="g" x2="0" y2="1"><stop offset="0" stop-color="#0f0"/><stop offset="1" stop-color="#000"/></linearGradient>' +
                `<filter id="b"><feGaussianBlur stdDeviation="${borda / 2}"/></filter>` +
              '</defs>' +
              `<rect width="${largura}" height="${altura}" fill="url(#r)"/>` +
              `<rect width="${largura}" height="${altura}" fill="url(#g)" style="mix-blend-mode:screen"/>` +
              `<rect x="${borda}" y="${borda}" width="${largura - 2 * borda}" height="${altura - 2 * borda}" ` +
                    `rx="${raioInterno}" fill="#808080" filter="url(#b)"/>` +
            '</svg>';
        return 'data:image/svg+xml,' + encodeURIComponent(mapa);
    }

    document.querySelectorAll('.moldura-vidro').forEach(function (moldura, i) {
        const id = 'lente-vidro-' + i;

        const filtro = document.createElementNS(NS, 'filter');
        filtro.setAttribute('id', id);
        filtro.setAttribute('x', '0');
        filtro.setAttribute('y', '0');
        filtro.setAttribute('width', '100%');
        filtro.setAttribute('height', '100%');
        filtro.setAttribute('color-interpolation-filters', 'sRGB');

        const imagem = document.createElementNS(NS, 'feImage');
        imagem.setAttribute('x', '0');
        imagem.setAttribute('y', '0');
        imagem.setAttribute('preserveAspectRatio', 'none');
        imagem.setAttribute('result', 'mapa');

        const deslocamento = document.createElementNS(NS, 'feDisplacementMap');
        deslocamento.setAttribute('in', 'SourceGraphic');
        deslocamento.setAttribute('in2', 'mapa');
        deslocamento.setAttribute('xChannelSelector', 'R');
        deslocamento.setAttribute('yChannelSelector', 'G');

        filtro.append(imagem, deslocamento);
        svg.appendChild(filtro);

        
        function atualizar() {
            const estilo = getComputedStyle(moldura);
            const largura = moldura.offsetWidth;
            const altura = moldura.offsetHeight;
            const borda = parseFloat(estilo.paddingTop) || 40;
            const raio = parseFloat(estilo.borderTopLeftRadius) || 0;

            imagem.setAttribute('width', largura);
            imagem.setAttribute('height', altura);
            imagem.setAttribute('href', criarMapa(largura, altura, borda, raio));
            deslocamento.setAttribute('scale', Math.round(borda * INTENSIDADE));
        }

        new ResizeObserver(atualizar).observe(moldura);
        atualizar();

        // O glass.css usa esta variável para ligar a lente.
        moldura.style.setProperty('--lente', 'url(#' + id + ')');
        moldura.classList.add('com-lente');
    });
})();