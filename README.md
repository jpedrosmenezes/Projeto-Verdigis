<div align=center>
  <img width="472,5" height="324,75" alt="logo readme2" src="https://github.com/user-attachments/assets/561b4865-47a9-43d0-a905-254a732766e9" />


Plataforma web para aumentar a percepção de valor e a adoção de práticas ESG em pequenas e médias empresas (PMEs). Projeto desenvolvido a partir de um desafio proposto pela Deloitte.

**Site:** https://projeto-verdigis.onrender.com
</div>

## Sobre o projeto

A pergunta do desafio: como aumentar a percepção de importância e impulsionar a aplicação de práticas ESG nas PMEs?

Muitas PMEs já adotam práticas sustentáveis e sociais sem reconhecê-las como ESG, e tendem a ver o tema como custo, não como vantagem competitiva. O Verdigis busca traduzir os pilares ESG para a realidade dessas empresas, mostrar o que elas já fazem e evidenciar o retorno dessas práticas.

### Contexto

- As micro, pequenas e médias empresas respondem por 26,5% do PIB e por cerca de 80% dos empregos no país.
- 67% delas não conhecem formalmente o significado da sigla ESG.
- Investidores, instituições financeiras e grandes empresas passaram a considerar critérios ESG em decisões de crédito, aporte e contratação de fornecedores.

### Barreiras identificadas

- Percepção de ESG como custo sem retorno garantido
- Foco em caixa e operação de curto prazo
- Falta de direcionamento prático sobre por onde começar
- Dificuldade em mensurar o retorno das ações
- Impressão de que a exigência recai apenas sobre grandes empresas

### Riscos da não adoção

Perda de contratos, crédito mais caro, exposição reputacional e dificuldade de atrair e reter profissionais.

## Funcionalidades

- Páginas institucionais: início, sobre o projeto e fale conosco
- Apresentação dos pilares ESG (Ambiental, Social e Governança) com práticas associadas a cada um
- Formulário de contato com registro das mensagens no banco de dados
- Conteúdo, equipe, pilares e tecnologias editáveis pelo painel administrativo do Django, sem alteração de código
- Contas com login por e-mail e escolha de papel: empresa, funcionário ou consultor
- Equipe da empresa: entrada pelo código da empresa, aprovação de pedidos e permissões por consultor
- Fábrica de metas com regras por papel e relatos da equipe com anonimato e moderação
- Notificações dentro do site

Detalhes técnicos (permissões, fluxos e comandos) em [ARQUITETURA.md](./ARQUITETURA.md).

| Rota | Descrição |
| --- | --- |
| `/` | Página inicial |
| `/sobre/` | Objetivos, pilares, práticas e tecnologias |
| `/fale-conosco/` | Formulário de contato |
| `/account/signup/` e `/account/login/` | Cadastro e login por e-mail |
| `/account/onboarding/` | Escolha do papel (empresa, funcionário ou consultor) |
| `/dashboard/` | Painel da empresa, com o menu de cada papel |
| `/dashboard/equipe/` | Pedidos de entrada, funcionários e consultores |
| `/dashboard/metas/` | Fábrica de metas |
| `/dashboard/avaliacao/` | Central de avaliações (relatos da equipe) |
| `/dashboard/visualizar_tabela/` | Quadro de tarefas (atividades de cada meta) |
| `/dashboard/esg/dashboard/` | Desempenho ESG (pontos por pilar e atividades recentes) |
| `/dashboard/parcerias/` | Painel de Parcerias |
| `/admin/` | Painel administrativo |

---

## Stack

| Camada | Tecnologia |
| --- | --- |
| Back-end | Python, Django 6.1 |
| Front-end | HTML, CSS, JavaScript (templates Django) |
| Banco de dados | SQLite (desenvolvimento), PostgreSQL (produção) |
| Servidor | Gunicorn, WhiteNoise (arquivos estáticos) |
| Hospedagem | Render |

## Executando localmente

Requisitos: Python 3.12 ou superior e Git.

```bash
git clone https://github.com/jpedrosmenezes/Projeto-Verdigis.git
cd Projeto-Verdigis

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

Crie um arquivo `.env` na raiz do projeto:

```env
SECRET_KEY=<uma-chave-secreta-qualquer>
ENVIRONMENT=development
```

Aplique as migrações, carregue os dados de demonstração (opcional) e inicie o servidor:

```bash
python manage.py migrate
python manage.py popular_demo      # usuários, empresa, metas e relatos de exemplo
python manage.py runserver
```

Sem os dados de demonstração, crie o superusuário com `python manage.py createsuperuser` (pede e-mail, nome e senha).

A aplicação ficará disponível em http://127.0.0.1:8000. O conteúdo das páginas é cadastrado em http://127.0.0.1:8000/admin/.

> Se o `.env` tiver `DATABASE_URL`, o projeto usa esse PostgreSQL mesmo em desenvolvimento. Para usar o SQLite local, deixe a variável fora do `.env`.

### Testes

Os testes ficam em `dashboard/tests.py` (unitários) e em `tests/` (Selenium, ponta a ponta). Os de Selenium sobem o site num servidor de teste e o abrem no **Google Chrome em modo headless**, então o Chrome precisa estar instalado. O driver é baixado sozinho pelo Selenium Manager na primeira execução (precisa de internet nessa hora). Sem o Chrome, os testes de Selenium são pulados e os demais rodam normalmente.

```bash
python manage.py test               # todos os testes
python manage.py test tests         # só os de Selenium
python manage.py test dashboard     # só os unitários
```

Os testes usam um banco temporário e criam os dados com o `popular_demo`; não mexem no seu `db.sqlite3`. Com o `.env` acima (`ENVIRONMENT=development`) não é preciso configurar mais nada. Para achar elementos na tela, os testes usam atributos `data-testid` nos templates; mantenha-os ao alterar o HTML.

### Integração contínua e deploy (GitHub Actions)

O repositório tem dois workflows em `.github/workflows/`:

- **`ci.yml`** roda `python manage.py check` e toda a suíte (`python manage.py test`) em cada push para `main` e em pull requests. O Chrome já vem instalado no runner `ubuntu-latest`, então os testes Selenium rodam em modo headless.
- **`deploy.yml`** é disparado quando o `ci.yml` termina com sucesso na `main` e chama o deploy hook do Render. Também pode ser executado manualmente em **Actions → CD → Run workflow**.

Para ativar o deploy automático, cadastre o segredo `RENDER_DEPLOY_HOOK_URL` em **Settings → Secrets and variables → Actions** com a URL do deploy hook do serviço no Render (**Settings → Deploy Hook**). Sem o segredo, o CD só emite um aviso e não falha. O build no Render continua sendo feito pelo `build.sh`.

### Usuários de demonstração

Senha de todos: `verdigis123`.

| E-mail | Papel |
| --- | --- |
| `admin@demo.com` | Superusuário |
| `empresa@demo.com` | Empresa "Farmácia Vida Verde [DEMO]" |
| `funcionario@demo.com` e `funcionario2@demo.com` | Funcionários da empresa |
| `consultor@demo.com` | Consultor da empresa, com permissão para criar metas |
| `pendente@demo.com` | Funcionário com pedido de entrada pendente |

### Variáveis de ambiente

| Variável | Obrigatória | Descrição |
| --- | --- | --- |
| `SECRET_KEY` | Sim | Chave secreta do Django |
| `ENVIRONMENT` | Sim | `development` liga o modo de depuração e, sem `DATABASE_URL`, usa SQLite local |
| `DATABASE_URL` | Em produção | URL de conexão do PostgreSQL. Quando definida, é usada em qualquer ambiente |
| `DJANGO_SUPERUSER_EMAIL` e `DJANGO_SUPERUSER_PASSWORD` | Não | Criam o superusuário durante o build (o Render gratuito não tem shell) |
| `CARREGAR_DEMO` | Não | `sim` carrega os dados de demonstração no build |

## Deploy

O deploy é feito no Render (plano gratuito). O script `build.sh` instala as dependências, coleta os arquivos estáticos, prepara o banco, aplica as migrações e cria o superusuário:

```bash
./build.sh
```

Configure `SECRET_KEY`, `ENVIRONMENT` e `DATABASE_URL` como variáveis de ambiente do serviço e use `gunicorn verdigis.wsgi` como comando de inicialização.

No plano gratuito o disco é apagado a cada deploy ou reinício (fotos de perfil enviadas se perdem e o avatar padrão volta a aparecer) e o serviço hiberna após 15 minutos sem acesso.

---

## Estrutura do repositório

```
.
├── verdigis/
├── forum/
├── accounts/
├── dashboard/
├── templates/
├── docs/
├── ARQUITETURA.md
├── build.sh
├── manage.py
├── .gitignore
└── requirements.txt
```

---

## Entregas
Veja o andamento de cada entrega em [docs/README.md](./docs/README.md).

---

## Equipe

Estudantes de Ciências da Computação e Design, CESAR School.

- Ana Luiza Carvalho Xavier
- Carlos Henrique Corrêa de Araújo Soares de Sousa
- Carlos Vinicius Encarnação do Nascimento
- João Marcelo Franca da Costa Casado
- João Pedro dos Santos Menezes
- Lucas de Moura Mattos
- Matheus Raulino de Souza Moreira
- Pétala Kiara da Silva
- Thácio Soares Miranda dos Santos
- Vitória de Assis Seabra

Parceiro do desafio: Deloitte
