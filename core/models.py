from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db.models import Count, Q
from datetime import timedelta
from .utils import add_workdays
from django.utils import timezone


class AnalistaInstrutor(models.Model):
    TIPO_CHOICES = [
        ('analista', 'Analista'),
        ('instrutor', 'Instrutor'),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} - {self.get_tipo_display()}"


class Servico(models.Model):
    nome = models.CharField(max_length=100)

    def __str__(self):
        return self.nome


class Colaborador(models.Model):
    nome = models.CharField(max_length=100)
    matricula = models.CharField(max_length=20, unique=True)
    admissao = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=50,
        choices=[
            ('ATIVO', 'Ativo'),
            ('INATIVO', 'Inativo'),
            ('FERIAS', 'Férias'),
        ],
        default='ATIVO'
    )
    empresa = models.CharField(max_length=100, blank=True, null=True)
    vaga = models.CharField(max_length=100, blank=True, null=True)
    servico = models.ForeignKey(Servico, on_delete=models.CASCADE)
    cargo = models.CharField(max_length=100, blank=True, null=True)
    responsavel_direto = models.CharField(max_length=100, blank=True, null=True)
    coord_atendimento = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.nome} ({self.matricula})"
    

class ParticipanteExterno(models.Model):
    nome = models.CharField(max_length=200)
    email = models.EmailField(blank=True, null=True)
    cargo = models.CharField(max_length=200, blank=True, null=True)
    unidade = models.CharField(max_length=200, blank=True, null=True)
    cidade = models.CharField(max_length=200, blank=True, null=True)
    estado = models.CharField(max_length=200, blank=True, null=True)
    gestor = models.CharField(max_length=200, blank=True, null=True)
    data_participacao = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.nome


from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from datetime import timedelta
from django.db.models import Count

# Função para validar tamanho do arquivo
def validate_file_size(value):
    max_mb = 10  # limite de 10MB
    limit = max_mb * 1024 * 1024
    if value.size > limit:
        raise ValidationError(f"O arquivo não pode ser maior que {max_mb} MB.")

class Treinamento(models.Model):
    TIPO_CHOICES = [
        ('capacitacao', 'Capacitação'),
        ('educacao_continua', 'Educação Contínua'),
        ('formacao_inicial', 'Formação Inicial'),
        ('comportamental', 'Comportamental'),
    ]

    FORMATO_CHOICES = [
        ('presencial', 'Presencial'),
        ('online', 'On-line'),
        ('hibrido', 'Híbrido'),
    ]

    LOCAL_CHOICES = [
        ('BC Duque', 'BC Duque'),
        ('BC4', 'BC4'),
        ('BC2', 'BC2'),
        ('Juvenal de Carvalho', 'Juvenal de Carvalho'),
        ('outro', 'Outro'),
    ]

    TIPO_PARTICIPANTE_CHOICES = [
        ('interno', 'Interno'),
        ('externo', 'Externo'),
    ]

    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('em_andamento', 'Em andamento'),
        ('concluido', 'Concluído'),
    ]

    titulo = models.CharField(max_length=200)
    local = models.CharField(max_length=255, choices=LOCAL_CHOICES, default='BC Duque')
    local_personalizado = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Local Personalizado (se 'Outro')"
    )

    status_manual = models.BooleanField(default=False)
    data_inicio = models.DateField()
    data_fim = models.DateField()
    carga_horaria = models.DurationField(help_text="Formato hh:mm:ss", null=True, blank=True)
    tipo = models.CharField(max_length=30, choices=TIPO_CHOICES)
    formato = models.CharField(max_length=30, choices=FORMATO_CHOICES)

    colaboradores = models.ManyToManyField('Colaborador', related_name='treinamentos')

    participantes_externos = models.ManyToManyField(
        'ParticipanteExterno',
        blank=True,
        related_name='treinamentos'
    )

    tipo_participante = models.CharField(
        max_length=20,
        choices=TIPO_PARTICIPANTE_CHOICES,
        default='interno'
    )

    on_the_job = models.BooleanField(
        default=False,
        verbose_name="On the Job"
    )

    instrutores = models.ManyToManyField(
        'AnalistaInstrutor',
        related_name='treinamentos_instrutor',
        blank=True,
        limit_choices_to={'tipo': 'instrutor'},
        verbose_name='Instrutores'
    )

    analistas = models.ManyToManyField(
        'AnalistaInstrutor',
        related_name='treinamentos_analista',
        blank=True,
        limit_choices_to={'tipo': 'analista'},
        verbose_name='Analistas'
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pendente'
    )

    status_manual = models.BooleanField(default=False)

    numero_treinados = models.IntegerField(default=0)

    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='treinamentos_criados',
        null=True,
        blank=True
    )

    observacoes = models.TextField(blank=True, null=True)

    #Novo campo para anexo
    anexo_frequencia = models.FileField(
        upload_to='frequencias/%Y/%m/%d/',
        blank=True,
        null=True,
        verbose_name="Anexo da Frequência (PDF/Imagem)",
        help_text="Tipos aceitos: PDF, JPG, PNG. Máx. 10MB.",
        validators=[
            FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png']),
            validate_file_size
        ]
    )

    def calcular_percentual_curso(self):
        total_dias = Frequencia.objects.filter(treinamento=self).values('data').distinct().count()
        if total_dias == 0:
            return 0.0
        total_colaboradores = self.colaboradores.count()
        if total_colaboradores == 0:
            return 0.0

        presencas = Frequencia.objects.filter(
            treinamento=self,
            presente=True
        ).values('colaborador').annotate(dias_presentes=Count('data'))

        percentuais = [(p['dias_presentes'] / total_dias) * 100 for p in presencas]
        if not percentuais:
            return 0.0

        soma_percentuais = sum(percentuais)
        media_percentual = soma_percentuais / total_colaboradores
        return round(media_percentual, 1)

    def calcular_media_aderencia(self):
        return self.calcular_percentual_curso()

    def carga_horaria_total(self):
        if self.data_inicio and self.data_fim and self.carga_horaria:
            dias = (self.data_fim - self.data_inicio).days + 1
            return self.carga_horaria * dias
        return timedelta(0)

    def colaborador_esta_treinado(self, colaborador):
        total = self.carga_horaria_total()
        if total.total_seconds() == 0:
            return False

        presencas = self.frequencia_set.filter(colaborador=colaborador, presente=True).count()
        carga_presenca = self.carga_horaria * presencas

        percentual = (carga_presenca.total_seconds() / total.total_seconds()) * 100
        return percentual >= 75

    def colaboradores_treinados(self):
        return [col for col in self.colaboradores.all() if self.colaborador_esta_treinado(col)]

    def quantidade_treinados(self):
        total = len(self.colaboradores_treinados())

        # 🔹 EXTERNOS
        if self.data_inicio and self.data_fim and self.carga_horaria:
            dias_total = (self.data_fim - self.data_inicio).days + 1
            carga_total = self.carga_horaria.total_seconds() * dias_total

            for externo in self.participantes_externos.all():
                presencas = self.frequencia_set.filter(
                    participante_externo=externo,
                    presente=True
                ).count()

                carga_presenca = self.carga_horaria.total_seconds() * presencas
                percentual = (carga_presenca / carga_total) * 100 if carga_total else 0

                if percentual >= 75:
                    total += 1

        return total

    def carga_horaria_total_formatada(self):
        total = self.carga_horaria_total()
        total_segundos = int(total.total_seconds())
        horas, resto = divmod(total_segundos, 3600)
        minutos, segundos = divmod(resto, 60)
        return f"{horas:02}:{minutos:02}:{segundos:02}"

    def clean(self):
        super().clean()

        if self.data_inicio and self.data_fim and self.data_fim < self.data_inicio:
            raise ValidationError("A data de fim não pode ser anterior à data de início.")

        if self.local == 'outro' and not self.local_personalizado:
            raise ValidationError({'local_personalizado': "Informe o local personalizado quando 'Outro' for selecionado."})

        if self.local != 'outro' and self.local_personalizado:
            raise ValidationError({'local_personalizado': "O local personalizado só deve ser preenchido quando 'Outro' for selecionado."})

    def obter_frequencia_geral(self):
        total_internos = self.colaboradores.count()
        total_externos = self.participantes_externos.count()

        total_participantes = total_internos + total_externos

        # IDs únicos de presentes (internos)
        presentes_internos = set(
            Frequencia.objects.filter(
                treinamento=self,
                presente=True,
                colaborador__isnull=False
            ).values_list('colaborador', flat=True)
        )

        # IDs únicos de presentes (externos)
        presentes_externos = set(
            Frequencia.objects.filter(
                treinamento=self,
                presente=True,
                participante_externo__isnull=False
            ).values_list('participante_externo', flat=True)
        )

        total_presentes = len(presentes_internos) + len(presentes_externos)

        total_faltantes = total_participantes - total_presentes

        # PROTEÇÃO EXTRA (evita negativo)
        if total_faltantes < 0:
            total_faltantes = 0

        return {
            'aplicado': total_presentes,
            'absenteismo': total_faltantes
        }

    def obter_frequencia_por_dia(self):
        """
        Retorna uma lista com dados de presença e ausência por data.
        """
        dias = Frequencia.objects.filter(treinamento=self).values_list('data', flat=True).distinct()
        total_colaboradores = self.colaboradores.count()

        resultado = []
        for dia in dias:
            presentes_ids = Frequencia.objects.filter(
                treinamento=self,
                data=dia,
                presente=True
            ).values_list('colaborador', flat=True).distinct()

            presentes = len(set(presentes_ids))
            faltantes = total_colaboradores - presentes

            resultado.append({
                'data': dia,
                'aplicado': presentes,
                'absenteismo': faltantes
            })
        return resultado

    def __str__(self):
        return self.titulo


class Frequencia(models.Model):
    colaborador = models.ForeignKey('Colaborador', on_delete=models.CASCADE, null=True, blank=True)
    treinamento = models.ForeignKey('Treinamento', on_delete=models.CASCADE)
    data = models.DateField()
    presente = models.BooleanField(default=False)

    participante_externo = models.ForeignKey(
        'ParticipanteExterno',
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    justificativa = models.TextField(blank=True, null=True)
    anexo = models.FileField(
        upload_to='justificativas/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png'])]
    )

    class Meta:
        unique_together = (
            ('colaborador', 'treinamento', 'data'),
            ('participante_externo', 'treinamento', 'data'),
        )
        ordering = ['data']

    def clean(self):
        # Validação de prazo útil (retroativo)
        if self.treinamento_id and self.data:
            prazo_limite_data = add_workdays(self.treinamento.data_inicio, 1)  # 1 dia útil após início
            if self.data < self.treinamento.data_inicio and timezone.now().date() > prazo_limite_data:
                raise ValidationError("A data da frequência está fora do prazo permitido para registro retroativo.")
            
        if not self.colaborador and not self.participante_externo:
            raise ValidationError("Informe um colaborador ou participante externo.")

        if self.colaborador and self.participante_externo:
            raise ValidationError("Informe apenas um: colaborador OU participante externo.")

        # Limpar justificativa/anexo caso presente = True
        if self.presente:
            self.justificativa = None
            self.anexo = None
        else:
            if not self.justificativa and not self.anexo:
                self.justificativa = "Falta sem justificativa"

            if self.anexo and self.anexo.size > 5 * 1024 * 1024:
                raise ValidationError("O anexo não pode ultrapassar 5MB.")

    def __str__(self):
        if self.colaborador_id:
            pessoa = self.colaborador.nome
        elif self.participante_externo_id:
            pessoa = self.participante_externo.nome
        else:
            pessoa = "Sem participante"

        data = self.data.strftime('%d/%m/%Y') if self.data else "Sem data"
        status = 'Presente' if self.presente else 'Faltou'
        
        return f"{pessoa} em {data} - {status}"

class Avaliacao(models.Model):
    treinamento = models.ForeignKey(Treinamento, on_delete=models.CASCADE)
    colaborador = models.ForeignKey(Colaborador, on_delete=models.CASCADE)
    data_avaliacao = models.DateTimeField(auto_now_add=True)

    nota_infraestrutura = models.IntegerField()
    nota_material = models.IntegerField()
    nota_assunto = models.IntegerField()
    nota_didatica_analista = models.IntegerField()

    comentarios = models.TextField(blank=True)

    class Meta:
        unique_together = ('treinamento', 'colaborador')

    def nota_media(self):
        total = (
            self.nota_infraestrutura +
            self.nota_material +
            self.nota_assunto +
            self.nota_didatica_analista
        )
        return round(total / 4, 2)

    def __str__(self):
        return f"{self.colaborador} - {self.treinamento}"


class RelatorioColaboradorProxy(Colaborador):
    class Meta:
        verbose_name = "Relatório de Colaborador"
        verbose_name_plural = "Relatórios de Colaboradores"
        proxy = True

    def __str__(self):
        return "Relatório de Colaborador"
