"""Unit tests for ASOS data models validation."""

import json
from pathlib import Path
import pytest
from src.models import AsosPrice, AsosProduct, AsosSearchResponse

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "search_sample.json"


@pytest.fixture
def raw_fixture_data() -> dict:
    with open(FIXTURE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def search_response(raw_fixture_data: dict) -> AsosSearchResponse:
    return AsosSearchResponse.model_validate(raw_fixture_data)


@pytest.mark.unit
def test_search_response_counts(search_response: AsosSearchResponse) -> None:
    """Verify total item count and parsed products list length."""
    assert search_response.itemCount == 1233
    assert len(search_response.products) == 16


@pytest.mark.unit
def test_first_product_validation(search_response: AsosSearchResponse) -> None:
    """Verify first product (id: 205774480) attributes."""
    product = search_response.products[0]
    assert product.id == 205774480
    assert product.price.current == 110.0
    assert product.price.previous is None
    assert product.price.isMarkedDown is False
    assert product.price.discount_percent == 0.0


@pytest.mark.unit
def test_discounted_product_validation(search_response: AsosSearchResponse) -> None:
    """Verify discounted product (id: 210252768, Superstar II) attributes and discount calculation."""
    matches = [p for p in search_response.products if p.id == 210252768]
    assert len(matches) == 1
    product = matches[0]
    assert "Superstar II" in product.name
    assert product.price.current == 89.99
    assert product.price.previous == 120.0
    assert product.price.isMarkedDown is True
    assert product.price.discount_percent == 25.0


@pytest.mark.unit
def test_product_urls_normalization(search_response: AsosSearchResponse) -> None:
    """Verify absolute URLs for product url and imageUrl attributes."""
    for product in search_response.products:
        assert product.url.startswith("https://www.asos.com/"), f"Unexpected url: {product.url}"
        assert product.imageUrl.startswith("https://images.asos-media.com/"), f"Unexpected imageUrl: {product.imageUrl}"
        for additional_url in product.additionalImageUrls:
            assert additional_url.startswith("https://"), f"Unexpected additionalImageUrl: {additional_url}"


@pytest.mark.unit
def test_price_model_standalone() -> None:
    """Test standalone price parsing and discount computation logic."""
    raw_price_nested = {
        "current": {"value": 75.0, "text": "£75.00"},
        "previous": {"value": 100.0, "text": "£100.00"},
        "rrp": {"value": 120.0, "text": "£120.00"},
        "lowestPriceInLast30Days": {"value": 70.0, "text": "£70.00"},
        "isMarkedDown": True,
        "isOutletPrice": False,
        "currency": "GBP",
    }
    price = AsosPrice.model_validate(raw_price_nested)
    assert price.current == 75.0
    assert price.previous == 100.0
    assert price.rrp == 120.0
    assert price.lowestPriceInLast30Days == 70.0
    assert price.currency == "GBP"
    assert price.isMarkedDown is True
    assert price.discount_percent == 25.0

    # Test edge case: no discount when previous is smaller or equal
    price_no_discount = AsosPrice(current=100.0, previous=100.0)
    assert price_no_discount.discount_percent == 0.0

    price_increased = AsosPrice(current=120.0, previous=100.0)
    assert price_increased.discount_percent == 0.0


@pytest.mark.unit
def test_product_url_validator_variations() -> None:
    """Test URL normalization with different input formats."""
    prod = AsosProduct.model_validate({
        "id": 1,
        "name": "Test Item",
        "productCode": 100,
        "brandName": "Test Brand",
        "price": {"current": {"value": 10.0}},
        "url": "/test-item/prd/1",
        "imageUrl": "//images.asos-media.com/test.jpg",
        "additionalImageUrls": ["images.asos-media.com/extra1.jpg", "https://images.asos-media.com/extra2.jpg"],
    })
    assert prod.url == "https://www.asos.com/test-item/prd/1"
    assert prod.imageUrl == "https://images.asos-media.com/test.jpg"
    assert prod.additionalImageUrls == [
        "https://images.asos-media.com/extra1.jpg",
        "https://images.asos-media.com/extra2.jpg",
    ]


@pytest.mark.unit
def test_null_image_url_handling() -> None:
    """Ensure null/None/empty imageUrl parses without ValidationError."""
    prod = AsosProduct.model_validate({
        "id": 2,
        "name": "Placeholder Item",
        "productCode": 200,
        "brandName": "Brand",
        "price": {"current": {"value": 50.0}},
        "url": "/item/2",
        "imageUrl": None,
    })
    assert prod.imageUrl == ""


@pytest.mark.unit
def test_language_sanitization(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure POSIX locales like en_US.UTF-8 from terminal environments are sanitized."""
    from config.settings import Settings
    from src.extractors.asos import AsosExtractor

    monkeypatch.setenv("LANG", "en_US.UTF-8")
    s = Settings()
    assert s.LANG == "en-GB"

    extractor = AsosExtractor(lang="en_US.UTF-8")
    assert extractor.lang == "en-GB"


@pytest.mark.unit
def test_database_category_relations(tmp_path: Path) -> None:
    """Test category mapping, isolation, and filtering in SQLite."""
    from src.pipelines.db import AsosDatabase

    test_db_path = tmp_path / "test_asos.db"
    db = AsosDatabase(db_path=test_db_path)

    # Mock products
    trainer = AsosProduct.model_validate({
        "id": 101,
        "name": "Nike Air Max",
        "productCode": 1001,
        "brandName": "Nike",
        "price": {
            "current": {"value": 80.0},
            "previous": {"value": 100.0},
            "isMarkedDown": True,
            "currency": "EUR"
        },
        "url": "/nike-air-max/prd/101",
        "imageUrl": "https://images.asos-media.com/101.jpg"
    })

    hoodie = AsosProduct.model_validate({
        "id": 202,
        "name": "Adidas Oversized Hoodie",
        "productCode": 2002,
        "brandName": "Adidas",
        "price": {
            "current": {"value": 50.0},
            "previous": {"value": 100.0},
            "isMarkedDown": True,
            "currency": "EUR"
        },
        "url": "/adidas-hoodie/prd/202",
        "imageUrl": "https://images.asos-media.com/202.jpg"
    })

    # Upsert with category IDs
    db.upsert_products([trainer], category_id=5775)
    db.upsert_products([hoodie], category_id=5668)

    # Check category product counts
    cats = {c["id"]: c["product_count"] for c in db.get_categories()}
    assert cats.get(5775) == 1
    assert cats.get(5668) == 1

    # Filtered deals
    trainer_deals = db.get_top_deals(category_id=5775)
    assert len(trainer_deals) == 1
    assert trainer_deals[0]["id"] == 101

    hoodie_deals = db.get_top_deals(category_id=5668)
    assert len(hoodie_deals) == 1
    assert hoodie_deals[0]["id"] == 202

    # Global deals
    all_deals = db.get_top_deals(category_id=None)
    assert len(all_deals) == 2

    # Filtered all products
    trainer_products = db.get_all_products(category_id=5775)
    assert len(trainer_products) == 1
    assert trainer_products[0]["id"] == 101


@pytest.mark.unit
def test_category_and_global_exports(tmp_path: Path) -> None:
    """Test exporting category samples and global summary files."""
    import csv
    from src.pipelines.export import export_category_samples, export_global_summary

    sample_deals = [
        {"id": 1, "name": "Item 1", "current_price": 50.0, "previous_price": 100.0, "discount_percent": 50.0}
    ]
    sample_products = [
        {"id": 1, "name": "Item 1", "current_price": 50.0, "is_marked_down": 1}
    ]

    # Category export
    cat_files = export_category_samples("test-slug", sample_deals, sample_products, base_dir=tmp_path)
    assert cat_files["deals_csv"].exists()
    assert cat_files["deals_json"].exists()
    assert cat_files["products_csv"].exists()
    assert cat_files["products_json"].exists()

    with open(cat_files["deals_csv"], "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
        assert len(rows) == 1
        assert rows[0]["id"] == "1"

    # Global summary export
    summary_files = export_global_summary(sample_deals, sample_products, summary_dir=tmp_path / "summary")
    assert summary_files["deals_csv"].exists()
    assert summary_files["deals_json"].exists()
    assert summary_files["products_csv"].exists()
    assert summary_files["products_json"].exists()


@pytest.mark.unit
def test_telegram_alerter_mock_mode() -> None:
    """Ensure TelegramAlerter operates smoothly in mock mode without credentials."""
    from src.alerts.telegram import TelegramAlerter

    alerter = TelegramAlerter(bot_token="", chat_id="", min_discount=50.0)
    assert not alerter.is_configured

    deals = [
        {"id": 1, "name": "Super Discount Item", "brand": "Nike", "current_price": 40.0, "previous_price": 100.0, "discount_percent": 60.0, "currency": "EUR", "url": "https://www.asos.com/1"},
        {"id": 2, "name": "Low Discount Item", "brand": "Puma", "current_price": 80.0, "previous_price": 100.0, "discount_percent": 20.0, "currency": "EUR", "url": "https://www.asos.com/2"},
    ]

    dispatched = alerter.notify_deals(deals)
    assert dispatched == 1

    # Test single alert formatting
    msg = alerter.format_deal_message(deals[0])
    assert "Super Discount Item" in msg
    assert "Nike" in msg
    assert "-60.0%" in msg
    assert "40.00 EUR" in msg
    assert "100.00 EUR" in msg


@pytest.mark.unit
def test_lifecycle_tracking_and_deactivation(tmp_path: Path) -> None:
    """Verify last_seen_at updates, is_active flag, and automatic deactivation."""
    import time
    from datetime import datetime, timezone
    from src.pipelines.db import AsosDatabase
    from src.models import AsosProduct

    db_path = tmp_path / "lifecycle_test.db"
    db = AsosDatabase(db_path=db_path)

    p1 = AsosProduct.model_validate({
        "id": 901,
        "name": "Product 1",
        "productCode": 90100,
        "brandName": "Brand A",
        "url": "https://www.asos.com/prod1",
        "price": {"current": {"value": 50.0}}
    })
    p2 = AsosProduct.model_validate({
        "id": 902,
        "name": "Product 2",
        "productCode": 90200,
        "brandName": "Brand B",
        "url": "https://www.asos.com/prod2",
        "price": {"current": {"value": 80.0}}
    })

    # Scrape 1: Both products found
    db.upsert_products([p1, p2], category_id=5775)

    active_prods = db.get_all_products(category_id=5775, active_only=True)
    assert len(active_prods) == 2
    for p in active_prods:
        assert p["is_active"] == 1
        assert p["last_seen_at"] is not None

    time.sleep(0.05)
    crawl_2_start = datetime.now(timezone.utc).isoformat()
    time.sleep(0.05)

    # Scrape 2: Only Product 1 is seen (Product 2 is missing/out of stock)
    db.upsert_products([p1], category_id=5775)

    # Deactivate unseen products for category 5775
    deactivated = db.deactivate_unseen_products(category_id=5775, scrape_start_time=crawl_2_start)
    assert deactivated == 1

    # Active only returns Product 1
    active_after = db.get_all_products(category_id=5775, active_only=True)
    assert len(active_after) == 1
    assert active_after[0]["id"] == 901

    # All products returns both, but Product 2 is inactive
    all_after = db.get_all_products(category_id=5775, active_only=False)
    assert len(all_after) == 2
    p2_record = next(p for p in all_after if p["id"] == 902)
    assert p2_record["is_active"] == 0

    # Categories list reflects active count vs total count
    cats = db.get_categories()
    cat_5775 = next(c for c in cats if c["id"] == 5775)
    assert cat_5775["product_count"] == 2
    assert cat_5775["active_count"] == 1




