# ASOS Data Schema Specification

Документация контракта данных, валидации Pydantic v2 и структуры хранения в SQLite.

---

## 1. Pydantic v2 Модели (`src/models/product.py`)

### `AsosPrice`
Структура цен и параметров скидки.

| Поле | Тип | Nullable | Описание |
|:---|:---|:---:|:---|
| `current` | `float` | Нет | Текущая цена продажи товара |
| `previous` | `float` | Да | Исходная цена до скидки (null, если скидки нет) |
| `rrp` | `float` | Да | Рекомендованная розничная цена производителя (RRP) |
| `lowestPriceInLast30Days` | `float` | Да | Минимальная цена за последние 30 дней (EU Omnibus Directive) |
| `currency` | `str` | Нет | Код валюты (по умолчанию `'EUR'`) |
| `isMarkedDown` | `bool` | Нет | Флаг наличия скидки (`True`, если товар на распродаже) |
| `isOutletPrice` | `bool` | Нет | Флаг специальной цены аутлета |
| `discount_percent` *(computed)* | `float` | Нет | Вычисляемый процент скидки: `round(((previous - current) / previous) * 100, 1)` |

### `AsosProduct`
Основная сущность товара каталога.

| Поле | Тип | Описание | Нормализация |
|:---|:---|:---|:---|
| `id` | `int` | Уникальный цифровой ID товара в ASOS | — |
| `name` | `str` | Полное коммерческое наименование товара | Очистка от спецсимволов |
| `productCode` | `int` | Внутренний артикул / SKU | — |
| `productType` | `str` | Тип номенклатуры (по умолчанию `'Product'`) | — |
| `brandName` | `str` | Бренд производителя (Nike, adidas, Salomon и др.) | — |
| `colour` | `str` | Цветовая гамма (если указана) | — |
| `price` | `AsosPrice` | Вложенный объект цены | Автоматический парсинг из структуры API |
| `url` | `str` | Абсолютная ссылка на карточку товара | Автодобавление `https://www.asos.com/` |
| `imageUrl` | `str` | Абсолютная ссылка на главное фото | Автодобавление `https://` |
| `additionalImageUrls` | `list[str]` | Массив ссылок на дополнительные ракурсы | Автодобавление `https://` ко всем элементам |
| `isSellingFast` | `bool` | Индикатор высокого спроса / быстрого раскупа | — |
| `isPromotion` | `bool` | Товар участвует в маркетинговой акции | — |
| `isNew` | `bool` | Новинка сезона (New Season) | — |

---

## 2. Схема реляционной базы данных (SQLite `data/asos.db`)

### Таблица `products` (Уникальные сущности каталога)
```sql
CREATE TABLE products (
    id INTEGER PRIMARY KEY,
    product_code INTEGER,
    name TEXT NOT NULL,
    brand TEXT NOT NULL,
    url TEXT NOT NULL,
    image_url TEXT,
    is_selling_fast INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Таблица `price_history` (Временные ряды цен для мониторинга динамики)
```sql
CREATE TABLE price_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    current_price REAL NOT NULL,
    previous_price REAL,
    is_marked_down INTEGER DEFAULT 0,
    discount_percent REAL DEFAULT 0.0,
    currency TEXT DEFAULT 'EUR',
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id)
);

CREATE INDEX idx_price_product ON price_history(product_id);
CREATE INDEX idx_price_discount ON price_history(discount_percent DESC);
```

---

## 3. Форматы экспорта (`data/samples/`)

1. **`all_products.csv` / `all_products.json`**:
   - Полная выгрузка всех спарсенных уникальных товаров каталога с их последней актуальной ценой.
   - Поля: `id`, `product_code`, `name`, `brand`, `url`, `image_url`, `is_selling_fast`, `current_price`, `previous_price`, `is_marked_down`, `discount_percent`, `currency`.

2. **`deals.csv` / `deals.json`**:
   - Отфильтрованная выгрузка товаров со скидками (`is_marked_down = 1`), дедуплицированная по ID товара и отсортированная по `discount_percent DESC`.
