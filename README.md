# Vendor Invoice Validation Automation

Automation for extracting and validating vendor invoice data from PDF invoices and comparing extracted invoice data against the Nassau workbook.

## Overview

This project processes vendor invoice PDFs, identifies the invoice format, extracts invoice information and line items, validates the extracted invoice data, and compares available invoice fields with the corresponding Nassau workbook record.

The current implementation supports two invoice formats:

- Standard vendor invoices
- Commodity Cables invoices

The validation workflow is:

```text
PDF Invoice
    ↓
Invoice Extraction
    ↓
Invoice Validation
    ↓
PO Lookup in Nassau Workbook
    ↓
Workbook Field Comparison
    ↓
CSV Validation Report
## Validation

### Invoice Validation

The invoice validator checks:

- Required invoice fields
- Line-item calculations
- Quantity × unit price
- MFT pricing
- Invoice total versus extracted line-item totals

For MFT pricing, the price represents the cost per 1,000 feet.

Example:

```text
15 FT × $1,950/MFT
= 15 × 1,950 / 1,000
= $29.25A one-cent rounding tolerance is allowed for calculations.

### Workbook Validation

The application uses the Nassau workbook to look up the invoice PO and compare available fields.

The current comparison fields include:

- PO
- Quantity
- Product
- Cost/M
- Tracking
- Freight
- Carrier

The workbook reader searches the configured Nassau workbook worksheets and can also use the `Split Order PO#` field when appropriate.

### Comparison Statuses

Workbook comparisons can produce:

```text
MATCH
MISMATCH
PO NOT FOUND
NOT_COMPARABLE
## Supported Invoice Formats

### Standard Invoices

Standard invoices may contain:

- Invoice number
- Invoice date
- Customer
- Purchase order number
- Ship-to information
- Tracking number
- Line items
- Unit price
- Price unit
- Invoice total

The parser supports multiple line items and MFT pricing.

### Commodity Cables Invoices

Commodity Cables invoices may contain:

- Invoice number
- Invoice date
- Customer
- Purchase order number
- Tracking number
- Line items
- Quantity
- Sales price
- Line total
- Invoice total
## Project Structure

```text
vendor-invoice-validation-automation/
│
├── config/
│
├── data/
│   ├── invoices/
│   │   └── Vendor invoice PDFs
│   │
│   └── output/
│       └── validation_report.csv
│
├── src/
│   ├── extraction/
│   │   └── invoice_parser.py
│   │
│   └── validation/
│       ├── validator.py
│       ├── workbook_reader.py
│       └── workbook_comparator.py
│
├── tests/
│   ├── test_invoice_validation.py
│   └── test_workbook_validation.py
│
├── .gitignore
├── README.md
└── requirements.txt
## Requirements

- Python 3.14.6
- PyMuPDF
- openpyxl
- pytest

## Setup

Clone the repository:

```bash
git clone https://github.com/Janabhi26/vendor-invoice-validation-automation.git
cd vendor-invoice-validation-automation
Create a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
## Input Files

Place vendor invoice PDFs in:

data/invoices/

Place the Nassau workbook in:

data/Nassau.xlsx

The workbook and invoice input files are excluded from Git through .gitignore.
## Running the Validator

Run:

python -m src.validation.validator

The application will:

1. Find PDF invoices in data/invoices/
2. Extract invoice data
3. Validate each invoice
4. Look up the invoice PO in the Nassau workbook
5. Compare available workbook fields
6. Display the results in the terminal
7. Generate a CSV report

## Validation Report

The generated report is:

data/output/validation_report.csv

The report contains:

- Invoice Number
- Invoice Date
- Invoice Format
- PO Number
- Invoice Total
- Invoice Validation
- Workbook Sheet
- Workbook Match
- PO Match
- Quantity Match
- Product Match
- Cost/M Match
- Tracking Match
- Freight Match
- Carrier Match
- Error Details

Generated output files are excluded from Git.
## Running Tests

Run the complete test suite:

python -m pytest

The test suite covers invoice validation and workbook comparison behavior.

## Current Data Validation Note

The current test run contains 12 invoice PDFs.

All 12 invoices passed the invoice-level validation:

Passed: 12
Failed: 0

For the current Nassau workbook, none of the 12 invoice POs were found.

Therefore:

POs found: 0
POs not found: 12
Workbook mismatches: 0

This means the current invoice dataset does not provide matching invoice/workbook PO pairs for demonstrating real workbook MATCH or MISMATCH results.

The application reports these cases as PO NOT FOUND instead of inventing or assuming workbook matches.
## Development

Before committing changes, run:

python -m pytest

Then check the Git working tree:

git status

Generated invoice data and validation reports should remain excluded from Git.

## Repository

GitHub:

https://github.com/Janabhi26/vendor-invoice-validation-automation.git
