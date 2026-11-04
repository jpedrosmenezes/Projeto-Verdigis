from django.core.management.base import BaseCommand

from dashboard.models import QualidadeESG, RecursoAcessibilidade

QUALIDADES = {
    'E': [
        'Energia renovável', 'Redução de emissões de carbono', 'Gestão de resíduos e reciclagem',
        'Uso consciente de água', 'Compras e logística sustentáveis', 'Economia circular',
    ],
    'S': [
        'Diversidade e inclusão', 'Saúde mental e bem-estar', 'Capacitação e desenvolvimento',
        'Voluntariado e impacto comunitário', 'Equidade salarial', 'Saúde e segurança do trabalho',
    ],
    'G': [
        'Código de ética e compliance', 'Transparência e relatórios', 'Canal de denúncias',
        'Gestão de riscos', 'Política anticorrupção', 'Proteção de dados (LGPD)',
    ],
}

ACESSIBILIDADES = [
    'Acessibilidade física (rampas, banheiros adaptados)', 'Intérprete de Libras',
    'Site e materiais acessíveis', 'Atendimento remoto ou híbrido', 'Atendimento em mais de um idioma',
]


class Command(BaseCommand):
    help = 'Cria as qualidades ESG e os recursos de acessibilidade iniciais do Painel de Parcerias.'

    def handle(self, *args, **options):
        for pilar, nomes in QUALIDADES.items():
            for nome in nomes:
                QualidadeESG.objects.get_or_create(pilar=pilar, nome=nome)
        for nome in ACESSIBILIDADES:
            RecursoAcessibilidade.objects.get_or_create(nome=nome)
        self.stdout.write(self.style.SUCCESS('Catálogo do Painel de Parcerias criado.'))