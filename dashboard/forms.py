from django import forms
from accounts.models import Funcionario
from .models import Meta
from .models import RelatoSocialVerdigis
#fabrica de metas!!
class FormsMetas(forms.ModelForm):
    class Meta:
        model =  Meta
        fields = ['nome', 'pilar_esg', 'deadline', 'resumo', 'prioridade', 'tipo', 'funcionario'] #será preenchido!!
        
        # 'widgets' definem o tipo de elemento HTML de cada campo
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Reduzir uso de papel'}),
            'pilar_esg': forms.Select(attrs={'class': 'form-select'}),
            'deadline': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'resumo': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'Descrição da meta...'}),
            'prioridade': forms.Select(attrs={'class': 'form-select'}),
            'tipo': forms.Select(attrs={'class': 'form-select', 'id': 'id_tipo'}),
            'funcionario': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        if company:
            self.fields['funcionario'].queryset = Funcionario.objects.filter(company=company)
        self.fields['funcionario'].empty_label = "Selecione o funcionário..."
        self.fields['funcionario'].required = False

    def clean(self):
        cleaned_data = super().clean()
        tipo = cleaned_data.get('tipo')
        funcionario = cleaned_data.get('funcionario')

        #so mostra a opacao de funcnioanrio se for meta individual
        if tipo == 'INDIVIDUAL' and not funcionario:
            self.add_error('funcionario', 'Selecione o funcionário responsável para a meta individual.')
        
        # marca funcionario em branco se for meta geral
        if tipo == 'GERAL':
            cleaned_data['funcionario'] = None

        return cleaned_data

class RelatoSocialForm(forms.ModelForm):
    class Meta:
        model = RelatoSocialVerdigis
        fields = ['tema_esg', 'sentimento', 'mensagem', 'eh_anonimo']
        labels = {
            'tema_esg': 'Tema',
            'sentimento': 'Tipo de avaliação',
            'mensagem': 'Sua mensagem',
            'eh_anonimo': 'Enviar como anônimo',
        }
        widgets = {
            'tema_esg': forms.Select(attrs={'class': 'form-control'}),
            'sentimento': forms.Select(attrs={'class': 'form-control'}),
            'mensagem': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
        }
    def __init__(self, *args, user=None, company=None, **kwargs):
        self.user = user
        self.company = company
        super().__init__(*args, **kwargs)
        self.fields['tema_esg'].choices = [('', 'Selecione o tema')] + list(self.fields['tema_esg'].choices)[1:]
        self.fields['sentimento'].choices = [('', 'Selecione o tipo')] + list(self.fields['sentimento'].choices)[1:]

    def save(self, commit=True):
        relato = super().save(commit=False)
        autenticado = self.user is not None and self.user.is_authenticated
        relato.usuario = self.user if (autenticado and not relato.eh_anonimo) else None
        relato.company = self.company
        if commit:
            relato.save()
        return relato