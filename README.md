# Shopify Listing Checker

A Python tool that checks a product spreadsheet for mistakes and prepares the good rows for Shopify import. I built it around the tasks in Irish e-commerce assistant jobs: uploading products and keeping titles, prices and barcodes accurate.

**All products in the sample file are made up.**

## What it checks

| Check | Result if it fails |
|---|---|
| Title is present | Error |
| SKU is present and not a duplicate | Error |
| Price can be read and is above zero | Error |
| Barcode is a valid EAN-13 and not a duplicate | Error |
| Image link uses https | Error |
| Stock is a whole number and not negative | Error |
| Title is 70 characters or fewer | Warning |
| Compare-at price is above the selling price | Warning |
| Barcode and image are present | Warning |

Rows with errors are held back. Rows with only warnings are still exported, and every problem is listed with its row number so it can be fixed in the original file.

It also tidies data as it goes: extra spaces, lower-case SKUs and prices such as `€7,95`.

## Run it

It needs Python 3 and nothing else.

```
python listing_checker.py sample_data/products_raw.csv --out output
```

With the sample file:

```
Products read:     15
Ready for Shopify: 6
Held back:         9
Errors:            9
Warnings:          4
```

It creates two files in the `output` folder:

- [`shopify_import.csv`](output/shopify_import.csv): clean rows using Shopify's column names
- [`issues_report.csv`](output/issues_report.csv): each problem, with its row number

## Tests

```
pip install pytest
pytest
```

The output columns are based on Shopify's product CSV format, but the file has not been imported into a live store. Do a small test import first.

Built with AI assistance (Claude Code).
