// Gráficos (Chart.js) do Desempenho ESG e da Central de Avaliações.
// Os dados vêm do Django pelo filtro json_script (tags <script type="application/json">).
document.addEventListener('DOMContentLoaded', function () {
    // Sem internet o Chart.js não carrega; a página continua mostrando os números em texto.
    if (typeof Chart === 'undefined') return;

    const CORES = {
        geral: '#525fa2',   // azul da marca
        E: '#5f7234',
        S: '#4f8fb8',
        G: '#c99a2e',
        positivo: '#5f7234',
        neutro: '#a7a9ac',
        negativo: '#c0392b',
    };

    Chart.defaults.font.family = '"helvetica-neue-lt-pro", sans-serif';
    Chart.defaults.color = '#555';
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        Chart.defaults.animation = false;
    }

    function lerDados(id) {
        const tag = document.getElementById(id);
        return tag ? JSON.parse(tag.textContent) : null;
    }

    // 1. Desempenho ESG: evolução dos pontos acumulados (linha)
    const canvasEvolucao = document.getElementById('grafico-evolucao');
    const evolucao = lerDados('dados-evolucao');
    if (canvasEvolucao && evolucao) {
        const linhas = [{
            label: 'Geral',
            data: evolucao.geral,
            borderColor: CORES.geral,
            backgroundColor: 'rgba(82, 95, 162, 0.08)',
            fill: true,
            borderWidth: 3,
        }];
        evolucao.pilares.forEach(function (pilar) {
            linhas.push({
                label: pilar.codigo + ' · ' + pilar.nome,
                data: pilar.pontos,
                borderColor: CORES[pilar.codigo],
                backgroundColor: CORES[pilar.codigo],
                borderWidth: 2,
            });
        });
        linhas.forEach(function (linha) {
            linha.tension = 0.25;
            linha.pointRadius = 4;
            linha.pointHoverRadius = 6;
            linha.pointBackgroundColor = linha.borderColor;
        });

        new Chart(canvasEvolucao, {
            type: 'line',
            data: { labels: evolucao.datas, datasets: linhas },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: 'index', intersect: false },
                plugins: {
                    legend: { position: 'top', labels: { usePointStyle: true } },
                    tooltip: {
                        callbacks: {
                            label: function (ctx) { return ctx.dataset.label + ': ' + ctx.parsed.y + ' pts'; },
                        },
                    },
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { precision: 0 },
                        title: { display: true, text: 'Pontos acumulados' },
                    },
                    x: { grid: { display: false } },
                },
            },
        });
    }

    // 2. Central de Avaliações: positivas, neutras e negativas (pizzas)
    const resumo = lerDados('dados-resumo-avaliacoes');
    if (resumo) {
        document.querySelectorAll('canvas[data-pizza]').forEach(function (canvas) {
            const item = resumo[Number(canvas.dataset.pizza)];
            new Chart(canvas, {
                type: 'pie',
                data: {
                    labels: ['Positivas', 'Neutras', 'Negativas'],
                    datasets: [{
                        data: [item.positivo, item.neutro, item.negativo],
                        backgroundColor: [CORES.positivo, CORES.neutro, CORES.negativo],
                        borderColor: '#fff',
                        borderWidth: 2,
                    }],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {
                        legend: { display: false },   // a legenda fica no HTML, uma só para todas
                        tooltip: {
                            callbacks: {
                                label: function (ctx) { return ' ' + ctx.label + ': ' + ctx.parsed; },
                            },
                        },
                    },
                },
            });
        });
    }
});
