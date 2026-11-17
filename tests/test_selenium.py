"""Testes ponta a ponta no navegador."""
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait

from accounts.models import TipoNotificacao, User
from accounts.services import notificar
from dashboard.models import AtividadeMeta, Meta, RelatoSocialVerdigis

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

    def test_cadastro_leva_a_triagem(self):
        self.abrir('/account/signup/')
        self.driver.find_element(By.NAME, 'nome').send_keys('Pessoa Nova')
        self.driver.find_element(By.NAME, 'email').send_keys('nova@teste.com')
        self.driver.find_element(By.NAME, 'password1').send_keys('SenhaForte#2026')
        self.driver.find_element(By.NAME, 'password2').send_keys('SenhaForte#2026')
        self.driver.find_element(By.CSS_SELECTOR, 'form button[type="submit"]').click()
        self.esperar_url('/account/onboarding/')
        self.assertTrue(User.objects.filter(email='nova@teste.com').exists())

    def test_logout_pelo_perfil(self):
        self.login(FUNCIONARIO)
        self.abrir('/account/profile/')
        self.driver.find_element(By.CLASS_NAME, 'btn-logout').click()
        WebDriverWait(self.driver, 10).until(lambda d: '/account/profile/' not in d.current_url)
        self.abrir('/dashboard/')
        self.esperar_url_contem('/account/login/')


class FluxoTests(SeleniumTestCase):
    def test_atividade_criada_aparece_sem_pontos_no_desempenho_esg(self):
        meta = Meta.objects.get(nome='Reduzir o consumo de papel')
        self.login(EMPRESA)
        self.abrir(f'/dashboard/visualizar_tabela/?meta={meta.id}')

        self.por_testid('nova-atividade').click()
        self.driver.find_element(By.ID, 'ativ-nome').send_keys('Trocar lâmpadas por LED')
        Select(self.driver.find_element(By.ID, 'ativ-prioridade')).select_by_value('ALTA')
        self.driver.find_element(By.CSS_SELECTOR, '#form-atividade button[type="submit"]').click()
        WebDriverWait(self.driver, 10).until(lambda d: meta.atividades.exists())

        self.abrir('/dashboard/esg/dashboard/')
        self.assertIn('Trocar lâmpadas por LED', self.por_testid('esg-atividades').text)
        self.assertEqual(self.por_testid('esg-pontos-E').text, '0 pts')
        self.assertEqual(self.por_testid('esg-total').text, '0 pts')

    def test_atividade_pontua_conforme_avanca_no_kanban(self):
        meta = Meta.objects.get(nome='Reduzir o consumo de papel')
        self.login(EMPRESA)
        self.abrir(f'/dashboard/visualizar_tabela/?meta={meta.id}')

        self.por_testid('nova-atividade').click()
        self.driver.find_element(By.ID, 'ativ-nome').send_keys('Instalar torneiras automáticas')
        self.driver.find_element(By.CSS_SELECTOR, '#form-atividade button[type="submit"]').click()
        WebDriverWait(self.driver, 10).until(
            lambda d: meta.atividades.filter(nome='Instalar torneiras automáticas').exists(),
        )
        atividade = AtividadeMeta.objects.get(nome='Instalar torneiras automáticas')

        # Cada coluna do kanban libera uma parte dos 2 pontos finais (#116).
        for status, pontos in [('EM_ANDAMENTO', '0,5 pts'), ('REVISAO', '1 pts'), ('FEITO', '2 pts')]:
            self.abrir(f'/dashboard/visualizar_tabela/?meta={meta.id}')
            seletor = Select(self.por_testid('atividade').find_element(
                By.CSS_SELECTOR, '[data-testid="atividade-status"]',
            ))
            seletor.select_by_value(status)
            WebDriverWait(self.driver, 10).until(
                lambda d: AtividadeMeta.objects.get(pk=atividade.pk).status == status,
            )

            self.abrir('/dashboard/esg/dashboard/')
            self.assertEqual(self.por_testid('esg-pontos-E').text, pontos)
            self.assertEqual(self.por_testid('esg-total').text, pontos)

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


class FabricaMetasTests(SeleniumTestCase):
    def test_filtro_meta_geral_mostra_apenas_metas_gerais(self):
        self.login(EMPRESA)
        self.abrir('/dashboard/metas/')

        Select(self.por_testid('filtro-colaborador')).select_by_value('geral')
        self.por_testid('filtro-metas').find_element(By.CSS_SELECTOR, 'button[type="submit"]').click()
        self.esperar_url_contem('colaborador=geral')

        esperadas = set(Meta.objects.filter(tipo='GERAL').values_list('nome', flat=True))
        WebDriverWait(self.driver, 10).until(
            lambda d: {
                c.find_element(By.CLASS_NAME, 'fm-card__titulo').text
                for c in d.find_elements(By.CSS_SELECTOR, '[data-testid="meta-card"]')
            } == esperadas,
        )
        cartoes = self.driver.find_elements(By.CSS_SELECTOR, '[data-testid="meta-card"]')
        self.assertEqual({c.get_attribute('data-meta-tipo') for c in cartoes}, {'GERAL'})
        self.assertEqual({c.find_element(By.CLASS_NAME, 'fm-card__titulo').text for c in cartoes}, esperadas)

    def test_funcionario_nao_ve_o_filtro_de_colaborador(self):
        self.login(FUNCIONARIO)
        self.abrir('/dashboard/metas/')
        self.assertEqual(self.driver.find_elements(By.CSS_SELECTOR, '[data-testid="filtro-metas"]'), [])


    def test_funcionario_cria_meta_individual(self):
        self.login(FUNCIONARIO)
        self.abrir('/dashboard/metas/')
        self.driver.find_element(By.CSS_SELECTOR, '[data-abrir-modal="modal-meta"]').click()
        self.driver.find_element(By.CSS_SELECTOR, 'label[for="esg-S"]').click()
        self.driver.find_element(By.ID, 'id_nome').send_keys('Pausas para alongamento')
        # Campo date varia com o idioma do Chrome; o valor ISO é definido direto.
        self.driver.execute_script("arguments[0].value = '2030-12-31'", self.driver.find_element(By.ID, 'id_deadline'))
        self.driver.find_element(By.ID, 'id_resumo').send_keys('Duas pausas por dia.')
        self.driver.find_element(By.CSS_SELECTOR, '#form-meta button[type="submit"]').click()

        WebDriverWait(self.driver, 10).until(lambda d: Meta.objects.filter(nome='Pausas para alongamento').exists())
        meta = Meta.objects.get(nome='Pausas para alongamento')
        self.assertEqual((meta.tipo, meta.pilar_esg, meta.funcionario.user.email), ('INDIVIDUAL', 'S', FUNCIONARIO))


class AvaliacaoTests(SeleniumTestCase):
    def test_funcionario_envia_avaliacao(self):
        self.login(FUNCIONARIO)
        self.abrir('/dashboard/avaliacao/nova/')
        Select(self.driver.find_element(By.NAME, 'tema_esg')).select_by_value('SAUDE_MENTAL')
        Select(self.driver.find_element(By.NAME, 'sentimento')).select_by_value('POSITIVO')
        self.driver.find_element(By.NAME, 'mensagem').send_keys('Gostei do novo programa de bem-estar.')
        self.driver.find_element(By.CSS_SELECTOR, 'form.form-contato button[type="submit"]').click()

        WebDriverWait(self.driver, 10).until(
            lambda d: RelatoSocialVerdigis.objects.filter(mensagem='Gostei do novo programa de bem-estar.').exists(),
        )
        self.assertIn('Enviado', self.driver.find_element(By.TAG_NAME, 'body').text)


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
