import json
import csv
import io
from datetime import date
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Avg, F, Count, Q, Case, When, IntegerField, Sum, ExpressionWrapper
from django.db.models import DurationField
from django.db import transaction
from django.http import JsonResponse, HttpResponse
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect, csrf_exempt
import re
from .forms import TreinamentoAdminForm, FrequenciaForm
from django.forms import modelform_factory
from django.forms.models import modelformset_factory

from .models import Avaliacao, Treinamento, Frequencia, ParticipanteExterno
from .forms import AvaliacaoForm, TreinamentoAdminForm
from core.models import Colaborador, AnalistaInstrutor
from django.utils.dateparse import parse_date
from django.utils.timezone import now
from django.utils.http import urlencode
from django.urls import reverse
from django.http import FileResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from datetime import timedelta
from django.db.models.functions import Coalesce
from datetime import datetime, timedelta, time
from django.utils import timezone
from django.core.paginator import Paginator
from .utils import add_workdays


@require_POST
@login_required
@csrf_protect
def atualizar_colaboradores_por_matriculas(request):
    entrada_raw = request.POST.get("matriculas", "")
    linhas = [linha.strip() for linha in entrada_raw.splitlines() if linha.strip()]

    colaboradores_encontrados = []

    for linha in linhas:
        if linha.isdigit():
            colaboradores_encontrados += list(
                Colaborador.objects.filter(matricula=linha)
            )
        else:
            colaboradores_encontrados += list(
                Colaborador.objects.filter(nome__icontains=linha)
            )

    colaboradores_unicos = list({c.id: c for c in colaboradores_encontrados}.values())

    html_options = render_to_string(
        "admin/partials/campo_colaboradores_options.html",
        {"colaboradores": colaboradores_unicos}
    )

    return JsonResponse({"html": html_options})


@login_required
def treinamento_detail(request, treinamento_id):
    treinamento = get_object_or_404(
        Treinamento.objects.prefetch_related('colaboradores', 'instrutores'),
        id=treinamento_id
    )

    # Verificação de permissão
    if not (
        request.user.is_superuser or
        request.user == treinamento.criado_por or
        treinamento.instrutores.filter(user=request.user).exists() or
        treinamento.analistas.filter(user=request.user).exists()
    ):
        messages.error(request, "Você não tem permissão para acessar este treinamento.")
        return redirect('dashboard')

    hoje = now().date()
    total_programados = treinamento.colaboradores.count()
    dias_totais = (treinamento.data_fim - treinamento.data_inicio).days + 1 if treinamento.data_inicio and treinamento.data_fim else 0

    # Cálculo da carga horária total formatada
    carga_horaria_total = "N/D"
    if treinamento.carga_horaria and dias_totais > 0:
        try:
            horas, minutos, segundos = map(int, str(treinamento.carga_horaria).split(':'))
            carga_diaria = timedelta(hours=horas, minutes=minutos, seconds=segundos)
            carga_total = carga_diaria * dias_totais
            carga_horaria_total = str(carga_total)
        except Exception as e:
            print(f"Erro ao calcular carga horária total: {e}")
            carga_horaria_total = "N/D"

    treinados = faltosos = aplicado_percent = absenteismo_percent = 0

    # Consolidar dados somente após a conclusão do treinamento
    consolidado = hoje >= treinamento.data_fim
    if consolidado and total_programados > 0:
        # Usa os métodos do model
        frequencia_geral = treinamento.obter_frequencia_geral()
        treinados = treinamento.quantidade_treinados()
        faltosos = frequencia_geral['absenteismo']
        
        aplicado_percent = (frequencia_geral['aplicado'] / total_programados) * 100
        absenteismo_percent = (faltosos / total_programados) * 100

    contexto = {
        'treinamento': treinamento,
        'programados': total_programados,
        'treinados': treinados,
        'faltosos': faltosos,
        'aplicado_percent': round(aplicado_percent, 2),
        'absenteismo_percent': round(absenteismo_percent, 2),
        'consolidado': consolidado,
        'carga_horaria_total': carga_horaria_total,
        'dias': dias_totais,
        'hoje': hoje
    }

    return render(request, 'core/treinamento_detail.html', contexto)

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import Treinamento

def calcular_status_automatico(treinamento):
    hoje = timezone.now().date()

    if treinamento.data_fim < hoje:
        if Frequencia.objects.filter(treinamento=treinamento, presente=True).exists():
            return "concluido"
        return "pendente"

    if treinamento.data_inicio <= hoje <= treinamento.data_fim:
        return "em_andamento"

    return "pendente"

@login_required
def treinamento_list(request):
    user = request.user

    # Base queryset por permissão
    if user.is_superuser:
        treinamentos = Treinamento.objects.all()
        is_admin = True
    else:
        ai = AnalistaInstrutor.objects.filter(user=user).first()
        is_admin = False
        if ai:
            if ai.tipo == 'analista':
                treinamentos = Treinamento.objects.filter(analistas=ai)
            elif ai.tipo == 'instrutor':
                treinamentos = Treinamento.objects.filter(instrutores=ai)
        else:
            treinamentos = Treinamento.objects.none()

    # --------------------
    # Filtros
    # --------------------
    status = request.GET.get('status')
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    instrutor_id = request.GET.get('instrutor')

    if is_admin and instrutor_id:
        treinamentos = treinamentos.filter(instrutores__id=instrutor_id)

    if data_inicio:
        treinamentos = treinamentos.filter(data_inicio__gte=data_inicio)

    if data_fim:
        treinamentos = treinamentos.filter(data_fim__lte=data_fim)

    # --------------------
    # Status calculado
    # --------------------
    hoje = date.today()

    for t in treinamentos:
        if not t.status_manual:
            if t.data_fim < hoje and t.frequencia_set.exists():
                t.status = 'concluido'
            elif t.data_inicio <= hoje <= t.data_fim:
                t.status = 'em_andamento'
            else:
                t.status = 'pendente'

    if status and status != 'todos':
        treinamentos = [t for t in treinamentos if t.status == status]

    # --------------------
    # Contadores (antes da paginação)
    # --------------------
    contadores = {
        'pendente': len([t for t in treinamentos if t.status == 'pendente']),
        'em_andamento': len([t for t in treinamentos if t.status == 'em_andamento']),
        'concluido': len([t for t in treinamentos if t.status == 'concluido']),
    }

    # --------------------
    # PAGINAÇÃO
    # --------------------
    paginator = Paginator(treinamentos, 10)  # 10 por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    instrutores = AnalistaInstrutor.objects.filter(tipo='instrutor') if is_admin else None

    context = {
        'treinamentos': page_obj,
        'page_obj': page_obj,
        'is_admin': is_admin,
        'instrutores': instrutores,
        'contadores': contadores,
    }

    return render(request, 'core/treinamento_list.html', context)


@login_required
def registrar_frequencia(request, treinamento_id):
    user = request.user

    treinamento = get_object_or_404(
        Treinamento.objects.prefetch_related(
            'colaboradores',
            'instrutores',
            'analistas',
            'participantes_externos'
        ),
        id=treinamento_id
    )

    # ===============================
    # PERMISSÃO
    # ===============================
    if not (
        user.is_superuser or
        treinamento.instrutores.filter(user=user).exists() or
        treinamento.analistas.filter(user=user).exists()
    ):
        messages.error(request, "Você não tem permissão para acessar este treinamento.")
        return redirect('treinamento_list')

    # ===============================
    # DATA DA FREQUÊNCIA
    # ===============================
    data_str = request.GET.get('data')
    data = parse_date(data_str) if data_str else date.today()

    if not data:
        messages.error(request, "Data da frequência inválida.")
        return redirect('treinamento_list')

    # ===============================
    # PRAZOS
    # ===============================
    prazo_limite_data = add_workdays(treinamento.data_inicio, 1)

    if data < treinamento.data_inicio and timezone.now().date() > prazo_limite_data:
        messages.error(
            request,
            "⚠️ O prazo para registrar a frequência retroativa já expirou."
        )
        return redirect('treinamento_list')

    agora = timezone.now()
    fim_prazo_data = add_workdays(treinamento.data_inicio, 1)
    prazo_final = timezone.make_aware(
        datetime.combine(fim_prazo_data, time(8, 0))
    ) + timedelta(hours=24)

    if agora > prazo_final:
        messages.error(
            request,
            "⚠️ O prazo para registrar a frequência desse treinamento já expirou."
        )
        return redirect('treinamento_list')

    # ===============================
    # CRIA REGISTROS AUTOMÁTICOS (GET)
    # ===============================
    if request.method == 'GET':
        for colaborador in treinamento.colaboradores.all():
            Frequencia.objects.get_or_create(
                colaborador=colaborador,
                treinamento=treinamento,
                data=data,
                defaults={'presente': True}
            )

    # ===============================
    # FORMSET (COLABORADORES)
    # ===============================
    frequencias = (
        Frequencia.objects
        .filter(treinamento=treinamento, data=data)
        .select_related('colaborador')
        .order_by('colaborador__nome')
    )

    FrequenciaFormSet = modelformset_factory(
        Frequencia,
        form=FrequenciaForm,
        extra=0,
        can_delete=False
    )

    # ===============================
    # POST
    # ===============================
    if request.method == 'POST':
        formset = FrequenciaFormSet(
            request.POST,
            request.FILES,
            queryset=frequencias,
            form_kwargs={
                'treinamento': treinamento,
                'data_param': data
            }
        )

        if formset.is_valid():
            formset.save()
            messages.success(request, "✅ Frequência salva com sucesso.")
            return redirect(
                f"{reverse('registrar_frequencia', args=[treinamento.id])}"
                f"?data={data.strftime('%Y-%m-%d')}"
            )
        else:
            messages.error(
                request,
                "⚠️ Corrija os erros nos campos de frequência."
            )

    # ===============================
    # GET
    # ===============================
    else:
        formset = FrequenciaFormSet(
            queryset=frequencias,
            form_kwargs={
                'treinamento': treinamento,
                'data_param': data
            }
        )

    # ===============================
    # RENDER
    # ===============================
    return render(
        request,
        'core/registrar_frequencia.html',
        {
            'treinamento': treinamento,
            'formset': formset,
            'data': data,
            'data_frequencia': data,
            'prazo_final_timestamp': int(prazo_final.timestamp() * 1000),
        }
    )

def calcular_status_dashboard(treinamento):
    hoje = timezone.now().date()
    if treinamento.data_inicio > hoje:
        return 'pendente'
    if treinamento.data_inicio <= hoje <= treinamento.data_fim:
        return 'em_andamento'
    return 'concluido'

# ========================================
# Função auxiliar para formatar HH:MM:SS
# ========================================
def format_hh_mm_ss(td):
    total_seconds = int(td.total_seconds())
    horas, resto = divmod(total_seconds, 3600)
    minutos, segundos = divmod(resto, 60)
    return f"{horas:02d}:{minutos:02d}:{segundos:02d}"

# DASHBOARD
@login_required
def dashboard_view(request):
    usuario = request.user

    nivel = (
        usuario.get_user_level_display()
        if hasattr(usuario, 'get_user_level_display')
        else 'usuário'
    )

    is_admin = usuario.is_superuser or (nivel and nivel.lower() == 'administrador')

    # ========================================
    # FILTROS
    # ========================================
    data_inicio_str = request.GET.get('data_inicio')
    data_fim_str = request.GET.get('data_fim')
    instrutor_id = request.GET.get('instrutor')

    inicio = parse_date(data_inicio_str) if data_inicio_str else None
    fim = parse_date(data_fim_str) if data_fim_str else None

    # ========================================
    # BASE DE TREINAMENTOS (SEM FILTRO AINDA)
    # ========================================
    if is_admin:
        treinamentos = Treinamento.objects.all()
    else:
        try:
            perfil = AnalistaInstrutor.objects.get(user=usuario)
            if perfil.tipo == 'instrutor':
                treinamentos = perfil.treinamentos_instrutor.all()
            else:
                treinamentos = Treinamento.objects.filter(criado_por=usuario)
        except AnalistaInstrutor.DoesNotExist:
            treinamentos = Treinamento.objects.none()

    # ========================================
    # APLICA FILTROS (CRÍTICO: ANTES DOS KPIs)
    # ========================================
    if inicio:
        treinamentos = treinamentos.filter(data_inicio__gte=inicio)

    if fim:
        treinamentos = treinamentos.filter(data_fim__lte=fim)

    if instrutor_id:
        treinamentos = treinamentos.filter(instrutores__id=instrutor_id)

    treinamentos = treinamentos.distinct()

    # ========================================
    # KPIs PRINCIPAIS
    # ========================================
    total_treinamentos = treinamentos.count()

    # STATUS
    contadores = {'pendente': 0, 'em_andamento': 0, 'concluido': 0}
    for t in treinamentos:
        contadores[calcular_status_dashboard(t)] += 1

    treinamentos_concluidos = contadores['concluido']

    labels_status = ['Pendente', 'Em andamento', 'Concluído']
    dados_status = [
        contadores['pendente'],
        contadores['em_andamento'],
        contadores['concluido'],
    ]

    # ========================================
    # PARTICIPAÇÕES (CORRIGIDO E PERFORMÁTICO)
    # ========================================
    participacoes_validas = Frequencia.objects.filter(
        treinamento__in=treinamentos
    ).values('treinamento', 'colaborador').annotate(
        total=Count('id'),
        presentes=Count('id', filter=Q(presente=True))
    ).filter(
        total__gt=0,
        presentes__gte=F('total') * 0.75
    ).values('colaborador').distinct().count()

    total_participacoes = Frequencia.objects.filter(
        treinamento__in=treinamentos,
        presente=True
    ).count()

    media_participacoes = (
        total_participacoes / participacoes_validas
        if participacoes_validas > 0 else 0
    )

    # PRODUTIVIDADE (APENAS USUÁRIO)
    produtividade_usuario = 0
    if not is_admin:
        produtividade_usuario = Frequencia.objects.filter(
            treinamento__in=treinamentos.filter(criado_por=usuario),
            presente=True
        ).count()

    # ========================================
    # CARGA HORÁRIA TOTAL (CONSISTENTE COM FILTRO)
    # ========================================
    carga_horaria_total_td = treinamentos.aggregate(
        total=Sum('carga_horaria')
    )['total'] or timedelta()

    carga_horaria_total = format_hh_mm_ss(carga_horaria_total_td)

    # ========================================
    # KPIs - PARTICIPANTES EXTERNOS (CORRIGIDO)
    # ========================================
    externos_qs = ParticipanteExterno.objects.filter(
        treinamentos__in=treinamentos
    ).distinct()

    total_externos = externos_qs.count()

    treinamentos_com_externos = treinamentos.filter(
        participantes_externos__isnull=False
    ).distinct().count()

    media_externos_por_treinamento = (
        total_externos / treinamentos_com_externos
        if treinamentos_com_externos > 0
        else 0
    )

    # ========================================
    # TOP INSTRUTORES (COM DISTINCT)
    # ========================================
    instrutores = AnalistaInstrutor.objects.filter(tipo='instrutor').select_related('user')

    instrutores_stats = instrutores.annotate(
        total_treinamentos=Count(
            'treinamentos_instrutor',
            filter=Q(treinamentos_instrutor__in=treinamentos),
            distinct=True
        )
    ).order_by('-total_treinamentos')[:5]

    instrutores_tabela = [
        (i.user.get_full_name() or i.user.username, i.total_treinamentos or 0)
        for i in instrutores_stats
    ]

    labels_instrutores = json.dumps([i for i, _ in instrutores_tabela])
    dados_instrutores = json.dumps([t for _, t in instrutores_tabela])

    # ========================================
    # SERVIÇOS (CORRIGIDO - SEM DUPLICAÇÃO)
    # ========================================
    servicos_qs = (
        Frequencia.objects
        .filter(treinamento__in=treinamentos, presente=True)
        .values('colaborador__servico__nome')
        .annotate(total=Count('colaborador', distinct=True))
        .order_by('-total')
    )

    servicos_tabela = [
        (item['colaborador__servico__nome'] or 'Não informado', item['total'])
        for item in servicos_qs
    ]

    labels_servico = json.dumps([s for s, _ in servicos_tabela])
    dados_servico = json.dumps([t for _, t in servicos_tabela])

    # ========================================
    # CONTEXTO
    # ========================================
    context = {
        'usuario': usuario,
        'nivel': nivel,

        'contadores': contadores,
        'labels_status': labels_status,
        'dados_status': dados_status,

        'total_treinamentos': total_treinamentos,
        'treinamentos_concluidos': treinamentos_concluidos,
        'participacoes_validas': participacoes_validas,
        'total_participacoes': total_participacoes,
        'media_participacoes': media_participacoes,
        'produtividade_usuario': produtividade_usuario,

        'carga_horaria_total': carga_horaria_total,

        'instrutores_tabela': instrutores_tabela,
        'instrutores': instrutores,
        'labels_instrutores': labels_instrutores,
        'dados_instrutores': dados_instrutores,

        'labels_servico': labels_servico,
        'dados_servico': dados_servico,
        'servicos_tabela': servicos_tabela,

        'instrutor_selecionado': instrutor_id,
        'data_inicio': data_inicio_str,
        'data_fim': data_fim_str,

        'total_externos': total_externos,
        'treinamentos_com_externos': treinamentos_com_externos,
        'media_externos_por_treinamento': round(media_externos_por_treinamento, 1),
    }

    return render(request, 'core/dashboard.html', context)


from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, get_object_or_404
from .models import Treinamento, Frequencia, Colaborador

@staff_member_required
def dashboard_frequencia(request):
    treinamentos = Treinamento.objects.prefetch_related('colaboradores').all()
    treinamento_id = request.GET.get('treinamento')
    nome_colaborador = request.GET.get('colaborador', '').strip()
    matricula_colaborador = request.GET.get('matricula', '').strip()

    colaboradores_qs = Colaborador.objects.prefetch_related('treinamentos').all()
    if nome_colaborador:
        colaboradores_qs = colaboradores_qs.filter(nome__icontains=nome_colaborador)
    if matricula_colaborador:
        colaboradores_qs = colaboradores_qs.filter(matricula__icontains=matricula_colaborador)

    frequencias = Frequencia.objects.select_related('colaborador', 'treinamento').all()
    colaboradores_dados = []

    if treinamento_id:
        treinamento = get_object_or_404(Treinamento, id=treinamento_id)
        total_dias = (treinamento.data_fim - treinamento.data_inicio).days + 1
        colaboradores_qs = colaboradores_qs.filter(treinamentos=treinamento)
        frequencias = frequencias.filter(treinamento=treinamento)

        for colaborador in colaboradores_qs:
            freq_colab = frequencias.filter(colaborador=colaborador)
            presencas = freq_colab.filter(presente=True).count()
            faltas_qs = freq_colab.filter(presente=False).order_by('data')
            faltas = [f.data.strftime("%d/%m/%Y") for f in faltas_qs]
            porcentagem_presenca = (presencas / total_dias) * 100 if total_dias else 0
            

            colaboradores_dados.append({
                'nome': colaborador.nome,
                'matricula': colaborador.matricula,
                'dias_presenca': presencas,
                'dias_falta': len(faltas),
                'porcentagem_presenca': round(porcentagem_presenca),
                'total_dias': total_dias,
                'faltas': faltas,
                'total_treinamentos': colaborador.treinamentos.count(),
                'treinamentos': [{
                    'titulo': treinamento.titulo,
                    'data_inicio': treinamento.data_inicio,
                    'data_fim': treinamento.data_fim,
                    'porcentagem_presenca': round(porcentagem_presenca),
                    'dias_presenca': presencas,
                    'dias_falta': len(faltas),
                    'faltas': faltas
                }]
            })

    else:
        for colaborador in colaboradores_qs:
            treinamentos_colab = colaborador.treinamentos.all()
            dados_treinamentos = []
            total_dias = presencas = 0
            faltas = []

            for treinamento in treinamentos_colab:
                dias_total = (treinamento.data_fim - treinamento.data_inicio).days + 1
                freq_treinamento = frequencias.filter(colaborador=colaborador, treinamento=treinamento)
                presencas_t = freq_treinamento.filter(presente=True).count()
                faltas_qs = freq_treinamento.filter(presente=False).order_by('data')
                faltas_t = [f.data.strftime("%d/%m/%Y") for f in faltas_qs]
                porcentagem_t = (presencas_t / dias_total) * 100 if dias_total else 0

                dados_treinamentos.append({
                    'titulo': treinamento.titulo,
                    'data_inicio': treinamento.data_inicio,
                    'data_fim': treinamento.data_fim,
                    'porcentagem_presenca': round(porcentagem_t),
                    'dias_presenca': presencas_t,
                    'dias_falta': len(faltas_t),
                    'faltas': faltas_t
                })

                total_dias += dias_total
                presencas += presencas_t
                faltas.extend(faltas_t)

            if total_dias > 0:
                porcentagem_presenca = (presencas / total_dias) * 100
                colaboradores_dados.append({
                    'nome': colaborador.nome,
                    'matricula': colaborador.matricula,
                    'dias_presenca': presencas,
                    'dias_falta': len(faltas),
                    'porcentagem_presenca': round(porcentagem_presenca),
                    'total_dias': total_dias,
                    'faltas': faltas,
                    'total_treinamentos': treinamentos_colab.count(),
                    'treinamentos': dados_treinamentos
                })

    chart_labels = [c['nome'] for c in colaboradores_dados]
    chart_data = [c['porcentagem_presenca'] for c in colaboradores_dados]

    return render(request, "admin/frequencia_dashboard.html", {
        "chart_data": {
            "labels": chart_labels,
            "data": chart_data,
        },
        "treinamentos": treinamentos,
        "treinamento_selecionado": int(treinamento_id) if treinamento_id else None,
        "colaboradores_dados": colaboradores_dados,
        "colaborador_nome": nome_colaborador,
        "matricula_colaborador": matricula_colaborador,
    })

@login_required
def avaliar_treinamento(request, treinamento_id):
    treinamento = get_object_or_404(Treinamento, id=treinamento_id)
    colaborador = get_object_or_404(Colaborador, user=request.user)

    if Avaliacao.objects.filter(treinamento=treinamento, colaborador=colaborador).exists():
        return render(request, 'avaliacao_ja_realizada.html')

    total_dias = (treinamento.data_fim - treinamento.data_inicio).days + 1
    presencas = Frequencia.objects.filter(
        colaborador=colaborador,
        treinamento=treinamento,
        presente=True
    ).count()

    percentual_presenca = (presencas / total_dias) * 100 if total_dias else 0

    if percentual_presenca < 75:
        return render(request, 'avaliacao_nao_permitida.html', {
            'percentual_presenca': round(percentual_presenca, 1),
            'treinamento': treinamento
        })

    if request.method == 'POST':
        form = AvaliacaoForm(request.POST)
        if form.is_valid():
            avaliacao = form.save(commit=False)
            avaliacao.treinamento = treinamento
            avaliacao.colaborador = colaborador
            avaliacao.save()
            return render(request, 'avaliacao_sucesso.html')
    else:
        form = AvaliacaoForm()

    return render(request, 'avaliar_treinamento.html', {
        'form': form,
        'treinamento': treinamento
    })


@staff_member_required
def dashboard_avaliacoes(request):
    cursos = Treinamento.objects.all()
    curso_id = request.GET.get('curso')
    labels = []
    media_geral = []

    for curso in cursos:
        avaliacoes = Avaliacao.objects.filter(treinamento=curso)
        if avaliacoes.exists():
            media = avaliacoes.aggregate(
                media=Avg(
                    (F('nota_infraestrutura') +
                     F('nota_material') +
                     F('nota_assunto') +
                     F('nota_didatica_analista')) / 4.0
                )
            )['media']
            labels.append(curso.titulo)
            media_geral.append(round(media, 2) if media else 0)

    comentarios_query = Avaliacao.objects.filter(
        comentarios__isnull=False
    ).exclude(
        comentarios=""
    ).order_by('-data_avaliacao')

    if curso_id:
        comentarios_query = comentarios_query.filter(treinamento_id=curso_id)

    ultimos_comentarios = comentarios_query[:5]

    return render(request, 'admin/dashboard_avaliacoes.html', {
        'chart_data': {
            'labels': labels,
            'data': media_geral
        },
        'ultimos_comentarios': ultimos_comentarios,
        'cursos': cursos,
        'curso_id': curso_id,
    })


@staff_member_required
def exportar_dashboard_excel(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="frequencia_detalhada_colaboradores.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Nome', 'Matrícula', 'Presença Geral (%)', 'Dias com Presença', 'Dias com Falta', 'Total de Dias',
        'Treinamento', 'Início', 'Fim', '% Presença', 'Presenças', 'Faltas', 'Datas de Faltas'
    ])

    colaboradores_dados = obter_dados_filtrados(request, return_data_only=True)

    for c in colaboradores_dados:
        for treinamento in c['treinamentos']:
            writer.writerow([
                c['nome'],
                c['matricula'],
                c['porcentagem_presenca'],
                c['dias_presenca'],
                c['dias_falta'],
                c['total_dias'],
                treinamento['titulo'],
                treinamento['data_inicio'].strftime('%d/%m/%Y'),
                treinamento['data_fim'].strftime('%d/%m/%Y'),
                treinamento['porcentagem_presenca'],
                treinamento['dias_presenca'],
                treinamento['dias_falta'],
                ", ".join(treinamento['faltas'])
            ])

    return response

@staff_member_required
def obter_dados_filtrados(request, return_data_only=False):
    treinamento_id = request.GET.get('treinamento')
    nome_colaborador = request.GET.get('colaborador', '').strip()
    matricula_colaborador = request.GET.get('matricula', '').strip()

    treinamentos = Treinamento.objects.prefetch_related('colaboradores').all()
    frequencias = Frequencia.objects.select_related('colaborador', 'treinamento')

    colaboradores = Colaborador.objects.all()
    if nome_colaborador:
        colaboradores = colaboradores.filter(nome__icontains=nome_colaborador)
    if matricula_colaborador:
        colaboradores = colaboradores.filter(matricula__icontains=matricula_colaborador)
    if treinamento_id and treinamento_id.isdigit():
        frequencias = frequencias.filter(treinamento_id=int(treinamento_id))

    colaboradores_dados = []

    for colaborador in colaboradores:
        frequencias_colab = frequencias.filter(colaborador=colaborador)
        treinamentos_participados = Treinamento.objects.filter(colaboradores=colaborador)

        info_treinamentos = []
        for t in treinamentos_participados:
            dias_total = (t.data_fim - t.data_inicio).days + 1
            presencas = frequencias_colab.filter(treinamento=t, presente=True).count()
            faltas_qs = frequencias_colab.filter(treinamento=t, presente=False).order_by('data')
            faltas = [f.data.strftime("%d/%m/%Y") for f in faltas_qs]
            presenca_percentual = round((presencas / dias_total) * 100, 2) if dias_total else 0

            info_treinamentos.append({
                'titulo': t.titulo,
                'data_inicio': t.data_inicio,
                'data_fim': t.data_fim,
                'porcentagem_presenca': presenca_percentual,
                'dias_presenca': presencas,
                'dias_falta': len(faltas),
                'total_dias': dias_total,
                'faltas': faltas
            })

        if info_treinamentos:
            total_presenca = sum(t['dias_presenca'] for t in info_treinamentos)
            total_falta = sum(t['dias_falta'] for t in info_treinamentos)
            total_dias = sum(t['total_dias'] for t in info_treinamentos)
            porcentagem_geral = round((total_presenca / total_dias) * 100, 2) if total_dias else 0

            colaboradores_dados.append({
                'nome': colaborador.nome,
                'matricula': colaborador.matricula,
                'dias_presenca': total_presenca,
                'dias_falta': total_falta,
                'total_dias': total_dias,
                'porcentagem_presenca': porcentagem_geral,
                'treinamentos': info_treinamentos
            })

    if return_data_only:
        return colaboradores_dados

    chart_labels = [c['nome'] for c in colaboradores_dados]
    chart_data = [c['porcentagem_presenca'] for c in colaboradores_dados]

    return render(request, "admin/frequencia_dashboard.html", {
        "chart_data": {
            "labels": chart_labels,
            "data": chart_data,
        },
        "treinamentos": treinamentos,
        "treinamento_selecionado": int(treinamento_id) if treinamento_id else None,
        "colaboradores_dados": colaboradores_dados,
    })

@staff_member_required
def exportar_dashboard_pdf(request):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 50

    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, y, "Relatório de Frequência Detalhado")
    y -= 30

    p.setFont("Helvetica", 10)

    colaboradores_dados = obter_dados_filtrados(request, return_data_only=True)

    for c in colaboradores_dados:
        if y < 100:
            p.showPage()
            y = height - 50
            p.setFont("Helvetica", 10)

        p.drawString(50, y, f"Nome: {c['nome']} | Matrícula: {c['matricula']} | Presença Geral: {c['porcentagem_presenca']}%")
        y -= 15
        p.drawString(60, y, f"Dias com Presença: {c['dias_presenca']} | Faltas: {c['dias_falta']} | Total de Dias: {c['total_dias']}")
        y -= 20

        for treinamento in c['treinamentos']:
            if y < 100:
                p.showPage()
                y = height - 50
                p.setFont("Helvetica", 10)

            p.drawString(70, y, f"- {treinamento['titulo']} ({treinamento['data_inicio'].strftime('%d/%m/%Y')} a {treinamento['data_fim'].strftime('%d/%m/%Y')})")
            y -= 15
            p.drawString(80, y, f"Presença: {treinamento['porcentagem_presenca']}% ({treinamento['dias_presenca']} dias) | Faltas: {treinamento['dias_falta']}")
            y -= 15
            p.drawString(80, y, f"Datas de Faltas: {', '.join(treinamento['faltas']) if treinamento['faltas'] else 'Nenhuma'}")
            y -= 20

        y -= 10

    p.showPage()
    p.save()
    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename='relatorio_frequencia_detalhado.pdf')

@login_required
@staff_member_required
def relatorio_por_colaborador(request):
    query = request.GET.get('query', '').strip()
    query = re.sub(r'\s+', ' ', query)  # remove espaços duplicados

    colaboradores = Colaborador.objects.none()
    colaborador = None
    relatorio = []
    total_treinamentos = 0

    # Filtro por nome ou matrícula
    if query:
        colaboradores = Colaborador.objects.filter(
            Q(nome__icontains=query) | Q(matricula__icontains=query)
        ).order_by('nome')

    colaborador_id = request.GET.get('colaborador_id')
    if colaborador_id:
        colaborador = get_object_or_404(Colaborador, id=colaborador_id)

        treinamentos = Treinamento.objects.filter(
            colaboradores=colaborador
        ).prefetch_related('instrutores').annotate(
            total_aulas=Count('frequencia__data', distinct=True),
            presencas=Count(Case(
                When(frequencia__colaborador=colaborador, frequencia__presente=True, then=1),
                output_field=IntegerField()
            ))
        ).order_by('-data_inicio')

        for treinamento in treinamentos:
            total_dias = (treinamento.data_fim - treinamento.data_inicio).days + 1
            carga_total = (treinamento.carga_horaria or 0) * total_dias

            instrutores = ", ".join([
                instrutor.user.get_full_name() or instrutor.user.username
                for instrutor in treinamento.instrutores.all()
            ])

            presenca_percentual = (
                f"{(treinamento.presencas / treinamento.total_aulas * 100):.0f}%"
                if treinamento.total_aulas > 0 else "N/A"
            )

            relatorio.append({
                'treinamento': treinamento.titulo,
                'data_inicio': treinamento.data_inicio,
                'data_fim': treinamento.data_fim,
                'instrutores': instrutores,
                'presenca': presenca_percentual,
                'carga_horaria_total': carga_total
            })

        total_treinamentos = treinamentos.count()

    context = {
        'query': query,
        'colaboradores': colaboradores,
        'colaborador': colaborador,
        'relatorio': relatorio,
        'total_treinamentos': total_treinamentos
    }

    return render(request, 'admin/relatorio_por_colaborador.html', context)


@login_required
@transaction.atomic
def treinamento_create(request):
    if request.method == 'POST':
        form = TreinamentoAdminForm(
            request.POST,
            request.FILES,
            user=request.user
        )

        if form.is_valid():
            form.save()
            messages.success(
                request,
                'Treinamento criado com sucesso.'
            )

            return redirect('treinamento_list')
        else:
            messages.error(
                request,
                'Erro ao criar treinamento. Verifique os campos.'
            )

    else:
        form = TreinamentoAdminForm(user=request.user)

    return render(
        request,
        'core/treinamento_form.html',
        {'form': form}
    )