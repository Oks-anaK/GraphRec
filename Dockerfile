FROM python:3.12-slim

# Базовые настройки Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Устанавливаем Poetry
# Во избежание несовместимости версий, укажем ее явно
RUN pip install --upgrade pip && pip install "poetry==1.8.3"

# Сначала копируем только файлы зависимостей (лучше кэш слоев)
COPY pyproject.toml poetry.lock ./

# Ставим зависимости в системный python (без venv)
# --no-root не пытается устанавливать сам проект как пакет (частая причина падения на Railway).
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --only main --no-root

# Копируем код проекта
COPY . .

# Порт Railway
ENV PORT=8000
EXPOSE 8000

# Важно: bind на 0.0.0.0 и порт из переменной PORT
CMD ["sh", "-c", "python manage.py migrate && python manage.py collectstatic --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:${PORT} --workers 3 --timeout 120"]