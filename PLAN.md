# 🚀 Project Plan: ASOS Price Intelligence Monitor

> **Текущий этап:** ✅ Финализация и полировка (Релизная готовность)  
> **Репозиторий:** `d:/Programming/Projects/Portfolio/Scraping/asos-store`  
> **Ветка Git:** `master`  
> **Связанные документы:** [SRS.md](file:///d:/Programming/Projects/Portfolio/Scraping/asos-store/SRS.md), [README.md](file:///d:/Programming/Projects/Portfolio/Scraping/asos-store/README.md), [SCRAPER_SPEC.md](file:///d:/Programming/Projects/Portfolio/Scraping/asos-store/SCRAPER_SPEC.md)

---

## 📊 Общий статус выполнения (Milestones)

- [x] **Фаза 1: Реверс-инжиниринг API и обход Akamai CDN**
- [x] **Фаза 2: Строгие схемы Pydantic v2 и реляционная база SQLite**
- [x] **Фаза 3: Высокоскоростная пагинация и устранение дубликатов**
- [x] **Фаза 4: Управление жизненным циклом каталога (`last_seen_at`, `is_active`)**
- [x] **Фаза 5: Аналитический дашборд Streamlit, Telegram-алерты и шоукейс**

---

## 🗓 Детальный план по фазам

### Фаза 1: Реверс-инжиниринг API и обход Akamai CDN
- [x] Анализ сетевого трафика каталога ASOS (`/api/product/search/v2/categories`).
- [x] Интеграция `curl_cffi` с аппаратной имперсонацией Chrome 124 TLS/JA3.
- [x] Локализация и устранение ошибки HTTP 400 `No valid store was found` через инъекцию набора сессионных кук Edge CDN (`storeCode=ROE`, `currency=19`, `browseCountry=BG`, `siteChromeVersion`).
- [x] Санитизация системной локали (блокировка утечки `en_US.UTF-8` в query params, принудительный `en-GB`).
- [x] Настройка экспоненциального отката ретраев и ротации логов в `loguru`.

### Фаза 2: Строгие схемы Pydantic v2 и реляционная база SQLite
- [x] Разработка моделей `AsosPrice`, `AsosProduct`, `AsosSearchResponse`.
- [x] Нормализация ссылок: авто-конвертация относительных путей в абсолютные (`https://www.asos.com/`).
- [x] Проектирование схемы SQLite:
  - `products`: уникальные товары.
  - `price_history`: временные срезы цен с валютой и флагом markdown.
  - `categories` & `product_categories`: Many-to-Many отношения категорий.
- [x] Разработка юнит-тестов валидации на оффлайн-фикстурах (`tests/fixtures/search_sample.json`).

### Фаза 3: Высокоскоростная пагинация и устранение дубликатов
- [x] Поддержка максимального размера пачки (72 товара за один запрос).
- [x] Динамическая остановка пагинации по достижению `itemCount`.
- [x] Устранение дубликатов в выборках скидок через SQL Window функции (`ROW_NUMBER() OVER PARTITION BY product_id ORDER BY id DESC`).
- [x] Создание реестра 11 категорий мужского каталога в `config/categories.py`.
- [x] Раздельный экспорт в поддиректории `data/samples/<category>/` и сводные глобальные отчеты.

### Фаза 4: Управление жизненным циклом каталога (`last_seen_at`, `is_active`)
- [x] Добавление полей `last_seen_at TIMESTAMP` и `is_active INTEGER DEFAULT 1` с безопасной автомиграцией существующей БД SQLite.
- [x] Автоматическая деактивация товаров (`deactivate_unseen_products`): при полном сборе (`--all`) товары, отсутствующие в текущем ответе витрины, помечаются как `is_active = 0`.
- [x] Интеграция фильтрации `active_only=True` в методы выборки `get_top_deals`, `get_all_products`, `get_categories`.
- [x] Успешный E2E сбор всей обуви:
  - Зонтичная категория обуви (ID 4209): собраны все 2 306 товаров (100% совпадение с сайтом).
  - Категория кроссовок (ID 5775): собраны 1 244 активных товара, автоматически деактивировано 267 распроданных позиций.
- [x] Написание юнит-теста жизненного цикла `test_lifecycle_tracking_and_deactivation`.

### Фаза 5: Аналитический дашборд Streamlit, Telegram-алерты и шоукейс
- [x] Создание интерактивного веб-приложения на Streamlit (`src/dashboard/app.py`).
- [x] Добавление визуальной витрины карточек скидок, графиков распределения скидок и цен.
- [x] Внедрение переключателя «Show active products only» и экспорта данных в CSV/JSON прямо из UI.
- [x] Разработка безопасного каркаса Telegram-алертинга (`TelegramAlerter`) с режимом симуляции (Mock Mode).
- [x] Оформление репрезентативного `README.md` с Mermaid-диаграммой архитектуры.
- [x] Полное прохождение тест-сьюта: 13 из 13 тестов PASS.

---

## 📌 Архитектурные решения (Changelog Summary)

- **2026-09-23:** Инициализация проекта, фиксация сетевого контракта с ASOS, настройка `curl_cffi` с Chrome 124 TLS.
- **2026-09-24:** Решена проблема HTTP 400 (интеграция кук Postman cURL), внедрены модели Pydantic v2 и SQLite Many-to-Many схема.
- **2026-09-26:** Добавлен расчет скидок через SQL Window функции (`ROW_NUMBER()`), устранены дубликаты товаров в CSV/JSON.
- **2026-09-27:** Реализован флаг `--all-categories`, сформирован раздельный каталог по 10 категориям.
- **2026-10-04:**
  - Реализован каркас жизненного цикла: `last_seen_at`, `is_active`, метод `deactivate_unseen_products()`.
  - Зарегистрирована категория `Shoes, Boots & Trainers` (ID 4209), проведен полный сбор 2 306 товаров.
  - Написаны и верифицированы тесты жизненного цикла (13/13 PASS).
  - Streamlit дашборд дополнен фильтрацией статуса активности и расширенной аналитикой.
