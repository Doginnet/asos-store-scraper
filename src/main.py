import argparse
import sys
from pathlib import Path
from rich.console import Console
from rich.table import Table

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import settings
from config.categories import AsosCategory, CATEGORY_REGISTRY, resolve_store_and_currency
from src.extractors.asos import AsosExtractor
from src.pipelines.db import AsosDatabase
from src.pipelines.export import (
    export_deals_to_csv,
    export_deals_to_json,
    export_all_products_to_csv,
    export_all_products_to_json
)
from src.utils.logger import logger

# Ensure UTF-8 output encoding on Windows consoles
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

console = Console(highlight=False)


def display_deals_table(deals: list[dict], max_display: int = 15) -> None:
    if not deals:
        console.print("[yellow]No marked-down deals found in the current selection.[/yellow]")
        return

    table = Table(
        title=f"[DEALS] ASOS Top Marked-Down Deals (Showing {min(len(deals), max_display)} of {len(deals)} unique deals)",
        show_header=True,
        header_style="bold magenta"
    )
    table.add_column("ID", style="dim", width=10)
    table.add_column("Brand", style="cyan")
    table.add_column("Product Name", style="white", max_width=45)
    table.add_column("Current Price", justify="right", style="green")
    table.add_column("Old Price", justify="right", style="red")
    table.add_column("Discount", justify="right", style="bold yellow")

    for d in deals[:max_display]:
        current = f"{d['current_price']:.2f} {d['currency']}"
        prev = f"{d['previous_price']:.2f} {d['currency']}" if d.get('previous_price') else "-"
        disc = f"-{d['discount_percent']:.1f}%" if d.get('discount_percent') else "-"
        table.add_row(str(d['id']), d['brand'], d['name'], current, prev, disc)

    console.print(table)


def main() -> None:
    parser = argparse.ArgumentParser(description="ASOS E-commerce Catalog Extractor & Price Monitor")
    parser.add_argument(
        "--category-id", "-c",
        type=int,
        default=AsosCategory.TRAINERS,
        help="ASOS category ID (default: 5775 for Trainers)"
    )
    parser.add_argument(
        "--limit", "-l",
        type=int,
        default=settings.DEFAULT_LIMIT,
        help=f"Page size per request (default: {settings.DEFAULT_LIMIT})"
    )
    parser.add_argument(
        "--max-items", "-m",
        type=int,
        default=144,
        help="Maximum total items to fetch (default: 144). Use --all to scrape the whole category."
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Scrape all available products in the category (ignores --max-items)"
    )
    parser.add_argument(
        "--country",
        type=str,
        default=settings.COUNTRY,
        help=f"Country code (default: {settings.COUNTRY})"
    )
    parser.add_argument(
        "--store",
        type=str,
        default=None,
        help="ASOS store code (default: auto-resolved from country)"
    )
    parser.add_argument(
        "--no-export",
        action="store_true",
        help="Skip exporting samples to CSV/JSON"
    )

    args = parser.parse_args()

    max_items = None if args.all else args.max_items

    resolved_country, resolved_store, resolved_currency = resolve_store_and_currency(
        country=args.country,
        store=args.store
    )

    cat_info = CATEGORY_REGISTRY.get(args.category_id, {"title": f"Category {args.category_id}"})
    console.print(f"[bold green]Starting ASOS scraper for: {cat_info['title']} (ID: {args.category_id})[/bold green]")
    console.print(f"[dim]Store: {resolved_store} | Country: {resolved_country} | Currency: {resolved_currency}[/dim]")
    console.print(f"[dim]Batch limit: {args.limit} | Max items: {'ALL' if args.all else max_items}[/dim]\n")

    extractor = AsosExtractor(
        store=resolved_store,
        country=resolved_country,
        currency=resolved_currency
    )
    db = AsosDatabase()

    collected_products = []
    try:
        for product in extractor.iter_category(
            category_id=args.category_id,
            max_items=max_items,
            limit=args.limit
        ):
            collected_products.append(product)

    except Exception as exc:
        logger.error(f"Error during extraction: {exc}")
        console.print(f"[bold red]Extraction failed:[/bold red] {exc}")
        sys.exit(1)
    finally:
        extractor.close()

    console.print(f"\n[bold green]Successfully extracted {len(collected_products)} products.[/bold green]")

    # Persist to database
    db.upsert_products(collected_products)

    # Get deduplicated deals and all products
    deals = db.get_top_deals(limit=100)
    all_db_products = db.get_all_products()

    # Display deduplicated deals
    display_deals_table(deals, max_display=15)

    # Export to samples
    if not args.no_export:
        deals_csv = export_deals_to_csv(deals)
        deals_json = export_deals_to_json(deals)
        all_csv = export_all_products_to_csv(all_db_products)
        all_json = export_all_products_to_json(all_db_products)
        
        console.print(f"\n[cyan]Samples exported successfully:[/cyan]")
        console.print(f" - [bold]Deals (Discounted only, {len(deals)} items):[/bold] {deals_csv} & {deals_json}")
        console.print(f" - [bold]All Products ({len(all_db_products)} total in DB):[/bold] {all_csv} & {all_json}")


if __name__ == "__main__":
    main()
