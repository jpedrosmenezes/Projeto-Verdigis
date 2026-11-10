from django.conf import settings
from django.db import models
from django.utils import timezone



# Fábrica de metas
class Meta(models.Model):
    ESG_ESCOLHA = [
        ('E', 'Ambiental (Environmental)'),
        ('S', 'Social'),
        ('G', 'Governança (Governance)'),
    ]

    NIVEL_PRIORIDADE = [
        ('BAIXA', 'Baixa'),
        ('MEDIA', 'Média'),
        ('ALTA', 'Alta'),
    ]

    TIPO_ESCOLHA = [
        ('GERAL', 'Meta Geral'),
        ('INDIVIDUAL', 'Meta Individual'),
    ]

    company = models.ForeignKey(
        'accounts.Company',
        on_delete=models.CASCADE,
        related_name='metas',
        verbose_name='Empresa',
    )
    # Nulo numa meta individual = funcionário saiu e a meta ficou sem responsável.
    funcionario = models.ForeignKey(
        'accounts.Vinculo',
        on_delete=models.SET_NULL,
        related_name='metas',
        null=True,
        blank=True,
        verbose_name='Funcionário responsável',
    )
    tipo = models.CharField(max_length=10, choices=TIPO_ESCOLHA, default='GERAL', verbose_name='Tipo de meta')
    # Quem criou a meta (usado na regra "funcionário só edita o que criou").
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='metas',
    )
    nome = models.CharField(max_length=255)
    pilar_esg = models.CharField(max_length=1, choices=ESG_ESCOLHA)
    deadline = models.DateField()
    resumo = models.TextField()
    prioridade = models.CharField(max_length=5, choices=NIVEL_PRIORIDADE, default='MEDIA')
    completo = models.BooleanField(default=False)
    data_criacao = models.DateTimeField(auto_now_add=True)

    @property
    def sem_responsavel(self):
        return self.tipo == 'INDIVIDUAL' and self.funcionario_id is None

    def __str__(self):
        if self.tipo == 'INDIVIDUAL' and self.funcionario:
            return f'{self.nome} - {self.funcionario.user} [{self.pilar_esg}]'
        return f'{self.nome} - Meta Geral [{self.pilar_esg}]'


# Relatos da equipe (Central de Avaliações)
class RelatoSocialVerdigis(models.Model):
    TEMA_ESG_CHOICES = [
        ('SAUDE_MENTAL', 'Saúde Mental e Bem-estar'),
        ('DIVERSIDADE', 'Diversidade, Equidade e Inclusão'),
        ('SEGURANCA', 'Saúde e Segurança do Trabalho'),
        ('LIDERANCA', 'Práticas de Liderança e Gestão'),
        ('BENEFICIOS', 'Remuneração e Benefícios'),
    ]

    IMPACTO_CHOICES = [
        ('POSITIVO', 'Impacto Positivo (Elogio/Boa Prática)'),
        ('NEGATIVO', 'Impacto Negativo (Reclamação/Risco)'),
        ('NEUTRO', 'Neutro (Sugestão/Dúvida)'),
    ]

    company = models.ForeignKey(
        'accounts.Company',
        on_delete=models.CASCADE,
        related_name='relatos',
        verbose_name='Empresa',
    )
    mensagem = models.TextField(help_text='Relato ou avaliação do colaborador')
    tema_esg = models.CharField(max_length=20, choices=TEMA_ESG_CHOICES)
    sentimento = models.CharField(max_length=10, choices=IMPACTO_CHOICES)
    data_registro = models.DateTimeField(auto_now_add=True)

    # Sempre guarda o autor, inclusive nos anônimos. Quem decide o que aparece
    # na tela é dashboard.services.nome_exibido; nenhuma tela lê este campo direto.
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='relatos',
        verbose_name='Autor',
    )
    eh_anonimo = models.BooleanField(default=True)

    oculto_em = models.DateTimeField(null=True, blank=True)
    oculto_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='relatos_ocultados',
    )
    motivo_ocultacao = models.CharField(max_length=300, blank=True)

    class Meta:
        verbose_name = 'Relato Social ESG'
        verbose_name_plural = 'Relatos Sociais ESG'

    def __str__(self):
        return f'Relato {self.get_tema_esg_display()} - {self.get_sentimento_display()}'


# ---------- Painel de Parcerias ----------

# Reaproveita os três pilares da Meta (E, S, G) sem depender do nome "Meta",
# que dentro das classes abaixo é a classe interna de configuração do Django.
PILARES_ESG = Meta.ESG_ESCOLHA


class QualidadeESG(models.Model):
    """Prática/qualidade ESG que uma empresa pode declarar (ex.: "Energia renovável")."""

    nome = models.CharField(max_length=80)
    pilar = models.CharField(max_length=1, choices=PILARES_ESG)

    class Meta:
        verbose_name = 'Qualidade ESG'
        verbose_name_plural = 'Qualidades ESG'
        ordering = ['pilar', 'nome']
        constraints = [
            models.UniqueConstraint(fields=['pilar', 'nome'], name='qualidade_unica_por_pilar'),
        ]

    def __str__(self):
        return f'{self.get_pilar_display()} · {self.nome}'


class RecursoAcessibilidade(models.Model):
    """Condição de acessibilidade/atendimento da empresa (ex.: "Intérprete de Libras")."""

    nome = models.CharField(max_length=80, unique=True)

    class Meta:
        verbose_name = 'Recurso de acessibilidade'
        verbose_name_plural = 'Recursos de acessibilidade'
        ordering = ['nome']

    def __str__(self):
        return self.nome


class PerfilParceria(models.Model):
    """Perfil público da empresa no Painel de Parcerias. Só aparece para as outras se `visivel`."""

    company = models.OneToOneField(
        'accounts.Company',
        on_delete=models.CASCADE,
        related_name='perfil_parceria',
        verbose_name='Empresa',
    )
    visivel = models.BooleanField(
        default=False,
        verbose_name='Aparecer no Painel de Parcerias',
        help_text='Desligado, nenhuma outra empresa encontra o seu perfil.',
    )
    descricao = models.TextField(max_length=600, blank=True, verbose_name='Apresentação')
    qualidades = models.ManyToManyField(
        QualidadeESG, blank=True, related_name='perfis', verbose_name='O que a empresa já faz',
    )
    acessibilidades = models.ManyToManyField(
        RecursoAcessibilidade, blank=True, related_name='perfis', verbose_name='Acessibilidade',
    )
    necessidades = models.ManyToManyField(
        QualidadeESG, blank=True, related_name='perfis_interessados', verbose_name='O que a empresa procura em parceiros',
    )
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Perfil de parceria'
        verbose_name_plural = 'Perfis de parceria'

    def __str__(self):
        return f'Perfil de parceria de {self.company}'


class InteresseParceria(models.Model):
    """Match dado por `origem` em `destino`. É mútuo quando existe o registro inverso."""

    origem = models.ForeignKey(
        'accounts.Company', on_delete=models.CASCADE, related_name='interesses_enviados',
    )
    destino = models.ForeignKey(
        'accounts.Company', on_delete=models.CASCADE, related_name='interesses_recebidos',
    )
    # Eixo em que a empresa estava navegando quando deu o match.
    pilar = models.CharField(max_length=1, choices=PILARES_ESG)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Interesse de parceria'
        verbose_name_plural = 'Interesses de parceria'
        ordering = ['-criado_em']
        constraints = [
            models.UniqueConstraint(fields=['origem', 'destino'], name='interesse_unico_por_par'),
        ]

    def __str__(self):
        return f'{self.origem} → {self.destino} [{self.pilar}]'


#--------tabela de atividades-----------

class AtividadeMeta(models.Model):
    KANBAM_CHOICES = [
        ('A_FAZER', 'A Fazer'),
        ('EM_ANDAMENTO', 'Em Andamento'),
        ('REVISAO', 'Em Revisão'),
        ('FEITO', 'Feito'),
    ]

    meta = models.ForeignKey(
        Meta,
        on_delete=models.CASCADE,
        related_name='atividades',
        verbose_name='Meta',
    )
    nome = models.CharField(max_length=255, verbose_name='Nome da atividade')
    descricao = models.TextField(blank=True, verbose_name='Descrição')
    prazo = models.DateField(null=True, blank=True, verbose_name='Prazo')
    prioridade = models.CharField(
        max_length=5,
        choices=Meta.NIVEL_PRIORIDADE,
        default='MEDIA',
        verbose_name='Prioridade',
    )
    status = models.CharField(
        max_length=20,
        choices=KANBAM_CHOICES,
        default='A_FAZER',
        verbose_name='Status',
    )
    data_criacao = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Atividade da Meta'
        verbose_name_plural = 'Atividades da Meta'
        ordering = ['prazo', 'id']

    @property
    def em_atraso(self):
        """Retorna True se tiver prazo definido, não estiver em 'FEITO' e a data já venceu."""
        if self.prazo and self.status != 'FEITO':
            return self.prazo < timezone.localdate()
        return False

    def __str__(self):
        return f'{self.nome} [{self.get_status_display()}]'
