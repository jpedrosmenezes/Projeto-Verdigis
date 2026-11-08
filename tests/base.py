"""Base dos testes Selenium (Chrome headless)."""
from unittest import SkipTest

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from dashboard.tests import popular_demo

SENHA = 'verdigis123'
EMPRESA = 'empresa@demo.com'
FUNCIONARIO = 'funcionario@demo.com'


class SeleniumTestCase(StaticLiveServerTestCase):
    # Preserva os nichos criados por migração entre os testes.
    serialized_rollback = True

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        opcoes = webdriver.ChromeOptions()
        for arg in ('--headless=new', '--no-sandbox', '--disable-dev-shm-usage', '--window-size=1280,1000'):
            opcoes.add_argument(arg)
        try:
            cls.driver = webdriver.Chrome(options=opcoes)
        except WebDriverException as erro:
            super().tearDownClass()
            raise SkipTest(f'Google Chrome indisponível para os testes Selenium: {erro.msg}')
        cls.driver.implicitly_wait(2)

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()
        super().tearDownClass()

    def setUp(self):
        popular_demo()

    # ---------- atalhos ----------

    def abrir(self, caminho):
        self.driver.get(self.live_server_url + caminho)

    def por_testid(self, valor, visivel=True):
        condicao = EC.visibility_of_element_located if visivel else EC.presence_of_element_located
        return WebDriverWait(self.driver, 10).until(condicao((By.CSS_SELECTOR, f'[data-testid="{valor}"]')))

    def esperar_url(self, caminho):
        WebDriverWait(self.driver, 10).until(EC.url_to_be(self.live_server_url + caminho))

    def login(self, email, senha=SENHA):
        self.abrir('/account/login/')
        self.driver.find_element(By.NAME, 'username').send_keys(email)
        self.driver.find_element(By.NAME, 'password').send_keys(senha)
        self.driver.find_element(By.CSS_SELECTOR, 'form button[type="submit"]').click()
        WebDriverWait(self.driver, 10).until(lambda d: '/account/login/' not in d.current_url)
