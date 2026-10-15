import io
import os
import zipfile
from django.http import HttpResponse
from datetime import timedelta
from import_export import resources, fields
from import_export.admin import ImportExportModelAdmin
from django.contrib import admin
from django.db.models import Q, Count, Prefetch
from django.urls import path
from django.shortcuts import render, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from rangefilter.filters import DateRangeFilter

from .models import Avaliacao, AnalistaInstrutor, Treinamento, Frequencia, Colaborador, Servico
from .forms import TreinamentoAdminForm, ColaboradorAdminForm, FrequenciaForm
from .models import RelatorioColaboradorProxy, ParticipanteExterno
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.utils.html import format_html
import calendar
from .forms import AlterarDataFrequenciaForm
from django import forms


MESES_PT = [
    "", "JANEIRO", "FEVEREIRO", "MARÇO", "ABRIL", "MAIO", "JUNHO",
    "JULHO", "AGOSTO", "SETEMBRO", "OUTUBRO", "NOVEMBRO", "DEZEMBRO"
]

class TreinamentoResource(resources.ModelResource):
    tipo = fields.Field(attribute='get_tipo_display', column_name='TIPO')
    formato = fields.Field(attribute='get_formato_display', column_name='FORMATO')
    local_display = fields.Field(column_name='LOCAL')
    nome_treinamento = fields.Field(column_name='NOME DO TREINAMENTO')
    programados = fields.Field(column_name='PROGRAMADOS')
    treinados = fields.Field(column_name='TREINADOS')
    faltosos = fields.Field(column_name='FALTOSOS')
    inicio = fields.Field(column_name='INICIO')
    termino = fields.Field(column_name='TERMINO')
    mes = fields.Field(column_name='MÊS')
    dias_aprendizado = fields.Field(column_name='DIAS APRENDIZADO')
    ch_curso = fields.Field(column_name='CH CURSO')
    analista_instrutor = fields.Field(column_name='ANALISTA/INSTRUTOR')
    ano = fields.Field(column_name='ANO')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Descobre todos os serviços usados nos treinamentos
        servicos = set()
        for t in Treinamento.objects.all():
            servicos.update(t.colaboradores.values_list('servico__nome', flat=True))

        # Adiciona um field dinâmico para cada serviço
        for servico in servicos:
            f = fields.Field(column_name=servico)
            setattr(self, f'dehydrate_{servico}', self._make_dehydrate_servico(servico))
            self.fields[servico] = f

    def _make_dehydrate_servico(self, servico_nome):
        def dehydrate(obj):
            return obj.colaboradores.filter(servico__nome=servico_nome).count()
        return dehydrate

    class Meta:
        model = Treinamento
        import_id_fields = ('id',)
        fields = (
            'tipo', 'formato', 'local_display', 'nome_treinamento', 'programados',
            'treinados', 'faltosos', 'inicio', 'termino', 'mes', 'dias_aprendizado',
            'ch_curso', 'analista_instrutor', 'ano'
        )
        export_order = fields

    # =====================
    # Dehydrates fixos
    # =====================
    def dehydrate_local_display(self, obj):
        return obj.local_personalizado if obj.local == 'outro' else obj.get_local_display()

    def dehydrate_nome_treinamento(self, obj):
        return obj.titulo

    def dehydrate_programados(self, obj):
        return obj.colaboradores.count() + obj.participantes_externos.count()

    def dehydrate_treinados(self, obj):
        return obj.quantidade_treinados()

    def dehydrate_faltosos(self, obj):
        freq = obj.obter_frequencia_geral()
        return freq['absenteismo']

    def dehydrate_inicio(self, obj):
        return obj.data_inicio.strftime('%d/%m/%Y') if obj.data_inicio else ''

    def dehydrate_termino(self, obj):
        return obj.data_fim.strftime('%d/%m/%Y') if obj.data_fim else ''

    def dehydrate_mes(self, obj):
        if obj.data_inicio:
            return MESES_PT[obj.data_inicio.month]
        return ''

    def dehydrate_dias_aprendizado(self, obj):
        if obj.data_inicio and obj.data_fim:
            return (obj.data_fim - obj.data_inicio).days + 1
        return 0

    def dehydrate_ch_curso(self, obj):
        return obj.carga_horaria_total_formatada()

    def dehydrate_analista_instrutor(self, obj):
        return ", ".join(i.user.username for i in obj.instrutores.all())

    def dehydrate_ano(self, obj):
        return obj.data_inicio.year if obj.data_inicio else ''


# =====================
# Inline Somente Leitura - Colaboradores
# =====================
class ColaboradoresInline(admin.TabularInline):
    model = Treinamento.colaboradores.through
    extra = 0
    verbose_name = "Colaborador"
    verbose_name_plural = "Colaboradores Vinculados (Somente Leitura)"
    can_delete = False
    show_change_link = False
    fields = ('colaborador',)
    readonly_fields = ('colaborador',)

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False
    
# Inline Somente Leitura - ColaboradoresExternos
class ParticipantesExternosInline(admin.TabularInline):
    model = Treinamento.participantes_externos.through
    extra = 0
    verbose_name = "Participante Externo"
    verbose_name_plural = "Participantes Externos"
    autocomplete_fields = ("participanteexterno",)

    # Permite edição no admin
    can_delete = True  
    show_change_link = True


# =====================
# Inline Somente Leitura - Frequência
# =====================
class FrequenciaInline(admin.TabularInline):
    model = Frequencia
    extra = 0
    readonly_fields = ('colaborador', 'data', 'presente')
    can_delete = False
    show_change_link = False
    verbose_name = "Registro de Frequência"
    verbose_name_plural = "Frequências dos Colaboradores (Somente Leitura)"

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


# =====================
# Admin de AnalistaInstrutor
# =====================
@admin.register(AnalistaInstrutor)
class AnalistaInstrutorAdmin(admin.ModelAdmin):
    list_display = ('user', 'tipo')
    search_fields = ('user__username', 'user__first_name', 'user__last_name')
    list_filter = ('tipo',)
    autocomplete_fields = ('user',)


@admin.register(ParticipanteExterno)
class ParticipanteExternoAdmin(admin.ModelAdmin):
    list_display = ("nome", "email", "cargo", "unidade", "cidade", "estado")
    search_fields = ("nome", "email", "cargo", "cidade", "estado")
    list_filter = ("estado", "cidade", "cargo", "unidade")
    list_per_page = 25


# =====================
# Admin de Treinamento
# =====================
@admin.register(Treinamento)
class TreinamentoAdmin(ImportExportModelAdmin):
    form = TreinamentoAdminForm
    resource_class = TreinamentoResource
    actions = [
    'baixar_anexos_pdf',
    'marcar_concluido',
    'marcar_em_andamento',
    'marcar_pendente',
    'resetar_status'
    ]
    autocomplete_fields = ('colaboradores', 'participantes_externos',)


    list_display = (
        'titulo', 'get_display_local', 'data_inicio', 'data_fim', 'status_badge',
        'tipo', 'formato', 'criado_por', 'get_instrutores_display', 
        'get_analistas_display', 'quantidade_colaboradores', 'qtd_participantes_externos',
        'quantidade_treinados', 'carga_horaria_total', 'link_anexo_frequencia'
    )
    list_per_page = 10
    search_fields = (
        'titulo', 'local', 'criado_por__username', 'instrutores__user__username', 'analistas__user__username',
        'colaboradores__nome', 'colaboradores__matricula', 'participantes_externos__nome', 'participantes_externos__email'
    )
    list_filter = (
        'status', 'local', 'tipo', 'formato', ('data_inicio', DateRangeFilter), #'data_fim',
        'criado_por', 'instrutores__user', #'analistas__user'
    )
    inlines = [ColaboradoresInline, ParticipantesExternosInline, FrequenciaInline]
    autocomplete_fields = ('colaboradores',)
    readonly_fields = ('criado_por', 'preview_anexo_frequencia')
    filter_horizontal = ('instrutores', 'analistas')

    fieldsets = (
        (None, {
            'fields': ('titulo', 'tipo', 'formato', 'tipo_participante', 'carga_horaria', 'on_the_job', 'status', 'status_manual', 'criado_por', 'instrutores', 'analistas')
        }),
        ('Localização e Datas', {
            'fields': ('local', 'local_personalizado', 'data_inicio', 'data_fim'),
            'classes': ('collapse',),
        }),
        ('Seleção de Colaboradores', {
            'fields': ('matriculas_filter', 'matriculas_file', 'colaboradores'),
            'description': "Use os campos abaixo para buscar e adicionar colaboradores, ou selecione na lista."
        }),
        ('Participantes Externos', {
            'fields': ('participantes_externos',),
            'description': "Esses participantes são cadastrados via planilha XLSX no sistema ou diretamente aqui.",
        }),
        ('Frequência e Documentos', {
            'fields': ('anexo_frequencia', 'preview_anexo_frequencia'),
            'description': "Faça upload do PDF ou imagem com a frequência assinada."
        }),
        ('Observações Adicionais', {
            'fields': ('observacoes',),
            'classes': ('collapse',),
        }),
    )

    def get_fieldsets(self, request, obj=None):
        if obj is None:
            # CRIAÇÃO (SEM status)
            return (
                (None, {
                    'fields': (
                        'titulo', 'tipo', 'formato', 'tipo_participante',
                        'carga_horaria', 'on_the_job',
                        'criado_por', 'instrutores', 'analistas'
                    )
                }),
                ('Localização e Datas', {
                    'fields': ('local', 'local_personalizado', 'data_inicio', 'data_fim'),
                    'classes': ('collapse',),
                }),
                ('Seleção de Colaboradores', {
                    'fields': ('matriculas_filter', 'matriculas_file', 'colaboradores'),
                    'description': "Use os campos abaixo para buscar e adicionar colaboradores, ou selecione na lista."
                }),
                ('Participantes Externos', {
                    'fields': ('participantes_externos',),
                    'description': "Esses participantes são cadastrados via planilha XLSX no sistema ou diretamente aqui.",
                }),
                ('Frequência e Documentos', {
                    'fields': ('anexo_frequencia',),
                    'description': "Faça upload do PDF ou imagem com a frequência assinada."
                }),
                ('Observações Adicionais', {
                    'fields': ('observacoes',),
                    'classes': ('collapse',),
                }),
            )

        else:
            # 🔹 EDIÇÃO (COM status)
            return (
                (None, {
                    'fields': (
                        'titulo', 'tipo', 'formato', 'tipo_participante',
                        'carga_horaria', 'on_the_job',
                        'status', 'status_manual',
                        'criado_por', 'instrutores', 'analistas'
                    )
                }),
                ('Localização e Datas', {
                    'fields': ('local', 'local_personalizado', 'data_inicio', 'data_fim'),
                    'classes': ('collapse',),
                }),
                ('Seleção de Colaboradores', {
                    'fields': ('matriculas_filter', 'matriculas_file', 'colaboradores'),
                    'description': "Use os campos abaixo para buscar e adicionar colaboradores, ou selecione na lista."
                }),
                ('Participantes Externos', {
                    'fields': ('participantes_externos',),
                    'description': "Esses participantes são cadastrados via planilha XLSX no sistema ou diretamente aqui.",
                }),
                ('Frequência e Documentos', {
                    'fields': ('anexo_frequencia', 'preview_anexo_frequencia'),
                    'description': "Faça upload do PDF ou imagem com a frequência assinada."
                }),
                ('Observações Adicionais', {
                    'fields': ('observacoes',),
                    'classes': ('collapse',),
                }),
            )

    class Media:
        js = ('admin/js/treinamento_local_toggle.js',)

    #Link de visualização/download do anexo
    def link_anexo_frequencia(self, obj):
        if obj.anexo_frequencia:
            return format_html(
                "<a href='{}' target='_blank'>Ver Anexo</a>",
                obj.anexo_frequencia.url
            )
        return "-"
    link_anexo_frequencia.short_description = "Anexo Frequência"

    def qtd_participantes_externos(self, obj):
        try:
            return obj.participantes_externos.count()
        except Exception:
            return 0

    qtd_participantes_externos.short_description = "Qtd. Participantes Externos"

    def baixar_anexos_pdf(self, request, queryset):
        buffer = io.BytesIO()
        
        with zipfile.ZipFile(buffer, 'w') as zip_file:
            for treinamento in queryset:
                if treinamento.anexo_frequencia:
                    file_path = treinamento.anexo_frequencia.path
                    
                    if os.path.exists(file_path):
                        nome_arquivo = os.path.basename(file_path)

                        # Evita conflito de nomes
                        nome_zip = f"{treinamento.titulo}_{nome_arquivo}"
                        
                        zip_file.write(file_path, nome_zip)

        buffer.seek(0)

        response = HttpResponse(buffer, content_type='application/zip')
        response['Content-Disposition'] = 'attachment; filename=anexos_treinamentos.zip'

        return response

    baixar_anexos_pdf.short_description = "📥 Baixar todos os PDFs dos treinamentos selecionados"

    def status_badge(self, obj):
        cores = {
            'pendente': '#6c757d',
            'em_andamento': '#ffc107',
            'concluido': '#28a745',
        }
        cor = cores.get(obj.status, '#000')

        return format_html(
            '<span style="color: white; background-color: {}; padding: 4px 8px; border-radius: 6px;">{}</span>',
            cor,
            obj.get_status_display()
        )

    status_badge.short_description = "Status"

    @admin.action(description="Marcar como Concluído")
    def marcar_concluido(self, request, queryset):
        for obj in queryset:
            if obj.data_inicio and obj.data_fim:
                dias = (obj.data_fim - obj.data_inicio).days + 1

                for i in range(dias):
                    data = obj.data_inicio + timedelta(days=i)

                    # 🔹 COLABORADORES INTERNOS
                    for colaborador in obj.colaboradores.all():
                        Frequencia.objects.get_or_create(
                            treinamento=obj,
                            colaborador=colaborador,
                            data=data,
                            defaults={'presente': True}
                        )

                    # 🔹 PARTICIPANTES EXTERNOS (AQUI ESTÁ O QUE FALTAVA)
                    for externo in obj.participantes_externos.all():
                        Frequencia.objects.get_or_create(
                            treinamento=obj,
                            participante_externo=externo,
                            data=data,
                            defaults={'presente': True}
                        )

            # Atualiza status
            obj.status = 'concluido'
            obj.status_manual = True

            # Atualiza número de treinados (agora incluindo externos)
            obj.numero_treinados = obj.quantidade_treinados()

            obj.save()

    @admin.action(description="Marcar como Em Andamento")
    def marcar_em_andamento(self, request, queryset):
        queryset.update(status='em_andamento', status_manual=True)

    @admin.action(description="Marcar como Pendente")
    def marcar_pendente(self, request, queryset):
        queryset.update(status='pendente', status_manual=True)

    @admin.action(description="Voltar para Automático")
    def resetar_status(self, request, queryset):
        queryset.update(status_manual=False)


    #Campo de pré-visualização no admin
    def preview_anexo_frequencia(self, obj):
        if obj.anexo_frequencia:
            return format_html(
                """
                <a href="#" class="open-anexo" data-url="{}">Clique para abrir</a>
                <div id="modal-anexo" class="modal" style="display:none;">
                    <div class="modal-content">
                        <span class="close">&times;</span>
                        <iframe id="iframe-anexo" src="" width="100%" height="600px"></iframe>
                    </div>
                </div>
                <style>
                    .modal {{
                        position: fixed;
                        z-index: 1000;
                        left: 0;
                        top: 0;
                        width: 100%;
                        height: 100%;
                        overflow: auto;
                        background-color: rgba(0,0,0,0.5);
                    }}
                    .modal-content {{
                        background-color: #fefefe;
                        margin: 5% auto;
                        padding: 20px;
                        border: 1px solid #888;
                        width: 80%;
                        max-width: 900px;
                        position: relative;
                    }}
                    .close {{
                        color: #aaa;
                        position: absolute;
                        top: 10px;
                        right: 20px;
                        font-size: 28px;
                        font-weight: bold;
                        cursor: pointer;
                    }}
                    .close:hover {{
                        color: black;
                    }}
                </style>
                <script>
                    document.addEventListener("DOMContentLoaded", function() {{
                        var modal = document.getElementById("modal-anexo");
                        var iframe = document.getElementById("iframe-anexo");
                        var openBtn = document.querySelector(".open-anexo");
                        var closeBtn = document.querySelector(".close");

                        if(openBtn){{
                            openBtn.onclick = function(e) {{
                                e.preventDefault();
                                iframe.src = this.dataset.url;
                                modal.style.display = "block";
                            }};
                        }}

                        if(closeBtn){{
                            closeBtn.onclick = function() {{
                                modal.style.display = "none";
                                iframe.src = "";
                            }};
                        }}

                        window.onclick = function(event) {{
                            if (event.target == modal) {{
                                modal.style.display = "none";
                                iframe.src = "";
                            }}
                        }};
                    }});
                </script>
                """,
                obj.anexo_frequencia.url
            )
        return "Nenhum arquivo enviado"

    preview_anexo_frequencia.short_description = "Visualização do Anexo"

    # Métodos existentes mantidos:
    def get_display_local(self, obj):
        return obj.local_personalizado if obj.local == 'outro' else obj.get_local_display()
    get_display_local.short_description = "Local"
    get_display_local.admin_order_field = 'local'

    def get_instrutores_display(self, obj):
        instrutores = obj.instrutores.all()
        return ", ".join([str(i.user.get_full_name() or i.user.username) for i in instrutores]) or "-"
    get_instrutores_display.short_description = "Instrutores"

    def get_analistas_display(self, obj):
        analistas = obj.analistas.all()
        return ", ".join([str(a.user.get_full_name() or a.user.username) for a in analistas]) or "-"
    get_analistas_display.short_description = "Analistas"

    def _user_is_analista_ou_instrutor(self, user):
        if user.is_superuser:
            return True
        return AnalistaInstrutor.objects.filter(user=user, tipo__in=['analista', 'instrutor']).exists()

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        user = request.user
        if user.is_superuser:
            return qs
        analista_instrutor = AnalistaInstrutor.objects.filter(user=user).first()
        if not analista_instrutor:
            return qs.none()
        if analista_instrutor.tipo == 'analista':
            return qs.filter(analistas=analista_instrutor)
        elif analista_instrutor.tipo == 'instrutor':
            return qs.filter(instrutores=analista_instrutor)
        return qs.none()

    def has_view_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        analista_instrutor = AnalistaInstrutor.objects.filter(user=request.user).first()
        if not analista_instrutor:
            return False
        if obj:
            if analista_instrutor.tipo == 'analista':
                return obj.analistas.filter(pk=analista_instrutor.pk).exists()
            elif analista_instrutor.tipo == 'instrutor':
                return obj.instrutores.filter(pk=analista_instrutor.pk).exists()
            return False
        return True
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)

        # Força o campo carga_horaria a ser VISÍVEL apenas no Admin
        if 'carga_horaria' in form.base_fields:
            form.base_fields['carga_horaria'].widget = forms.TextInput(
                attrs={
                    'placeholder': 'HH:MM:SS',
                    'class': 'vTextField'
                }
            )

        return form

    def has_add_permission(self, request):
        return self._user_is_analista_ou_instrutor(request.user)

    def has_change_permission(self, request, obj=None):
        return self.has_view_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return self.has_view_permission(request, obj)

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.criado_por = request.user
        super().save_model(request, obj, form, change)

    def quantidade_colaboradores(self, obj):
        return obj.colaboradores.count()
    quantidade_colaboradores.short_description = "Nº Colaboradores"

    def percentual_curso(self, obj):
        return f"{obj.calcular_percentual_curso():.1f}%"
    percentual_curso.short_description = "Presença Média"

    def media_aderencia(self, obj):
        return f"{obj.calcular_media_aderencia():.1f}%"
    media_aderencia.short_description = "Aderência Média"

    def carga_horaria_total(self, obj):
        if obj.data_inicio and obj.data_fim and obj.carga_horaria:
            dias = (obj.data_fim - obj.data_inicio).days + 1
            total = dias * obj.carga_horaria
            return f"{total} h"
        return "-"
    carga_horaria_total.short_description = "Carga Horária Total"

    def quantidade_treinados(self, obj):
        if not obj.data_inicio or not obj.data_fim or not obj.carga_horaria:
            return 0

        dias_total = (obj.data_fim - obj.data_inicio).days + 1
        carga_total = obj.carga_horaria.total_seconds() * dias_total

        treinados = 0

        # 🔹 COLABORADORES INTERNOS
        for colaborador in obj.colaboradores.all():
            presencas = obj.frequencia_set.filter(
                colaborador=colaborador,
                presente=True
            ).count()

            carga_presenca = obj.carga_horaria.total_seconds() * presencas
            percentual = (carga_presenca / carga_total) * 100 if carga_total else 0

            if percentual >= 75:
                treinados += 1

        # 🔹 PARTICIPANTES EXTERNOS
        for externo in obj.participantes_externos.all():
            presencas = obj.frequencia_set.filter(
                participante_externo=externo,
                presente=True
            ).count()

            carga_presenca = obj.carga_horaria.total_seconds() * presencas
            percentual = (carga_presenca / carga_total) * 100 if carga_total else 0

            if percentual >= 75:
                treinados += 1

        return treinados
    quantidade_treinados.short_description = "Nº Treinados"


@admin.register(Frequencia)
class FrequenciaAdmin(admin.ModelAdmin):
    form = FrequenciaForm
    fields = ['colaborador', 'participante_externo', 'treinamento', 'data', 'presente', 'justificativa', 'anexo']
    autocomplete_fields = ['colaborador', 'participante_externo']
    list_display = ("nome_colaborador", "treinamento", "data", "presente", "justificativa", "link_anexo")
    search_fields = ("colaborador__nome", "treinamento__titulo")
    list_filter = ('treinamento', 'presente', ('data', DateRangeFilter))

    actions = ['alterar_data_frequencia']

    def nome_colaborador(self, obj):
        if obj.colaborador_id:
            return obj.colaborador.nome
        if obj.participante_externo_id:
            return obj.participante_externo.nome
        return "Sem participantes"
    nome_colaborador.short_description = "Colaborador"
    nome_colaborador.admin_order_field = 'colaborador__nome'

    def link_anexo(self, obj):
        if obj.anexo and hasattr(obj.anexo, 'url'):
            nome_arquivo = os.path.basename(obj.anexo.name)
            return format_html(
                '<a href="{}" target="_blank" title="{}">📎 {}</a>',
                obj.anexo.url,
                nome_arquivo,
                nome_arquivo if len(nome_arquivo) < 25 else nome_arquivo[:22] + '...'
            )
        return "—"
    link_anexo.short_description = "Anexo"

    def alterar_data_frequencia(self, request, queryset):
        """Ação para alterar a data das frequências selecionadas."""
        if 'aplicar' in request.POST:
            form = AlterarDataFrequenciaForm(request.POST)
            if form.is_valid():
                nova_data = form.cleaned_data['nova_data']
                total = queryset.update(data=nova_data)
                self.message_user(request, f"Data atualizada para {nova_data} em {total} registros.")
                return
        else:
            form = AlterarDataFrequenciaForm()

        return render(request, 'admin/alterar_data_frequencia.html', {
            'form': form,
            'queryset': queryset,
            'title': 'Alterar data das frequências selecionadas',
            'action_checkbox_name': admin.helpers.ACTION_CHECKBOX_NAME,
        })

    alterar_data_frequencia.short_description = "Alterar data das frequências selecionadas"


# =====================
# Admin de Colaborador
# =====================
@admin.register(Colaborador)
class ColaboradorAdmin(admin.ModelAdmin):
    form = ColaboradorAdminForm
    list_display = ('matricula', 'nome', 'empresa', 'vaga', 'status', 'admissao', 'servico')
    search_fields = ('nome', 'matricula')
    list_filter = ('empresa', 'servico', 'status', 'cargo')
    list_per_page = 25

    fieldsets = (
        ('Dados do Colaborador', {
            'fields': ('nome', 'matricula', 'admissao', 'status')
        }),
        ('Informações Corporativas', {
            'fields': ('empresa', 'vaga', 'cargo', 'servico', 'responsavel_direto', 'coord_atendimento')
        }),
    )


# =====================
# Admin de Servico
# =====================
@admin.register(Servico)
class ServicoAdmin(admin.ModelAdmin):
    search_fields = ('nome',)


# =====================
# View Customizada: Relatório de Colaborador no Admin
# =====================
@staff_member_required
def relatorio_colaborador_view(request):
    colaboradores = Colaborador.objects.all()
    colaborador_id = request.GET.get('colaborador_id')
    colaborador = None
    relatorio = []

    if colaborador_id:
        colaborador = get_object_or_404(Colaborador, id=colaborador_id)
        treinamentos = Treinamento.objects.filter(colaboradores=colaborador)

        for treinamento in treinamentos:
            total_dias = Frequencia.objects.filter(treinamento=treinamento).values('data').distinct().count()
            presencas = Frequencia.objects.filter(
                colaborador=colaborador,
                treinamento=treinamento,
                presente=True
            ).values('data').distinct().count()
            percentual = (presencas / total_dias * 100) if total_dias else 0

            instrutores = ", ".join(
                set([t.criado_por.get_full_name() or t.criado_por.username for t in Treinamento.objects.filter(id=treinamento.id)])
            )

            relatorio.append({
                'treinamento': treinamento.titulo,
                'data_inicio': treinamento.data_inicio,
                'data_fim': treinamento.data_fim,
                'instrutores': instrutores,
                'presenca': f"{percentual:.1f}%",
            })

    context = {
        "colaboradores": colaboradores,
        "colaborador": colaborador,
        "relatorio": relatorio,
        "title": "Relatório de Colaborador",
    }
    return render(request, "admin/relatorio_colaborador.html", context)
