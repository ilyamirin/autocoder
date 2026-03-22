# Autonomous Coding Demo

Live demo автономного coding loop, собранного в одном `docker compose`.

Это не абстрактный toy-проект. Репозиторий сделан как уменьшенная и
обезличенная демонстрация реального проприетарного контура агентной разработки:
человеческий intake задачи, автоматическое исполнение, независимая проверка и
видимый deploy-результат в живом приложении.

В демо сохранена архитектурная суть реального проекта, но убраны закрытые
детали доменной модели, инфраструктуры и продуктовых данных.

## Что Это

Платформа показывает полный путь задачи:

`Kanboard -> orchestrator -> aider -> local tests -> Gitea Actions -> live pet-app`

Система не ограничивается “агент что-то предложил”. Здесь видно весь
инженерный контур:

- задача берётся с живой Kanban-доски
- под задачу создаётся отдельный `git worktree`
- агент реально меняет код в отдельной ветке
- изменения прогоняются локальными тестами
- ветка уходит в `Gitea`
- `Gitea Actions` независимо проверяет результат
- успешный commit промоутится в live runtime
- изменение становится видно в браузере

## На Что Опирается Демо

Целевой `pet-app` здесь специально маленький: это seller operations dashboard,
уменьшенная копия e-commerce backoffice. Он достаточно реалистичен, чтобы:

- показывать KPI
- иметь таблицы заказов и товаров
- содержать доменную логику
- позволять агенту чинить баги и добавлять маленькие фичи
- давать видимый результат после deploy

Именно поэтому демо выглядит как настоящий операторский workflow, а не как чат
с агентом поверх тестового `todo app`.

## Ключевые Фишки

- весь стек поднимается одной командой: `docker compose up --build -d`
- `Kanboard` является человеческой точкой входа
- `orchestrator` сам claim-ит задачи из `Ready`
- под каждую задачу создаётся отдельный `git worktree`
- coding engine сейчас: `aider`
- `aider` работает через `OpenRouter`
- правила поведения агента лежат в одном versioned файле:
  [`docs/AGENT_POLICY.md`](docs/AGENT_POLICY.md)
- агент ограничен execution profile и write-scope по area
- после успеха ветка проходит через `Gitea Actions`
- live `pet-app` реально обслуживается из `data/live_runtime`
- completed и failed задачи не скрываются с доски, а остаются видимыми

## Что Уже Работает

- full stack runs in one `docker compose`
- `Kanboard` используется как human intake и status board
- `orchestrator` синхронизируется с `Kanboard` и забирает `Ready` задачи
- executor создаёт отдельную task branch под каждую попытку
- `aider` запускается прямо внутри `orchestrator`, без отдельного agent-container
- `aider` редактирует только whitelisted файлы в рамках area profile
- локальные тесты и `Gitea Actions` работают как независимые ступени проверки
- успешные изменения промоутятся в live runtime checkout
- live `pet-app` показывает результат в браузере

Проверенный живой сценарий:

- `BL-014` `Исправить долю возвратов только локальной доменной правкой`
  уже прошёл полный e2e:
  `Kanboard -> aider -> local tests -> Gitea Actions -> live promote -> Done`

## Архитектура Сервисов

- `pet-app`: целевое demo-приложение
- `control-room`: обзорный UI по pipeline, branch, commit, CI и live runtime
- `orchestrator`: state machine и исполнитель task lifecycle
- `aider`: coding engine, запускаемый как subprocess внутри `orchestrator`
- `kanboard`: task intake и человеко-видимый board
- `gitea`: git hosting, branch visibility, repo UI
- `gitea-actions-runner`: независимый CI runner

## Реальный Workflow

```text
Kanboard Backlog
  -> Ready
  -> orchestrator claim
  -> git worktree + task branch
  -> aider edits code
  -> local pytest
  -> commit + push to Gitea
  -> Gitea Actions
  -> promote to codex/runtime
  -> live pet-app updated
  -> Kanboard Done / Failed
```

Важно:

- `main` не является обязательным deploy-источником
- live deploy сейчас идёт через `codex/runtime`
- task branches вида `codex/<task-id>-<suffix>` нужны для изоляции, diff и CI

## Agent Execution

- `aider` использует глобальные `CODING_*` настройки из `.env`
- модель по умолчанию: `openrouter/qwen/qwen3-coder-plus`
- `reasoning_effort`: `medium`
- `extended_thinking_budget`: `200000`
- `critic_max_iterations`: `5`
- `aider` работает в strict `diff` mode
- `.gitignore` агент не мутирует
- логи и LLM history пишутся в `data/aider`

Поведение агента задаётся не размазанными prompt-строками, а единым
политическим документом:

- [`docs/AGENT_POLICY.md`](docs/AGENT_POLICY.md)

Именно этот файл определяет:

- глобальные правила минимального патча
- area-specific heuristics
- soft limits и guardrails

## Manual Demo Flow

1. Открыть `Kanboard`
2. Перевести backlog-карточку в `Ready`
3. Следить за pipeline в `Control Room`
4. Смотреть branch и CI в `Gitea`
5. После `Done` проверить изменение в live `pet-app`

Хорошие карточки для ручного прогона:

- `BL-014` `Исправить долю возвратов только локальной доменной правкой`
- `BL-013` `Минимально обогатить данные возвратов без изменения расчётов`
- `BL-015` `Показать low stock без новых компонентов и API`
- `BL-016` `Добавить live build badge минимальным platform-патчем`

## Development

1. Скопировать `.env.example` в `.env`
2. Заполнить placeholder values
3. Поднять стек:

```bash
docker compose up --build -d
```

Локальная разработка ведётся через Homebrew Python 3.12 и project venv:

```bash
python3.12 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

## Default URLs

- `pet-app`: [http://localhost:18000](http://localhost:18000)
- `control-room`: [http://localhost:18010](http://localhost:18010)
- `orchestrator`: [http://localhost:18020](http://localhost:18020)
- `kanboard`: [http://localhost:18080](http://localhost:18080)
- `gitea`: [http://localhost:13000](http://localhost:13000)
- `gitea actions`: [http://localhost:13000/ilya/autonomous-coding-demo/actions](http://localhost:13000/ilya/autonomous-coding-demo/actions)

## Demo Credentials

- `Kanboard` admin: `configured in .env`
- `Kanboard` demo user: `demo.operator / replace-me`
- `Gitea`: `ilya / replace-me`

## Port Map

- `18000` -> `pet-app:8000`
- `18010` -> `control-room:8010`
- `18020` -> `orchestrator:8020`
- `18080` -> `kanboard:80`
- `13000` -> `gitea:3000`
- `12222` -> `gitea:22`

## Routing Notes

- human intake starts in `Kanboard`
- demo services share orchestration state through `data/demo.db`
- `control-room` aggregates task state, branch, CI and live commit metadata
- `kanboard-seed` talks to `http://kanboard/jsonrpc.php`
- `orchestrator` bind-mounts the repo and creates worktrees in `data/worktrees`
- live runtime is maintained in `data/live_runtime`
- `pet-app` serves code from `data/live_runtime`
- `orchestrator` launches `aider` directly as a subprocess
- no separate coding-agent container is created for task execution

## Infrastructure Sizing

If `aider` uses `OpenRouter` or another external model provider, this stack
does not need a local GPU. The main host load comes from:

- local tests
- `Gitea Actions`
- git worktrees
- Docker I/O
- logs and persistence

### Recommended Starting Point

For a small operator team around `5-7` people with moderate task volume:

- `8 vCPU`
- `16 GB RAM`
- `300-500 GB NVMe SSD`
- `Ubuntu 24.04 LTS`
- no GPU

### Comfortable Capacity

For heavier builds, larger repos, and overlapping CI activity:

- `12-16 vCPU`
- `32 GB RAM`
- `500 GB NVMe SSD`
- no GPU

### Database Recommendation

For real long-running usage, move off local `SQLite`:

- use `PostgreSQL` for `Gitea`
- use `PostgreSQL` for internal orchestrator/control-room state

`SQLite` здесь оставлен потому, что это live demo, а не production install.

## Safety

- секреты не коммитятся
- локальные креды и API keys живут в `.env`
- перед каждым коммитом гоняется `./scripts/check_no_secrets.sh`
- git-операции внутри executor защищены от stale `.lock` файлов
- `Done` и `Failed` карточки остаются видимыми в `Kanboard`

## Test Notes

Не запускай bare `pytest` из корня после появления live runtime и task worktrees.
Там лежат зеркальные тестовые файлы, и pytest соберёт дубли.

Используй один из вариантов:

```bash
PYTHONPATH=. .venv/bin/pytest tests/test_kanboard_sync.py tests/test_orchestrator.py tests/test_store.py tests/test_control_room.py tests/test_git_safety.py tests/test_live_runtime.py
```

или:

```bash
PYTHONPATH=. .venv/bin/pytest tests/test_pet_app.py
```

## License

Этот репозиторий лицензирован под `MIT`. См. [LICENSE](LICENSE).

Сторонние компоненты, включая `Kanboard`, `Gitea`, `Gitea act_runner`,
`aider`, Python и зависимости, остаются под своими лицензиями. См.
[THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md).
