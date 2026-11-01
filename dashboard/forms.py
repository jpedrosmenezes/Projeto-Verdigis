from django import forms

from accounts.models import TipoVinculo, Vinculo

from .models import Meta, RelatoSocialVerdigis

WIDGETS_META = {
    'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Reduzir uso de papel'}),
    'pilar_esg': forms.Select(attrs={'class': 'form-select'}),
    'deadline': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}, format='%Y-%m-%d'),
    'resumo': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'Descrição da meta...'}),
    'prioridade': forms.Select(attrs={'class': 'form-select'}),
    'tipo': forms.Select(attrs={'class': 'form-select', 'id': 'id_tipo'}),
    'funcionario': forms.Select(attrs={'class': 'form-select'}),
}


class FuncionarioChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, vinculo):
        return f'{vinculo.user.nome} ({vinculo.cargo})'


def funcionarios_da_empresa(company):
    """Só funcionários com vínculo ativo na empresa da requisição."""
    return (
        Vinculo.objects.filter(company=company, tipo=TipoVinculo.FUNCIONARIO)
        .select_related('user').order_by('user__nome')
    )


class FormsMetas(forms.ModelForm):
    """Formulário completo (Empresa e consultor): escolhe tipo e responsável."""

    class Meta:
        model = Meta
        fields = ['nome', 'pilar_esg', 'deadline', 'resumo', 'prioridade', 'tipo', 'funcionario']
        field_classes = {'funcionario': FuncionarioChoiceField}
        widgets = WIDGETS_META
        labels = {'nome': 'Nome', 'deadline': 'Prazo', 'resumo': 'Resumo', 'funcionario': 'Funcionário responsável'}

    def __init__(self, *args, company, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['funcionario'].queryset = funcionarios_da_empresa(company)
        self.fields['funcionario'].empty_label = 'Selecione o funcionário...'
        self.fields['funcionario'].required = False

    def clean(self):
        cleaned_data = super().clean()
        tipo = cleaned_data.get('tipo')
        if tipo == 'INDIVIDUAL' and not cleaned_data.get('funcionario'):
            self.add_error('funcionario', 'Selecione o funcionário responsável para a meta individual.')
        if tipo == 'GERAL':
            cleaned_data['funcionario'] = None
        return cleaned_data


class FormMetaFuncionario(forms.ModelForm):
    """Funcionário só cria meta individual para si: tipo e responsável vêm do servidor."""

    class Meta:
        model = Meta
        fields = ['nome', 'pilar_esg', 'deadline', 'resumo', 'prioridade']
        widgets = WIDGETS_META
        labels = {'nome': 'Nome', 'deadline': 'Prazo', 'resumo': 'Resumo'}


class RelatoSocialForm(forms.ModelForm):
    class Meta:
        model = RelatoSocialVerdigis
        fields = ['tema_esg', 'sentimento', 'mensagem', 'eh_anonimo']
        labels = {
            'tema_esg': 'Tema',
            'sentimento': 'Tipo de avaliação',
            'mensagem': 'Sua mensagem',
            'eh_anonimo': 'Anônimo: ninguém verá seu nome. Não anônimo: a empresa e os consultores verão seu nome.',
        }
        widgets = {
            'tema_esg': forms.Select(attrs={'class': 'form-control'}),
            'sentimento': forms.Select(attrs={'class': 'form-control'}),
            'mensagem': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tema_esg'].choices = [('', 'Selecione o tema')] + list(self.fields['tema_esg'].choices)[1:]
        self.fields['sentimento'].choices = [('', 'Selecione o tipo')] + list(self.fields['sentimento'].choices)[1:]


class OcultarRelatoForm(forms.Form):
    motivo = forms.CharField(
        label='Motivo (opcional)', max_length=300, required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Ex.: conteúdo ofensivo'}),
    )
