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
        logger.warning(f"No products to export to CSV at {output_path}.")
        return output_path

    fieldnames = list(products[0].keys())
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(products)
    logger.info(f"Exported {len(products)} products to {output_path}")
    return output_path


def export_category_samples(
    category_slug: str,
    deals: List[Dict[str, Any]],
    products: List[Dict[str, Any]],
    base_dir: Path = settings.SAMPLES_DIR
) -> Dict[str, Path]:
    """
    Exports category-specific deals and products into data/samples/{category_slug}/.
    """
    cat_dir = base_dir / category_slug
    cat_dir.mkdir(parents=True, exist_ok=True)

    deals_csv = export_deals_to_csv(deals, output_path=cat_dir / "deals.csv")
    deals_json = export_deals_to_json(deals, output_path=cat_dir / "deals.json")
    products_csv = export_all_products_to_csv(products, output_path=cat_dir / "products.csv")
    products_json = export_all_products_to_json(products, output_path=cat_dir / "products.json")

    return {
        "deals_csv": deals_csv,
        "deals_json": deals_json,
        "products_csv": products_csv,
        "products_json": products_json,
    }


def export_global_summary(
    all_deals: List[Dict[str, Any]],
    all_products: List[Dict[str, Any]],
    summary_dir: Path = settings.SAMPLES_DIR / "summary"
) -> Dict[str, Path]:
    """
    Exports aggregated cross-category summary into data/samples/summary/ and root data/samples/.
    """
    summary_dir.mkdir(parents=True, exist_ok=True)

    # In data/samples/summary/
    deals_csv = export_deals_to_csv(all_deals, output_path=summary_dir / "global_deals.csv")
    deals_json = export_deals_to_json(all_deals, output_path=summary_dir / "global_deals.json")
    products_csv = export_all_products_to_csv(all_products, output_path=summary_dir / "global_products.csv")
    products_json = export_all_products_to_json(all_products, output_path=summary_dir / "global_products.json")

    # Also update backward-compatible root files data/samples/deals.csv and data/samples/all_products.csv
    export_deals_to_csv(all_deals, output_path=settings.SAMPLES_DIR / "deals.csv")
    export_deals_to_json(all_deals, output_path=settings.SAMPLES_DIR / "deals.json")
    export_all_products_to_csv(all_products, output_path=settings.SAMPLES_DIR / "all_products.csv")
    export_all_products_to_json(all_products, output_path=settings.SAMPLES_DIR / "all_products.json")

    return {
        "deals_csv": deals_csv,
        "deals_json": deals_json,
        "products_csv": products_csv,
        "products_json": products_json,
    }

