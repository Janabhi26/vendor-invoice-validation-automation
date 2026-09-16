from typing import Any, Dict, Optional


MONEY_TOLERANCE = 0.01
NUMBER_TOLERANCE = 0.01


def normalize_text(value: Any) -> Optional[str]:
    """Normalize text for comparison."""

    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    return text.upper()


def to_float(value: Any) -> Optional[float]:
    """Convert a value to float when possible."""

    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def compare_text(
    field: str,
    invoice_value: Any,
    workbook_value: Any,
) -> Dict[str, Any]:
    """Compare two text values."""

    invoice_text = normalize_text(invoice_value)
    workbook_text = normalize_text(workbook_value)

    if invoice_text is None or workbook_text is None:

        return {
            "field": field,
            "invoice_value": invoice_value,
            "workbook_value": workbook_value,
            "status": "NOT_COMPARABLE",
        }

    return {
        "field": field,
        "invoice_value": invoice_value,
        "workbook_value": workbook_value,
        "status": (
            "MATCH"
            if invoice_text == workbook_text
            else "MISMATCH"
        ),
    }


def compare_number(
    field: str,
    invoice_value: Any,
    workbook_value: Any,
    tolerance: float = NUMBER_TOLERANCE,
) -> Dict[str, Any]:
    """Compare numeric values."""

    invoice_number = to_float(invoice_value)
    workbook_number = to_float(workbook_value)

    if invoice_number is None or workbook_number is None:

        return {
            "field": field,
            "invoice_value": invoice_value,
            "workbook_value": workbook_value,
            "status": "NOT_COMPARABLE",
        }

    difference = abs(
        invoice_number - workbook_number
    )

    return {
        "field": field,
        "invoice_value": invoice_number,
        "workbook_value": workbook_number,
        "difference": round(difference, 2),
        "status": (
            "MATCH"
            if difference <= tolerance
            else "MISMATCH"
        ),
    }


def compare_money(
    field: str,
    invoice_value: Any,
    workbook_value: Any,
) -> Dict[str, Any]:
    """Compare monetary values."""

    return compare_number(
        field,
        invoice_value,
        workbook_value,
        MONEY_TOLERANCE,
    )


def get_invoice_quantity(
    invoice_data: Dict[str, Any],
) -> Optional[float]:
    """
    Get the invoice quantity.

    Standard invoices use shipped_quantity.
    Commodity invoices use quantity.
    """

    line_items = invoice_data.get(
        "line_items",
        [],
    )

    quantities = []

    for item in line_items:

        quantity = (
            item.get("shipped_quantity")
            if item.get("shipped_quantity") is not None
            else item.get("quantity")
        )

        number = to_float(quantity)

        if number is not None:
            quantities.append(number)

    if not quantities:
        return None

    return sum(quantities)


def get_invoice_unit_price(
    invoice_data: Dict[str, Any],
) -> Optional[float]:
    """
    Get the invoice price.

    Standard invoices use unit_price.
    Commodity invoices use sales_price.

    If all line items have the same price, that price
    is returned. If they have different prices, the
    value is left as not directly comparable.
    """

    line_items = invoice_data.get(
        "line_items",
        [],
    )

    prices = []

    for item in line_items:

        price = (
            item.get("unit_price")
            if item.get("unit_price") is not None
            else item.get("sales_price")
        )

        number = to_float(price)

        if number is not None:
            prices.append(number)

    if not prices:
        return None

    first_price = prices[0]

    if all(
        abs(price - first_price)
        <= MONEY_TOLERANCE
        for price in prices
    ):
        return first_price

    return None


def get_invoice_product(
    invoice_data: Dict[str, Any],
) -> Optional[str]:
    """
    Get a product description when there is exactly
    one invoice line item.
    """

    line_items = invoice_data.get(
        "line_items",
        [],
    )

    descriptions = [
        item.get("description")
        for item in line_items
        if item.get("description")
    ]

    if len(descriptions) == 1:
        return descriptions[0]

    return None


def get_invoice_freight(
    invoice_data: Dict[str, Any],
) -> Optional[float]:
    """
    Return an explicitly extracted freight value.

    The current parser does not yet expose a dedicated
    freight field, so invoice_total is deliberately NOT
    treated as freight here.
    """

    freight = invoice_data.get("freight")

    return to_float(freight)


def get_workbook_tracking(
    workbook_data: Dict[str, Any],
) -> Any:
    """Support both Tracking Number and Tracing Number."""

    return (
        workbook_data.get("tracking_number")
        or workbook_data.get("tracing_number")
    )


def compare_invoice_to_workbook(
    invoice_data: Dict[str, Any],
    workbook_result: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Compare extracted invoice data against a Nassau
    workbook record.

    The workbook_result should come from
    NassauWorkbookReader.find_po().
    """

    workbook_data = workbook_result.get(
        "data",
        {},
    )

    comparisons = []

    # -------------------------------------------------
    # PO
    # -------------------------------------------------

    comparisons.append(
        compare_text(
            "PO",
            invoice_data.get("po_number"),
            workbook_data.get("po"),
        )
    )

    # -------------------------------------------------
    # Quantity
    # -------------------------------------------------

    comparisons.append(
        compare_number(
            "QTY",
            get_invoice_quantity(invoice_data),
            workbook_data.get("qty"),
        )
    )

    # -------------------------------------------------
    # Product
    # -------------------------------------------------

    invoice_product = get_invoice_product(
        invoice_data
    )

    workbook_product = workbook_data.get(
        "product"
    )

    if invoice_product is None:

        comparisons.append(
            {
                "field": "Product",
                "invoice_value": [
                    item.get("description")
                    for item in invoice_data.get(
                        "line_items",
                        []
                    )
                    if item.get("description")
                ],
                "workbook_value": workbook_product,
                "status": "NOT_COMPARABLE",
            }
        )

    else:

        comparisons.append(
            compare_text(
                "Product",
                invoice_product,
                workbook_product,
            )
        )

    # -------------------------------------------------
    # Cost/M
    # -------------------------------------------------

    comparisons.append(
        compare_money(
            "Cost/M",
            get_invoice_unit_price(invoice_data),
            workbook_data.get("cost_per_m"),
        )
    )

    # -------------------------------------------------
    # Tracking
    # -------------------------------------------------

    comparisons.append(
        compare_text(
            "Tracking",
            invoice_data.get(
                "tracking_number"
            ),
            get_workbook_tracking(
                workbook_data
            ),
        )
    )

    # -------------------------------------------------
    # Freight
    #
    # IMPORTANT:
    # The current parser does not extract freight yet.
    # Therefore we do NOT compare invoice_total to
    # workbook Freight.
    # -------------------------------------------------

    invoice_freight = get_invoice_freight(
        invoice_data
    )

    if invoice_freight is None:

        comparisons.append(
            {
                "field": "Freight",
                "invoice_value": None,
                "workbook_value": workbook_data.get(
                    "freight"
                ),
                "status": "NOT_COMPARABLE",
            }
        )

    else:

        comparisons.append(
            compare_money(
                "Freight",
                invoice_freight,
                workbook_data.get(
                    "freight"
                ),
            )
        )

    # -------------------------------------------------
    # Carrier
    #
    # The current parser does not yet expose carrier.
    # -------------------------------------------------

    invoice_carrier = invoice_data.get(
        "carrier"
    )

    if invoice_carrier is None:

        comparisons.append(
            {
                "field": "Carrier",
                "invoice_value": None,
                "workbook_value": workbook_data.get(
                    "carrier"
                ),
                "status": "NOT_COMPARABLE",
            }
        )

    else:

        comparisons.append(
            compare_text(
                "Carrier",
                invoice_carrier,
                workbook_data.get(
                    "carrier"
                ),
            )
        )

    # -------------------------------------------------
    # Summary
    # -------------------------------------------------

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

    # A comparison is a mismatch only when a field
    # was actually comparable and failed.
    overall_status = (
        "MISMATCH"
        if mismatch_count > 0
        else "MATCH"
    )

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
        "not_comparable_count": (
            not_comparable_count
        ),
        "comparisons": comparisons,
    }
