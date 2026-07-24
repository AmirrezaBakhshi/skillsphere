"""
Production overrides. Loaded via DJANGO_SETTINGS_MODULE=config.settings.prod
(set in docker-compose.prod.yml). Everything here assumes it's sitting
behind Nginx doing TLS termination - see nginx/conf.d/skillsphere.conf.
"""
from .base import *  # noqa: F401,F403
from .base import env

DEBUG = False

# In production this MUST be your real domain(s) - the insecure "*"
# default from dev.py is never used here. No fallback default is given
# on purpose: a missing DJANGO_ALLOWED_HOSTS should fail loudly at
# startup, not silently accept requests for any Host header.
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS")

# --- Security headers & cookies ---
# Nginx terminates TLS and forwards plain HTTP to Django on the internal
# docker network, setting this header so Django knows the *original*
# request was HTTPS (see nginx/conf.d/skillsphere.conf's
# proxy_set_header X-Forwarded-Proto).
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = env.int("DJANGO_HSTS_SECONDS", default=60 * 60 * 24 * 30)  # 30 days
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

# The JWT refresh cookie (Stage 1) already sets secure=not settings.DEBUG,
# so it automatically becomes Secure here without any change needed.

# --- Static & media files ---
# WhiteNoise serves static files (admin CSS/JS, DRF browsable API assets)
# directly from Django/Gunicorn - simple and fine at this scale. Media
# (user-uploaded project files) stays on a shared volume that Nginx also
# reads directly for efficient serving - see the nginx config's
# `location /media/` block, which bypasses Django/Gunicorn entirely for
# actually serving the file bytes.
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# --- CORS ---
# No wildcard, no default - production CORS origins must be explicit.
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS")

# --- Logging ---
# Plain structured-ish console logging - a real deployment would ship
# these to an aggregator (e.g. via the Docker logging driver), which is
# an infrastructure concern outside Django itself.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} {name}: {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "verbose"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django.request": {"handlers": ["console"], "level": "ERROR", "propagate": False},
    },
}
