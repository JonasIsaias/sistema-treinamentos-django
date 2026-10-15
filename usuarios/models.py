from django.contrib.auth.models import AbstractUser
from django.db import models

NIVEL_ACESSO_CHOICES = (
    ('admin', 'Administrador'),
    ('analista', 'Analista'),
)

class Usuario(AbstractUser):
    nivel_acesso = models.CharField(
        max_length=20,
        choices=NIVEL_ACESSO_CHOICES,
        default='analista',
        verbose_name='Nível de Acesso'
    )

    groups = models.ManyToManyField(
        'auth.Group',
        related_name='usuarios',
        blank=True,
        help_text='Os grupos aos quais este usuário pertence.',
        verbose_name='Grupos'
    )
    
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='usuarios_permissoes',
        blank=True,
        help_text='Permissões específicas para este usuário.',
        verbose_name='Permissões de usuário'
    )

    def __str__(self):
        return self.username
