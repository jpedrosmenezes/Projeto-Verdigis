"""Cria (ou completa) os dados de demonstração. Pode rodar várias vezes sem duplicar nada."""
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from accounts.models import (
    Capacidade, Company, ConcessaoConsultor, Niche, Papel, PerfilConsultor, PerfilFuncionario,
    SolicitacaoVinculo, TipoVinculo, User, Vinculo,
)
from dashboard.models import Meta, RelatoSocialVerdigis

SENHA_DEMO = 'verdigis123'


def _cpf(base):
    """Completa 9 dígitos com os verificadores do CPF."""
    def dv(parcial):
        soma = sum(int(d) * p for d, p in zip(parcial, range(len(parcial) + 1, 1, -1)))
        return str((soma * 10) % 11 % 10)
    d1 = dv(base)
    return base + d1 + dv(base + d1)


def _cnpj(base):
    """Completa 12 dígitos com os verificadores do CNPJ."""
    def dv(parcial):
        pesos = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2][-len(parcial):]
        resto = sum(int(c) * p for c, p in zip(parcial, pesos)) % 11
        return '0' if resto < 2 else str(11 - resto)
    d1 = dv(base)
    return base + d1 + dv(base + d1)


class Command(BaseCommand):
    help = 'Popula o banco com dados de demonstração (senha de todos: verdigis123).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--permitir-fora-de-desenvolvimento', action='store_true',
            help='Permite rodar com ENVIRONMENT diferente de development (uso: demo no Render).',
        )

    def handle(self, *args, **opcoes):
        if settings.ENVIRONMENT != 'development' and not opcoes['permitir_fora_de_desenvolvimento']:
            raise CommandError('popular_demo só roda com ENVIRONMENT=development.')
        with transaction.atomic():
            self._usuarios_e_empresa()
            self._metas()
            self._relatos()
        self.stdout.write(self.style.SUCCESS(f'Dados de demonstração prontos. Senha de todos: {SENHA_DEMO}'))

    # ---------- Usuários, empresa e equipe ----------

    def _usuario(self, email, nome, papel='', **extra):
        user, criado = User.objects.get_or_create(email=email, defaults={'nome': nome, 'papel': papel, **extra})
        if criado:
            user.set_password(SENHA_DEMO)
            user.save()
        return user

    def _usuarios_e_empresa(self):
        admin = self._usuario('admin@demo.com', 'Administrador Verdigis', is_staff=True, is_superuser=True)
        if not admin.is_superuser:
            admin.is_staff = admin.is_superuser = True
            admin.save()

        dono = self._usuario('empresa@demo.com', 'Marina Costa', Papel.EMPRESA, telefone='81999998888')
        self.empresa = Company.objects.filter(responsavel=dono).first() or Company.objects.create(
            responsavel=dono,
            niche=Niche.objects.get(nome='Farmácia e drogaria'),
            razao_social='Farmácia Vida Verde Ltda [DEMO]',
            nome_fantasia='Farmácia Vida Verde [DEMO]',
            cnpj=_cnpj('112223330001'),
            cep='50030230', logradouro='Rua da Aurora', numero='100', bairro='Boa Vista',
            cidade='Recife', uf='PE',
            email_corporativo='contato@vidaverde.demo',
            telefone_fixo='(81) 3333-4444', celular_whatsapp='(81) 99999-8888',
        )

        equipe = [
            ('funcionario@demo.com', 'Lucas Andrade', '123456789', 'Farmacêutico', 'Atendimento'),
            ('funcionario2@demo.com', 'Beatriz Lima', '987654321', 'Auxiliar de estoque', 'Estoque'),
        ]
        self.vinculos = {}
        for email, nome, base_cpf, cargo, setor in equipe:
            user = self._usuario(email, nome, Papel.FUNCIONARIO, telefone='81988887777')
            PerfilFuncionario.objects.get_or_create(user=user, defaults={'cpf': _cpf(base_cpf)})
            self.vinculos[email], _ = Vinculo.objects.get_or_create(
                user=user, company=self.empresa,
                defaults={'tipo': TipoVinculo.FUNCIONARIO, 'cargo': cargo, 'setor': setor},
            )

        consultor = self._usuario('consultor@demo.com', 'Rafael Souza', Papel.CONSULTOR, telefone='81977776666')
        PerfilConsultor.objects.get_or_create(user=consultor, defaults={
            'documento_tipo': PerfilConsultor.TipoDocumento.CPF, 'documento': _cpf('111444777'),
            'especialidade': 'Gestão ambiental em farmácias',
        })
        vinculo_consultor, _ = Vinculo.objects.get_or_create(
            user=consultor, company=self.empresa,
            defaults={'tipo': TipoVinculo.CONSULTOR, 'cargo': 'Consultor ESG', 'setor': 'Externo'},
        )
        ConcessaoConsultor.objects.get_or_create(vinculo=vinculo_consultor, capacidade=Capacidade.METAS_CRIAR)
        self.consultor = consultor

        pendente = self._usuario('pendente@demo.com', 'Carla Mendes', Papel.FUNCIONARIO, telefone='81966665555')
        PerfilFuncionario.objects.get_or_create(user=pendente, defaults={'cpf': _cpf('222333444')})
        if not Vinculo.objects.filter(user=pendente).exists():
            SolicitacaoVinculo.objects.get_or_create(
                solicitante=pendente, company=self.empresa, status=SolicitacaoVinculo.Status.PENDENTE,
                defaults={'cargo': 'Balconista', 'setor': 'Atendimento',
                          'mensagem': 'Comecei esta semana no turno da tarde.'},
            )

    # ---------- Metas ----------

    def _metas(self):
        hoje = timezone.localdate()
        dono = self.empresa.responsavel
        func = self.vinculos['funcionario@demo.com']
        func2 = self.vinculos['funcionario2@demo.com']
        metas = [
            ('Reduzir o consumo de papel', 'GERAL', None, 'E', 60, 'MEDIA', False, dono,
             'Imprimir só o necessário\nDigitalizar receitas arquivadas'),
            ('Treinar a equipe em descarte de medicamentos', 'GERAL', None, 'S', -10, 'ALTA', False, dono,
             'Treinamento de 1 hora para todos os turnos'),
            ('Atualizar o PGRSS', 'GERAL', None, 'G', -30, 'ALTA', True, dono,
             'Revisão anual do plano de resíduos'),
            ('Organizar a separação de resíduos do balcão', 'INDIVIDUAL', func, 'E', 30, 'MEDIA', False, func.user,
             'Etiquetar as lixeiras do balcão'),
            ('Conferir a temperatura das geladeiras', 'INDIVIDUAL', func2, 'G', 20, 'ALTA', False, dono,
             'Registrar a temperatura duas vezes por dia'),
            ('Revisar a validade dos itens do estoque', 'INDIVIDUAL', None, 'G', 15, 'BAIXA', False, dono,
             'Meta de um funcionário que saiu da equipe'),
        ]
        for nome, tipo, vinculo, pilar, dias, prioridade, completo, autor, resumo in metas:
            Meta.objects.get_or_create(company=self.empresa, nome=nome, defaults={
                'tipo': tipo, 'funcionario': vinculo, 'pilar_esg': pilar,
                'deadline': hoje + timedelta(days=dias), 'prioridade': prioridade,
                'completo': completo, 'usuario': autor, 'resumo': resumo,
            })

    # ---------- Relatos ----------

    def _relatos(self):
        func = self.vinculos['funcionario@demo.com'].user
        func2 = self.vinculos['funcionario2@demo.com'].user
        relatos = [
            (func, False, 'SEGURANCA', 'POSITIVO', 'Os novos EPIs do laboratório chegaram e são confortáveis.', False),
            (func, True, 'SAUDE_MENTAL', 'NEGATIVO', 'O turno da noite está muito puxado, falta gente no balcão.', False),
            (func2, False, 'BENEFICIOS', 'NEUTRO', 'Seria bom ter vale-alimentação em vez de refeitório.', False),
            (func2, True, 'LIDERANCA', 'NEGATIVO', 'As escalas mudam sem aviso e fica difícil se organizar.', False),
            (func, True, 'DIVERSIDADE', 'POSITIVO', 'Gostei da campanha de inclusão do mês passado.', False),
            (self.consultor, False, 'SEGURANCA', 'NEUTRO', 'Sugiro sinalizar melhor a saída de emergência do estoque.', False),
            (func2, False, 'SAUDE_MENTAL', 'POSITIVO', 'A pausa de 15 minutos fez diferença no meu dia.', False),
            (func, True, 'LIDERANCA', 'NEGATIVO', 'Mensagem com ofensas pessoais (exemplo de relato ocultado).', True),
        ]
        for autor, anonimo, tema, sentimento, mensagem, oculto in relatos:
            RelatoSocialVerdigis.objects.get_or_create(company=self.empresa, mensagem=mensagem, defaults={
                'usuario': autor, 'eh_anonimo': anonimo, 'tema_esg': tema, 'sentimento': sentimento,
                'oculto_em': timezone.now() if oculto else None,
                'oculto_por': self.empresa.responsavel if oculto else None,
                'motivo_ocultacao': 'Conteúdo ofensivo' if oculto else '',
            })
