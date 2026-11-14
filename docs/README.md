# Entregas do Projeto Verdigis

Repositório: [`Projeto-Verdigis`](https://github.com/jpedrosmenezes/Projeto-Verdigis)

## Índice

- [Entrega 01](#entrega-01)
- [Entrega 02](#entrega-02)
- [Entrega 03](#entrega-03)
- [Entrega 04](#entrega-04)

---

<a id="entrega-01"></a>
## Entrega 01

### Documentação
- [Benchmark - Análise de Competidores](./competitoranalysis/competitoranalysis.md)

### Backlog
![Print do Backlog](./backlogs/backlog-1.jpg)

### Quadro do 1º Sprint
![Print do Quadro do 1º Sprint](./sprints/sprint-1.jpg)

---

<a id="entrega-02"></a>
## Entrega 02

### Quadro do 2º Sprint
![Print do Quadro do 2º Sprint](./sprints/Sprint2.jpeg)

### Site
- [Acessar o site](https://projeto-verdigis.onrender.com)

### Screencast de explicação do código Django
- [Assistir no YouTube](https://youtu.be/IaMJn3oHWg4)

### Screencast do Deployment
- [Assistir no YouTube](https://youtu.be/w_VHeL16tqk)

> Legendas disponíveis no YouTube.

### Issue/Bug Tracker
![Print do Bug Tracker](./sprints/issue.jpeg)

---

<a id="entrega-03"></a>
## Entrega 03

### Backlog
![Print do Backlog](./backlogs/backlog-3.jpeg)

### Quadro do 3º Sprint
![Print do Quadro do 3º Sprint](./sprints/sprint3.jpeg)

### Site
- [Acessar o site](https://projeto-verdigis.onrender.com)

### Screencast de explicação do código Django
- [Assistir no YouTube](https://youtu.be/lO8UCX8t5BI)

### Screencast do Deployment
- [Assistir no YouTube](https://youtu.be/b2IN5Jz2a6U)



### Histórias Implementadas:

#### *História 01 :*

Como gestor de uma empresa, quero fazer o cadastro dela na plataforma Verdigis, para começar a usar os benefícios que a plataforma traz na questão da ESG, melhorando algumas atividades que são aplicadas ou não na minha empresa.

Critérios de aceitação: 
O gestor da empresa precisa colocar os  dados da empresa.
Além disso, a empresa deve colocar o seu nicho para a plataforma focar naquilo que a empresa precisa.
O sistema deve pedir informações importantes na parte do ESG para ter uma noção do que a empresa aplica.
O sistema avaliará as informações dadas e validar elas.

#### *História 02 :*

Como representante da empresa, quero estabelecer metas de atividades de ESG para minha empresa, buscando trazer objetivos para melhorar algumas partes da empresa, principalmente a questão da sustentabilidade.

Critérios de aceitação:
O usuário deve criar a meta.
Após isso, ele deve relacionar a meta com alguma atividade/área que deseja focar.
Juntamente com isso,  o usuário deve colocar um tempo limite para realizar a atividade que ele colocou.

#### *História 03 :*
Como responsável pela empresa, quero analisar a seção de reclamações/avaliações dos funcionários, buscando trazer um melhor bem-estar com os funcionários da empresa, fortalecendo a questão social.

Critérios de aceitação:
Deve mostrar de forma simplificada quantas mensagens que abordam determinado conteúdo foram enviadas
Filtrar a avaliação dos funcionários, verificando se é algo positivo ou negativo, buscando fazer com que o empresário vá atrás de mudanças.


### Issue/Bug Tracker
![Print do Bug Tracker](./issues/issue.bugtracker.jpeg)

---

<a id="entrega-04"></a>
## Entrega 04

Testes automatizados:
- Testes unitários em `dashboard/tests.py` e testes de navegador com Selenium em `tests/` (Chrome headless), cobrindo login, cadastro, logout, criação de meta, envio de avaliação, o fluxo do #111 de ponta a ponta, a pontuação do #116 conforme a atividade avança no kanban, o filtro "Meta Geral" do #118, o quadro no painel do funcionário, o cancelar da avaliação, o voltar das parcerias e checagens de layout. O `ci.yml` roda tudo automaticamente no GitHub Actions. Como rodar: veja a seção "Testes" do [README](../README.md#testes).

### Histórias Implementadas

#### *História 01 :*

##### *Painel de Atividades de uma empresa*
Deve ser implementado um painel, no estilo Kanban, para que o gestor tenha controle total sobre a forma como as suas metas estão a ser tratadas, além de receber notificações sobre atividades em atraso.

#### *História 02 :*
##### *Painel de Parcerias*
Deve ser implementado um painel no qual a empresa possa procurar parceiros de ESG de acordo com o seu perfil e as suas necessidades. Deve tratar-se de uma listagem de empresas, separadas pelos três pilares, na qual a empresa poderá dar um match de acordo com o que preferir.

#### *História 03 :*
##### *Análise de Desempenho e Gráfico ESG*
Deve ser implementada uma aba com uma análise detalhada de como a empresa está a progredir em cada pilar ESG. Deve existir um cadastro inicial das métricas ESG e, para cada atividade cumprida num pilar, o seu valor correspondente deve ser incrementado nas métricas. Paralelamente a isso, deve ser implementado um sistema de pontuação, que vai computando ao longo da conclusão das metas cadastradas pela empresa.

### Backlog
![Print do Backlog](./backlogs/backlog-4.jpeg)

### Quadro do 4º Sprint
![Print do Quadro do 4º Sprint](./sprints/sprint.4.jpeg)

### Site
- [Acessar o site](https://projeto-verdigis.onrender.com)

### Screencast do Front-End e Back-End
- [Assistir no YouTube](https://youtu.be/4qkoctXl6BY)
  - O Front-end começa em 10:50, mas a imagem do Back-End ficou ruim. O screencast do Back-End está no link abaixo.

### Screencast do Back-End
- [Assistir no YouTube](https://youtu.be/9N2g4tt19mU)

### Screencast dos testes
- [Assistir no Youtube](https://youtu.be/l2WLd680l3I)

### Screencast CI/CD
- [Assistir no Youtube](https://youtu.be/On9BI8n3060)

### Issue/Bug Tracker
![Print do Bug Tracker](./issues/issue.bugtracker4.jpeg)
