"""Cria o superusuário a partir de variáveis de ambiente (o Render gratuito não tem shell)."""
import os

from django.core.management.base import BaseCommand

from accounts.models import User


class Command(BaseCommand):
    help = 'Cria o superusuário de DJANGO_SUPERUSER_EMAIL/DJANGO_SUPERUSER_PASSWORD se ele ainda não existir.'

    def handle(self, *args, **opcoes):
        email = os.getenv('DJANGO_SUPERUSER_EMAIL', '').strip().lower()
        senha = os.getenv('DJANGO_SUPERUSER_PASSWORD', '')
        nome = os.getenv('DJANGO_SUPERUSER_NOME', 'Administrador Verdigis')
        if not email or not senha:
            self.stdout.write('DJANGO_SUPERUSER_EMAIL/PASSWORD não definidos. Nenhum superusuário criado.')
            return

        user = User.objects.filter(email__iexact=email).first()
        if user is None:
            User.objects.create_superuser(email=email, password=senha, nome=nome)
            self.stdout.write(self.style.SUCCESS(f'Superusuário {email} criado.'))
            return
        # A senha só é definida na criação; depois, quem manda é quem usa a conta.
        if not (user.is_superuser and user.is_staff):
            user.is_superuser = user.is_staff = True
            user.save(update_fields=['is_superuser', 'is_staff'])
        self.stdout.write(f'Superusuário {email} já existe.')
