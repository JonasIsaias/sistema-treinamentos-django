from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    # URL para o painel de administração do Django
    path('admin/', admin.site.urls),

    # Inclusão das URLs da aplicação 'core'
    path('', include('core.urls')),  # Rota principal para a aplicação core

    # Inclusão das URLs da aplicação 'usuarios'
    path('usuarios/', include('usuarios.urls')),  # Rota para gerenciamento de usuários
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)