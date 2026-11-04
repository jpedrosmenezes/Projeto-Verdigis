from django.conf import settings
from django.db import models


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
