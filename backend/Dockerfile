FROM python:3.13-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1
WORKDIR /app
# psycopg2-binary ships its own libpq, so no compiler or system libraries are needed.
COPY requirements.txt ./
RUN pip install -r requirements.txt

# Development: adds test tooling; docker-compose.yaml bind-mounts the code.
FROM base AS development
COPY requirements-dev.txt ./
RUN pip install -r requirements-dev.txt
COPY . .
EXPOSE 8000

# Production: gunicorn, static files collected (served by WhiteNoise), non-root.
FROM base AS production
COPY . .
RUN DJANGO_SECRET_KEY=build-only DATABASE_URL=postgres://build@localhost/build \
    python manage.py collectstatic --noinput
RUN useradd --create-home --uid 10001 app && mkdir -p /app/media && chown app /app/media
USER app
EXPOSE 8000
CMD ["gunicorn", "nettle_core.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "60", "--access-logfile", "-"]
