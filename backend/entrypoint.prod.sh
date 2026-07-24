#!/bin/sh
set -e

echo "Waiting for postgres..."
until python3 -c "
import os, psycopg2
psycopg2.connect(os.environ['DATABASE_URL'].replace('postgres://', 'postgresql://'))
" 2>/dev/null; do
  sleep 1
done
echo "Postgres is up."

python3 manage.py migrate --noinput
python3 manage.py collectstatic --noinput

if [ "$DJANGO_SUPERUSER_EMAIL" ]; then
  python3 manage.py shell -c "
from apps.users.infrastructure.django.models import User
if not User.objects.filter(email='$DJANGO_SUPERUSER_EMAIL').exists():
    User.objects.create_superuser(
        email='$DJANGO_SUPERUSER_EMAIL',
        username='$DJANGO_SUPERUSER_USERNAME',
        password='$DJANGO_SUPERUSER_PASSWORD',
    )
"
fi

# Daphne (an ASGI server), not Gunicorn: Gunicorn's default worker only
# speaks WSGI (plain request/response) and can't handle a WebSocket
# upgrade at all. Since Stage 5 added real-time chat over Channels, the
# production server has to speak ASGI end to end - Daphne is the
# reference ASGI server, maintained by the Channels project itself.
exec daphne -b 0.0.0.0 -p 8000 config.asgi:application
