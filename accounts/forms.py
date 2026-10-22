import re

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from accounts.models import UserProfile

User = get_user_model()


def _normalizar_cnpj(valor):
    return re.sub(r'[^0-9A-Za-z]', '', valor or '').upper()


class SignupForm(UserCreationForm):
    email = forms.EmailField(label='E-mail')
    # Novos campos adicionados ao cadastro do usuário:
    # CPF, CNPJ, número de telefone e identificação de funcionário.
    cpf = forms.CharField(label='CPF', max_length=14, required=True)
    cnpj = forms.CharField(label='CNPJ', max_length=18, required=False)
    telefone = forms.CharField(label='Número de Telefone', max_length=20, required=True)
    funcionario = forms.BooleanField(label='Sou funcionário da empresa', required=False)
    
    class Meta(UserCreationForm.Meta):
        model = User
        # Inclusão dos novos campos no formulário de cadastro.
        fields = ('username', 'email', 'cpf', 'cnpj', 'telefone', 'funcionario')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs['placeholder'] = 'Digite seu nome de usuário'
        self.fields['email'].widget.attrs['placeholder'] = 'seuemail@exemplo.com'
        self.fields['password1'].widget.attrs['placeholder'] = 'Crie uma senha'
        self.fields['password2'].widget.attrs['placeholder'] = 'Repita a senha'

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Já existe uma conta cadastrada com este e-mail.')
        return email
    


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
        fields = ['name', 'cnpj', 'email', 'profile_picture']
        labels = {
            'name': 'Nome',
            'cnpj': 'CNPJ',
            'email': 'E-mail',
            'profile_picture': 'Foto de Perfil',
        }
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Digite seu nome'}),
            'cnpj': forms.TextInput(attrs={'placeholder': 'Digite seu CNPJ'}),
            'email': forms.EmailInput(attrs={'placeholder': 'Digite seu e-mail'}),
            'profile_picture': forms.FileInput(attrs={'accept': 'image/*'}),
        }


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
            'cep': '00000-000',
            'email_corporativo': 'contato@empresa.com.br',
            'telefone_fixo': '(81) 3333-4444',
            'celular_whatsapp': '(81) 99999-8888',
        }
        for name, text in placeholders.items():
            self.fields[name].widget.attrs['placeholder'] = text
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

    def is_valid(self):
        valid = super().is_valid()
        for name in self.errors:
            if name in self.fields:
                attrs = self.fields[name].widget.attrs
                if 'is-invalid' not in attrs.get('class', ''):
                    attrs['class'] = attrs.get('class', '') + ' is-invalid'
        return valid


class EmployeeSignupForm(SignupForm):
    cnpj = forms.CharField(label='CNPJ da empresa')
    senha_empresa = forms.CharField(
        label='Senha da empresa', strip=False, widget=forms.PasswordInput()
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.company = None
        self.fields['cnpj'].widget.attrs['placeholder'] = '00.000.000/0000-00'
        self.fields['senha_empresa'].widget.attrs['placeholder'] = 'Senha fornecida pela empresa'

    def clean(self):
        cleaned = super().clean()
        cnpj = _normalizar_cnpj(cleaned.get('cnpj'))
        senha = cleaned.get('senha_empresa')
        if cnpj and senha:
            company = Company.objects.filter(cnpj=cnpj).first()
            if not company or not company.check_senha_acesso(senha):
                raise forms.ValidationError('CNPJ ou senha da empresa inválidos.')
            self.company = company
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=True)
        Funcionario.objects.create(user=user, company=self.company)
        UserProfile.objects.update_or_create(
            user=user,
            defaults={
                'tipo': 'funcionario',
                'nome_empresa': self.company.nome_fantasia,
                'email': user.email,
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
                raise forms.ValidationError('Dados de acesso da empresa inválidos.')
        return cleaned
    