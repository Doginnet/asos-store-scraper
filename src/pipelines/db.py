import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from loguru import logger

from config.settings import settings
from config.categories import CATEGORY_REGISTRY


class AsosDatabase:
    """
    SQLite persistence layer for ASOS catalog and historical price monitoring.
    Supports relational category mapping and isolated category filtering.
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or settings.DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY,
                product_code INTEGER,
                name TEXT NOT NULL,
                brand TEXT NOT NULL,
                url TEXT NOT NULL,
                image_url TEXT,
                is_selling_fast INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                current_price REAL NOT NULL,
                previous_price REAL,
                is_marked_down INTEGER DEFAULT 0,
                discount_percent REAL DEFAULT 0.0,
                currency TEXT DEFAULT 'EUR',
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY,
                slug TEXT NOT NULL,
                title TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS product_categories (
                product_id INTEGER NOT NULL,
                category_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (product_id, category_id),
                FOREIGN KEY (product_id) REFERENCES products(id),
                FOREIGN KEY (category_id) REFERENCES categories(id)
            )
            """)

            cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_price_product ON price_history(product_id)
            """)
            cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_price_discount ON price_history(discount_percent DESC)
            """)
            cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_pc_category ON product_categories(category_id)
            """)

            # Seed known categories from registry
            for cat_id, info in CATEGORY_REGISTRY.items():
                cursor.execute("""
                INSERT OR IGNORE INTO categories (id, slug, title)
                VALUES (?, ?, ?)
                """, (cat_id, info["slug"], info["title"]))

            # Backfill existing products to category 5775 (Trainers) if product_categories is empty
            cursor.execute("SELECT count(*) FROM product_categories")
            if cursor.fetchone()[0] == 0:
                cursor.execute("""
                INSERT OR IGNORE INTO product_categories (product_id, category_id)
                SELECT id, 5775 FROM products
                """)

            conn.commit()

    def upsert_products(self, products: List[Any], category_id: Optional[int] = None) -> int:
        """
        Upserts products into 'products', appends to 'price_history', and links to 'product_categories'.
        """
        if not products:
            return 0

        inserted_count = 0
        now = datetime.now(timezone.utc).isoformat()

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Ensure category exists in categories table
            if category_id is not None:
                cat_info = CATEGORY_REGISTRY.get(category_id, {"slug": f"category_{category_id}", "title": f"Category {category_id}"})
                cursor.execute("""
                INSERT INTO categories (id, slug, title, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    slug=excluded.slug,
                    title=excluded.title,
                    updated_at=excluded.updated_at
                """, (category_id, cat_info["slug"], cat_info["title"], now))

            for p in products:
                # Upsert into products
                cursor.execute("""
                INSERT INTO products (id, product_code, name, brand, url, image_url, is_selling_fast, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name=excluded.name,
                    brand=excluded.brand,
                    url=excluded.url,
                    image_url=excluded.image_url,
                    is_selling_fast=excluded.is_selling_fast,
                    updated_at=excluded.updated_at
                """, (
                    p.id,
                    p.productCode,
                    p.name,
                    p.brandName,
                    str(p.url),
                    str(p.imageUrl) if p.imageUrl else None,
                    1 if p.isSellingFast else 0,
                    now
                ))

                # Append to price_history
                cursor.execute("""
                INSERT INTO price_history (
                    product_id, current_price, previous_price, is_marked_down, discount_percent, currency, recorded_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    p.id,
                    p.price.current,
                    p.price.previous,
                    1 if p.price.isMarkedDown else 0,
                    p.price.discount_percent,
                    p.price.currency,
                    now
                ))

                # Link product to category
                if category_id is not None:
                    cursor.execute("""
                    INSERT OR IGNORE INTO product_categories (product_id, category_id, created_at)
                    VALUES (?, ?, ?)
                    """, (p.id, category_id, now))

                inserted_count += 1

            conn.commit()

        logger.info(f"Saved {inserted_count} products and price records into {self.db_path} (category_id={category_id})")
        return inserted_count

    def get_top_deals(self, category_id: Optional[int] = None, limit: Optional[int] = 50) -> List[Dict[str, Any]]:
        """
        Returns top discounted products (deduplicated by latest price entry) sorted by discount_percent descending.
        Optionally filtered by category_id.
        """
        join_clause = ""
        where_conditions = ["lp.is_marked_down = 1"]
        params: List[Any] = []

        if category_id is not None:
            join_clause = "JOIN product_categories pc ON p.id = pc.product_id"
            where_conditions.append("pc.category_id = ?")
            params.append(category_id)

        where_clause = " AND ".join(where_conditions)

        query = f"""
        WITH latest_prices AS (
            SELECT 
                product_id,
                current_price,
                previous_price,
                is_marked_down,
                discount_percent,
                currency,
                ROW_NUMBER() OVER (PARTITION BY product_id ORDER BY id DESC) as rn
            FROM price_history
        )
        SELECT 
            p.id, p.name, p.brand, p.url, p.image_url, p.is_selling_fast,
            lp.current_price, lp.previous_price, lp.discount_percent, lp.currency
        FROM products p
        JOIN latest_prices lp ON p.id = lp.product_id AND lp.rn = 1
        {join_clause}
        WHERE {where_clause}
        ORDER BY lp.discount_percent DESC
        """
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, tuple(params))
            return [dict(row) for row in cursor.fetchall()]

    def get_all_products(self, category_id: Optional[int] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Returns all unique products from database with their latest recorded price.
        Optionally filtered by category_id.
        """
        join_clause = ""
        where_clause = ""
        params: List[Any] = []

        if category_id is not None:
            join_clause = "JOIN product_categories pc ON p.id = pc.product_id"
            where_clause = "WHERE pc.category_id = ?"
            params.append(category_id)

        query = f"""
        WITH latest_prices AS (
            SELECT 
                product_id,
                current_price,
                previous_price,
                is_marked_down,
                discount_percent,
                currency,
                ROW_NUMBER() OVER (PARTITION BY product_id ORDER BY id DESC) as rn
            FROM price_history
        )
        SELECT 
            p.id, p.product_code, p.name, p.brand, p.url, p.image_url, p.is_selling_fast,
            lp.current_price, lp.previous_price, lp.is_marked_down, lp.discount_percent, lp.currency
        FROM products p
        JOIN latest_prices lp ON p.id = lp.product_id AND lp.rn = 1
        {join_clause}
        {where_clause}
        ORDER BY p.id ASC
        """
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, tuple(params))
            return [dict(row) for row in cursor.fetchall()]

    def get_categories(self) -> List[Dict[str, Any]]:
        """
        Returns all registered categories with count of mapped products.
        """
        query = """
        SELECT c.id, c.slug, c.title, count(pc.product_id) as product_count
        FROM categories c
        LEFT JOIN product_categories pc ON c.id = pc.category_id
        GROUP BY c.id, c.slug, c.title
        ORDER BY c.id ASC
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            return [dict(row) for row in cursor.fetchall()]

