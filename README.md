# Система рекомендаций на графах (GraphRec)

Веб-сервис на **Django** и **Django REST Framework**: граф предпочтений (NetworkX), алгоритмы PageRank, коллаборативная фильтрация и k-NN, гибридные рекомендации, кэш в **Redis**. Есть **веб-интерфейс** на HTML и **Bootstrap 5** (предпочтения, рекомендации, статистика) и **REST API** под `/api/`.

## Демо-ссылка

- Railway (production): <https://graphrec-production.up.railway.app>
- API base: <https://graphrec-production.up.railway.app/api/>
- Документация API (Browsable API DRF): <https://graphrec-production.up.railway.app/api/>
- Swagger/OpenAPI: пока не подключены

---

## Стек

- Python 3.12+
- Django 6
- Django REST Framework
- PostgreSQL
- Redis (кэш рекомендаций)
- NetworkX, NumPy, scikit-learn
- Gunicorn
- Docker + Railway (production deploy)

---

## Документация

### О чём эта инструкция

| Сценарий | Что описано ниже |
|----------|------------------|
| **Локально (ПК)** | Основной сценарий: клонирование, зависимости, `.env`, Redis (и при необходимости PostgreSQL), миграции, `runserver`, веб-интерфейс, API и админка. |
| **Сервер (продакшен)** | Деплой на Railway из этого README: `Dockerfile`, переменные окружения, `DEBUG=0`, свой `SECRET_KEY`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, PostgreSQL/Redis. |

Инструкция в README рассчитана прежде всего на **локальный запуск** для разработки и тестов; на сервере те же команды выполняются в виртуальном окружении на машине или в CI/CD пайплайне.

---

## Требования

- **Python** 3.12–3.13 (см. `pyproject.toml`). В задании допускается Python 3.11+; **Django 6** в проекте требует **не ниже 3.12**.
- **Poetry** (рекомендуется) или pip
- **Redis** — для кэша рекомендаций (локально: служба Redis или установка с redis.io)
- **БД:** **PostgreSQL** — целевое хранилище по ТЗ; в `settings` оно включается, если в окружении задан **`DB_NAME`** (драйвер **psycopg** в зависимостях). Если `DB_NAME` не задан, для быстрой разработки используется **SQLite** (`db.sqlite3`).

---

## Как запустить локально

1. **Клонировать репозиторий**

   ```bash
   git clone <url-репозитория>
   cd <каталог-репозитория>
   ```

2. **Установить зависимости**

   ```bash
   pip install poetry
   poetry install
   ```

   Для проверки стиля кода (Black, isort, flake8) установите группу **lint**:

   ```bash
   poetry install --with lint
   ```

3. **Переменные окружения**

   Скопируйте пример и подставьте значения:

   ```bash
   copy .env.example .env
   ```

   Минимум для локальной работы:

   | Переменная | Назначение |
   |------------|------------|
   | `SECRET_KEY` | Секрет Django (для разработки можно сгенерировать случайную строку) |
   | `DEBUG` | `1` — режим отладки |
   | `ALLOWED_HOSTS` | `localhost,127.0.0.1` |
   | `LOCATION` | URL Redis, например `redis://127.0.0.1:6379/1` |
   | `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | **PostgreSQL** (опционально): если задан **`DB_NAME`**, Django подключается к PostgreSQL; иначе — SQLite |

4. **Запустить Redis** (служба должна слушать тот же хост/порт, что в `LOCATION`). При недоступности Redis операции кэша рекомендаций могут завершаться ошибкой; перед запуском приложения и тестов убедитесь, что сервис отвечает по указанному адресу.

5. **PostgreSQL (по ТЗ):** создайте БД и пользователя, пропишите переменные в `.env`, затем выполните миграции. Без PostgreSQL можно работать с SQLite, указав только `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `LOCATION`.

6. **Миграции и суперпользователь (опционально)**

   ```bash
   poetry run python manage.py migrate
   poetry run python manage.py createsuperuser
   ```

7. **Запуск сервера разработки**

   ```bash
   poetry run python manage.py runserver
   ```

   - **Веб-интерфейс (Bootstrap):** <http://127.0.0.1:8000/> — главная; разделы «Предпочтения», «Рекомендации», «Статистика» в шапке.
   - Админка: <http://127.0.0.1:8000/admin/>
   - API: префикс **`/api/`** (см. ниже)

---

## Архитектура

### Основные модули

- `config/` - настройки Django, роутинг, WSGI/ASGI
- `recommendations/models.py` - пользователи, элементы каталога, взаимодействия
- `recommendations/services/` - алгоритмы рекомендаций (hybrid, pagerank, collaborative, knn)
- `recommendations/web_views.py` - HTML-интерфейс
- `recommendations/views.py` и `serializers.py` - REST API
- `recommendations/management/commands/seed_demo.py` - загрузка шаблонных демо-данных

### Поток данных

1. Пользователь создает взаимодействия с элементами (viewed/liked/rated/purchased).
2. Данные сохраняются в PostgreSQL.
3. Сервис рекомендаций строит кандидатов на основе графа и поведенческих сигналов.
4. Результат кэшируется в Redis.
5. API и веб-интерфейс возвращают готовые рекомендации.

---

## Взаимодействие с проектом

### Через браузер (веб-интерфейс)

1. В админке или через API создайте хотя бы одного пользователя (`RecommendationUser`) и элементы (`Item`).
2. Откройте **«Предпочтения»** — добавьте взаимодействие (тип, при необходимости оценку); по ID пользователя можно просмотреть список взаимодействий.
3. **«Рекомендации»** — выберите пользователя, алгоритм (гибрид, PageRank, коллаборативная фильтрация, k-NN) и нажмите «Получить рекомендации».
4. **«Статистика»** — сводные счётчики, распределение по типам и оценкам, популярные элементы.

### Через админку

Создайте пользователей (`RecommendationUser`), элементы (`Item`) и при необходимости взаимодействия (`Interaction`), либо используйте API или форму на сайте.

### API examples

Базовый URL: `http://127.0.0.1:8000/api/`

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/items/` | Список элементов |
| POST | `/api/preferences/` | Добавить предпочтение (JSON: `user_id`, `item_id`, `interaction_type`, опционально `rating`) |
| GET | `/api/recommendations/<user_id>/?algorithm=hybrid&limit=10` | Рекомендации |
| GET | `/api/users/<user_id>/preferences/` | Предпочтения пользователя |
| GET | `/api/statistics/` | Сводная статистика |
| GET | `/api/statistics/popular/` | Популярные элементы |
| GET | `/api/statistics/distribution/` | Распределение по типам и оценкам |

Пример добавления предпочтения:

```bash
curl -X POST http://127.0.0.1:8000/api/preferences/ ^
  -H "Content-Type: application/json" ^
  -d "{\"user_id\": 1, \"item_id\": 1, \"interaction_type\": \"viewed\"}"
```

В браузере для POST с сессией нужен CSRF-токен; удобнее **Browsable API** DRF или клиент вроде Postman.

Пример для production:

```bash
curl -X GET "https://graphrec-production.up.railway.app/api/recommendations/1/?algorithm=hybrid&limit=10"
```

### Тесты

```bash
poetry run python manage.py test recommendations
```

### Покрытие кода

Пакет **coverage** указан в зависимостях проекта (`pyproject.toml`); после `poetry install` команда `coverage` доступна в окружении. Измерение по пакету приложения `recommendations`:

```bash
poetry run coverage run --source=recommendations manage.py test recommendations
poetry run coverage report -m
```

Ориентировочное покрытие пакета `recommendations`: **~87%** (точное значение см. в выводе `coverage report` после запуска).

### Линтеры и форматирование

После `poetry install --with lint` доступны **Black**, **isort** и **flake8**. Длина строки везде **119** символов (см. `pyproject.toml` и `.flake8`). **isort** настроен с `profile = "black"`, чтобы не спорить с форматированием. Во **flake8** игнорируются **E203** и **W503**, чтобы не конфликтовать с Black.

```bash
poetry run isort .
poetry run black .
poetry run flake8 .
```

Black по умолчанию не трогает служебные каталоги (`.git`, `__pycache__` и т.д.); дополнительно через `extend-exclude` исключены каталоги **`migrations`**. Исключения для flake8 — в **`.flake8`** (в т.ч. `*/migrations/*`).

---

## Структура (кратко)

```
config/              # настройки Django, urls
recommendations/     # приложение: API, web_views, forms, templates (Bootstrap), services, graph
manage.py
pyproject.toml
```

---

## Deploy on Railway

1. Подключите GitHub-репозиторий к Railway (`Deploy from GitHub Repo`).
2. Убедитесь, что в корне есть рабочий `Dockerfile`.
3. Добавьте сервис `PostgreSQL` (и `Redis`, если нужен кэш).
4. В `Variables` app-сервиса задайте: `SECRET_KEY`, `DEBUG=0`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, `LOCATION`.
5. Задеплойте приложение (Railway сам собирает Docker-образ).
6. После первого успешного деплоя сгенерируйте `Public Domain` в `Settings -> Networking`.
7. Разово наполните демо-данными командой `python manage.py seed_demo` (через Run Command/Shell или временный start command).
8. Проверьте эндпоинты: `/`, `/api/`, `/api/recommendations/<user_id>/`.

---

## Автор

Оксана Конкина. Контакты: [`pyproject.toml`](pyproject.toml) (секция `authors`).
