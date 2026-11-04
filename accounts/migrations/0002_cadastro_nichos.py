from django.db import migrations

# Nichos do ramo farmacêutico exibidos no cadastro da empresa.
NICHOS_PADRAO = [
    ('Farmácia e drogaria', 'Comércio de medicamentos e produtos de saúde ao consumidor.'),
    ('Farmácia de manipulação', 'Preparo de fórmulas magistrais e oficinais sob prescrição.'),
    ('Distribuidora de medicamentos', 'Armazenagem, distribuição e transporte de medicamentos e insumos.'),
    ('Indústria farmacêutica', 'Fabricação de medicamentos, fitoterápicos ou produtos para saúde.'),
    ('Insumos farmacêuticos', 'Fabricação, importação ou fracionamento de insumos e princípios ativos.'),
    ('Laboratório de análises', 'Análises clínicas, controle de qualidade ou ensaios para o setor.'),
]


def popular_nichos(apps, schema_editor):
    Niche = apps.get_model('accounts', 'Niche')
    for nome, descricao in NICHOS_PADRAO:
        Niche.objects.update_or_create(nome=nome, defaults={'descricao': descricao})


def remover_nichos(apps, schema_editor):
    Niche = apps.get_model('accounts', 'Niche')
    Niche.objects.filter(nome__in=[nome for nome, _ in NICHOS_PADRAO]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(popular_nichos, reverse_code=remover_nichos),
    ]
