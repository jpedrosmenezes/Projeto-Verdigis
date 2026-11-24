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


# Depoimentos ILUSTRATIVOS da landing page: pessoas e empresas fictícias, só para
# demonstração (a página avisa isso). Troque por avaliações reais quando houver.
DEPOIMENTOS_ILUSTRATIVOS = [
    {
        'nota': 5,
        'texto': 'A Verdigis organizou nossos indicadores ESG em um só lugar. '
                 'Ficou muito mais fácil mostrar o progresso para a diretoria.',
        'nome': 'Fernanda Regueira',
        'cargo': 'Orientadora · Cesar School',
    },
    {
        'nota': 4.5,
        'texto': 'O quadro de tarefas engajou a equipe nas metas ambientais. '
                 'Em poucas semanas, todo mundo sabia o que fazer.',
        'nome': 'Laura Pacífico',
        'cargo': 'Orientadora · Cesar School',
    },
    {
        'nota': 4,
        'texto': 'Encontramos parceiros com valores parecidos com os nossos pelo '
                 'painel de parcerias. Falta só mais filtros.',
        'nome': 'Léo Macedo',
        'cargo': 'Orientador · Cesar School',
    },
]


def flores_da_nota(nota):
    """Lista com o estado de cada uma das 5 flores: 'cheia', 'meia' ou 'vazia'.

    Ex.: 3.5 -> ['cheia', 'cheia', 'cheia', 'meia', 'vazia']
    """
    cheias = int(nota)
    meia = nota - cheias >= 0.5
    vazias = 5 - cheias - (1 if meia else 0)
    return ['cheia'] * cheias + (['meia'] if meia else []) + ['vazia'] * vazias


def index(request):
    secoes = SecaoConteudo.objects.filter(pagina=SecaoConteudo.PAGINA_INDEX)
    pilares = Pilar.objects.prefetch_related('praticas').all()

    depoimentos = [
        {
            **d,
            'flores': flores_da_nota(d['nota']),
            # "4.5" vira "4,5" e "5.0" vira "5"
            'nota_texto': f"{d['nota']:g}".replace('.', ','),
        }
        for d in DEPOIMENTOS_ILUSTRATIVOS
    ]

    context = {
        'secoes': secoes,
        'pilares': pilares,
        'depoimentos': depoimentos,
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