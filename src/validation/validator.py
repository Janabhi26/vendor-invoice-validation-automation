import os
import sys
from decimal import Decimal, InvalidOperation


# ------------------------------------------------------------
# Project paths
# ------------------------------------------------------------

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../..")
)

EXTRACTION_PATH = os.path.join(
    PROJECT_ROOT,
    "src",
    "extraction"
)

if EXTRACTION_PATH not in sys.path:
    sys.path.insert(0, EXTRACTION_PATH)

from invoice_parser import parse_invoice


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def parse_amount(value):
    """Convert a currency/number value into Decimal."""

    if value is None:
        return None

    try:
        cleaned = (
            str(value)
            .replace("$", "")
            .replace(",", "")
            .strip()
        )

        if not cleaned:
            return None

        return Decimal(cleaned)

    except (InvalidOperation, ValueError):
        return None


def format_amount(value):
    """Format a number as currency."""

    if value is None:
        return "N/A"

    return f"${value:,.2f}"


# ------------------------------------------------------------
# Required field validation
# ------------------------------------------------------------

def validate_required_fields(invoice):
    """
    Validate the important fields that should exist
    on a vendor invoice.
    """

    required_fields = {
        "invoice_number": "Invoice Number",
        "invoice_date": "Invoice Date",
        "po_number": "PO Number",
        "customer": "Customer",
        "invoice_total": "Invoice Total",
    }

    missing = []

    for field, label in required_fields.items():

        value = invoice.get(field)

        if value is None or str(value).strip() == "":
            missing.append(label)

    return missing


# ------------------------------------------------------------
# Line item calculation
# ------------------------------------------------------------

def calculate_expected_line_total(
    quantity,
    unit_price,
    price_unit=None,
    unit=None
):
    """
    Calculate the expected line total.

    Standard invoices may use MFT pricing.

    MFT = price per 1,000 feet.

    Example:
        15 FT × $1,950/MFT
        = 15 × 1,950 / 1,000
        = $29.25

    EA pricing is calculated normally:

        1 EA × $219.18/EA
        = $219.18

    Commodity Cables invoices also use their extracted
    quantity and sales price directly.
    """

    if quantity is None or unit_price is None:
        return None

    price_unit_normalized = (
        str(price_unit).strip().upper()
        if price_unit is not None
        else ""
    )

    unit_normalized = (
        str(unit).strip().upper()
        if unit is not None
        else ""
    )

    # --------------------------------------------------------
    # MFT = price per thousand feet
    # --------------------------------------------------------

    if price_unit_normalized == "MFT":

        return (
            quantity
            * unit_price
            / Decimal("1000")
        )

    # --------------------------------------------------------
    # Normal per-unit pricing
    #
    # EA, PCS, FT, etc.
    # --------------------------------------------------------

    return quantity * unit_price


# ------------------------------------------------------------
# Line item validation
# ------------------------------------------------------------

def validate_line_items(invoice):
    """
    Validate extracted line items.

    Checks:

        quantity × unit price = line total

    For MFT pricing:

        quantity × unit price / 1000 = line total

    Also calculates the total of all extracted line items.
    """

    line_items = invoice.get("line_items", [])

    if not line_items:

        return {
            "passed": False,
            "errors": [
                "No line items were extracted."
            ],
            "calculated_total": Decimal("0"),
        }

    errors = []

    calculated_total = Decimal("0")

    for index, item in enumerate(
        line_items,
        start=1
    ):

        # ----------------------------------------------------
        # Quantity
        # ----------------------------------------------------

        quantity = parse_amount(
            item.get("quantity")
            or item.get("ordered_quantity")
        )

        # ----------------------------------------------------
        # Unit price
        # ----------------------------------------------------

        unit_price = parse_amount(
            item.get("sales_price")
            or item.get("unit_price")
            or item.get("price")
        )

        # ----------------------------------------------------
        # Invoice line total
        # ----------------------------------------------------

        line_total = parse_amount(
            item.get("line_total")
            or item.get("total")
            or item.get("extension")
        )

        # ----------------------------------------------------
        # Price unit
        # ----------------------------------------------------

        price_unit = (
            item.get("price_unit")
            or item.get("unit")
        )

        unit = item.get("unit")

        # ----------------------------------------------------
        # A line must have a total so it can contribute to
        # the invoice total.
        # ----------------------------------------------------

        if line_total is None:

            errors.append(
                f"Line {index}: "
                f"line total could not be extracted."
            )

            continue

        # Include the invoice's actual line total when
        # calculating the overall invoice total.
        calculated_total += line_total

        # ----------------------------------------------------
        # Some invoice lines may not have enough information
        # to independently calculate the line total.
        # ----------------------------------------------------

        if quantity is None or unit_price is None:
            continue

        # ----------------------------------------------------
        # Calculate expected amount.
        # ----------------------------------------------------

        expected_total = calculate_expected_line_total(
            quantity,
            unit_price,
            price_unit,
            unit
        )

        if expected_total is None:
            continue

        difference = abs(
            expected_total - line_total
        )

        # ----------------------------------------------------
        # Allow one cent rounding difference.
        # ----------------------------------------------------

        if difference > Decimal("0.01"):

            price_description = (
                f"{unit_price}"
            )

            if price_unit:
                price_description += (
                    f" per {price_unit}"
                )

            errors.append(
                f"Line {index}: "
                f"{quantity} × "
                f"{price_description}"
                f"{' / 1000' if str(price_unit).upper() == 'MFT' else ''}"
                f" = {expected_total:.2f}, "
                f"but invoice shows "
                f"{line_total:.2f}."
            )

    return {
        "passed": len(errors) == 0,
        "errors": errors,
        "calculated_total": calculated_total,
    }


# ------------------------------------------------------------
# Invoice total validation
# ------------------------------------------------------------

def validate_invoice_total(
    invoice,
    calculated_total
):
    """
    Compare the sum of extracted line totals
    with the invoice's final total.
    """

    invoice_total = parse_amount(
        invoice.get("invoice_total")
    )

    if invoice_total is None:

        return {
            "passed": False,
            "message": (
                "Invoice total could not be extracted."
            )
        }

    difference = abs(
        invoice_total - calculated_total
    )

    if difference <= Decimal("0.01"):

        return {
            "passed": True,
            "message": (
                f"Line items total "
                f"{format_amount(calculated_total)} "
                f"matches invoice total "
                f"{format_amount(invoice_total)}."
            )
        }

    return {
        "passed": False,
        "message": (
            f"Line items total "
            f"{format_amount(calculated_total)} "
            f"does not match invoice total "
            f"{format_amount(invoice_total)}."
        )
    }


# ------------------------------------------------------------
# Complete invoice validation
# ------------------------------------------------------------

def validate_invoice(invoice):
    """
    Run all validations against one invoice.
    """

    result = {
        "passed": True,
        "required_fields": True,
        "line_items": True,
        "invoice_total": True,
        "errors": [],
    }

    # --------------------------------------------------------
    # Required fields
    # --------------------------------------------------------

    missing_fields = validate_required_fields(
        invoice
    )

    if missing_fields:

        result["required_fields"] = False
        result["passed"] = False

        result["errors"].append(
            "Missing required fields: "
            + ", ".join(missing_fields)
        )

    # --------------------------------------------------------
    # Line items
    # --------------------------------------------------------

    line_result = validate_line_items(
        invoice
    )

    if not line_result["passed"]:

        result["line_items"] = False
        result["passed"] = False

        result["errors"].extend(
            line_result["errors"]
        )

    # --------------------------------------------------------
    # Invoice total
    # --------------------------------------------------------

    total_result = validate_invoice_total(
        invoice,
        line_result["calculated_total"]
    )

    if not total_result["passed"]:

        result["invoice_total"] = False
        result["passed"] = False

        result["errors"].append(
            total_result["message"]
        )

    return result


# ------------------------------------------------------------
# Display helpers
# ------------------------------------------------------------

def print_invoice_result(
    filename,
    invoice,
    result
):
    """Print validation results for one invoice."""

    print()
    print("=" * 64)
    print(
        f"PROCESSING: {filename}"
    )
    print("=" * 64)

    print(
        f"Invoice Number : "
        f"{invoice.get('invoice_number', 'N/A')}"
    )

    print(
        f"Invoice Format : "
        f"{invoice.get('invoice_format', 'N/A')}"
    )

    print(
        f"PO Number      : "
        f"{invoice.get('po_number', 'N/A')}"
    )

    print(
        f"Customer       : "
        f"{invoice.get('customer', 'N/A')}"
    )

    print(
        f"Invoice Total  : "
        f"{format_amount(parse_amount(invoice.get('invoice_total')))}"
    )

    print(
        f"Line Items     : "
        f"{len(invoice.get('line_items', []))}"
    )

    print()
    print("VALIDATION")

    if result["required_fields"]:
        print("  ✅ Required fields")
    else:
        print("  ❌ Required fields")

    if result["line_items"]:
        print("  ✅ Line item calculations")
    else:
        print("  ❌ Line item calculations")

    if result["invoice_total"]:
        print("  ✅ Invoice total")
    else:
        print("  ❌ Invoice total")

    print()

    if result["passed"]:

        print("  ✅ PASS")

    else:

        print("  ❌ FAIL")

        for error in result["errors"]:

            print(
                f"     • {error}"
            )


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------

def main():

    invoice_directory = os.path.join(
        PROJECT_ROOT,
        "data",
        "invoices"
    )

    print()
    print("=" * 64)
    print(
        "VENDOR INVOICE VALIDATION AUTOMATION"
    )
    print("=" * 64)

    print()
    print(
        "Invoice directory:"
    )
    print(invoice_directory)

    if not os.path.isdir(
        invoice_directory
    ):

        print()
        print(
            "❌ Invoice directory does not exist."
        )

        return

    pdf_files = sorted(
        [
            filename
            for filename in os.listdir(
                invoice_directory
            )
            if filename.lower().endswith(".pdf")
        ]
    )

    print(
        f"Found {len(pdf_files)} "
        f"PDF invoice(s)."
    )

    passed_count = 0
    failed_count = 0

    results = []

    # --------------------------------------------------------
    # Process every invoice
    # --------------------------------------------------------

    for filename in pdf_files:

        file_path = os.path.join(
            invoice_directory,
            filename
        )

        try:

            invoice = parse_invoice(
                file_path
            )

            result = validate_invoice(
                invoice
            )

            results.append(
                (
                    filename,
                    result["passed"]
                )
            )

            if result["passed"]:
                passed_count += 1
            else:
                failed_count += 1

            print_invoice_result(
                filename,
                invoice,
                result
            )

        except Exception as error:

            failed_count += 1

            results.append(
                (
                    filename,
                    False
                )
            )

            print()
            print("=" * 64)
            print(
                f"PROCESSING: {filename}"
            )
            print("=" * 64)

            print(
                f"❌ ERROR: {error}"
            )

    # --------------------------------------------------------
    # Final summary
    # --------------------------------------------------------

    print()
    print("=" * 64)
    print("FINAL SUMMARY")
    print("=" * 64)

    print()
    print(
        f"Total invoices : {len(pdf_files)}"
    )

    print(
        f"Passed         : {passed_count}"
    )

    print(
        f"Failed         : {failed_count}"
    )

    print()
    print("-" * 64)

    for filename, passed in results:

        status = (
            "✅ PASS"
            if passed
            else "❌ FAIL"
        )

        print(
            f"{status}  {filename}"
        )

    print()
    print("-" * 64)

    if failed_count == 0:

        print(
            "🎉 All invoices passed validation."
        )

    else:

        print(
            f"⚠️ {failed_count} "
            f"invoice(s) need attention."
        )

    print()


if __name__ == "__main__":
    main()