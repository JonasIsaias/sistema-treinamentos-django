import csv
import openpyxl
from itertools import chain
from datetime import timedelta
from zipfile import BadZipFile
from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.contrib.auth import get_user_model
from .models import Treinamento, Colaborador, Avaliacao, AnalistaInstrutor, Frequencia, ParticipanteExterno
from .utils import add_workdays

User = get_user_model()

LOCAIS_SEDE = [
    ('BC Duque', 'BC Duque'),
    ('BC4', 'BC4'),
    ('BC2', 'BC2'),
    ('Juvenal de Carvalho', 'Juvenal de Carvalho'),
    ('outro', 'Outro (especifique abaixo)')
]

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

TIPO_PARTICIPANTE_CHOICES = [
    ('interno', 'Interno'),
    ('externo', 'Externo'),
]


#Função para validar tamanho do arquivo
def validate_file_size(value):
    max_mb = 10
    limit = max_mb * 1024 * 1024
    if value.size > limit:
        raise ValidationError(f"O arquivo não pode ser maior que {max_mb} MB.")

# Função para normalizar matrícula
def formatar_matricula(valor):
    try:
        return str(int(float(valor))).strip()
    except:
        return None
    

class AlterarDataFrequenciaForm(forms.Form):
    nova_data = forms.DateField(
        label="Nova Data",
        widget=forms.DateInput(attrs={'type': 'date'})
    )

class TreinamentoAdminForm(forms.ModelForm):
    tipo = forms.ChoiceField(choices=TIPO_CHOICES, label='Tipo')
    formato = forms.ChoiceField(choices=FORMATO_CHOICES, label='Formato')
    carga_horaria = forms.CharField(
        required=False,
        widget=forms.HiddenInput()
    )

    status = forms.ChoiceField(
        choices=Treinamento.STATUS_CHOICES,
        required=False
    )

    tipo_participante = forms.ChoiceField(
        choices=TIPO_PARTICIPANTE_CHOICES,
        label="Tipo de Participante",
        initial="interno"
    )

    colaboradores = forms.ModelMultipleChoiceField(
        queryset=Colaborador.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={'size': 15})
    )

    participantes_externos = forms.ModelMultipleChoiceField(
        queryset=ParticipanteExterno.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={'size': 15})
    )

    local = forms.ChoiceField(choices=LOCAIS_SEDE, label='Local do Treinamento')

    arquivo_participantes_externos = forms.FileField(
        required=False,
        label="Planilha de participantes externos (XLSX)",
        validators=[FileExtensionValidator(allowed_extensions=['xlsx'])],
        help_text="A planilha deve seguir o modelo padrão disponível no sistema."
    )

    # Campo On The Job
    on_the_job = forms.BooleanField(
        required=False,
        label="On The Job",
        help_text="Marque se o treinamento é On The Job"
    )

    tempo_on_the_job = forms.IntegerField(
        required=False,
        min_value=1,
        label="Tempo por pessoa (minutos)",
        help_text="Informe o tempo em minutos, apenas para On The Job"
    )

    # Datas
    data_inicio = forms.DateField(
        input_formats=['%d-%m-%Y'],
        widget=forms.DateInput(format='%d-%m-%Y', attrs={'placeholder': 'dd-mm-aaaa'})
    )
    data_fim = forms.DateField(
        input_formats=['%d-%m-%Y'],
        widget=forms.DateInput(format='%d-%m-%Y', attrs={'placeholder': 'dd-mm-aaaa'})
    )
    
    analistas = forms.ModelMultipleChoiceField(
        queryset=AnalistaInstrutor.objects.filter(tipo='analista'),
        required=False,
        widget=forms.SelectMultiple(attrs={'size': 10}),
        label="Analistas"
    )

    # Filtro interno + CSV
    matriculas_filter = forms.CharField(
        required=False,
        label='Filtrar Colaboradores por Matrículas ou Nomes:',
        help_text='Insira uma matrícula ou nome por linha.',
        widget=forms.Textarea(attrs={'rows': 5})
    )

    matriculas_file = forms.FileField(
        required=False,
        label='Ou envie um arquivo CSV:',
        help_text="O arquivo deve conter uma coluna chamada 'matricula'."
    )

    # Anexo frequência
    anexo_frequencia = forms.FileField(
        required=False,
        label="Anexo da Frequência (PDF/Imagem)",
        validators=[
            FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png']),
            validate_file_size
        ],
        widget=forms.ClearableFileInput(attrs={'accept': '.pdf,.jpg,.jpeg,.png'})
    )

    class Meta:
        model = Treinamento
        exclude = ['status', 'numero_treinados']

    # INICIALIZAÇÃO
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if "criado_por" in self.fields:
            self.fields['criado_por'].initial = self.user
            self.fields['criado_por'].widget = forms.HiddenInput()

        self.fields['instrutores'].queryset = AnalistaInstrutor.objects.filter(tipo='instrutor')

        if self.instance.pk:
            self.fields['colaboradores'].queryset = self.instance.colaboradores.all()
        else:
            # Se for novo, carregar todos os colaboradores inicialmente
            self.fields['colaboradores'].queryset = Colaborador.objects.all()

        if 'local_personalizado' in self.fields:
            self.fields['local_personalizado'].widget.attrs.update({'placeholder': 'Descreva o local'})

    # PROCESSAMENTO DE ARQUIVO XLSX - PARTICIPANTES EXTERNOS
    def _processar_externos(self, file):
        externos_data = []
        erros = []

        # 1. Validação da extensão
        if not file.name.lower().endswith(".xlsx"):
            return [], [
                "O arquivo de participantes externos deve estar no formato .xlsx."
            ]

        # 2. Tenta abrir o Excel com tratamento de arquivo inválido
        try:
            file.seek(0)
            wb = openpyxl.load_workbook(
                file,
                read_only=True,
                data_only=True
            )
            ws = wb.active

        except (BadZipFile, OSError, ValueError):
            return [], [
                "O arquivo enviado não é um Excel (.xlsx) válido. "
                "Baixe o modelo novamente e envie o arquivo sem alterá-lo."
            ]

        # 3. Processamento das linhas
        for i, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            # Ignora linhas totalmente vazias
            if not row or all(cell in (None, "") for cell in row):
                continue

            # Garante exatamente 8 colunas
            row = list(row) + [None] * (8 - len(row))

            nome, email, cargo, unidade, cidade, estado, gestor, data = row[:8]

            # Apenas nome é obrigatório
            if not nome:
                erros.append(f"Linha {i}: O campo Nome é obrigatório.")
                continue

            externos_data.append({
                "nome": str(nome).strip(),
                "email": str(email).strip() if email else None,
                "cargo": cargo,
                "unidade": unidade,
                "cidade": cidade,
                "estado": estado,
                "gestor": gestor,
                "data_participacao": data,
            })

        if not externos_data:
            erros.append(
                "Nenhum participante externo válido foi encontrado na planilha."
            )

        return externos_data, erros
    
    def _get_matriculas_ou_nomes_from_input(self, entradas):
        """
        Recebe uma string de entradas (nomes ou matrículas) e retorna uma lista limpa.
        """
        if not entradas:
            return []

        # separa por linhas ou por espaços
        linhas = []
        for item in entradas.splitlines():
            linhas.extend(item.split())

        # remove strings vazias
        return [linha.strip() for linha in linhas if linha.strip()]

    # PROCESSAMENTO DE CSV INTERNO
    def _process_csv(self, file):
        matriculas = []
        erros = []

        try:
            file.seek(0)
            decoded = file.read().decode('utf-8-sig').splitlines()
            reader = csv.DictReader(decoded)

            if "matricula" not in reader.fieldnames:
                erros.append("O CSV deve ter uma coluna chamada 'matricula'.")
                return [], erros

            for i, row in enumerate(reader, start=2):
                raw = row['matricula'].strip()
                m = formatar_matricula(raw)

                if m:
                    matriculas.append(m)
                else:
                    erros.append(f"Linha {i}: matrícula inválida '{raw}'.")
        except:
            erros.append("Erro ao processar o CSV. Verifique o formato e codificação.")

        return list(set(matriculas)), erros

    # CLEAN PRINCIPAL
    def clean(self):
        cleaned = super().clean()

        tipo_participante = cleaned.get("tipo_participante")
        on_the_job = cleaned.get("on_the_job")

        # =========================
        # Validação de datas
        # =========================
        data_inicio = cleaned.get("data_inicio")
        data_fim = cleaned.get("data_fim")

        if data_inicio and data_fim and data_fim < data_inicio:
            self.add_error(
                "data_fim",
                "A data de fim não pode ser anterior à data de início."
            )

        # =========================
        # Local personalizado
        # =========================
        if (
            cleaned.get("local") == "outro"
            and not cleaned.get("local_personalizado")
        ):
            self.add_error(
                "local_personalizado",
                "Informe o local personalizado."
            )

        # =========================================================
        # PARTICIPANTES
        # =========================================================

        if tipo_participante == "externo":

            file = self.files.get("arquivo_participantes_externos")

            if not file:
                self.add_error(
                    "arquivo_participantes_externos",
                    "Envie a planilha de participantes externos."
                )
            else:
                externos_data, erros = self._processar_externos(file)

                for erro in erros:
                    self.add_error(
                        "arquivo_participantes_externos",
                        erro
                    )

                if not erros:
                    cleaned["externos_data"] = externos_data
                    cleaned["colaboradores"] = []
                    cleaned["participantes_externos"] = []

        else:
            # =====================================================
            # PARTICIPANTES INTERNOS
            # =====================================================

            entradas = cleaned.get("matriculas_filter", "")
            arquivo = self.files.get("matriculas_file")

            erros = []
            novos = []

            # -------------------------
            # Entradas manuais
            # -------------------------
            if entradas:
                linhas = [
                    linha.strip()
                    for linha in entradas.splitlines()
                    if linha.strip()
                ]

                for linha in linhas:
                    matricula = formatar_matricula(linha)

                    if matricula:
                        qs = Colaborador.objects.filter(
                            matricula=matricula
                        )
                    else:
                        qs = Colaborador.objects.filter(
                            nome__icontains=linha
                        )

                    if qs.exists():
                        novos.extend(list(qs))
                    else:
                        erros.append(
                            f"Nenhum colaborador encontrado para '{linha}'."
                        )

            # -------------------------
            # CSV
            # -------------------------
            if arquivo:
                csv_mats, csv_erros = self._process_csv(arquivo)

                erros.extend(csv_erros)

                for matricula in csv_mats:
                    qs = Colaborador.objects.filter(
                        matricula=matricula
                    )
                    novos.extend(list(qs))

            # -------------------------
            # Reportar erros
            # -------------------------
            for erro in erros:
                self.add_error("matriculas_filter", erro)

            if not erros:
                colaboradores_post = cleaned.get("colaboradores")

                if novos:
                    cleaned["colaboradores"] = list(
                        dict.fromkeys(novos)
                    )
                elif colaboradores_post:
                    cleaned["colaboradores"] = colaboradores_post
                else:
                    cleaned["colaboradores"] = []

            cleaned["participantes_externos"] = []

        # =========================================================
        # CARGA HORÁRIA
        # =========================================================

        carga = cleaned.get("carga_horaria")

        if on_the_job:

            colaboradores = cleaned.get("colaboradores") or []
            tempo = cleaned.get("tempo_on_the_job")

            if not tempo:
                self.add_error(
                    "tempo_on_the_job",
                    "Informe o tempo por pessoa."
                )

            if not colaboradores:
                self.add_error(
                    "colaboradores",
                    "Informe pelo menos um colaborador para o On The Job."
                )

            if tempo and colaboradores:
                cleaned["carga_horaria"] = timedelta(
                    minutes=int(tempo) * len(colaboradores)
                )

        else:

            if not carga:
                self.add_error(
                    "carga_horaria",
                    "A carga horária é obrigatória."
                )

            elif isinstance(carga, timedelta):

                if carga <= timedelta(0):
                    self.add_error(
                        "carga_horaria",
                        "A carga horária deve ser maior que zero."
                    )

            elif isinstance(carga, str):

                try:
                    partes = carga.strip().split(":")

                    if len(partes) != 3:
                        raise ValueError

                    h, m, s = [int(x) for x in partes]

                    if h < 0 or not 0 <= m < 60 or not 0 <= s < 60:
                        raise ValueError

                    carga_td = timedelta(
                        hours=h,
                        minutes=m,
                        seconds=s
                    )

                    if carga_td <= timedelta(0):
                        raise ValueError

                    cleaned["carga_horaria"] = carga_td

                except (ValueError, TypeError):
                    self.add_error(
                        "carga_horaria",
                        "Formato inválido. Use HH:MM:SS."
                    )

            else:
                self.add_error(
                    "carga_horaria",
                    "Formato inválido. Use HH:MM:SS."
                )

        return cleaned

    
    def save(self, commit=True):
        treinamento = super().save(commit=False)

        # Garantir que o criador esteja definido
        if not treinamento.criado_por and hasattr(self, 'user'):
            treinamento.criado_por = self.user

        # Prefixo no título se for On The Job
        on_the_job = self.cleaned_data.get("on_the_job")
        if on_the_job:
            titulo = treinamento.titulo or ""
            if not titulo.startswith("On The Job - "):
                treinamento.titulo = f"On The Job - {titulo}"

        # Garantir que a carga horária seja um timedelta
        carga = self.cleaned_data.get("carga_horaria")
        on_the_job = self.cleaned_data.get("on_the_job")
        tempo = self.cleaned_data.get("tempo_on_the_job")
        colaboradores = self.cleaned_data.get("colaboradores", [])

        if on_the_job and tempo:
            carga_total_minutos = tempo * len(colaboradores)
            treinamento.carga_horaria = timedelta(minutes=carga_total_minutos)
        elif carga:
            if not isinstance(carga, timedelta):
                raise ValueError("Carga horária inválida no save()")

            treinamento.carga_horaria = carga
        if treinamento.carga_horaria is None:
            raise ValueError("Carga horária não pode ser nula neste ponto")

        # Salva o objeto antes de M2M
        treinamento.save()

        tipo = self.cleaned_data.get("tipo_participante")

        if tipo == "externo":
            externos_data = self.cleaned_data.get("externos_data", [])
            externos_objs = []
            for data in externos_data:
                # Aqui pode ser ajustado para evitar duplicatas, se necessário
                externos_objs.append(ParticipanteExterno.objects.create(**data))

            treinamento.participantes_externos.set(externos_objs)
            treinamento.colaboradores.clear()

        else:
            treinamento.colaboradores.set(colaboradores)
            treinamento.participantes_externos.clear()

        # Salva novamente se commit=True para garantir M2M
        if commit:
            treinamento.save()

        # =========================
        # SALVAR M2M
        # =========================
        if 'instrutores' in self.cleaned_data:
            treinamento.instrutores.set(self.cleaned_data['instrutores'])

        if 'analistas' in self.cleaned_data:
            treinamento.analistas.set(self.cleaned_data['analistas'])

        return treinamento


class AvaliacaoForm(forms.ModelForm):
    class Meta:
        model = Avaliacao
        fields = [
            'nota_infraestrutura', 'nota_material',
            'nota_assunto', 'nota_didatica_analista', 'comentarios'
        ]
        widgets = {
            'comentarios': forms.Textarea(attrs={'rows': 3}),
        }


class ColaboradorAdminForm(forms.ModelForm):
    class Meta:
        model = Colaborador
        fields = [
            'empresa', 'vaga', 'status', 'admissao', 'matricula',
            'nome', 'servico', 'cargo', 'responsavel_direto', 'coord_atendimento'
        ]


STATUS_PRESENCA = (
    (True, 'Presente'),
    (False, 'Faltou'),
)

class FrequenciaForm(forms.ModelForm):
    presente = forms.TypedChoiceField(
        choices=STATUS_PRESENCA,
        widget=forms.RadioSelect(attrs={'class': 'radio-presente'}),
        required=True,
        label="Status",
        coerce=lambda x: x == 'True'
    )

    justificativa = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 2,
            'class': 'justificativa-field',
            'placeholder': 'Informe a justificativa da ausência'
        })
    )

    anexo = forms.FileField(
        required=False,
        widget=forms.ClearableFileInput(attrs={
            'class': 'anexo-field',
            'accept': '.pdf,.jpg,.jpeg,.png'
        })
    )

    class Meta:
        model = Frequencia
        fields = ["colaborador", "presente", "justificativa", "anexo"]

    def __init__(self, *args, **kwargs):
        self.treinamento = kwargs.pop("treinamento", None)
        self.data_param = kwargs.pop("data_param", None)
        super().__init__(*args, **kwargs)

        if not self.instance.pk:
            self.instance.treinamento = self.treinamento
            self.instance.data = self.data_param

    def clean(self):
        cleaned_data = super().clean()
        presente = cleaned_data.get('presente')
        justificativa = cleaned_data.get('justificativa')
        anexo = cleaned_data.get('anexo')

        # Se faltou e não tem justificativa nem anexo, preenche automático
        if presente is False and not justificativa and not anexo:
            cleaned_data['justificativa'] = "Falta sem justificativa"

        # Nova validação: respeitar apenas prazo útil (não período fixo do treinamento)
        if self.treinamento and self.data_param:
            prazo_limite_data = add_workdays(self.treinamento.data_inicio, 1)  # 1 dia útil
            # Se data é anterior ao início do treinamento e já passou do prazo útil → erro
            from django.utils import timezone
            if self.data_param < self.treinamento.data_inicio and timezone.now().date() > prazo_limite_data:
                raise forms.ValidationError("Data da frequência está fora do prazo permitido para registro retroativo.")

        return cleaned_data
