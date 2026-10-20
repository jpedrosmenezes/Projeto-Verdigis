import re
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.core.files.uploadedfile import UploadedFile

from accounts.models import Company, Funcionario, UserProfile
from accounts.validators import validate_cnpj, validate_cpf

User = get_user_model()

TAMANHO_MAX_AVATAR = 2 * 1024 * 1024

CODIGO_CREDENCIAL_EMPRESA = 'credencial_empresa'


def _normalizar_cnpj(valor):
    return re.sub(r'[^0-9A-Za-z]', '', valor or '').upper()


class SignupForm(UserCreationForm):
    email = forms.EmailField(label='E-mail')
    # Novos campos adicionados ao cadastro do usuário:
    # CNPJ, número de telefone e identificação de funcionário.
    cnpj = forms.CharField(label='CNPJ', max_length=18, required=False)
    telefone = forms.CharField(label='Número de Telefone', max_length=20, required=True)
    funcionario = forms.BooleanField(label='Sou funcionário da empresa', required=False)
    
    class Meta(UserCreationForm.Meta):
        model = User
        # Inclusão dos novos campos no formulário de cadastro.
        fields = ('username', 'email', 'cnpj', 'telefone', 'funcionario')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs['placeholder'] = 'Digite seu nome de usuário'
        self.fields['email'].widget.attrs['placeholder'] = 'seuemail@exemplo.com'
        self.fields['cnpj'].widget.attrs['data-mask'] = 'cnpj'
        self.fields['cnpj'].widget.attrs['placeholder'] = '00.000.000/0000-00'
        self.fields['telefone'].widget.attrs['data-mask'] = 'telefone'
        self.fields['telefone'].widget.attrs['placeholder'] = '(81) 99999-8888'
        self.fields['password1'].widget.attrs['placeholder'] = 'Crie uma senha'
        self.fields['password2'].widget.attrs['placeholder'] = 'Repita a senha'

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Já existe uma conta cadastrada com este e-mail.')
        return email

    def clean_cnpj(self):
        cnpj = _normalizar_cnpj(self.cleaned_data.get('cnpj'))
        if cnpj:
            validate_cnpj(cnpj)
        return cnpj

    def clean_telefone(self):
        telefone = re.sub(r'\D', '', self.cleaned_data['telefone'])
        if len(telefone) not in (10, 11):
            raise forms.ValidationError('Telefone inválido. Informe DDD e número.')
        return telefone

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            UserProfile.objects.update_or_create(
                user=user,
                defaults={
                    'cpf': self.cleaned_data.get('cpf', ''),
                    'telefone': self.cleaned_data['telefone'],
                    'cnpj': self.cleaned_data.get('cnpj', ''),
                    'email': user.email,
                },
            )
        return user


class LoginForm(AuthenticationForm):
    error_messages = {
        'invalid_login': 'Usuário ou senha incorretos.',
        'inactive': 'Esta conta está desativada.',
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs['placeholder'] = 'Digite seu nome de usuário'
        self.fields['password'].widget.attrs['placeholder'] = 'Digite sua senha'


class DeleteAccountForm(forms.Form):
    password = forms.CharField(
        label='Senha',
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'current-password'}),
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        self.fields['password'].widget.attrs['placeholder'] = 'Digite sua senha'

    def clean_password(self):
        password = self.cleaned_data['password']
        if not self.user.check_password(password):
            raise forms.ValidationError('Senha incorreta.')
        return password


class ProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['nome', 'cnpj', 'email', 'foto_perfil']
        labels = {
            'nome': 'Nome',
            'cnpj': 'CNPJ',
            'email': 'E-mail',
            'foto_perfil': 'Foto de Perfil',
        }
        widgets = {
            'nome': forms.TextInput(attrs={'placeholder': 'Digite seu nome'}),
            'cnpj': forms.TextInput(attrs={'placeholder': 'Digite seu CNPJ'}),
            'email': forms.EmailInput(attrs={'placeholder': 'Digite seu e-mail'}),
            'foto_perfil': forms.FileInput(attrs={'accept': 'image/*'}),
        }

    def clean_cnpj(self):
        cnpj = _normalizar_cnpj(self.cleaned_data.get('cnpj'))
        if cnpj:
            validate_cnpj(cnpj)
        return cnpj

    def clean_foto_perfil(self):
        foto = self.cleaned_data.get('foto_perfil')
        if isinstance(foto, UploadedFile) and foto.size > TAMANHO_MAX_AVATAR:
            raise forms.ValidationError('A imagem deve ter no máximo 2 MB.')
        return foto


class CompanyForm(forms.ModelForm):
    senha_funcionarios = forms.CharField(
        label='Senha de acesso dos funcionários',
        min_length=8,
        strip=False,
        widget=forms.PasswordInput(render_value=False),
        help_text='Mínimo de 8 caracteres. Seus funcionários usam essa senha para cadastrar e entrar.',
    )

    class Meta:
        model = Company
        exclude = ('responsavel', 'created_at')

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
            'senha_funcionarios': 'Senha para seus funcionários acessarem',
        }

        #Adicionada checagem de chave nome para evitar KeyError
        for nome, text in placeholders.items():
            if nome in self.fields:
                self.fields[nome].widget.attrs['placeholder'] = text

        #Removido o loop duplicado de placeholders e mantida apenas a definição do empty_label do nicho
        if 'niche' in self.fields:
            self.fields['niche'].empty_label = 'Selecione o nicho'

        mascaras = {
            'cnpj': 'cnpj',
            'cep': 'cep',
            'telefone_fixo': 'telefone',
            'celular_whatsapp': 'telefone',
        }
        for name, mask in mascaras.items():
            if name in self.fields:
                self.fields[name].widget.attrs['data-mask'] = mask

        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')

    def clean_cnpj(self):
        # normaliza antes da checagem de unicidade (ignora máscara)
        return _normalizar_cnpj(self.cleaned_data['cnpj'])

    def clean_cep(self):
        cep = re.sub(r'\D', '', self.cleaned_data['cep'])
        if len(cep) != 8:
            raise forms.ValidationError('CEP deve ter 8 dígitos.')
        return cep

    def clean_uf(self):
        return self.cleaned_data['uf'].strip().upper()

    #Método save() adicionado. O formulário lia a senha digitada no campo 'senha_funcionarios',
    # mas não a gravava no objeto Company. Agora chama o set_senha_acesso(senha) para criptografar e salvar no banco.
    def save(self, commit=True):
        company = super().save(commit=False)
        senha_raw = self.cleaned_data.get('senha_funcionarios')
        if senha_raw:
            company.set_senha_acesso(senha_raw)
        if commit:
            company.save()
        return company

    def is_valid(self):
        valid = super().is_valid()
        for nome in self.errors:
            if nome in self.fields:
                attrs = self.fields[nome].widget.attrs
                if 'is-invalid' not in attrs.get('class', ''):
                    attrs['class'] = attrs.get('class', '') + ' is-invalid'
        return valid


class EmployeeSignupForm(SignupForm):
    #Adicionado required=True explícito para garantir preenchimento
    # O CPF não é pedido no cadastro de empresa, só no de funcionário.
    cpf = forms.CharField(label='CPF', max_length=14, required=True)
    cnpj = forms.CharField(label='CNPJ da empresa', required=True)
    senha_empresa = forms.CharField(
        label='Senha da empresa', strip=False, widget=forms.PasswordInput(), required=True
    )
    class Meta(SignupForm.Meta):
        fields = ('username', 'email', 'cpf', 'cnpj', 'telefone', 'funcionario')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.company = None
        self.fields['cpf'].widget.attrs['data-mask'] = 'cpf'
        self.fields['cpf'].widget.attrs['placeholder'] = '000.000.000-00'
        self.fields['cnpj'].widget.attrs['data-mask'] = 'cnpj'
        self.fields['cnpj'].widget.attrs['placeholder'] = '00.000.000/0000-00'
        self.fields['senha_empresa'].widget.attrs['placeholder'] = 'Senha fornecida pela empresa'

    def clean_cpf(self):
        cpf = re.sub(r'\D', '', self.cleaned_data['cpf'])
        validate_cpf(cpf)
        if UserProfile.objects.filter(cpf=cpf).exists():
            raise forms.ValidationError('Já existe uma conta cadastrada com este CPF.')
        return cpf
   
    def clean_cnpj(self):
        return _normalizar_cnpj(self.cleaned_data.get('cnpj'))

    def clean(self):
        cleaned = super().clean()
        cnpj = cleaned.get('cnpj')
        senha = cleaned.get('senha_empresa')
        if cnpj and senha:
            company = Company.objects.filter(cnpj=cnpj).first()
            if not company or not company.check_senha_acesso(senha):
                raise forms.ValidationError(
                    'CNPJ ou senha da empresa inválidos.', code=CODIGO_CREDENCIAL_EMPRESA
                )
            self.company = company
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=commit)
        # 1. Trocado 'tipo': 'funcionario' por 'tipo': 'FUNCIONARIO' para bater com o TIPO_CHOICES do UserProfile.
        # 2. Adicionada a trava `and self.company` e uso do `get_or_create` para evitar duplicidades na tabela Funcionario.
        if commit and self.company:
            Funcionario.objects.get_or_create(user=user, company=self.company)
            UserProfile.objects.update_or_create(
                user=user,
                defaults={
                    'tipo': 'FUNCIONARIO',
                    'nome_empresa': self.company.nome_fantasia,
                    'email': user.email,
                    'cnpj': '',
                },
            )
        return user


class EmployeeLoginForm(LoginForm):
    cnpj = forms.CharField(label='CNPJ da empresa')
    senha_empresa = forms.CharField(
        label='Senha da empresa', strip=False, widget=forms.PasswordInput()
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['cnpj'].widget.attrs['data-mask'] = 'cnpj'
        self.fields['cnpj'].widget.attrs['placeholder'] = '00.000.000/0000-00'
        self.fields['senha_empresa'].widget.attrs['placeholder'] = 'Senha fornecida pela empresa'

    def clean(self):
        cleaned = super().clean()  # autentica usuário e senha pessoal
        cnpj = _normalizar_cnpj(cleaned.get('cnpj'))
        senha = cleaned.get('senha_empresa')
        if self.user_cache is not None and cnpj and senha:
            vinculo = (
                Funcionario.objects.select_related('company')
                .filter(user=self.user_cache)
                .first()
            )
            if (
                vinculo is None
                or vinculo.company.cnpj != cnpj
                or not vinculo.company.check_senha_acesso(senha)
            ):
                raise forms.ValidationError(
                    'Dados de acesso da empresa inválidos.', code=CODIGO_CREDENCIAL_EMPRESA
                )
        return cleaned

class EditProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['nome', 'foto_perfil']
        labels = {
            'nome': 'Nome',
            'foto_perfil': 'Foto de Perfil',
        }
        widgets = {
            'nome': forms.TextInput(attrs={'placeholder': 'Digite seu nome'}),
            'foto_perfil': forms.FileInput(attrs={'accept': 'image/*'}),
        }

    def clean_profile_picture(self):
        foto = self.cleaned_data.get('foto_perfil')
        if isinstance(foto, UploadedFile) and foto.size > TAMANHO_MAX_AVATAR:
            raise forms.ValidationError('A imagem deve ter no máximo 2 MB.')
        return foto