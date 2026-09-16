from validation.workbook_comparator import (
    compare_invoice_to_workbook,
)


def make_workbook_result():
    """Create a controlled workbook record for testing."""

    return {
        "sheet": "NNC NES & Non-Wire",
        "matched_by": "PO",
        "data": {
            "po": "N159173",
            "product": "500-500-500-350 Wofford (1x550')",
            "cost_per_m": 6321.0,
            "cost": None,
            "cut_charge": 98.0,
            "freight": 582.07,
            "extended": 4156.62,
            "extended_total_cost": None,
            "carrier": "Dayton Freight",
            "tracking_number": "09017397799",
            "tracing_number": None,
            "split_order_po": None,
            "qty": 550.0,
        },
        "raw_data": {},
    }


def make_matching_invoice():
    """Create invoice data that matches the workbook record."""

    return {
        "invoice_number": "TEST-001",
        "po_number": "N159173",
        "line_items": [
            {
                "description": "500-500-500-350 Wofford (1x550')",
                "quantity": 550,
                "sales_price": 6321,
            }
        ],
    }


def test_workbook_comparison_matches_core_fields():

    invoice = make_matching_invoice()
    workbook = make_workbook_result()

    result = compare_invoice_to_workbook(
        invoice,
        workbook,
    )

    assert result["overall_status"] == "MATCH"
    assert result["mismatch_count"] == 0

    statuses = {
        item["field"]: item["status"]
        for item in result["comparisons"]
    }

    assert statuses["PO"] == "MATCH"
    assert statuses["QTY"] == "MATCH"
    assert statuses["Product"] == "MATCH"
    assert statuses["Cost/M"] == "MATCH"


def test_workbook_comparison_detects_quantity_mismatch():

    invoice = make_matching_invoice()

    invoice["line_items"][0]["quantity"] = 500

    workbook = make_workbook_result()

    result = compare_invoice_to_workbook(
        invoice,
        workbook,
    )

    assert result["overall_status"] == "MISMATCH"
    assert result["mismatch_count"] == 1

    quantity_result = next(
        item
        for item in result["comparisons"]
        if item["field"] == "QTY"
    )

    assert quantity_result["status"] == "MISMATCH"


def test_workbook_comparison_handles_unavailable_invoice_fields():

    invoice = make_matching_invoice()
    workbook = make_workbook_result()

    result = compare_invoice_to_workbook(
        invoice,
        workbook,
    )

    statuses = {
        item["field"]: item["status"]
        for item in result["comparisons"]
    }

    assert statuses["Tracking"] == "NOT_COMPARABLE"
    assert statuses["Freight"] == "NOT_COMPARABLE"
    assert statuses["Carrier"] == "NOT_COMPARABLE"


def test_workbook_comparison_handles_missing_workbook():

    invoice = make_matching_invoice()

    result = compare_invoice_to_workbook(
        invoice,
        None,
    )

    assert result["overall_status"] == "PO NOT FOUND"
