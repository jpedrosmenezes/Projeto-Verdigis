from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from dashboard.models import AtividadeMeta, Meta, RelatoSocialVerdigis


def popular_demo():
    """Empresa, equipe e metas de demonstração (senha de todos: verdigis123)."""
    call_command('popular_demo', permitir_fora_de_desenvolvimento=True, stdout=StringIO())


class DesempenhoESGTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        popular_demo()

    def test_atividade_so_pontua_conforme_avanca_no_kanban(self):
        self.client.force_login(User.objects.get(email='empresa@demo.com'))
        meta = Meta.objects.get(nome='Reduzir o consumo de papel')
        antes = self.client.get(reverse('dashboard:esg_dashboard')).context['metricas'][0]['pontos']

        self.client.post(reverse('dashboard:criar_atividade'), {
            'meta_id': meta.id, 'nome': 'Trocar lâmpadas', 'prioridade': 'ALTA',
        })
        atividade = AtividadeMeta.objects.get(nome='Trocar lâmpadas')

        # Criada em "A Fazer", ainda não soma pontos.
        resposta = self.client.get(reverse('dashboard:esg_dashboard'))
        self.assertContains(resposta, 'Trocar lâmpadas')
        self.assertEqual(resposta.context['metricas'][0]['pontos'], antes)

        # Cada avanço no kanban libera uma parte dos 2 pontos finais.
        for status, pontos in [('EM_ANDAMENTO', 0.5), ('REVISAO', 1), ('FEITO', 2)]:
            self.client.post(reverse('dashboard:mover_atividade', args=[atividade.id]), {'status': status})
            resposta = self.client.get(reverse('dashboard:esg_dashboard'))
            self.assertEqual(resposta.context['metricas'][0]['pontos'], antes + pontos)

    def test_evolucao_bate_com_os_cartoes(self):
        self.client.force_login(User.objects.get(email='empresa@demo.com'))
        meta = Meta.objects.get(nome='Reduzir o consumo de papel')
        meta.atividades.create(nome='Feita', status='FEITO')
        meta.atividades.create(nome='Andando', status='EM_ANDAMENTO')

        resposta = self.client.get(reverse('dashboard:esg_dashboard'))
        evolucao = resposta.context['evolucao']
        # O último ponto do gráfico bate com os totais dos cartões, no geral e no pilar da meta.
        self.assertEqual(evolucao['geral'][-1], resposta.context['pontuacao_geral'])
        indice = [codigo for codigo, _ in Meta.ESG_ESCOLHA].index(meta.pilar_esg)
        self.assertEqual(evolucao['pilares'][indice]['pontos'][-1], resposta.context['metricas'][indice]['pontos'])
        self.assertContains(resposta, 'id="dados-evolucao"')

    def test_nao_mostra_atividades_de_outra_empresa(self):
        meta = Meta.objects.get(nome='Reduzir o consumo de papel')
        meta.atividades.create(nome='Atividade privada')
        self.client.force_login(User.objects.get(email='pendente@demo.com'))
        self.assertNotEqual(self.client.get(reverse('dashboard:esg_dashboard')).status_code, 200)


class PainelFuncionarioTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        popular_demo()

    def test_funcionario_ve_quadro_de_tarefas(self):
        self.client.force_login(User.objects.get(email='funcionario@demo.com'))
        self.assertContains(self.client.get(reverse('dashboard:dashboard')), reverse('dashboard:visualizar_tabela'))
        self.assertEqual(self.client.get(reverse('dashboard:visualizar_tabela')).status_code, 200)


class PreencherTabelaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        popular_demo()

    def test_agrupa_atividades_por_coluna(self):
        meta = Meta.objects.get(nome='Reduzir o consumo de papel')
        meta.atividades.create(nome='A')
        meta.atividades.create(nome='B', status='FEITO')
        self.client.force_login(User.objects.get(email='empresa@demo.com'))
        dados = self.client.get(reverse('dashboard:preencher_tabela', args=[meta.id])).json()
        self.assertEqual([a['nome'] for a in dados['a_fazer']], ['A'])
        self.assertEqual([a['nome'] for a in dados['feito']], ['B'])
        self.assertEqual(dados['em_andamento'], [])
        self.assertEqual(dados['revisao'], [])


class ResumoAvaliacoesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        popular_demo()

    def test_pizzas_contam_por_tema_e_sentimento(self):
        empresa = User.objects.get(email='empresa@demo.com')
        self.client.force_login(empresa)
        company = Meta.objects.get(nome='Reduzir o consumo de papel').company
        antes = self.client.get(reverse('dashboard:dashboard_social')).context['resumo_avaliacoes']

        RelatoSocialVerdigis.objects.create(company=company, mensagem='Ótimo', tema_esg='SEGURANCA', sentimento='POSITIVO')
        RelatoSocialVerdigis.objects.create(company=company, mensagem='Ruim', tema_esg='SEGURANCA', sentimento='NEGATIVO')

        resumo = self.client.get(reverse('dashboard:dashboard_social')).context['resumo_avaliacoes']
        geral = resumo[0]
        seguranca = next(t for t in resumo if t['codigo'] == 'SEGURANCA')
        seguranca_antes = next(t for t in antes if t['codigo'] == 'SEGURANCA')
        self.assertEqual(geral['total'], antes[0]['total'] + 2)
        self.assertEqual(seguranca['positivo'], seguranca_antes['positivo'] + 1)
        self.assertEqual(seguranca['negativo'], seguranca_antes['negativo'] + 1)
        # Um item para o total e um para cada tema
        self.assertEqual(len(resumo), 1 + len(RelatoSocialVerdigis.TEMA_ESG_CHOICES))
