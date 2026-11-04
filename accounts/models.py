import re
import secrets

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower
from django.templatetags.static import static
from django.utils import timezone

from .validators import validate_cnpj, validate_cpf


class Papel(models.TextChoices):
    NENHUM = '', 'Sem papel'
    EMPRESA = 'EMPRESA', 'Empresa'
    FUNCIONARIO = 'FUNCIONARIO', 'Funcionário'
    CONSULTOR = 'CONSULTOR', 'Consultor'


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra):
        if not email:
            raise ValueError('O e-mail é obrigatório.')
        user = self.model(email=self.normalize_email(email).lower(), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra):
        extra.setdefault('is_staff', False)
        extra.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra)

    def create_superuser(self, email, password=None, **extra):
        extra['is_staff'] = True
        extra['is_superuser'] = True
        return self._create_user(email, password, **extra)

    def get_by_natural_key(self, email):
        # Login sem diferenciar maiúsculas: "Ana@X.com" e "ana@x.com" são a mesma conta.
        return self.get(email__iexact=email)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField('E-mail', unique=True)
    nome = models.CharField('Nome', max_length=150)
    telefone = models.CharField('Telefone', max_length=11, blank=True)
    bio = models.TextField('Bio', blank=True)
    foto_perfil = models.ImageField('Foto de perfil', upload_to='avatars/', blank=True, null=True)
    papel = models.CharField('Papel', max_length=12, choices=Papel.choices, blank=True, default=Papel.NENHUM)
    is_active = models.BooleanField('Ativo', default=True)
    is_staff = models.BooleanField('Acesso ao admin', default=False)
    date_joined = models.DateTimeField('Membro desde', default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    EMAIL_FIELD = 'email'
    REQUIRED_FIELDS = ['nome']

    class Meta:
        verbose_name = 'Usuário'
        verbose_name_plural = 'Usuários'
        constraints = [
            # Um e-mail por pessoa, mesmo que digitado com maiúsculas diferentes.
            models.UniqueConstraint(Lower('email'), name='accounts_user_email_unico_ci'),
        ]

    def save(self, *args, **kwargs):
        self.email = (self.email or '').strip().lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nome or self.email

    def get_full_name(self):
        return self.nome or self.email

    def get_short_name(self):
        return (self.nome or self.email).split(' ')[0]

    @property
    def avatar_url(self):
        # No Render gratuito o disco é apagado a cada deploy: se o arquivo sumiu,
        # mostramos o avatar padrão em vez de uma imagem quebrada.
        if self.foto_perfil and self.foto_perfil.storage.exists(self.foto_perfil.name):
            return self.foto_perfil.url
        return static('img/default-avatar.png')


class Niche(models.Model):
    nome = models.CharField('Nicho', max_length=100, unique=True)
    descricao = models.TextField('Orientações', blank=True)

    class Meta:
        ordering = ['nome']

    def __str__(self):
        return self.nome


# Sem 0, 1, I, L e O: evita confusão ao ditar ou digitar o código.
ALFABETO_CODIGO = '23456789ABCDEFGHJKMNPQRSTUVWXYZ'
TAMANHO_CODIGO = 10


def gerar_codigo_empresa():
    return ''.join(secrets.choice(ALFABETO_CODIGO) for _ in range(TAMANHO_CODIGO))


def normalizar_codigo(valor):
    """Aceita o código com ou sem hífen e em qualquer caixa."""
    return re.sub(r'[^0-9A-Za-z]', '', valor or '').upper()


class Company(models.Model):
    codigo = models.CharField('Código da empresa', max_length=TAMANHO_CODIGO, unique=True, editable=False)
    responsavel = models.OneToOneField(
        'accounts.User', on_delete=models.PROTECT, related_name='empresa', verbose_name='Responsável',
    )
    niche = models.ForeignKey(Niche, on_delete=models.PROTECT, verbose_name='Nicho')

    razao_social = models.CharField('Razão Social', max_length=255)
    nome_fantasia = models.CharField('Nome Fantasia', max_length=255)
    cnpj = models.CharField('CNPJ', max_length=18, unique=True, validators=[validate_cnpj])
    inscricao_estadual = models.CharField('Inscrição Estadual', max_length=20, blank=True)
    inscricao_municipal = models.CharField('Inscrição Municipal', max_length=20, blank=True)

    cep = models.CharField('CEP', max_length=9)
    logradouro = models.CharField('Logradouro', max_length=255)
    numero = models.CharField('Número', max_length=10)
    complemento = models.CharField('Complemento', max_length=100, blank=True)
    bairro = models.CharField('Bairro', max_length=100)
    cidade = models.CharField('Cidade', max_length=100)
    uf = models.CharField('UF', max_length=2)

    email_corporativo = models.EmailField('E-mail corporativo')
    telefone_fixo = models.CharField(
        'Telefone fixo', max_length=15,
        validators=[RegexValidator(r'^\(?\d{2}\)?\s?\d{4}-?\d{4}$', 'Telefone inválido.')],
    )
    celular_whatsapp = models.CharField(
        'Celular/WhatsApp', max_length=15,
        validators=[RegexValidator(r'^\(?\d{2}\)?\s?9\d{4}-?\d{4}$', 'Celular inválido.')],
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Empresa'
        verbose_name_plural = 'Empresas'

    def save(self, *args, **kwargs):
        self.cnpj = re.sub(r'[^0-9A-Za-z]', '', self.cnpj).upper()
        self.cep = re.sub(r'\D', '', self.cep)
        self.uf = (self.uf or '').strip().upper()
        if not self.codigo:
            codigo = gerar_codigo_empresa()
            while Company.objects.filter(codigo=codigo).exists():
                codigo = gerar_codigo_empresa()
            self.codigo = codigo
        super().save(*args, **kwargs)

    @property
    def codigo_formatado(self):
        return f'{self.codigo[:5]}-{self.codigo[5:]}'

    def __str__(self):
        return self.nome_fantasia


class PerfilFuncionario(models.Model):
    user = models.OneToOneField('accounts.User', on_delete=models.CASCADE, related_name='perfil_funcionario')
    cpf = models.CharField('CPF', max_length=11, unique=True, validators=[validate_cpf])

    def __str__(self):
        return f'Funcionário {self.user}'


class PerfilConsultor(models.Model):
    class TipoDocumento(models.TextChoices):
        CPF = 'CPF', 'CPF'
        CNPJ = 'CNPJ', 'CNPJ'

    user = models.OneToOneField('accounts.User', on_delete=models.CASCADE, related_name='perfil_consultor')
    documento_tipo = models.CharField('Tipo de documento', max_length=4, choices=TipoDocumento.choices)
    documento = models.CharField('Documento', max_length=14, unique=True)
    especialidade = models.CharField('Especialidade', max_length=150)
    link_profissional = models.URLField('Link profissional', blank=True)

    def __str__(self):
        return f'Consultor {self.user}'


class TipoVinculo(models.TextChoices):
    FUNCIONARIO = 'FUNCIONARIO', 'Funcionário'
    CONSULTOR = 'CONSULTOR', 'Consultor'


class Vinculo(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='vinculos')
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='vinculos')
    # Definido no servidor a partir de user.papel, nunca vindo de formulário.
    tipo = models.CharField(max_length=12, choices=TipoVinculo.choices)
    cargo = models.CharField('Cargo', max_length=100)
    setor = models.CharField('Setor', max_length=100)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['criado_em']
        constraints = [
            # Uma pessoa entra uma única vez em cada empresa.
            models.UniqueConstraint(fields=['user', 'company'], name='accounts_vinculo_unico_por_empresa'),
            # Funcionário trabalha em uma empresa por vez (consultor pode atender várias).
            models.UniqueConstraint(
                fields=['user'], condition=Q(tipo='FUNCIONARIO'), name='accounts_vinculo_funcionario_unico',
            ),
        ]

    def __str__(self):
        return f'{self.user} em {self.company} ({self.get_tipo_display()})'


class Capacidade(models.TextChoices):
    METAS_CRIAR = 'METAS_CRIAR', 'Criar metas'
    METAS_EDITAR = 'METAS_EDITAR', 'Editar metas'
    METAS_CONCLUIR = 'METAS_CONCLUIR', 'Concluir e reabrir metas'
    METAS_APAGAR = 'METAS_APAGAR', 'Apagar metas'
    RELATOS_MODERAR = 'RELATOS_MODERAR', 'Moderar relatos'


DESCRICAO_CAPACIDADE = {
    Capacidade.METAS_CRIAR: 'Cria metas gerais e individuais para a equipe.',
    Capacidade.METAS_EDITAR: 'Altera qualquer meta da empresa.',
    Capacidade.METAS_CONCLUIR: 'Marca metas como concluídas ou as reabre.',
    Capacidade.METAS_APAGAR: 'Exclui metas da empresa.',
    Capacidade.RELATOS_MODERAR: 'Oculta e restaura relatos da equipe.',
}


class ConcessaoConsultor(models.Model):
    vinculo = models.ForeignKey(Vinculo, on_delete=models.CASCADE, related_name='concessoes')
    capacidade = models.CharField(max_length=30, choices=Capacidade.choices)
    concedida_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            # A linha existir é a permissão ligada; duas iguais não fazem sentido.
            models.UniqueConstraint(fields=['vinculo', 'capacidade'], name='accounts_concessao_unica'),
        ]


class SolicitacaoVinculo(models.Model):
    class Status(models.TextChoices):
        PENDENTE = 'PENDENTE', 'Pendente'
        ACEITA = 'ACEITA', 'Aceita'
        RECUSADA = 'RECUSADA', 'Recusada'
        CANCELADA = 'CANCELADA', 'Cancelada'

    solicitante = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='solicitacoes')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='solicitacoes')
    cargo = models.CharField('Cargo', max_length=100)
    setor = models.CharField('Setor', max_length=100)
    mensagem = models.TextField('Mensagem', blank=True, max_length=500)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDENTE)
    criada_em = models.DateTimeField(auto_now_add=True)
    respondida_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-criada_em']
        constraints = [
            # No máximo um pedido em análise por pessoa e empresa.
            models.UniqueConstraint(
                fields=['solicitante', 'company'], condition=Q(status='PENDENTE'),
                name='accounts_solicitacao_pendente_unica',
            ),
        ]


class TipoNotificacao(models.TextChoices):
    SOLICITACAO_RECEBIDA = 'SOLICITACAO_RECEBIDA', 'Solicitação recebida'
    SOLICITACAO_ACEITA = 'SOLICITACAO_ACEITA', 'Solicitação aceita'
    SOLICITACAO_RECUSADA = 'SOLICITACAO_RECUSADA', 'Solicitação recusada'
    VINCULO_REMOVIDO = 'VINCULO_REMOVIDO', 'Vínculo removido'
    MEMBRO_SAIU = 'MEMBRO_SAIU', 'Membro saiu'
    PERMISSOES_ALTERADAS = 'PERMISSOES_ALTERADAS', 'Permissões alteradas'
    EMPRESA_ENCERRADA = 'EMPRESA_ENCERRADA', 'Empresa encerrada'


class Notificacao(models.Model):
    destinatario = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='notificacoes')
    tipo = models.CharField(max_length=30, choices=TipoNotificacao.choices)
    texto = models.CharField(max_length=500)
    url = models.CharField(max_length=300, blank=True)
    criada_em = models.DateTimeField(auto_now_add=True)
    lida_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-criada_em']
        indexes = [models.Index(fields=['destinatario', 'lida_em'], name='accounts_notif_dest_lida')]
