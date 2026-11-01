# Миграции микросервисов

У `auth`, `org` и `tasks` собственные `alembic.ini`, папка `alembic/` и история
миграций. Каждая история начинается с одной baseline-миграции
`alembic/versions/0001_baseline.py`, отражающей текущую схему сервиса, включая
локальные inbox, outbox, идемпотентность и реплики пользователей, где они нужны.
История монолита намеренно не переносилась: для учебного проекта используются
новые независимые baseline, как разрешено в ТЗ. Старые миграции в корневой
`alembic/` сохранены как история монолита; для сервисов запускаются только их
собственные конфигурации.

Baseline предназначены для новых пустых БД `auth_db`, `org_db` и `tasks_db`.
Это создание схемы, а не перенос данных из монолита. Сами базы и пользователи
В Compose у каждого сервиса свой PostgreSQL-контейнер: `db_auth`, `db_org`
и `db_tasks`, со своим volume. При первом запуске с пустым volume PostgreSQL
создаёт пользователя и базу по `POSTGRES_USER`, `POSTGRES_PASSWORD` и
`POSTGRES_DB` из соответствующего сервисного `.env`. Миграции создают схемы
`auth`, `org`, `tasks` в соответствующих БД; у каждой БД своя таблица
`public.alembic_version`. Только org устанавливает расширение `ltree`.

Из корня репозитория с установленными тестовыми зависимостями:

```shell
poetry run alembic -c services/auth/alembic.ini upgrade head
poetry run alembic -c services/org/alembic.ini upgrade head
poetry run alembic -c services/tasks/alembic.ini upgrade head
```

Или из папки нужного сервиса: `poetry run alembic upgrade head`.
Конфигурация берётся из `.env` именно этого сервиса независимо от текущей
папки; переменные окружения имеют приоритет. Значения `DB_HOST=db_auth`,
`DB_HOST=db_org` и `DB_HOST=db_tasks` рассчитаны на Docker-сеть.
Для запуска с хоста укажи доступный адрес PostgreSQL
и опубликованный порт через `DB_HOST` и `DB_PORT`.

Проверка SQL без подключения к БД:

```shell
poetry run alembic -c services/auth/alembic.ini upgrade head --sql
```

Следующие изменения схемы создаются из папки соответствующего сервиса:

```shell
poetry run alembic revision --autogenerate -m "describe schema change"
poetry run alembic upgrade head
```

Каждая конфигурация autogenerate рассматривает только схему своего сервиса.
После проверки сгенерированной миграции её нужно добавить в Git. В Compose
миграции запускаются отдельными контейнерами `migrate_auth`, `migrate_org`
и `migrate_tasks` с командой `alembic upgrade head`. Каждый API ждёт
успешного завершения своей миграции через `service_completed_successfully`.
Dockerfile запускает только Uvicorn.

Порядок запуска через `docker compose up --build`: каждый PostgreSQL проходит
healthcheck, затем `migrate_auth`, `migrate_org`
и `migrate_tasks` применяют миграции. Каждый API стартует после своей миграции
и готовности Kafka. В постоянно работающем состоянии это три API-контейнера,
три PostgreSQL-контейнера со своими БД и одна Kafka; контейнеры миграций
завершаются. API доступны на портах 8000 (auth), 8001 (org)
и 8002 (tasks), с прежними путями запросов.

Рабочий Compose использует только сервисные `.env`; корневой `.env` пока
оставлен для старого тестового окружения. Изменение `POSTGRES_PASSWORD` в
`.env` не меняет пароль в уже инициализированном volume.

# Содержание
- [Запуск проекта](#запуск-проекта)
- [Переменные окружения](#переменные-окружения)
- [Подразделения](#подразделения)
- [Паттерн -> где в коде](#паттерн---где-в-коде)
- [Что поменять при распиле на микросервисы](#что-поменять-при-распиле-на-микросервисы)
- [Список эндпоинтов](#список-эндпоинтов)
- [Тест запросов через Postman](#тест-запросов-через-postman)


# Запуск проекта
- Клонируйте репозиторий
```shell
git clone https://github.com/sqqqwer/Zadan4FastApi.git
```
- Перейдите в проект
```shell
cd Zadan4FastApi/
```
- Подготовьте .env файл.
- Запустите docker

### Запустить проект
- Поднимите контейнеры
```shell
make docker-up
```
### Запустить тесты
- Поднять тестовые контейнеры, линтер, запустить все тесты
```shell
make prepare
```
# Переменные окружения

- POSTGRES_USER - пользователь постгреса
- POSTGRES_PASSWORD - пароль постгреса
- POSTGRES_DB - имя базы данных постгреса
- DB_HOST - название контейнера базы данных
- DB_PORT - внутренний порт контейнера базы данных 
- FRONTEND_URL - ссылка фронтенда для генерации ссылки с приглашением
- JWT_PRIVATE_KEY_PATH - путь к файлу (в контейнере) приватного ключа RS256 для jwt
- JWT_PUBLIC_KEY_PATH - путь к файлу (в контейнере) публичного ключа RS256 для jwt
- JWT_ALGORITHM - имя алгоритма (RS256)
- JWT_ISSUER - название модуля, подписывающего jwt (auth-module)
- JWT_AUDIENCE - аудитория, кто может проверять jwt (tasks-platform)
- IDEMPOTENCY_HMAC_SECRET - HMAC-SHA256 секретный ключ для request, который сохраняется в Idempotency
- AUTH_BASE_URL - адрес auth для HTTP fallback (по умолчанию `http://127.0.0.1:8000`)
- AUTH_HTTP_TIMEOUT - таймаут HTTP-клиента auth в секундах

# Подразделения
- Решил что связи Должность-Пользователь, привязанные к Подразделению, это важные данные, поэтому Подразделение нельзя удалить, пока у него есть Должности.
- При переносе ветки под собственного потомка, выкидывает отдельное исключение StructMoveTargetInSubTree (код 409 - конфликт).

# Паттерн -> где в коде
- Репозиторий - в папке ***repositories*** в модулях и core
- Сервис слой - в папке ***services*** в модулях и core
- Uow [Uow-сервис](./src/core/services/uow.py) | [получение сессии](./src/core/dependencies/session.py)
- Dependency Injection - Стандартный Depends в папке ***dependencies*** в модулях и core
- Публичный DTO [auth](./src/modules/auth/public/dto.py) | [org](./src/modules/org/public/dto.py)
| [tasks](./src/modules/tasks/public/dto.py)
- Порты и адаптеры [tasks_port](./src/modules/tasks/ports.py) | [org_port](./src/modules/org/ports.py) | [tasks_adapter](./src/adapters/tasks_local_user_directory.py) | [org_adapter](./src/adapters/org_local_user_directory.py) | [auth_public_service](./src/modules/auth/public/service.py)
- Эвенты - отдельно в папке [events](./src/core/events/). Создаётся в lifespan в [main](./src/core/main.py)

# Что поменять при распиле на микросервисы
Перекинуть всё, что в модулях импортируется из core, в модули.
(Идемпотентность, абстрактные репозитории, crud сервисы, зависимости, систему эвентов, логирование, обработку исключений, базовые схемы, uow, получение сессии, jwt-decoder, token_claims_sheme, зависимости аутентификации)

Убрать зависимости адаптеров и переписать их.
# Список эндпоинтов

http://localhost:8000/docs

# Тест запросов через Postman
- Импортируйте файл [tasks-platform.postman_collection](./postman/tasks-platform.postman_collection.json) в Postman
