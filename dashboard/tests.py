from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from dashboard.models import AtividadeMeta, Meta


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
            'meta_id': meta.id, 'nome': 'Trocar lâmpadas', 'pilar_esg': 'E', 'prioridade': 'ALTA',
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

    def test_nao_mostra_atividades_de_outra_empresa(self):
        meta = Meta.objects.get(nome='Reduzir o consumo de papel')
        meta.atividades.create(nome='Atividade privada', pilar_esg='E')
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
        meta.atividades.create(nome='A', pilar_esg='E')
        meta.atividades.create(nome='B', pilar_esg='E', status='FEITO')
        self.client.force_login(User.objects.get(email='empresa@demo.com'))
        dados = self.client.get(reverse('dashboard:preencher_tabela', args=[meta.id])).json()
        self.assertEqual([a['nome'] for a in dados['a_fazer']], ['A'])
        self.assertEqual([a['nome'] for a in dados['feito']], ['B'])
        self.assertEqual(dados['em_andamento'], [])
        self.assertEqual(dados['revisao'], [])
