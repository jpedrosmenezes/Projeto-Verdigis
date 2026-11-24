from django.test import TestCase
from django.urls import reverse

from .views import DEPOIMENTOS_ILUSTRATIVOS, flores_da_nota


class FloresDaNotaTests(TestCase):
    def test_nota_inteira_meia_e_zero(self):
        self.assertEqual(flores_da_nota(5), ['cheia'] * 5)
        self.assertEqual(flores_da_nota(4), ['cheia'] * 4 + ['vazia'])
        self.assertEqual(flores_da_nota(3.5), ['cheia'] * 3 + ['meia', 'vazia'])
        self.assertEqual(flores_da_nota(0), ['vazia'] * 5)


class AvaliacoesLandingTests(TestCase):
    def test_landing_mostra_depoimentos_ilustrativos(self):
        resposta = self.client.get(reverse('index'))
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'Depoimentos ilustrativos')
        for d in DEPOIMENTOS_ILUSTRATIVOS:
            self.assertContains(resposta, d['nome'])
        # 3 depoimentos x 5 flores
        self.assertContains(resposta, 'class="flor flor--', count=15)
