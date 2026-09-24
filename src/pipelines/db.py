import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from loguru import logger

from config.settings import settings


class AsosDatabase:
    """
    SQLite persistence layer for ASOS catalog and historical price monitoring.
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
            CREATE INDEX IF NOT EXISTS idx_price_product ON price_history(product_id)
            """)
            cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_price_discount ON price_history(discount_percent DESC)
            """)
            conn.commit()

    def upsert_products(self, products: List[Any]) -> int:
        """
        Upserts products into 'products' and appends a record to 'price_history'.
        """
        if not products:
            return 0

        inserted_count = 0
        now = datetime.utcnow().isoformat()

        with self._get_connection() as conn:
            cursor = conn.cursor()
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
                inserted_count += 1

            conn.commit()

        logger.info(f"Saved {inserted_count} products and price records into {self.db_path}")
        return inserted_count

    def get_top_deals(self, limit: Optional[int] = 50) -> List[Dict[str, Any]]:
        """
        Returns top discounted products (deduplicated by latest price entry) sorted by discount_percent descending.
        """
        query = """
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
        WHERE lp.is_marked_down = 1
        ORDER BY lp.discount_percent DESC
        """
        params = ()
        if limit is not None:
            query += " LIMIT ?"
            params = (limit,)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_all_products(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Returns all unique products from database with their latest recorded price.
        """
        query = """
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
        ORDER BY p.id ASC
        """
        params = ()
        if limit is not None:
            query += " LIMIT ?"
            params = (limit,)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

