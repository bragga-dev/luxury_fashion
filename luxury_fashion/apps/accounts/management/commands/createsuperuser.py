"""
Comando `python manage.py createsuperuser` customizado.

Sobrescreve o comando padrão do Django para, além de criar o User ADMIN,
criar junto o AdminProfile (nome completo). A foto fica com o valor padrão
e pode ser enviada depois via API (POST /upload-admin-photo).
"""
import getpass
import os

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from luxury_fashion.apps.accounts.models.user_model import User
from luxury_fashion.apps.accounts.repositories.admin_repository import create_admin_profile
from luxury_fashion.apps.accounts.selectors.user_selector import email_exists


class Command(BaseCommand):
    help = "Cria um superusuário ADMIN junto com o seu perfil (nome completo)."

    def add_arguments(self, parser):
        parser.add_argument("--email", dest="email", default=None, help="E-mail do administrador.")
        parser.add_argument("--full_name", dest="full_name", default=None, help="Nome completo do administrador.")
        parser.add_argument(
            "--noinput", "--no-input",
            action="store_false", dest="interactive", default=True,
            help="Não solicita input. Requer --email, --full_name e a env DJANGO_SUPERUSER_PASSWORD.",
        )

    def handle(self, *args, **options):
        interactive = options["interactive"]
        email = options.get("email")
        full_name = options.get("full_name")

        if interactive:
            self.stdout.write("Criação de superusuário (ADMIN)")
            email = self._prompt_email(email)
            full_name = self._prompt_full_name(full_name)
            password = self._prompt_password()
        else:
            password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")
            if not email:
                raise CommandError("--email é obrigatório em modo --noinput.")
            if not full_name:
                raise CommandError("--full_name é obrigatório em modo --noinput.")
            if not password:
                raise CommandError("Defina a variável de ambiente DJANGO_SUPERUSER_PASSWORD em modo --noinput.")
            if email_exists(email):
                raise CommandError(f"Já existe um usuário com o e-mail '{email}'.")

        try:
            with transaction.atomic():
                user = User.objects.create_superuser(email=email, password=password)
                create_admin_profile(user_id=user, full_name=full_name)
        except Exception as e:
            raise CommandError(str(e))

        self.stdout.write(self.style.SUCCESS(f"Administrador '{email}' criado com sucesso."))

    def _prompt_email(self, default=None):
        while True:
            raw = input(f"E-mail{f' [{default}]' if default else ''}: ").strip()
            email = raw or (default or "")
            if not email:
                self.stderr.write("O e-mail é obrigatório.")
                continue
            if email_exists(email):
                self.stderr.write(f"Já existe um usuário com o e-mail '{email}'.")
                continue
            return email

    def _prompt_full_name(self, default=None):
        while True:
            raw = input(f"Nome completo{f' [{default}]' if default else ''}: ").strip()
            full_name = raw or (default or "")
            if len(full_name) < 2:
                self.stderr.write("Informe o nome completo (mínimo 2 caracteres).")
                continue
            return full_name

    def _prompt_password(self):
        while True:
            password = getpass.getpass("Senha: ")
            password2 = getpass.getpass("Senha (confirmação): ")
            if password != password2:
                self.stderr.write("As senhas não coincidem.")
                continue
            try:
                validate_password(password)
            except DjangoValidationError as e:
                self.stderr.write("\n".join(e.messages))
                continue
            return password