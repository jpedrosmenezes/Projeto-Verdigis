"""Testes ponta a ponta no navegador."""
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait

from accounts.models import TipoNotificacao, User
from accounts.services import notificar
from dashboard.models import Meta

from .base import EMPRESA, FUNCIONARIO, SeleniumTestCase


class LoginTests(SeleniumTestCase):
    def test_login_leva_ao_dashboard(self):
        self.login(EMPRESA)
        self.abrir('/dashboard/')
        self.assertIn('BEM-VINDO', self.driver.find_element(By.CLASS_NAME, 'dash-banner').text)

    def test_senha_errada_fica_no_login(self):
        self.abrir('/account/login/')
        self.driver.find_element(By.NAME, 'username').send_keys(EMPRESA)
        self.driver.find_element(By.NAME, 'password').send_keys('errada')
        self.driver.find_element(By.CSS_SELECTOR, 'form button[type="submit"]').click()
        self.assertIn('/account/login/', self.driver.current_url)


class FluxoTests(SeleniumTestCase):
    def test_atividade_criada_aparece_sem_pontos_no_desempenho_esg(self):
        meta = Meta.objects.get(nome='Reduzir o consumo de papel')
        self.login(EMPRESA)
        self.abrir(f'/dashboard/visualizar_tabela/?meta={meta.id}')

        self.por_testid('nova-atividade').click()
        self.driver.find_element(By.CSS_SELECTOR, 'label[for="ativ-esg-E"]').click()
        self.driver.find_element(By.ID, 'ativ-nome').send_keys('Trocar lâmpadas por LED')
        Select(self.driver.find_element(By.ID, 'ativ-prioridade')).select_by_value('ALTA')
        self.driver.find_element(By.CSS_SELECTOR, '#form-atividade button[type="submit"]').click()
        WebDriverWait(self.driver, 10).until(lambda d: meta.atividades.exists())

        self.abrir('/dashboard/esg/dashboard/')
        self.assertIn('Trocar lâmpadas por LED', self.por_testid('esg-atividades').text)
        self.assertEqual(self.por_testid('esg-pontos-E').text, '0 pts')
        self.assertEqual(self.por_testid('esg-total').text, '0 pts')

    def test_funcionario_abre_o_quadro_de_tarefas(self):
        self.login(FUNCIONARIO)
        self.abrir('/dashboard/')
        self.por_testid('link-quadro-tarefas').click()
        self.esperar_url('/dashboard/visualizar_tabela/')
        self.assertIn('Ambiental', self.por_testid('quadro-faixas').text)

    def test_cancelar_avaliacao_volta_ao_dashboard(self):
        self.login(FUNCIONARIO)
        self.abrir('/dashboard/avaliacao/nova/')
        cancelar = self.por_testid('cancelar-avaliacao')
        self.assertNotEqual(cancelar.value_of_css_property('color'), 'rgba(255, 255, 255, 1)')
        cancelar.click()
        self.esperar_url('/dashboard/')

    def test_voltar_do_painel_de_parcerias(self):
        self.login(EMPRESA)
        self.abrir('/dashboard/parcerias/')
        self.por_testid('parcerias-voltar').click()
        self.esperar_url('/dashboard/')


class LayoutTests(SeleniumTestCase):
    def test_v_do_dashboard_ocupa_o_espaco(self):
        self.login(EMPRESA)
        self.abrir('/dashboard/')
        self.assertGreaterEqual(self.por_testid('dash-v').size['height'], 420)

    def test_botoes_do_perfil_alinhados(self):
        self.login(FUNCIONARIO)
        self.abrir('/account/profile/')
        botoes = self.por_testid('perfil-botoes').find_elements(By.TAG_NAME, 'a')
        # Espera o layout assentar; falha por timeout se nunca alinharem.
        WebDriverWait(self.driver, 5).until(lambda d: len({b.location['y'] for b in botoes}) == 1)

    def test_botao_de_notificacoes_visivel(self):
        notificar(User.objects.get(email=EMPRESA), TipoNotificacao.values[0], 'Teste')
        self.login(EMPRESA)
        self.abrir('/account/notificacoes/')
        self.assertTrue(self.por_testid('marcar-lidas').is_displayed())

    def test_titulo_dos_vinculos_em_destaque(self):
        self.login(FUNCIONARIO)
        self.abrir('/account/vinculos/')
        titulo = self.por_testid('vinculo-card').find_element(By.CLASS_NAME, 'fm-card__titulo')
        self.assertEqual(titulo.value_of_css_property('font-weight'), '700')

    def test_titulos_do_quadro_em_negrito(self):
        self.login(EMPRESA)
        self.abrir('/dashboard/visualizar_tabela/')
        coluna = self.driver.find_element(By.CLASS_NAME, 'ca-faixa__titulo')
        self.assertEqual(coluna.value_of_css_property('font-weight'), '700')

    def test_filtro_de_metas_visivel(self):
        self.login(EMPRESA)
        self.abrir('/dashboard/metas/')
        self.assertTrue(self.por_testid('filtro-metas').is_displayed())

    def test_aviso_alinhado_com_os_eixos(self):
        self.login(EMPRESA)
        self.abrir('/dashboard/parcerias/')
        aviso = self.por_testid('aviso-perfil')
        eixos = self.driver.find_element(By.CLASS_NAME, 'pc-eixos')
        self.assertEqual(aviso.size['width'], eixos.size['width'])
