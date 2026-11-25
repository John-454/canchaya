# Backend canchaya. — imagen de producción
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings.prod \
    PORT=8000

WORKDIR /app

# psycopg[binary] no necesita compilador en runtime.
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && pip uninstall -y pytest pytest-django pytest-cov factory-boy black ruff

COPY . .

# Usuario sin privilegios.
RUN useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# `migrate` se ejecuta en el arranque (idempotente) salvo DESPLIEGUE_SIN_MIGRATE=1.
CMD ["sh", "-c", "if [ \"$DESPLIEGUE_SIN_MIGRATE\" != \"1\" ]; then python manage.py migrate --noinput; fi; python -m gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers ${GUNICORN_WORKERS:-3} --timeout 60 --access-logfile - --error-logfile -"]
