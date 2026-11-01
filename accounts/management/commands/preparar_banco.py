"""Remove o esquema antigo de contas antes do migrate, preservando o conteúdo do site (forum).

O modelo de usuário passou a ser accounts.User (login por e-mail). Um banco criado com o
esquema anterior (auth.User + UserProfile) não pode ser migrado: as tabelas de contas, metas,
relatos, sessões e admin precisam ser recriadas. As tabelas do forum ficam intactas.

Por segurança, só apaga com RESETAR_CONTAS_LEGADO=sim no ambiente. Sem a variável, falha
e o deploy é interrompido (no Render, a versão anterior continua no ar).
"""
import os

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

# Tabelas que só existem no esquema antigo.
MARCADORES_LEGADO = {'accounts_userprofile', 'accounts_funcionario', 'dashboard_empresa', 'dashboard_avaliacaoesg'}
APPS_RECRIADOS = ('accounts', 'dashboard', 'auth', 'admin', 'sessions')
PREFIXOS_APAGADOS = ('accounts_', 'dashboard_', 'auth_')
TABELAS_APAGADAS = {'django_admin_log', 'django_session'}


class Command(BaseCommand):
    help = 'Detecta o esquema antigo de contas e o remove (com RESETAR_CONTAS_LEGADO=sim).'

    def handle(self, *args, **opcoes):
        tabelas = set(connection.introspection.table_names())
        if not tabelas & MARCADORES_LEGADO:
            self.stdout.write('Banco já está no esquema atual. Nada a fazer.')
            return

        if os.getenv('RESETAR_CONTAS_LEGADO', '').lower() != 'sim':
            raise CommandError(
                'O banco ainda usa o esquema antigo de contas. Para recriar contas, metas e relatos '
                '(o conteúdo do site é preservado), defina RESETAR_CONTAS_LEGADO=sim e rode de novo. '
                'Depois do deploy, remova a variável.'
            )

        apagar = sorted(t for t in tabelas if t.startswith(PREFIXOS_APAGADOS) or t in TABELAS_APAGADAS)
        sufixo = ' CASCADE' if connection.vendor == 'postgresql' else ''
        with transaction.atomic(), connection.cursor() as cursor:
            if connection.vendor == 'sqlite':
                cursor.execute('PRAGMA foreign_keys = OFF')
            for tabela in apagar:
                cursor.execute(f'DROP TABLE IF EXISTS {connection.ops.quote_name(tabela)}{sufixo}')
            marcadores = ', '.join(['%s'] * len(APPS_RECRIADOS))
            cursor.execute(f'DELETE FROM django_migrations WHERE app IN ({marcadores})', APPS_RECRIADOS)
            cursor.execute(f'DELETE FROM django_content_type WHERE app_label IN ({marcadores})', APPS_RECRIADOS)
        self.stdout.write(self.style.WARNING(
            f'Esquema antigo removido ({len(apagar)} tabelas). O migrate a seguir recria tudo.'
        ))
