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
    export_category_samples,
    export_global_summary,
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


def display_deals_table(deals: list[dict], max_display: int = 15, title_prefix: str = "ASOS") -> None:
    if not deals:
        console.print(f"[yellow]No marked-down deals found for {title_prefix}.[/yellow]")
        return

    table = Table(
        title=f"[DEALS] {title_prefix} Top Marked-Down Deals (Showing {min(len(deals), max_display)} of {len(deals)} unique deals)",
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
        "--all-categories",
        action="store_true",
        help="Scrape all registered ASOS categories in sequence"
    )
    parser.add_argument(
        "--db-per-category",
        action="store_true",
        help="Use a separate SQLite database file for this specific category (data/categories/<slug>.db)"
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

    categories_to_scrape = list(CATEGORY_REGISTRY.keys()) if args.all_categories else [args.category_id]

    console.print(f"[bold green]Starting ASOS scraper for {len(categories_to_scrape)} category(ies)[/bold green]")
    console.print(f"[dim]Store: {resolved_store} | Country: {resolved_country} | Currency: {resolved_currency}[/dim]")
    console.print(f"[dim]Batch limit: {args.limit} | Items per category: {'ALL' if args.all else max_items}[/dim]\n")

    extractor = AsosExtractor(
        store=resolved_store,
        country=resolved_country,
        currency=resolved_currency
    )

    category_results: list[dict] = []

    try:
        for idx, cat_id in enumerate(categories_to_scrape, 1):
            cat_info = CATEGORY_REGISTRY.get(cat_id, {"slug": f"category_{cat_id}", "title": f"Category {cat_id}"})
            cat_slug = cat_info.get("slug", f"category_{cat_id}")
            cat_title = cat_info.get("title", f"Category {cat_id}")

            console.print(f"[bold cyan][{idx}/{len(categories_to_scrape)}] Processing: {cat_title} (ID: {cat_id})[/bold cyan]")

            db_path = Path(f"data/categories/{cat_slug}.db") if args.db_per_category else settings.DB_PATH
            db = AsosDatabase(db_path=db_path)

            collected_products = []
            try:
                for product in extractor.iter_category(
                    category_id=cat_id,
                    max_items=max_items,
                    limit=args.limit
                ):
                    collected_products.append(product)
            except Exception as exc:
                logger.error(f"Error scraping category {cat_id}: {exc}")
                console.print(f"[bold red]Failed to scrape {cat_title}:[/bold red] {exc}")
                continue

            # Persist to database linked to category
            db.upsert_products(collected_products, category_id=cat_id)

            category_deals = db.get_top_deals(category_id=cat_id, limit=100)
            category_products = db.get_all_products(category_id=cat_id)

            if not args.no_export:
                cat_exports = export_category_samples(
                    category_slug=cat_slug,
                    deals=category_deals,
                    products=category_products
                )

            category_results.append({
                "id": cat_id,
                "title": cat_title,
                "slug": cat_slug,
                "scraped_count": len(collected_products),
                "total_in_db": len(category_products),
                "deals_count": len(category_deals),
                "max_discount": f"-{category_deals[0]['discount_percent']:.1f}%" if category_deals else "-"
            })

            console.print(f"  [green]Extracted {len(collected_products)} items | {len(category_deals)} deals found | Saved to data/samples/{cat_slug}/[/green]\n")

    finally:
        extractor.close()

    # Display overall category summary table if multiple categories scraped
    if len(categories_to_scrape) > 1 and category_results:
        summary_table = Table(
            title="[CATALOG OVERVIEW] All Categories Scraping Summary",
            show_header=True,
            header_style="bold cyan"
        )
        summary_table.add_column("ID", style="dim", width=8)
        summary_table.add_column("Category", style="bold white")
        summary_table.add_column("Scraped Now", justify="right", style="green")
        summary_table.add_column("Total in DB", justify="right", style="magenta")
        summary_table.add_column("Deals (Discounts)", justify="right", style="yellow")
        summary_table.add_column("Top Discount", justify="right", style="bold red")

        for res in category_results:
            summary_table.add_row(
                str(res["id"]),
                res["title"],
                str(res["scraped_count"]),
                str(res["total_in_db"]),
                str(res["deals_count"]),
                res["max_discount"]
            )
        console.print(summary_table)

    # Display top deals table
    target_cat = None if args.all_categories else args.category_id
    title_pref = "All ASOS Categories" if args.all_categories else CATEGORY_REGISTRY.get(args.category_id, {}).get("title", "ASOS")
    main_db = AsosDatabase()
    all_deals = main_db.get_top_deals(category_id=target_cat, limit=100)
    display_deals_table(all_deals, max_display=15, title_prefix=title_pref)

    # Export global catalog summary
    if not args.no_export:
        global_deals = main_db.get_top_deals(category_id=None, limit=100)
        global_products = main_db.get_all_products(category_id=None)
        global_exports = export_global_summary(
            all_deals=global_deals,
            all_products=global_products
        )

        console.print(f"\n[cyan]Global catalog summary exported:[/cyan]")
        console.print(f" - [dim]Folder:[/dim] data/samples/summary/ (and root data/samples/)")
        console.print(f" - [bold]Global Deals ({len(global_deals)} items):[/bold] {global_exports['deals_csv']}")
        console.print(f" - [bold]Total Products ({len(global_products)} total in DB):[/bold] {global_exports['products_csv']}")



if __name__ == "__main__":
    main()

