# Arquitetura da Verdigis

Documento técnico curto: como o código está organizado, quem pode fazer o quê e como os fluxos principais funcionam.

## Apps e pastas

| App | O que tem |
| --- | --- |
| `verdigis/` | Settings, URLs raiz, WSGI |
| `forum/` | Site institucional (início, sobre, fale conosco). Guarda também o CSS, o JS e as imagens compartilhados (`forum/static/`) e o `base.html` |
| `accounts/` | Usuário (login por e-mail), empresa, perfis de funcionário e consultor, vínculos, pedidos de entrada, capacidades do consultor, notificações, triagem e permissões |
| `dashboard/` | Menu do dashboard, equipe, Fábrica de Metas, relatos (Central de Avaliações), apagar empresa, dados de demonstração |
| `templates/` | Páginas de erro 403 e 404 |

Dentro de cada app:

- `models.py`: modelos. `services.py`: toda regra que altera dados (dentro de `transaction.atomic()`).
- `views.py`: valida o formulário, chama o service, redireciona.
- `accounts/permissions.py`: a função `pode()`, única fonte de autorização.
- `accounts/middleware.py`: `ContextoEmpresaMiddleware` (empresa da requisição) e `TriagemObrigatoriaMiddleware`.
- `accounts/context_processors.py`: contagem de notificações não lidas para o sino do menu.
- Template tags: `{% pode 'acao' obj as var %}` (`accounts/templatetags/permissoes.py`) e `{% nome_exibido relato %}` (`dashboard/templatetags/relatos.py`).

## Papéis e contexto da empresa

`User.papel`: vazio (ainda na triagem), `EMPRESA`, `FUNCIONARIO` ou `CONSULTOR`. Superusuário não passa pela triagem.

Em toda requisição autenticada o middleware define:

- `request.empresa`: a `Company` em que a pessoa atua (ou `None`);
- `request.vinculo`: o `Vinculo` com essa empresa (`None` para o responsável);
- `request.capacidades`: `frozenset` das capacidades do consultor nessa empresa.

O responsável atua na própria empresa. O funcionário tem no máximo um vínculo. O consultor pode ter vários: a empresa ativa fica em `session['empresa_ativa_id']` e é revalidada a cada requisição (vínculo removido cai para o primeiro que restar, ou para nenhum).

**Isolamento:** todo id na URL é buscado filtrando pela empresa da requisição (`get_object_or_404(Meta, id=..., company=request.empresa)`). Id de outra empresa dá 404; só depois a view chama `pode()`, que dá 403 se negar.

## Matriz de permissões (`accounts/permissions.py`)

| Ação | Empresa | Funcionário | Consultor observador | Capacidade do consultor |
| --- | --- | --- | --- | --- |
| `equipe.gerir` | sim | não | não | não delegável |
| `empresa.apagar` | sim | não | não | não delegável |
| `meta.ver` | todas | gerais e as individuais dele | todas | n/a |
| `meta.criar` | sim | só individual para si | não | `METAS_CRIAR` |
| `meta.editar` | sim | só as que criou | não | `METAS_EDITAR` |
| `meta.concluir` | sim | gerais e as dele | não | `METAS_CONCLUIR` |
| `meta.apagar` | sim | só as que criou | não | `METAS_APAGAR` |
| `relato.enviar` | não | sim | sim | n/a |
| `relato.ver_todos` | sim | não (vê só os próprios não anônimos) | sim | n/a |
| `relato.moderar` | sim | não | não | `RELATOS_MODERAR` |

Ação desconhecida levanta `KeyError`. `ACOES_NAO_DELEGAVEIS` (`equipe.gerir`, `empresa.apagar`, `diagnostico.responder`) nunca tem capacidade associada; um teste garante isso. A capacidade existe quando há uma linha em `ConcessaoConsultor`.

## Fluxos principais

**Cadastro e triagem.** A pessoa cria a conta com nome, e-mail e senha e cai na triagem. Escolhe Empresa (formulário da empresa, com busca de CEP), Funcionário (nome, CPF, telefone) ou Consultor (nome, documento, telefone, especialidade). `concluir_onboarding` grava o perfil e o papel numa transação e recusa quem já tem papel. Esqueceu a senha: fala com o suporte; o superusuário redefine pelo admin.

**Entrada na empresa.** A empresa tem um código de 10 caracteres (`XXXXX-XXXXX`, sem 0, 1, I, L, O). Funcionário ou consultor pede para entrar com o código, cargo e setor (`criar_solicitacao`). A Empresa aceita ou recusa na tela Equipe. Aceitar cria o `Vinculo` (tipo tirado do papel, nunca do formulário) e cancela os outros pedidos pendentes do funcionário.

**Saída.** O membro sai em "Meus vínculos" ou é removido pela Empresa (`encerrar_vinculo`). As metas individuais do funcionário ficam "Sem responsável" (`SET_NULL`) e a Empresa recebe `MEMBRO_SAIU` com os títulos de até 5 delas. Para reatribuir, basta editar a meta.

**Capacidades do consultor.** Na aba Consultores, um checkbox por capacidade e um botão "Salvar permissões". `atualizar_capacidades` só aceita consultor da empresa da requisição e notifica o consultor quando algo muda. Vale na próxima requisição.

**Relatos e anonimato.** O autor fica sempre gravado em `usuario`, mas só `nome_exibido()` decide o que aparece: "Anônimo" para relato anônimo (em qualquer tela, inclusive no admin, que não mostra o campo), nome · cargo · setor para Empresa e consultor, "Ex-colaborador" se a conta foi excluída, "Você" para o próprio autor. O funcionário vê só os próprios relatos não anônimos. Moderar oculta o relato das listas; ele fica na aba "Ocultos" para quem modera.

**Exclusões.** Apagar empresa pede senha e o código da empresa, avisa membros e solicitantes (`EMPRESA_ENCERRADA`), apaga em cascata vínculos, pedidos, metas e relatos e devolve o responsável à triagem. Excluir conta pede a senha; o responsável apaga a empresa junto; funcionário e consultor avisam cada empresa.

## Notificações

Só `accounts.services.notificar()` cria notificações. Tipos: `SOLICITACAO_RECEBIDA`, `SOLICITACAO_ACEITA`, `SOLICITACAO_RECUSADA`, `VINCULO_REMOVIDO`, `MEMBRO_SAIU`, `PERMISSOES_ALTERADAS`, `EMPRESA_ENCERRADA`. Abrir uma notificação a marca como lida e leva ao link dela (só links internos). Nenhum e-mail é enviado.

## Comandos

| Comando | Para quê |
| --- | --- |
| `python manage.py popular_demo` | Dados de demonstração. Idempotente. Só com `ENVIRONMENT=development`, a menos que receba `--permitir-fora-de-desenvolvimento` |
| `python manage.py preparar_banco` | Remove o esquema antigo de contas (anterior ao login por e-mail) antes do `migrate`, preservando o conteúdo do `forum`. Só apaga com `RESETAR_CONTAS_LEGADO=sim` |
| `python manage.py garantir_superusuario` | Cria o superusuário de `DJANGO_SUPERUSER_EMAIL` e `DJANGO_SUPERUSER_PASSWORD`, se ainda não existir |

## Usuários de demonstração

Senha de todos: `verdigis123`.

| E-mail | Papel |
| --- | --- |
| `admin@demo.com` | Superusuário |
| `empresa@demo.com` | Empresa "Farmácia Vida Verde [DEMO]" |
| `funcionario@demo.com` | Funcionário vinculado |
| `funcionario2@demo.com` | Funcionário vinculado |
| `consultor@demo.com` | Consultor vinculado, com `METAS_CRIAR` |
| `pendente@demo.com` | Funcionário com pedido pendente |

## Deploy no Render (plano gratuito)

- **Sem shell e sem pre-deploy command:** o `build.sh` roda `collectstatic`, `preparar_banco`, `migrate`, `garantir_superusuario` e, se `CARREGAR_DEMO=sim`, o `popular_demo`.
- **Primeiro deploy sobre o banco antigo:** defina `RESETAR_CONTAS_LEGADO=sim`, faça o deploy e depois remova a variável. Sem ela, o build para com uma mensagem explicativa e a versão anterior continua no ar. Usuários, metas e relatos antigos são apagados; o conteúdo do site fica.
- **Disco temporário:** fotos de perfil ficam em `media/`, que é apagado a cada deploy ou reinício. A aplicação mostra o avatar padrão quando o arquivo some. A mídia é servida pelo próprio Django em produção.
- **Logs:** erros vão para o console (aba Logs do Render).
- **Hibernação:** o serviço gratuito dorme após 15 minutos sem acesso; a primeira requisição depois disso demora.
- O Postgres gratuito do Render expira após um período; confira o painel antes de apresentações.

## Decisões de simplificação

- O `forum` continua sem `app_name` (as rotas `index`, `sobre` e `fale_conosco` são usadas sem namespace).
- O papel escolhido na triagem não pode ser trocado; para mudar, a pessoa exclui a conta (ou, se for Empresa, apaga a empresa e volta à triagem).
- Os botões "Diagnóstico de compatibilidade", "Práticas da empresa" e "Quadro de tarefas" continuam reservados, visíveis só para a Empresa.
