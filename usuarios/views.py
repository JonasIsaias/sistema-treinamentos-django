from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.shortcuts import render, redirect
from django.contrib import messages

def login_view(request):
    if request.user.is_authenticated:
        return redirect('treinamento_list')  # Redireciona se o usuário já estiver autenticado

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Bem-vindo, {user.username}!')
            return redirect('treinamento_list')  # Redireciona após login
        else:
            messages.error(request, 'Credenciais inválidas. Tente novamente.')  # Mensagem de erro para falha no login

    else:
        form = AuthenticationForm()

    return render(request, 'usuarios/login.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.success(request, 'Você saiu com sucesso.')  # Mensagem de sucesso após logout
    return redirect('login')

def register_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)

            nome_usuario = user.get_full_name() or user.username
            messages.success(request, f'Conta criada com sucesso! Bem-vindo, {nome_usuario}.')
            return redirect('treinamento_list')
        else:
            messages.error(request, 'Erro ao criar a conta. Verifique os dados fornecidos.')
    else:
        form = UserCreationForm()

    return render(request, 'usuarios/register.html', {'form': form})


