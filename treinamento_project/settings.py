
import os
from pathlib import Path

from dotenv import load_dotenv
from django.core.exceptions import ImproperlyConfigured

# CAMINHOS E VARIÁVEIS DE AMBIENTE
BASE_DIR = Path(__file__).resolve().parent.parent

# Carrega o .env local, caso exista.
# Em produção, as variáveis também podem ser configuradas
# diretamente no ambiente do servidor.
load_dotenv(BASE_DIR / ".env")

# SEGURANÇA E AMBIENTE
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY")

if not SECRET_KEY:
    raise ImproperlyConfigured(
        "Configure a variável DJANGO_SECRET_KEY."
    )

DEBUG = os.getenv("DJANGO_DEBUG", "False").strip().lower() in (
    "true", "1", "yes", "sim"
)

ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv(
        "DJANGO_ALLOWED_HOSTS",
        "localhost,127.0.0.1"
    ).split(",")
    if host.strip()
]

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "DJANGO_CSRF_TRUSTED_ORIGINS", ""
    ).split(",")
    if origin.strip()
]


# APLICAÇÕES
INSTALLED_APPS = [
    "admin_interface",
    "colorfield",
    "core",
    "usuarios",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_extensions",
    "rangefilter",
    "import_export",
    "widget_tweaks",
]

# MIDDLEWARE
MIDDLEWARE = [
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "treinamento_project.urls"

# TEMPLATES
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "treinamento_project.wsgi.application"

# BANCO DE DADOS MYSQL
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.getenv("DB_NAME", ""),
        "USER": os.getenv("DB_USER", ""),
        "PASSWORD": os.getenv("DB_PASSWORD", ""),
        "HOST": os.getenv("DB_HOST", "127.0.0.1"),
        "PORT": os.getenv("DB_PORT", "3306"),
        "OPTIONS": {
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
            "charset": "utf8mb4",
        },
    }
}

# USUÁRIO PERSONALIZADO
AUTH_USER_MODEL = "usuarios.Usuario"

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "MinimumLengthValidator"
        ),
    },
]

# IDIOMA E FUSO HORÁRIO
LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

# ARQUIVOS ESTÁTICOS E UPLOADS
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DATA_UPLOAD_MAX_NUMBER_FIELDS = 5000

# LOGIN
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "treinamento_list"

# E-MAIL
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
# SEGURANÇA HTTP
X_FRAME_OPTIONS = "DENY"

# Ative estas proteções quando a aplicação estiver servida
# por HTTPS corretamente configurado.
SECURE_SSL_REDIRECT = (
    os.getenv("DJANGO_SECURE_SSL_REDIRECT", "False").lower()
    in ("true", "1", "yes", "sim")
)

SESSION_COOKIE_SECURE = (
    os.getenv("DJANGO_SESSION_COOKIE_SECURE", "False").lower()
    in ("true", "1", "yes", "sim")
)

CSRF_COOKIE_SECURE = (
    os.getenv("DJANGO_CSRF_COOKIE_SECURE", "False").lower()
    in ("true", "1", "yes", "sim")
)

SECURE_HSTS_SECONDS = int(
    os.getenv("DJANGO_SECURE_HSTS_SECONDS", "0")
)

SECURE_HSTS_INCLUDE_SUBDOMAINS = (
    os.getenv("DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS", "False")
    .lower() in ("true", "1", "yes", "sim")
)

SECURE_HSTS_PRELOAD = (
    os.getenv("DJANGO_SECURE_HSTS_PRELOAD", "False")
    .lower() in ("true", "1", "yes", "sim")
)

# SESSÃO
SESSION_COOKIE_AGE = 60 * 30
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = True


# CAMPOS PADRÃO
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"