BOARD_COLUMNS = [
    "Backlog",
    "Ready",
    "Planning",
    "Coding",
    "Testing",
    "Deploy",
    "Done",
    "Failed",
]


def task(
    *,
    id: str,
    title: str,
    kind: str,
    status: str,
    summary: str,
    acceptance_criteria: str,
    target_area: str,
    execution_risk: str | None = None,
    visual_score: int,
    realism_score: int,
    agent_score: int,
) -> dict:
    return {
        "id": id,
        "title": title,
        "kind": kind,
        "status": status,
        "summary": summary,
        "acceptance_criteria": acceptance_criteria,
        "target_area": target_area,
        "execution_risk": execution_risk,
        "visual_score": visual_score,
        "realism_score": realism_score,
        "agent_score": agent_score,
    }


DEFAULT_TASKS = [
    task(
        id="DONE-001",
        title="Главная страница с KPI продавца",
        kind="feature",
        status="done",
        summary="На дашборде уже есть четыре базовые карточки: валовая выручка, чистая выручка, доля возвратов и количество заказов.",
        acceptance_criteria=(
            "1. Главная страница открывается без ошибок.\n"
            "2. На дашборде отображаются карточки Gross revenue, Net revenue, Return rate и Orders in seed set.\n"
            "3. Значения метрик берутся из текущего тестового набора заказов."
        ),
        target_area="dashboard",
        visual_score=5,
        realism_score=5,
        agent_score=5,
    ),
    task(
        id="DONE-002",
        title="Страница заказов с тестовой таблицей",
        kind="feature",
        status="done",
        summary="В pet-app уже есть отдельная страница заказов с непустой таблицей заказов продавца.",
        acceptance_criteria=(
            "1. Страница /orders открывается из навигации.\n"
            "2. В таблице есть колонки с номером заказа, датой, товаром, брендом, статусом и суммой.\n"
            "3. Таблица рендерится на тестовых данных без пустого состояния."
        ),
        target_area="orders",
        visual_score=4,
        realism_score=5,
        agent_score=5,
    ),
    task(
        id="DONE-003",
        title="Страница товаров с остатками и маржинальностью",
        kind="feature",
        status="done",
        summary="В приложении уже есть страница товаров с SKU, брендом, остатком и процентом маржи.",
        acceptance_criteria=(
            "1. Страница /products доступна из навигации.\n"
            "2. В таблице есть SKU, название, бренд, остаток и Margin %.\n"
            "3. Данные берутся из тестового каталога товаров."
        ),
        target_area="products",
        visual_score=4,
        realism_score=5,
        agent_score=5,
    ),
    task(
        id="DONE-004",
        title="Блок топ-товаров на дашборде",
        kind="feature",
        status="done",
        summary="На главной странице уже есть таблица Top delivered products по доставленным заказам.",
        acceptance_criteria=(
            "1. На дашборде выводится таблица Top delivered products.\n"
            "2. Таблица строится по доставленным заказам.\n"
            "3. В таблице отображаются название товара и количество доставок."
        ),
        target_area="dashboard",
        visual_score=4,
        realism_score=4,
        agent_score=5,
    ),
    task(
        id="DONE-005",
        title="Навигация между разделами Dashboard, Orders и Products",
        kind="feature",
        status="done",
        summary="В базовом layout уже есть навигация по ключевым разделам demo-приложения.",
        acceptance_criteria=(
            "1. В шапке отображаются ссылки Dashboard, Orders и Products.\n"
            "2. Активный раздел визуально выделяется.\n"
            "3. Переходы между разделами работают без перезагрузки compose-стека."
        ),
        target_area="platform",
        visual_score=3,
        realism_score=4,
        agent_score=5,
    ),
    task(
        id="DONE-006",
        title="Health-check для pet-app и orchestrator",
        kind="quality",
        status="done",
        summary="У pet-app и orchestrator уже есть базовые health endpoints для проверки контейнеров и CI.",
        acceptance_criteria=(
            "1. GET /health у pet-app возвращает статус ok.\n"
            "2. GET /health у orchestrator возвращает статус ok.\n"
            "3. Health-check можно использовать в smoke-проверках."
        ),
        target_area="platform",
        visual_score=2,
        realism_score=5,
        agent_score=5,
    ),
    task(
        id="DONE-007",
        title="Docker Compose запуск demo-стека",
        kind="quality",
        status="done",
        summary="Стек уже поднимается в Docker Compose и включает pet-app, control-room, Kanboard и Gitea.",
        acceptance_criteria=(
            "1. docker compose up --build запускает ключевые сервисы.\n"
            "2. Pet-app, Control Room, Kanboard и Gitea доступны на локальных портах.\n"
            "3. Сервисный маршрут не требует ручной донастройки кода."
        ),
        target_area="platform",
        visual_score=3,
        realism_score=5,
        agent_score=4,
    ),
    task(
        id="DONE-008",
        title="Сидовые данные продавца для демо",
        kind="quality",
        status="done",
        summary="В приложении уже есть тестовые заказы и товары, которых хватает для демонстрации багов и фич.",
        acceptance_criteria=(
            "1. В тестовом наборе есть несколько заказов разных статусов.\n"
            "2. В тестовом каталоге есть товары с разным остатком и маржой.\n"
            "3. На этих данных видны KPI, low stock и отрицательная маржа."
        ),
        target_area="data",
        visual_score=4,
        realism_score=4,
        agent_score=5,
    ),
    task(
        id="BL-001",
        title="Исправить расчёт чистой выручки с учётом возвратов",
        kind="bug",
        status="done",
        summary="Задача уже выполнена агентом: чистая выручка больше не включает возвращённые заказы как успешные продажи.",
        acceptance_criteria=(
            "1. Net revenue не учитывает returned-заказы как выручку.\n"
            "2. Для бага есть регрессионная проверка в тестах.\n"
            "3. Изменение подтверждено отдельной веткой и зелёным CI."
        ),
        target_area="finance",
        execution_risk="safe",
        visual_score=5,
        realism_score=5,
        agent_score=5,
    ),
    task(
        id="BL-002",
        title="Цветовые бейджи статусов в таблице заказов",
        kind="feature",
        status="backlog",
        summary="Статусы заказов сейчас выводятся обычным текстом. Для demo будет понятнее, если delivered, processing, returned и cancelled будут видны цветом.",
        acceptance_criteria=(
            "1. На странице Orders статус каждого заказа отображается как цветной бейдж.\n"
            "2. Delivered, processing, returned и cancelled визуально различаются.\n"
            "3. Вёрстка не ломается на desktop и mobile.\n"
            "4. Smoke-тест страницы Orders остаётся зелёным."
        ),
        target_area="orders",
        execution_risk="safe",
        visual_score=5,
        realism_score=4,
        agent_score=5,
    ),
    task(
        id="BL-003",
        title="Фильтр по бренду на странице товаров",
        kind="feature",
        status="backlog",
        summary="На странице Products пока нельзя быстро посмотреть товары одного бренда. Для seller-панели это естественный и наглядный сценарий.",
        acceptance_criteria=(
            "1. На странице Products появляется фильтр по бренду.\n"
            "2. При выборе бренда в таблице остаются только товары этого бренда.\n"
            "3. Сброс фильтра возвращает полный список.\n"
            "4. Изменение покрыто тестом или smoke-проверкой рендера."
        ),
        target_area="products",
        execution_risk="medium",
        visual_score=4,
        realism_score=5,
        agent_score=4,
    ),
    task(
        id="BL-004",
        title="Вывести на дашборд блок «Заканчиваются остатки»",
        kind="feature",
        status="done",
        summary="Задача уже не нужна: блок Low stock products уже отображается на главной странице.",
        acceptance_criteria=(
            "1. На дашборде есть отдельный блок Low stock products.\n"
            "2. В блок попадают товары с остатком на или ниже порога.\n"
            "3. Для каждой карточки видны бренд, название и остаток."
        ),
        target_area="dashboard",
        execution_risk="safe",
        visual_score=5,
        realism_score=4,
        agent_score=5,
    ),
    task(
        id="BL-005",
        title="Экспорт заказов в CSV",
        kind="feature",
        status="backlog",
        summary="Операционной команде нужен быстрый CSV-экспорт прямо со страницы Orders без ручного копирования таблицы.",
        acceptance_criteria=(
            "1. На странице Orders есть видимая кнопка или ссылка Export CSV.\n"
            "2. По нажатию скачивается CSV-файл с текущим набором заказов.\n"
            "3. В CSV есть минимум order id, date, product, brand, status и total.\n"
            "4. На экспорт есть автоматическая проверка или smoke-тест ответа."
        ),
        target_area="orders",
        execution_risk="medium",
        visual_score=4,
        realism_score=5,
        agent_score=4,
    ),
    task(
        id="BL-006",
        title="Подсветить отрицательную маржу на странице товаров",
        kind="feature",
        status="done",
        summary="Задача уже не нужна: отрицательная маржа уже выделяется на странице Products.",
        acceptance_criteria=(
            "1. Значения Margin % ниже нуля визуально выделены.\n"
            "2. Выделение заметно на таблице товаров без открытия карточки.\n"
            "3. Положительная маржа остаётся в обычном стиле."
        ),
        target_area="products",
        execution_risk="safe",
        visual_score=4,
        realism_score=5,
        agent_score=5,
    ),
    task(
        id="BL-007",
        title="Исправить расчёт доли возвратов на дашборде",
        kind="bug",
        status="backlog",
        summary="Сейчас return rate считается от delivered-заказов и переоценивает долю возвратов. В базе fulfilled-заказов должны учитываться и returned, и delivered.",
        acceptance_criteria=(
            "1. Return rate считается по базе fulfilled-заказов: delivered + returned.\n"
            "2. Cancelled и processing-заказы не входят в знаменатель.\n"
            "3. Для расчёта добавлен регрессионный тест.\n"
            "4. Значение на dashboard меняется ожидаемым образом на текущем seed-наборе."
        ),
        target_area="dashboard",
        execution_risk="medium",
        visual_score=4,
        realism_score=5,
        agent_score=4,
    ),
    task(
        id="BL-008",
        title="Бейдж Low stock на странице товаров",
        kind="feature",
        status="backlog",
        summary="На дашборде low stock уже видно, но в основной таблице товаров критичные остатки пока не отмечены явно.",
        acceptance_criteria=(
            "1. На странице Products у товаров с остатком на или ниже порога появляется бейдж Low stock.\n"
            "2. Бейдж не выводится для товаров с нормальным остатком.\n"
            "3. Визуальное решение не ломает таблицу.\n"
            "4. Изменение проверено тестом рендера или smoke-тестом."
        ),
        target_area="products",
        execution_risk="safe",
        visual_score=5,
        realism_score=4,
        agent_score=5,
    ),
    task(
        id="BL-009",
        title="Обогатить тестовые данные кейсами возвратов и отмен",
        kind="quality",
        status="backlog",
        summary="Для более правдоподобной аналитики demo-данных не хватает нескольких кейсов returned и cancelled, чтобы метрики и таблицы были менее игрушечными.",
        acceptance_criteria=(
            "1. В seed-данных появляется больше одного returned и больше одного cancelled кейса.\n"
            "2. Данные остаются согласованными для dashboard, orders и products.\n"
            "3. После изменения тесты не падают.\n"
            "4. На текущих страницах визуально заметно, что данные стали богаче."
        ),
        target_area="data",
        execution_risk="medium",
        visual_score=3,
        realism_score=5,
        agent_score=4,
    ),
    task(
        id="BL-010",
        title="Бейдж сборки с id последней задеплоенной задачи",
        kind="feature",
        status="backlog",
        summary="На live-приложении полезно сразу видеть, какой task id сейчас в проде. Это усиливает demo-эффект после успешного прогона агента.",
        acceptance_criteria=(
            "1. На главной странице или в шапке отображается build badge.\n"
            "2. В бейдже видны task id и время или версия деплоя.\n"
            "3. После следующего успешного прогона executor значение обновляется.\n"
            "4. Бейдж не перекрывает основную навигацию и не ломает layout."
        ),
        target_area="platform",
        execution_risk="medium",
        visual_score=5,
        realism_score=4,
        agent_score=3,
    ),
    task(
        id="BL-011",
        title="Подсветить отменённые и возвращённые заказы в таблице",
        kind="feature",
        status="backlog",
        summary="Проблемные статусы заказов сейчас теряются в общей таблице. Для demo и реального backoffice их лучше выделять сразу на уровне строки или ячейки.",
        acceptance_criteria=(
            "1. Returned и cancelled заказы визуально выделяются в таблице Orders.\n"
            "2. Delivered и processing заказы остаются в нейтральном стиле.\n"
            "3. Выделение сочетается с таблицей и не ухудшает читаемость.\n"
            "4. Рендер страницы покрыт smoke-проверкой."
        ),
        target_area="orders",
        execution_risk="safe",
        visual_score=5,
        realism_score=4,
        agent_score=5,
    ),
    task(
        id="BL-012",
        title="Smoke-тест главной страницы",
        kind="quality",
        status="done",
        summary="Задача уже закрыта: в тестах уже есть базовая smoke-проверка рендера главной страницы.",
        acceptance_criteria=(
            "1. Тест обращается к главной странице и получает 200 OK.\n"
            "2. В ответе есть ключевые элементы dashboard.\n"
            "3. Smoke-тест входит в обычный pytest-прогон."
        ),
        target_area="platform",
        execution_risk="safe",
        visual_score=2,
        realism_score=5,
        agent_score=5,
    ),
]
