"""Settings for the F.F Manufacturer website. Secrets come from environment variables."""
import os
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured

from .dburl import parse_database_url

BASE_DIR = Path(__file__).resolve().parent.parent


def env(name, default=""):
    return os.environ.get(name, default)


IS_VERCEL = bool(env("VERCEL"))
# Debug is OFF by default on Vercel; locally it is on unless DJANGO_DEBUG=0.
DEBUG = env("DJANGO_DEBUG", "0" if IS_VERCEL else "1") == "1"
TRUST_PROXY_HEADERS = IS_VERCEL or env("TRUST_PROXY_HEADERS") == "1"

_DEV_KEY = "dev-only-insecure-key-change-me"
SECRET_KEY = env("DJANGO_SECRET_KEY", _DEV_KEY)
if not DEBUG and (SECRET_KEY == _DEV_KEY or len(SECRET_KEY) < 40):
    raise ImproperlyConfigured("Set DJANGO_SECRET_KEY to a long random string (40+ characters) when DEBUG is off.")

ALLOWED_HOSTS = [h.strip() for h in env("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()]
CSRF_TRUSTED_ORIGINS = [o.strip() for o in env("DJANGO_CSRF_TRUSTED_ORIGINS").split(",") if o.strip()]
# Vercel provides the deployment hostnames; trust exactly those (no wildcard).
for _name in ("VERCEL_URL", "VERCEL_BRANCH_URL", "VERCEL_PROJECT_PRODUCTION_URL"):
    _host = env(_name)
    if _host:
        ALLOWED_HOSTS.append(_host)
        CSRF_TRUSTED_ORIGINS.append(f"https://{_host}")

# Admin lives at a configurable path. Set DJANGO_ADMIN_URL to something private, e.g. "ff-office-7k2/".
ADMIN_URL = env("DJANGO_ADMIN_URL", "admin/").strip("/") + "/"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sitemaps",
    "django.contrib.humanize",
    "core",
    "accounts",
    "store",
    "orders",
    "dashboard",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "core.security.SecurityMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

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
                "core.context_processors.site",
            ],
        },
    },
]

# Database: DATABASE_URL (Vercel Postgres / Neon / Supabase) > DB_* variables > local SQLite.
if env("DATABASE_URL"):
    _db = parse_database_url(env("DATABASE_URL"))
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            **_db,
            "CONN_MAX_AGE": 0,  # serverless: do not hold connections open
            "DISABLE_SERVER_SIDE_CURSORS": True,  # needed behind a transaction pooler
            "OPTIONS": {"sslmode": env("DB_SSLMODE", "require")},
        }
    }
elif env("DB_ENGINE") == "postgres":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env("DB_NAME", "ffmanufacturer"),
            "USER": env("DB_USER", "postgres"),
            "PASSWORD": env("DB_PASSWORD"),
            "HOST": env("DB_HOST", "localhost"),
            "PORT": env("DB_PORT", "5432"),
        }
    }
else:
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}

AUTH_USER_MODEL = "accounts.User"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "accounts:dashboard"
LOGOUT_REDIRECT_URL = "core:home"

LANGUAGE_CODE = "en-in"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"  # Vercel runs collectstatic and serves these from its CDN
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
        if DEBUG
        else "whitenoise.storage.CompressedManifestStaticFilesStorage"
    },
}
# Uploaded photos: Vercel has no persistent disk, so use S3-compatible storage (AWS S3, Cloudflare R2,
# Supabase Storage, Backblaze B2...) whenever a bucket is configured.
if env("AWS_STORAGE_BUCKET_NAME"):
    STORAGES["default"] = {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "bucket_name": env("AWS_STORAGE_BUCKET_NAME"),
            "access_key": env("AWS_ACCESS_KEY_ID"),
            "secret_key": env("AWS_SECRET_ACCESS_KEY"),
            "endpoint_url": env("AWS_S3_ENDPOINT_URL") or None,
            "region_name": env("AWS_S3_REGION_NAME") or None,
            "custom_domain": env("AWS_S3_CUSTOM_DOMAIN") or None,  # public CDN domain for the bucket
            "querystring_auth": False,
            "default_acl": None,
            "file_overwrite": False,
        },
    }
elif IS_VERCEL:
    raise ImproperlyConfigured("Set AWS_STORAGE_BUCKET_NAME (and keys): Vercel cannot store uploaded images on disk.")

# Cache is shared across serverless instances through the database (run: manage.py createcachetable).
CACHES = {"default": {"BACKEND": "django.core.cache.backends.db.DatabaseCache", "LOCATION": "django_cache"}} if env("DATABASE_URL") else {
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 8 * 1024 * 1024

# Email: prints to the console until SMTP details are set.
if env("EMAIL_HOST"):
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = env("EMAIL_HOST")
    EMAIL_PORT = int(env("EMAIL_PORT", "587"))
    EMAIL_HOST_USER = env("EMAIL_HOST_USER")
    EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD")
    EMAIL_USE_TLS = True
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", "F.F Manufacturer <orders@ffmanufacturer.example>")

# Razorpay (https://dashboard.razorpay.com). Leave blank to run in demo-payment mode (DEBUG only).
RAZORPAY_KEY_ID = env("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = env("RAZORPAY_KEY_SECRET")
RAZORPAY_WEBHOOK_SECRET = env("RAZORPAY_WEBHOOK_SECRET")

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_AGE = 60 * 60 * 24 * 14
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "loggers": {"django.security": {"handlers": ["console"], "level": "WARNING"}, "django.request": {"handlers": ["console"], "level": "WARNING"}},
}

if not DEBUG:
    SECURE_SSL_REDIRECT = env("DJANGO_SSL_REDIRECT", "1") == "1"
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_HSTS_PRELOAD = False  # turn on only after you are sure every subdomain is HTTPS

# Analytics: set GA_MEASUREMENT_ID (e.g. G-XXXXXXXXXX) to enable Google Analytics 4.
# It only loads after a visitor accepts the cookie banner.
GA_MEASUREMENT_ID = env("GA_MEASUREMENT_ID")
