import os
from django.core.wsgi import get_wsgi_application

# Define a variável de ambiente para o arquivo de configurações do Django
# Usado para o ambiente de produção e implementação
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'treinamento_project.settings')

# Obtém a aplicação WSGI para servir o Django
application = get_wsgi_application()

# Garantia de que a aplicação esteja pronta para servir em produção
# Adicionar configuracao de logging ou middlewares específicos, se necessário.
