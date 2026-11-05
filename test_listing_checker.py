from decimal import Decimal

from listing_checker import clean_text, make_handle, parse_price, process, valid_ean13


def good_row(**changes):
    row = {
        "title": "Ceramic Mug", "sku": "MUG-01", "barcode": "5901234123457", "price": "12.50",
        "compare_at_price": "", "stock": "10", "image_url": "https://example.ie/mug.jpg",
        "vendor": "Liffey Home", "category": "Kitchen", "description": "A mug.",
    }
    row.update(changes)
    return row


def issues_for(*rows):
    return [i["issue"] for i in process(list(rows))[1]]


def test_clean_text():
    assert clean_text("  Blue   Mug ") == "Blue Mug"
    assert clean_text(None) == ""


def test_parse_price_formats():
    assert parse_price("12.50") == Decimal("12.50")
    assert parse_price("€12,50") == Decimal("12.50")
    assert parse_price("EUR 1,299.00") == Decimal("1299.00")
    assert parse_price("1,299") == Decimal("1299.00")
    assert parse_price("free") is None
    assert parse_price("") is None


def test_ean13():
    assert valid_ean13("5901234123457")
    assert not valid_ean13("5901234123458")  # wrong check digit
    assert not valid_ean13("12345")


def test_handle():
    assert make_handle("Ceramic Mug - 350ml!") == "ceramic-mug-350ml"


def test_good_row_is_ready():
    ready, issues = process([good_row()])
    assert len(ready) == 1 and issues == []
    assert ready[0]["Handle"] == "ceramic-mug"
    assert ready[0]["Variant Price"] == "12.50"


def test_sku_is_tidied():
    ready, _ = process([good_row(sku=" mug-01 ")])
    assert ready[0]["Variant SKU"] == "MUG-01"


def test_duplicate_sku_held_back_and_first_kept():
    ready, issues = process([good_row(), good_row(barcode="4006381333931")])
    assert len(ready) == 1
    assert issues[0]["row"] == 3 and "Duplicate SKU" in issues[0]["issue"]


def test_duplicate_barcode_is_an_error():
    assert "Duplicate barcode" in issues_for(good_row(), good_row(sku="MUG-02"))[0]


def test_errors_hold_rows_back():
    for change, words in [
        ({"title": " "}, "Missing title"),
        ({"sku": ""}, "Missing SKU"),
        ({"price": "0"}, "above zero"),
        ({"price": "soon"}, "unreadable"),
        ({"stock": "-2"}, "negative"),
        ({"stock": "lots"}, "whole number"),
        ({"barcode": "111"}, "EAN-13"),
        ({"image_url": "http://example.ie/a.jpg"}, "https"),
    ]:
        ready, issues = process([good_row(**change)])
        assert ready == [], change
        assert any(words in i["issue"] and i["level"] == "ERROR" for i in issues), change


def test_warnings_do_not_hold_rows_back():
    for change in [{"barcode": ""}, {"image_url": ""}, {"title": "x" * 71},
                   {"compare_at_price": "5.00"}]:
        ready, issues = process([good_row(**change)])
        assert len(ready) == 1, change
        assert [i["level"] for i in issues] == ["WARNING"], change
