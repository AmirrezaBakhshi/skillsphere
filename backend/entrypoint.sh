#!/bin/sh
set -e

echo "Waiting for postgres..."
until python3 -c "
import os, sys, psycopg2
psycopg2.connect(os.environ['DATABASE_URL'].replace('postgres://', 'postgresql://'))
" 2>/dev/null; do
  sleep 1
done
echo "Postgres is up."

python3 manage.py migrate --noinput

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

exec python3 manage.py runserver 0.0.0.0:8000
