from django.db import migrations

# Lista de nichos
NICHOS_PADRAO = [
    {
        "nome": "Drogaria Tradicional ",
        "description": "Venda direta de medicamentos alopáticos, perfumaria, higiene e cosméticos.",
    },
    {
        "nome": "Farmácia de Manipulação",
        "description": "Produção de fórmulas personalizadas sob medida para cada paciente.",
    },
    {
        "nome": "Farmácia Popular",
        "description": "Foco em medicamentos genéricos, itens de alto giro e preços reduzidos.",
    },
    {
        "nome": "Drogaria E-commerce",
        "description": "Operação focada em vendas online, atendimento via WhatsApp e entregas rápidas.",
    },
    {
        "nome": "Farmácia Natural",
        "description": "Medicamentos homeopáticos, fitoterápicos, florais e tratamentos naturais.",
    },
]

#essas duas def servem pra armazenar com segurança os nichos no banco
def popular_nichos(apps, schema_editor):
    Niche = apps.get_model('accounts', 'Niche')
    for dados in NICHOS_PADRAO:
        Niche.objects.get_or_create(
            nome=dados["nome"],
            defaults={"description": dados["description"]}
        )


def remover_nichos(apps, schema_editor):
    Niche = apps.get_model('accounts', 'Niche')
    nomes = [dados["nome"] for dados in NICHOS_PADRAO]
    Niche.objects.filter(nome__in=nomes).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0006_rename_name_niche_nome_and_more'),
    ]


    operations = [
        migrations.RunPython(popular_nichos, reverse_code=remover_nichos),
    ]
