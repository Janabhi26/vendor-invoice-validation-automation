from typing import Any, Dict, Optional


MONEY_TOLERANCE = 0.01
NUMBER_TOLERANCE = 0.01


def normalize_text(value: Any) -> Optional[str]:
    """Normalize text for reliable comparison."""

    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    return text.upper()


def to_float(value: Any) -> Optional[float]:
    """Convert a value to float."""

    if value is None:
        return None

    try:
        return float(
            str(value)
            .replace("$", "")
            .replace(",", "")
            .strip()
        )
    except (TypeError, ValueError):
        return None


def compare_text(
    field: str,
    invoice_value: Any,
    workbook_value: Any,
) -> Dict[str, Any]:
    """Compare two text values."""

    invoice_normalized = normalize_text(
        invoice_value
    )

    workbook_normalized = normalize_text(
        workbook_value
    )

    if (
        invoice_normalized is None
        or workbook_normalized is None
    ):
        return {
            "field": field,
            "invoice_value": invoice_value,
            "workbook_value": workbook_value,
            "status": "NOT_COMPARABLE",
        }

    status = (
        "MATCH"
        if invoice_normalized == workbook_normalized
        else "MISMATCH"
    )

    return {
        "field": field,
        "invoice_value": invoice_value,
        "workbook_value": workbook_value,
        "status": status,
    }


def compare_number(
    field: str,
    invoice_value: Any,
    workbook_value: Any,
) -> Dict[str, Any]:
    """Compare numeric values."""

    invoice_number = to_float(
        invoice_value
    )

    workbook_number = to_float(
        workbook_value
    )

    if (
        invoice_number is None
        or workbook_number is None
    ):
        return {
            "field": field,
            "invoice_value": invoice_value,
            "workbook_value": workbook_value,
            "status": "NOT_COMPARABLE",
        }

    difference = abs(
        invoice_number - workbook_number
    )

    status = (
        "MATCH"
        if difference <= NUMBER_TOLERANCE
        else "MISMATCH"
    )

    return {
        "field": field,
        "invoice_value": invoice_number,
        "workbook_value": workbook_number,
        "difference": round(difference, 2),
        "status": status,
    }


def compare_money(
    field: str,
    invoice_value: Any,
    workbook_value: Any,
) -> Dict[str, Any]:
    """Compare monetary values."""

    invoice_amount = to_float(
        invoice_value
    )

    workbook_amount = to_float(
        workbook_value
    )

    if (
        invoice_amount is None
        or workbook_amount is None
    ):
        return {
            "field": field,
            "invoice_value": invoice_value,
            "workbook_value": workbook_value,
            "status": "NOT_COMPARABLE",
        }

    difference = abs(
        invoice_amount - workbook_amount
    )

    status = (
        "MATCH"
        if difference <= MONEY_TOLERANCE
        else "MISMATCH"
    )

    return {
        "field": field,
        "invoice_value": invoice_amount,
        "workbook_value": workbook_amount,
        "difference": round(difference, 2),
        "status": status,
    }


def get_invoice_quantity(
    invoice_data: Dict[str, Any],
) -> Optional[float]:
    """
    Get the total invoice quantity.

    Standard invoices use shipped_quantity.

    Commodity invoices use quantity.

    If multiple line items exist, their quantities
    are summed.
    """

    line_items = invoice_data.get(
        "line_items",
        []
    )

    quantities = []

    for item in line_items:

        value = (
            item.get("shipped_quantity")
            or item.get("quantity")
        )

        number = to_float(value)

        if number is not None:
            quantities.append(number)

    if not quantities:
        return None

    return sum(quantities)


def get_invoice_unit_price(
    invoice_data: Dict[str, Any],
) -> Optional[float]:
    """
    Get the invoice unit price.

    If every line uses the same unit price,
    return that price.

    If multiple different prices exist, return None
    because one workbook Cost/M value cannot safely
    represent multiple invoice prices.
    """

    line_items = invoice_data.get(
        "line_items",
        []
    )

    prices = []

    for item in line_items:

        value = (
            item.get("unit_price")
            or item.get("sales_price")
            or item.get("price")
        )

        number = to_float(value)

        if number is not None:
            prices.append(number)

    if not prices:
        return None

    first_price = prices[0]

    if all(
        abs(price - first_price)
        <= NUMBER_TOLERANCE
        for price in prices
    ):
        return first_price

    return None


def get_invoice_product(
    invoice_data: Dict[str, Any],
) -> Optional[str]:
    """
    Get the invoice product description.

    A single workbook Product field can safely be
    compared only when the invoice contains one
    product line.
    """

    line_items = invoice_data.get(
        "line_items",
        []
    )

    if len(line_items) != 1:
        return None

    return line_items[0].get(
        "description"
    )


def get_invoice_freight(
    invoice_data: Dict[str, Any],
) -> Optional[float]:
    """
    Get explicit freight extracted from the invoice.

    IMPORTANT:
    invoice_total is NOT treated as freight.
    """

    return to_float(
        invoice_data.get("freight")
    )


def get_workbook_tracking(
    workbook_data: Dict[str, Any],
) -> Any:
    """Get whichever tracking field exists."""

    return (
        workbook_data.get("tracking_number")
        or workbook_data.get("tracing_number")
    )


def compare_invoice_to_workbook(
    invoice_data: Dict[str, Any],
    workbook_result: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Compare extracted invoice data against a Nassau
    workbook record.

    The workbook_result should come from
    NassauWorkbookReader.find_po().

    If the PO is not found, workbook_result will be None.
    """

    # --------------------------------------------------------
    # PO NOT FOUND
    # --------------------------------------------------------

    if workbook_result is None:

        return {
            "po_number": invoice_data.get(
                "po_number"
            ),
            "invoice_number": invoice_data.get(
                "invoice_number"
            ),
            "workbook_sheet": None,
            "matched_by": None,
            "overall_status": "PO NOT FOUND",
            "match_count": 0,
            "mismatch_count": 0,
            "not_comparable_count": 0,
            "comparisons": [],
        }

    workbook_data = workbook_result.get(
        "data",
        {}
    )

    comparisons = []

    # --------------------------------------------------------
    # PO
    # --------------------------------------------------------

    comparisons.append(
        compare_text(
            "PO",
            invoice_data.get("po_number"),
            workbook_data.get("po"),
        )
    )

    # --------------------------------------------------------
    # QTY
    # --------------------------------------------------------

    invoice_quantity = get_invoice_quantity(
        invoice_data
    )

    comparisons.append(
        compare_number(
            "QTY",
            invoice_quantity,
            workbook_data.get("qty"),
        )
    )

    # --------------------------------------------------------
    # Product
    # --------------------------------------------------------

    invoice_product = get_invoice_product(
        invoice_data
    )

    comparisons.append(
        compare_text(
            "Product",
            invoice_product,
            workbook_data.get("product"),
        )
    )

    # --------------------------------------------------------
    # Cost/M
    # --------------------------------------------------------

    invoice_unit_price = get_invoice_unit_price(
        invoice_data
    )

    comparisons.append(
        compare_money(
            "Cost/M",
            invoice_unit_price,
            workbook_data.get("cost_per_m"),
        )
    )

    # --------------------------------------------------------
    # Tracking
    # --------------------------------------------------------

    workbook_tracking = get_workbook_tracking(
        workbook_data
    )

    invoice_tracking = (
        invoice_data.get("tracking_number")
        or invoice_data.get("tracking")
    )

    comparisons.append(
        compare_text(
            "Tracking",
            invoice_tracking,
            workbook_tracking,
        )
    )

    # --------------------------------------------------------
    # Freight
    # --------------------------------------------------------

    invoice_freight = get_invoice_freight(
        invoice_data
    )

    comparisons.append(
        compare_money(
            "Freight",
            invoice_freight,
            workbook_data.get("freight"),
        )
    )

    # --------------------------------------------------------
    # Carrier
    # --------------------------------------------------------

    comparisons.append(
        compare_text(
            "Carrier",
            invoice_data.get("carrier"),
            workbook_data.get("carrier"),
        )
    )

    # --------------------------------------------------------
    # Count results
    # --------------------------------------------------------

    match_count = sum(
        item["status"] == "MATCH"
        for item in comparisons
    )

    mismatch_count = sum(
        item["status"] == "MISMATCH"
        for item in comparisons
    )

    not_comparable_count = sum(
        item["status"] == "NOT_COMPARABLE"
        for item in comparisons
    )

    # --------------------------------------------------------
    # Overall status
    #
    # NOT_COMPARABLE does not create a mismatch.
    # --------------------------------------------------------

    if mismatch_count > 0:
        overall_status = "MISMATCH"
    else:
        overall_status = "MATCH"

    return {
        "po_number": invoice_data.get(
            "po_number"
        ),
        "invoice_number": invoice_data.get(
            "invoice_number"
        ),
        "workbook_sheet": workbook_result.get(
            "sheet"
        ),
        "matched_by": workbook_result.get(
            "matched_by"
        ),
        "overall_status": overall_status,
        "match_count": match_count,
        "mismatch_count": mismatch_count,
        "not_comparable_count": not_comparable_count,
        "comparisons": comparisons,
    }


if __name__ == "__main__":
    print(
        "workbook_comparator.py loaded successfully."
    )
