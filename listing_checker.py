#!/usr/bin/env python3
"""Check and clean a product spreadsheet before importing it into Shopify.

Usage:
    python listing_checker.py sample_data/products_raw.csv --out output
"""
import argparse
import csv
import re
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path

MAX_TITLE_LENGTH = 70

SHOPIFY_COLUMNS = [
    "Handle", "Title", "Body (HTML)", "Vendor", "Type", "Tags", "Published",
    "Variant SKU", "Variant Inventory Qty", "Variant Price",
    "Variant Compare At Price", "Variant Barcode", "Image Src",
]


def clean_text(value):
    """Trim the ends and squash repeated spaces inside the text."""
    return " ".join((value or "").split())


def parse_price(value):
    """Turn text such as 'EUR 12,50' or '€1,299.00' into a Decimal, or None if unreadable."""
    text = re.sub(r"[^\d.,-]", "", value or "")
    if not text:
        return None
    if "," in text and "." in text:
        text = text.replace(",", "")  # 1,299.00
    elif "," in text:
        whole, _, tail = text.rpartition(",")
        text = f"{whole}.{tail}" if len(tail) in (1, 2) else text.replace(",", "")
    try:
        return Decimal(text).quantize(Decimal("0.01"))
    except InvalidOperation:
        return None


def valid_ean13(code):
    """Check the length and the check digit of a 13-digit EAN barcode."""
    if not re.fullmatch(r"\d{13}", code or ""):
        return False
    digits = [int(d) for d in code]
    total = sum(d * (3 if i % 2 else 1) for i, d in enumerate(digits[:12]))
    return (10 - total % 10) % 10 == digits[12]


def make_handle(title):
    """Make the URL-friendly name Shopify uses to identify a product."""
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


def check_row(row, seen_skus, seen_barcodes):
    """Return (cleaned row, errors, warnings). An error stops a row being exported."""
    errors, warnings = [], []

    title = clean_text(row.get("title"))
    sku = clean_text(row.get("sku")).upper()
    barcode = clean_text(row.get("barcode"))
    price = parse_price(row.get("price"))
    compare_at = parse_price(row.get("compare_at_price"))
    image = clean_text(row.get("image_url"))
    stock_text = clean_text(row.get("stock"))

    if not title:
        errors.append("Missing title")
    elif len(title) > MAX_TITLE_LENGTH:
        warnings.append(f"Title is longer than {MAX_TITLE_LENGTH} characters")

    if not sku:
        errors.append("Missing SKU")
    elif sku in seen_skus:
        errors.append(f"Duplicate SKU (first seen on row {seen_skus[sku]})")

    if price is None:
        errors.append("Price missing or unreadable")
    elif price <= 0:
        errors.append("Price must be above zero")
    if compare_at is not None and price is not None and compare_at <= price:
        warnings.append("Compare-at price is not above the selling price")

    if not barcode:
        warnings.append("Missing barcode")
    elif not valid_ean13(barcode):
        errors.append("Barcode is not a valid EAN-13")
    elif barcode in seen_barcodes:
        errors.append(f"Duplicate barcode (first seen on row {seen_barcodes[barcode]})")

    if not image:
        warnings.append("Missing image")
    elif not image.lower().startswith("https://"):
        errors.append("Image link must start with https://")

    stock = None
    if re.fullmatch(r"-?\d+", stock_text):
        stock = int(stock_text)
        if stock < 0:
            errors.append("Stock cannot be negative")
    else:
        errors.append("Stock missing or not a whole number")

    clean = {
        "Handle": make_handle(title),
        "Title": title,
        "Body (HTML)": clean_text(row.get("description")),
        "Vendor": clean_text(row.get("vendor")),
        "Type": clean_text(row.get("category")),
        "Tags": clean_text(row.get("category")).lower(),
        "Published": "TRUE",
        "Variant SKU": sku,
        "Variant Inventory Qty": stock if stock is not None else "",
        "Variant Price": str(price) if price is not None else "",
        "Variant Compare At Price": str(compare_at) if compare_at is not None else "",
        "Variant Barcode": barcode,
        "Image Src": image,
    }
    return clean, errors, warnings


def process(rows):
    """Check all rows. Returns (rows ready for Shopify, list of issues)."""
    ready, issues = [], []
    seen_skus, seen_barcodes = {}, {}
    # Row 1 of the file is the header, so the data starts at row 2.
    for number, row in enumerate(rows, 2):
        clean, errors, warnings = check_row(row, seen_skus, seen_barcodes)
        sku = clean["Variant SKU"]
        if sku and sku not in seen_skus:
            seen_skus[sku] = number
        if clean["Variant Barcode"] and clean["Variant Barcode"] not in seen_barcodes:
            seen_barcodes[clean["Variant Barcode"]] = number
        issues += [{"row": number, "sku": sku, "level": "ERROR", "issue": e} for e in errors]
        issues += [{"row": number, "sku": sku, "level": "WARNING", "issue": w} for w in warnings]
        if not errors:
            ready.append(clean)
    return ready, issues


def main():
    parser = argparse.ArgumentParser(description="Check and clean a product file for Shopify import.")
    parser.add_argument("input", type=Path, help="CSV file of products")
    parser.add_argument("--out", type=Path, default=Path("output"), help="folder for the results")
    args = parser.parse_args()

    with args.input.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    ready, issues = process(rows)

    args.out.mkdir(parents=True, exist_ok=True)
    with (args.out / "shopify_import.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=SHOPIFY_COLUMNS)
        writer.writeheader()
        writer.writerows(ready)
    with (args.out / "issues_report.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["row", "sku", "level", "issue"])
        writer.writeheader()
        writer.writerows(issues)

    levels = Counter(i["level"] for i in issues)
    print(f"Products read:     {len(rows)}")
    print(f"Ready for Shopify: {len(ready)}")
    print(f"Held back:         {len(rows) - len(ready)}")
    print(f"Errors:            {levels['ERROR']}")
    print(f"Warnings:          {levels['WARNING']}")
    print(f"Results saved in:  {args.out}")


if __name__ == "__main__":
    main()
