import csv
import json
from pathlib import Path
from typing import Any, Dict, List
from loguru import logger

from config.settings import settings


def export_deals_to_json(deals: List[Dict[str, Any]], output_path: Path = settings.SAMPLES_DIR / "deals.json") -> Path:
    """Exports deals to formatted JSON file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(deals, f, ensure_ascii=False, indent=2)
    logger.info(f"Exported {len(deals)} unique deals to {output_path}")
    return output_path


def export_deals_to_csv(deals: List[Dict[str, Any]], output_path: Path = settings.SAMPLES_DIR / "deals.csv") -> Path:
    """Exports deals to CSV file with readable formatting."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not deals:
        logger.warning("No deals to export to CSV.")
        return output_path

    fieldnames = list(deals[0].keys())
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(deals)
    logger.info(f"Exported {len(deals)} unique deals to {output_path}")
    return output_path


def export_all_products_to_json(products: List[Dict[str, Any]], output_path: Path = settings.SAMPLES_DIR / "all_products.json") -> Path:
    """Exports all scraped catalog products to JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)
    logger.info(f"Exported {len(products)} products to {output_path}")
    return output_path


def export_all_products_to_csv(products: List[Dict[str, Any]], output_path: Path = settings.SAMPLES_DIR / "all_products.csv") -> Path:
    """Exports all scraped catalog products to CSV."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not products:
        logger.warning("No products to export to CSV.")
        return output_path

    fieldnames = list(products[0].keys())
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(products)
    logger.info(f"Exported {len(products)} products to {output_path}")
    return output_path
