import os
import sys
from decimal import Decimal

import pytest


# ------------------------------------------------------------
# Project paths
# ------------------------------------------------------------

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

SRC_PATH = os.path.join(
    PROJECT_ROOT,
    "src"
)

if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)


from extraction.invoice_parser import parse_invoice
from validation.validator import validate_invoice


# ------------------------------------------------------------
# Invoice directory
# ------------------------------------------------------------

INVOICE_DIRECTORY = os.path.join(
    PROJECT_ROOT,
    "data",
    "invoices"
)


# ------------------------------------------------------------
# Expected invoice results
# ------------------------------------------------------------

EXPECTED_INVOICES = [
    {
        "filename": "Invoice_1170959_For_Your_Order_E27473_20251229.pdf",
        "invoice_number": "1170959",
        "invoice_format": "standard",
        "po_number": "E27473",
        "invoice_total": "87.75",
        "line_items": 3,
    },
    {
        "filename": "Invoice_1170963_For_Your_Order_3117824_20251229.pdf",
        "invoice_number": "1170963",
        "invoice_format": "standard",
        "po_number": "3117824",
        "invoice_total": "1636.68",
        "line_items": 3,
    },
    {
        "filename": "Invoice_1171002_For_Your_Order_3117874_20251229.pdf",
        "invoice_number": "1171002",
        "invoice_format": "standard",
        "po_number": "3117874",
        "invoice_total": "122.50",
        "line_items": 1,
    },
    {
        "filename": "Invoice_1171035_For_Your_Order_E27468_20251229.pdf",
        "invoice_number": "1171035",
        "invoice_format": "standard",
        "po_number": "E27468",
        "invoice_total": "118.38",
        "line_items": 1,
    },
    {
        "filename": "Invoice_1171044_For_Your_Order_A27574_20251229.pdf",
        "invoice_number": "1171044",
        "invoice_format": "standard",
        "po_number": "A27574",
        "invoice_total": "146.25",
        "line_items": 1,
    },
    {
        "filename": "Invoice_1171155_For_Your_Order_N154821A_20251230.pdf",
        "invoice_number": "1171155",
        "invoice_format": "standard",
        "po_number": "N154821A",
        "invoice_total": "306.00",
        "line_items": 1,
    },
    {
        "filename": "Invoice_1171209_For_Your_Order_N154491_20251230.pdf",
        "invoice_number": "1171209",
        "invoice_format": "standard",
        "po_number": "N154491",
        "invoice_total": "1454.33",
        "line_items": 5,
    },
    {
        "filename": "Invoice_INV96777_1764104557634.pdf",
        "invoice_number": "INV96777",
        "invoice_format": "commodity_cables",
        "po_number": "E26824",
        "invoice_total": "84.00",
        "line_items": 2,
    },
    {
        "filename": "Invoice_INV97138_1764969109376.pdf",
        "invoice_number": "INV97138",
        "invoice_format": "commodity_cables",
        "po_number": "3117569",
        "invoice_total": "38700.00",
        "line_items": 1,
    },
    {
        "filename": "Invoice_INV97415_1765487918854.pdf",
        "invoice_number": "INV97415",
        "invoice_format": "commodity_cables",
        "po_number": "N153240",
        "invoice_total": "154.00",
        "line_items": 1,
    },
    {
        "filename": "Invoice_INV97748_1766180370436.pdf",
        "invoice_number": "INV97748",
        "invoice_format": "commodity_cables",
        "po_number": "N153950",
        "invoice_total": "205.00",
        "line_items": 1,
    },
    {
        "filename": "Invoice_INV97788_1766440182351.pdf",
        "invoice_number": "INV97788",
        "invoice_format": "commodity_cables",
        "po_number": "3117728",
        "invoice_total": "22107.06",
        "line_items": 3,
    },
]


# ------------------------------------------------------------
# Helper
# ------------------------------------------------------------

def invoice_path(filename):
    return os.path.join(
        INVOICE_DIRECTORY,
        filename
    )


# ------------------------------------------------------------
# Test invoice extraction
# ------------------------------------------------------------

@pytest.mark.parametrize(
    "expected",
    EXPECTED_INVOICES
)
def test_invoice_extraction(expected):

    path = invoice_path(
        expected["filename"]
    )

    assert os.path.exists(path), (
        f"Invoice sample not found: {path}"
    )

    invoice = parse_invoice(path)

    assert invoice["invoice_number"] == (
        expected["invoice_number"]
    )

    assert invoice["invoice_format"] == (
        expected["invoice_format"]
    )

    assert invoice["po_number"] == (
        expected["po_number"]
    )

    assert Decimal(
        invoice["invoice_total"]
    ) == Decimal(
        expected["invoice_total"]
    )

    assert len(
        invoice["line_items"]
    ) == expected["line_items"]


# ------------------------------------------------------------
# Test complete invoice validation
# ------------------------------------------------------------

@pytest.mark.parametrize(
    "expected",
    EXPECTED_INVOICES
)
def test_invoice_validation(expected):

    path = invoice_path(
        expected["filename"]
    )

    assert os.path.exists(path), (
        f"Invoice sample not found: {path}"
    )

    invoice = parse_invoice(path)

    result = validate_invoice(
        invoice
    )

    assert result["passed"] is True, (
        f"{expected['invoice_number']} "
        f"failed validation: "
        f"{result['errors']}"
    )


# ------------------------------------------------------------
# Test MFT calculation
# ------------------------------------------------------------

def test_standard_mft_calculation():

    path = invoice_path(
        "Invoice_1170959_For_Your_Order_E27473_20251229.pdf"
    )

    invoice = parse_invoice(path)

    first_item = invoice["line_items"][0]

    assert first_item["price_unit"] == "MFT"

    assert Decimal(
        first_item["ordered_quantity"]
    ) == Decimal("15")

    assert Decimal(
        first_item["unit_price"]
    ) == Decimal("1950.00000")

    assert Decimal(
        first_item["line_total"]
    ) == Decimal("29.25")


# ------------------------------------------------------------
# Test freight handling
# ------------------------------------------------------------

def test_standard_freight_handling():

    path = invoice_path(
        "Invoice_1170963_For_Your_Order_3117824_20251229.pdf"
    )

    invoice = parse_invoice(path)

    freight_items = [
        item
        for item in invoice["line_items"]
        if item["item_number"] == "F1"
    ]

    assert len(freight_items) == 1

    freight = freight_items[0]

    assert freight["description"] == (
        "FREIGHT CHARGE"
    )

    assert Decimal(
        freight["line_total"]
    ) == Decimal("219.18")