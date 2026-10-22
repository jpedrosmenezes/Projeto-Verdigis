from django.conf import settings
from django.db import models
from django.contrib.auth.models import User

#fabrica de metas!!
class Meta(models.Model):
    ESG_ESCOLHA = [
        ('E', 'Ambiental (Environmental)'),
        ('S', 'Social'),
        ('G', 'Governança (Governance)')
    ]

    NIVEL_PRIORIDADE = [
        ('BAIXA', 'Baixa'),
        ('MEDIA', 'Média'),
        ('ALTA', 'Alta')
    ]

    TIPO_ESCOLHA = [
        ('GERAL', 'Meta Geral'),
        ('INDIVIDUAL', 'Meta Individual:')
    ]
    
    #conexao de metas e empresas
    #o ForeignKey serve pra conectar coisas
    company = models.ForeignKey(
        'accounts.Company',
        on_delete=models.CASCADE,
        related_name='metas',
        verbose_name="Empresa",
    )
    funcionario = models.ForeignKey(
        'accounts.Funcionario',
        on_delete=models.CASCADE,
        related_name='metas',
        null=True,
        blank=True,
        verbose_name="Funcionário Responsável",
    )

    
    # Adicionado o campo 'tipo' usando TIPO_ESCOLHA
    tipo = models.CharField(max_length=10, choices=TIPO_ESCOLHA, default='GERAL', verbose_name="Tipo de Meta")#tipo de meta
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='metas')#quem criou
    nome = models.CharField(max_length=255)#nome da meta
    pilar_esg = models.CharField(max_length=1, choices=ESG_ESCOLHA)#pilar ESG
    deadline = models.DateField()#Quanto tempo dura a meta
    resumo = models.TextField()#resumo da meta
    prioridade = models.CharField(max_length=5, choices=NIVEL_PRIORIDADE, default='MEDIA')#nivel de prioridade
    completo = models.BooleanField(default=False)#statuts da meta
    data_criacao = models.DateTimeField(auto_now_add=True)#quando foi criado

    def __str__(self):
        if self.tipo == 'INDIVIDUAL' and self.funcionario:
            return f"{self.nome} - {self.funcionario.user.username} [{self.pilar_esg}]"
        return f"{self.nome} - Meta Geral [{self.pilar_esg}]"

    
#Quadro de avaliações
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

    mensagem = models.TextField(help_text="Relato ou avaliação do colaborador")
    tema_esg = models.CharField(max_length=20, choices=TEMA_ESG_CHOICES)
    sentimento = models.CharField(max_length=10, choices=IMPACTO_CHOICES)
    data_registro = models.DateTimeField(auto_now_add=True)

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='relatos',
        verbose_name="Autor",
    )
    
    eh_anonimo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Relato Social ESG"
        verbose_name_plural = "Relatos Sociais ESG"

    company = models.ForeignKey(
        'accounts.Company',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='relatos',
        verbose_name="Empresa",
    )

    def __str__(self):
        return f"Relato {self.get_tema_esg_display()} - {self.get_sentimento_display()}"

class Empresa(models.Model):
    nome = models.CharField(max_length=200)

    def __str__(self):
        return self.nome

class AvaliacaoESG(models.Model):
    PILARES_CHOICES = [
        ('E', 'Ambiental (Environmental)'),
        ('S', 'Social (Social)'),
        ('G', 'Governança (Governance)'),
    ]

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='avaliacoes')
    funcionario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='minhas_avaliacoes')
    pilar = models.CharField(max_length=1, choices=PILARES_CHOICES, verbose_name="Pilar ESG")
    nota = models.PositiveSmallIntegerField(verbose_name="Nota (1 a 5)")
    comentario = models.TextField(blank=True, null=True, verbose_name="Comentário")
    data_avaliacao = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.empresa.nome} - {self.get_pilar_display()} por {self.funcionario.username}"