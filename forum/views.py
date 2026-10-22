from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from .forms import ContatoForm
from .models import (
    SecaoConteudo,
    MembroEquipe,
    Pilar,
    ItemLista,
    Tecnologia,
    PraticaFarmacia,
    Contato
)


def index(request):
    secoes = SecaoConteudo.objects.filter(pagina=SecaoConteudo.PAGINA_INDEX)
    pilares = Pilar.objects.prefetch_related('praticas').all()

    context = {
        'secoes': secoes,
        'pilares': pilares,
    }
    return render(request, 'forum/index.html', context)


def sobre(request):
    secoes = SecaoConteudo.objects.filter(pagina=SecaoConteudo.PAGINA_SOBRE)
    objetivos = ItemLista.objects.filter(categoria=ItemLista.CATEGORIA_OBJETIVO)
    praticas_fds = ItemLista.objects.filter(categoria=ItemLista.CATEGORIA_PRATICA_FDS)
    beneficios = ItemLista.objects.filter(categoria=ItemLista.CATEGORIA_BENEFICIO)
    
    tecnologias = Tecnologia.objects.all()
    pilares = Pilar.objects.prefetch_related('praticas').all()

    context = {
        'secoes': secoes,
        'objetivos': objetivos,
        'praticas_fds': praticas_fds,
        'beneficios': beneficios,
        'tecnologias': tecnologias,
        'pilares': pilares,
    }
    return render(request, 'forum/sobre.html', context)


def fale_conosco(request):
    form = ContatoForm(request.POST if request.method == 'POST' else None)

    if request.method == 'POST':
        if form.is_valid():
            contato = form.save(commit=False)
            contato.data_envio = timezone.now()
            contato.save()
            messages.success(request, 'Sua mensagem foi enviada com sucesso! Entraremos em contato em breve.')
            return redirect('fale_conosco')
        messages.error(request, 'Por favor, preencha todos os campos obrigatórios.')

    context = {
        'assunto_choices': Contato.ASSUNTO_CHOICES,
        'form': form,
    }
    return render(request, 'forum/fale_conosco.html', context)