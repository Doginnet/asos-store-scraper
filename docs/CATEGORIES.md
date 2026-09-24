# ASOS Category Registry & Glossary

Справочник ключевых категорий каталога ASOS (Men's Fashion) с числовыми идентификаторами эндпоинтов REST API:
`GET https://www.asos.com/api/product/search/v2/categories/{categoryId}`

---

## 1. Реестр категорий

| ID | Название (RU) | Название (EN) | Slug | Описание |
|:---|:---|:---|:---|:---|
| **5775** | Кроссовки и кеды | Trainers & Sneakers | `trainers` | Спортивная и лайфстайл обувь (Nike, adidas Originals, New Balance, Salomon, Vans, Asics) |
| **5668** | Худи и свитшоты | Hoodies & Sweatshirts | `hoodies` | Повседневные толстовки, худи оверсайз, свитшоты и флисовые кофты |
| **7616** | Футболки и майки | T-Shirts & Vests | `t-shirts` | Базовые футболки, графические принты, брендовый streetwear |
| **4208** | Джинсы | Jeans | `jeans` | Джинсовая одежда: прямые, мешковатые (baggy), зауженные (slim), карго |
| **3606** | Куртки и пальто | Jackets & Coats | `jackets` | Верхняя одежда: пуховики, бомберы, ветровки, пальто, тренчи |
| **4910** | Брюки и чиносы | Trousers & Chinos | `trousers` | Классические брюки, чиносы, утилитарные карго |
| **3602** | Рубашки | Shirts | `shirts` | Оверсайз рубашки, оксфордские сорочки, фланелевые и летние рубашки |
| **7617** | Джемперы и кардиганы | Jumpers & Cardigans | `sweaters` | Вязаный трикотаж, свитеры с круглым вырезом, фактурные кардиганы |
| **5774** | Ботинки | Boots | `boots` | Челси, милитари-ботинки, хайкеры |
| **4210** | Аксессуары | Accessories | `accessories` | Кепки, панамы, шапки, сумки, рюкзаки, ремни, солнцезащитные очки |

---

## 2. Использование в CLI

Запуск сбора по ID категории:
```bash
# Кроссовки (Trainers)
uv run python -m src.main --category-id 5775

# Худи (Hoodies)
uv run python -m src.main --category-id 5668

# Куртки (Jackets)
uv run python -m src.main --category-id 3606
```

---

## 3. Региональная маршрутизация (Store & Currency Mapping)

Для предотвращения ошибки `400: No valid store was found`, ASOS строго сопоставляет страну и стор:

| Страна | Код страны (`country`) | Код стора (`store`) | Валюта (`currency`) |
|:---|:---:|:---:|:---:|
| Болгария / ЕС (Восток) | `BG` | `ROE` | `EUR` |
| Польша | `PL` | `ROE` | `EUR` / `PLN` |
| Германия | `DE` | `ROE` | `EUR` |
| Франция | `FR` | `ROE` | `EUR` |
| Великобритания | `GB` | `COM` | `GBP` |
| США | `US` | `COM` | `USD` |

*Модуль `config/categories.py` автоматически разрешает правильную комбинацию стора и валюты.*
