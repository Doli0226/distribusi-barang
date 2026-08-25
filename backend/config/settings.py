import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-change-me")
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = ["*"]
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

INSTALLED_APPS = [
    "django.contrib.admin", "django.contrib.auth", "django.contrib.contenttypes",
    "django.contrib.sessions", "django.contrib.messages", "django.contrib.staticfiles",
    "corsheaders", "distribution",
]
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware", "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware", "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware", "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]
TEMPLATES = [{"BACKEND": "django.template.backends.django.DjangoTemplates", "DIRS": [], "APP_DIRS": True,
              "OPTIONS": {"context_processors": ["django.template.context_processors.request", "django.contrib.auth.context_processors.auth", "django.contrib.messages.context_processors.messages"]}}]
DB_ENGINE = os.environ.get("DB_ENGINE", "django.db.backends.sqlite3")
DATABASES = {"default": {"ENGINE": DB_ENGINE, "NAME": os.environ.get("DB_NAME", str(BASE_DIR / "distribution.sqlite3"))}}
if DB_ENGINE.endswith("mysql"):
    DATABASES["default"].update({"USER": os.environ["DB_USER"], "PASSWORD": os.environ["DB_PASSWORD"], "HOST": os.environ["DB_HOST"], "PORT": os.environ.get("DB_PORT", "3306")})
LANGUAGE_CODE = "id"
TIME_ZONE = "Asia/Jakarta"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
FRONTEND_URL = os.environ.get("FRONTEND_URL", "")
CORS_ALLOW_ALL_ORIGINS = not FRONTEND_URL
CORS_ALLOW_CREDENTIALS = True
if FRONTEND_URL:
    CORS_ALLOWED_ORIGINS = [FRONTEND_URL]
    CORS_ALLOWED_ORIGIN_REGEXES = [r"^https://.*\.preview\.emergentagent\.com$"]
else:
    CORS_ALLOWED_ORIGIN_REGEXES = [r"^https?://.*$"]
    CORS_ALLOW_ALL_ORIGINS = False
CSRF_TRUSTED_ORIGINS = ["https://*.preview.emergentagent.com", "http://localhost:3000"]
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "None"
SESSION_COOKIE_SECURE = True
LOGIN_URL = "/api/auth/login"