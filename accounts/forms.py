import re

from django import forms
from django.contrib.auth.forms import AuthenticationForm, BaseUserCreationForm
from django.core.files.uploadedfile import UploadedFile

from .models import Company, PerfilConsultor, PerfilFuncionario, User
from .validators import validate_cnpj, validate_cpf

TAMANHO_MAX_AVATAR = 2 * 1024 * 1024

UFS = [
    'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MT', 'MS', 'MG', 'PA',
    'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO',
]


def _normalizar_cnpj(valor):
    return re.sub(r'[^0-9A-Za-z]', '', valor or '').upper()


def _so_digitos(valor):
    return re.sub(r'\D', '', valor or '')


def _limpar_telefone(valor, obrigatorio=False):
    telefone = _so_digitos(valor)
    if not telefone and not obrigatorio:
        return ''
    if len(telefone) not in (10, 11):
        raise forms.ValidationError('Telefone inválido. Informe DDD e número.')
    return telefone


def _validar_avatar(foto):
    if isinstance(foto, UploadedFile) and foto.size > TAMANHO_MAX_AVATAR:
        raise forms.ValidationError('A imagem deve ter no máximo 2 MB.')
    return foto


def _email_em_uso(email, exceto=None):
    qs = User.objects.filter(email__iexact=email)
    if exceto is not None:
        qs = qs.exclude(pk=exceto.pk)
    return qs.exists()


# ---------- Cadastro e login ----------

class SignupForm(BaseUserCreationForm):
    class Meta:
        model = User
        fields = ('nome', 'email')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['nome'].widget.attrs['placeholder'] = 'Seu nome completo'
        self.fields['email'].widget.attrs['placeholder'] = 'seuemail@exemplo.com'
        self.fields['password1'].widget.attrs['placeholder'] = 'Crie uma senha'
        self.fields['password2'].widget.attrs['placeholder'] = 'Repita a senha'

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if _email_em_uso(email):
            raise forms.ValidationError('Já existe uma conta cadastrada com este e-mail.')
        return email


class EmailAuthenticationForm(AuthenticationForm):
    error_messages = {
        'invalid_login': 'E-mail ou senha incorretos.',
        'inactive': 'Esta conta está desativada.',
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'E-mail'
        self.fields['username'].widget = forms.EmailInput(attrs={
            'placeholder': 'seuemail@exemplo.com', 'autocomplete': 'email', 'autofocus': True,
        })
        self.fields['password'].widget.attrs['placeholder'] = 'Digite sua senha'

    def clean_username(self):
        return (self.cleaned_data.get('username') or '').strip().lower()


class ConfirmarSenhaForm(forms.Form):
    """Confirmação por senha (excluir conta). Para o responsável, pede também o código da empresa."""
    password = forms.CharField(
        label='Confirme sua senha', strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'current-password', 'placeholder': 'Digite sua senha'}),
    )
    codigo = forms.CharField(label='Digite o código da empresa', required=False)

    def __init__(self, user, *args, company=None, **kwargs):
        self.user = user
        self.company = company
        super().__init__(*args, **kwargs)
        if company is None:
            del self.fields['codigo']
        else:
            self.fields['codigo'].required = True
            self.fields['codigo'].widget.attrs['placeholder'] = company.codigo_formatado
            self.fields['codigo'].help_text = 'Confirma que você sabe qual empresa está apagando.'

    def clean_password(self):
        password = self.cleaned_data['password']
        if not self.user.check_password(password):
            raise forms.ValidationError('Senha incorreta.')
        return password

    def clean_codigo(self):
        from .models import normalizar_codigo
        codigo = normalizar_codigo(self.cleaned_data.get('codigo'))
        if self.company is not None and codigo != self.company.codigo:
            raise forms.ValidationError('O código não confere com o da sua empresa.')
        return codigo


# ---------- Empresa ----------

class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = [
            'razao_social', 'nome_fantasia', 'cnpj', 'inscricao_estadual', 'inscricao_municipal', 'niche',
            'cep', 'logradouro', 'numero', 'complemento', 'bairro', 'cidade', 'uf',
            'email_corporativo', 'telefone_fixo', 'celular_whatsapp',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        placeholders = {
            'razao_social': 'Razão Social da empresa',
            'nome_fantasia': 'Nome Fantasia',
            'cnpj': '00.000.000/0000-00',
            'inscricao_estadual': 'Inscrição Estadual (opcional)',
            'inscricao_municipal': 'Inscrição Municipal (opcional)',
            'cep': '00000-000',
            'logradouro': 'Rua, avenida, travessa...',
            'numero': 'Número',
            'complemento': 'Sala, bloco, andar (opcional)',
            'bairro': 'Bairro',
            'cidade': 'Cidade',
            'uf': 'UF',
            'email_corporativo': 'contato@empresa.com.br',
            'telefone_fixo': '(00) 3333-4444',
            'celular_whatsapp': '(00) 99999-8888',
        }
        for nome, texto in placeholders.items():
            if nome in self.fields:
                self.fields[nome].widget.attrs['placeholder'] = texto
        if 'niche' in self.fields:
            self.fields['niche'].empty_label = 'Selecione o nicho'
        mascaras = {'cnpj': 'cnpj', 'cep': 'cep', 'telefone_fixo': 'telefone', 'celular_whatsapp': 'telefone'}
        for nome, mascara in mascaras.items():
            if nome in self.fields:
                self.fields[nome].widget.attrs['data-mask'] = mascara
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')

    def clean_cnpj(self):
        cnpj = _normalizar_cnpj(self.cleaned_data.get('cnpj'))
        validate_cnpj(cnpj)
        if Company.objects.filter(cnpj=cnpj).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('Já existe uma empresa cadastrada com este CNPJ.')
        return cnpj

    def clean_cep(self):
        cep = _so_digitos(self.cleaned_data['cep'])
        if len(cep) != 8:
            raise forms.ValidationError('CEP deve ter 8 dígitos.')
        return cep

    def clean_uf(self):
        uf = self.cleaned_data['uf'].strip().upper()
        if uf not in UFS:
            raise forms.ValidationError('UF inválida.')
        return uf

    def is_valid(self):
        valid = super().is_valid()
        for nome in self.errors:
            if nome in self.fields:
                attrs = self.fields[nome].widget.attrs
                if 'is-invalid' not in attrs.get('class', ''):
                    attrs['class'] = attrs.get('class', '') + ' is-invalid'
        return valid


class EditCompanyForm(CompanyForm):
    """Dados da empresa na edição de perfil. O CNPJ não muda depois do cadastro."""

    class Meta(CompanyForm.Meta):
        fields = [f for f in CompanyForm.Meta.fields if f != 'cnpj']


# ---------- Triagem: funcionário e consultor ----------

class _DadosPessoaisMixin(forms.Form):
    nome = forms.CharField(label='Nome completo', max_length=150)
    telefone = forms.CharField(label='Telefone', max_length=20)

    def _preparar_pessoais(self, user):
        self.fields['nome'].initial = user.nome
        self.fields['nome'].widget.attrs['placeholder'] = 'Seu nome completo'
        self.fields['telefone'].initial = user.telefone
        self.fields['telefone'].widget.attrs.update({'data-mask': 'telefone', 'placeholder': '(81) 99999-8888'})

    def clean_telefone(self):
        return _limpar_telefone(self.cleaned_data.get('telefone'), obrigatorio=True)


class FuncionarioOnboardingForm(_DadosPessoaisMixin, forms.ModelForm):
    # Declarado aqui porque o valor chega com máscara (14 caracteres) e é limpo depois.
    cpf = forms.CharField(label='CPF', max_length=14)

    class Meta:
        model = PerfilFuncionario
        fields = ['cpf']

    field_order = ['nome', 'cpf', 'telefone']

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self._preparar_pessoais(user)
        self.fields['cpf'].widget.attrs.update({'data-mask': 'cpf', 'placeholder': '000.000.000-00'})

    def clean_cpf(self):
        cpf = _so_digitos(self.cleaned_data.get('cpf'))
        validate_cpf(cpf)
        if PerfilFuncionario.objects.filter(cpf=cpf).exists():
            raise forms.ValidationError('Já existe uma conta cadastrada com este CPF.')
        return cpf


class ConsultorOnboardingForm(_DadosPessoaisMixin, forms.ModelForm):
    documento = forms.CharField(label='Número do documento', max_length=18)

    class Meta:
        model = PerfilConsultor
        fields = ['documento_tipo', 'documento', 'especialidade', 'link_profissional']

    field_order = ['nome', 'documento_tipo', 'documento', 'telefone', 'especialidade', 'link_profissional']

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self._preparar_pessoais(user)
        self.fields['documento'].widget.attrs.update({'data-mask': 'cpf-cnpj', 'placeholder': 'CPF ou CNPJ'})
        self.fields['especialidade'].widget.attrs['placeholder'] = 'Ex.: gestão ambiental, segurança do trabalho'
        self.fields['link_profissional'].widget.attrs['placeholder'] = 'https://www.linkedin.com/in/... (opcional)'

    def clean(self):
        cleaned = super().clean()
        tipo = cleaned.get('documento_tipo')
        bruto = self.data.get(self.add_prefix('documento'), '')
        if not tipo or 'documento' in self.errors:
            return cleaned
        if tipo == PerfilConsultor.TipoDocumento.CPF:
            documento = _so_digitos(bruto)
            validador = validate_cpf
        else:
            documento = _normalizar_cnpj(bruto)
            validador = validate_cnpj
        try:
            validador(documento)
        except forms.ValidationError as erro:
            self.add_error('documento', erro)
            return cleaned
        if PerfilConsultor.objects.filter(documento=documento).exists():
            self.add_error('documento', 'Já existe uma conta de consultor com este documento.')
            return cleaned
        cleaned['documento'] = documento
        self.instance.documento = documento
        return cleaned


# ---------- Vínculos ----------

class EntrarEmpresaForm(forms.Form):
    codigo = forms.CharField(
        label='Código da empresa', max_length=20,
        widget=forms.TextInput(attrs={'placeholder': 'XXXXX-XXXXX', 'autocomplete': 'off'}),
    )
    cargo = forms.CharField(label='Cargo', max_length=100, widget=forms.TextInput(attrs={'placeholder': 'Ex.: Farmacêutico'}))
    setor = forms.CharField(label='Setor', max_length=100, widget=forms.TextInput(attrs={'placeholder': 'Ex.: Atendimento'}))
    mensagem = forms.CharField(
        label='Mensagem (opcional)', max_length=500, required=False,
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Conte quem você é para a empresa'}),
    )


# ---------- Perfil ----------

class EditProfileForm(forms.ModelForm):
    senha_atual = forms.CharField(
        label='Senha atual', required=False, strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'current-password', 'placeholder': 'Só se for trocar o e-mail'}),
        help_text='Obrigatória apenas para trocar o e-mail.',
    )
    telefone = forms.CharField(
        label='Telefone', max_length=20, required=False,
        widget=forms.TextInput(attrs={'placeholder': '(81) 99999-8888', 'data-mask': 'telefone'}),
    )

    class Meta:
        model = User
        fields = ['nome', 'email', 'telefone', 'foto_perfil', 'bio']
        widgets = {
            'nome': forms.TextInput(attrs={'placeholder': 'Digite seu nome'}),
            'email': forms.EmailInput(attrs={'placeholder': 'seuemail@exemplo.com'}),
            'foto_perfil': forms.FileInput(attrs={'accept': 'image/*'}),
            'bio': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Fale um pouco sobre você'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.email_original = self.instance.email

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if _email_em_uso(email, exceto=self.instance):
            raise forms.ValidationError('Já existe uma conta com este e-mail.')
        return email

    def clean_telefone(self):
        return _limpar_telefone(self.cleaned_data.get('telefone'))

    def clean_foto_perfil(self):
        return _validar_avatar(self.cleaned_data.get('foto_perfil'))

    def clean(self):
        cleaned = super().clean()
        email = cleaned.get('email')
        if email and email != self.email_original:
            senha = cleaned.get('senha_atual') or ''
            if not self.instance.check_password(senha):
                self.add_error('senha_atual', 'Informe sua senha atual para trocar o e-mail.')
        return cleaned


class EditConsultorForm(forms.ModelForm):
    class Meta:
        model = PerfilConsultor
        fields = ['especialidade', 'link_profissional']
