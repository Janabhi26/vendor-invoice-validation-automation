import os
import re
import sys


# ============================================================
# PDF READER
# ============================================================

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from pdf_reader import extract_text_from_pdf


# ============================================================
# GENERAL HELPERS
# ============================================================

def clean_line(line):
    return re.sub(r"\s+", " ", line).strip()


def get_lines(text):
    lines = []

    for line in text.splitlines():
        cleaned = clean_line(line)

        if cleaned:
            lines.append(cleaned)

    return lines


def normalize_number(value):
    if value is None:
        return None

    return str(value).replace(",", "").strip()


def normalize_item_id(value):
    if not value:
        return None

    return re.sub(r"\s+", " ", value).strip()


def find_amount(text):
    match = re.search(
        r"\$?([\d,]+\.\d{2})",
        text
    )

    if match:
        return normalize_number(match.group(1))

    return None


# ============================================================
# FORMAT DETECTION
# ============================================================

def is_standard_invoice(lines):
    """
    Standard invoice format.

    Examples:
        Invoice 1170959
        Sold To:
        Customer PO
        Item
        Ordered
        Shipped
        Price
        Extension
        Invoice Total
    """

    text = " ".join(lines).lower()

    return (
        "sold to:" in text
        and "customer po" in text
        and "invoice total" in text
        and (
            "ordered" in text
            and "shipped" in text
        )
    )


def is_commodity_invoice(lines):
    """
    Commodity Cables invoice format.

    Examples:
        Bill To
        Sales Order #
        PO #
        Item ID
        Sales Price
        Total
    """

    text = " ".join(lines).lower()

    return (
        "bill to" in text
        and "sales order" in text
        and "po #" in text
        and "item id" in text
        and "sales price" in text
    )


# ============================================================
# STANDARD INVOICE HEADER
# ============================================================

def extract_standard_header(
    lines,
    pdf_path=None
):

    invoice_number = None
    invoice_date = None
    po_number = None
    customer = None
    ship_to = None
    tracking_number = None
    invoice_total = None

    # --------------------------------------------------------
    # Invoice Number
    # --------------------------------------------------------

    for index, line in enumerate(lines):

        if line == "Invoice":

            for candidate in lines[
                index:index + 10
            ]:

                if re.fullmatch(
                    r"\d{5,}",
                    candidate
                ):

                    invoice_number = candidate
                    break

            if invoice_number:
                break

    # --------------------------------------------------------
    # Invoice Date
    # --------------------------------------------------------

    date_pattern = re.compile(
        r"\b\d{1,2}/\d{1,2}/\d{4}\b"
    )

    for line in lines:

        match = date_pattern.search(line)

        if match:

            invoice_date = match.group(0)
            break

    # --------------------------------------------------------
    # Customer
    # --------------------------------------------------------

    for index, line in enumerate(lines):

        if line == "Sold To:":

            if index + 1 < len(lines):

                customer = lines[
                    index + 1
                ]

            break

        if line.startswith("Sold To:"):

            customer = line.replace(
                "Sold To:",
                "",
                1
            ).strip()

            break

    # --------------------------------------------------------
    # Ship To
    # --------------------------------------------------------

    for index, line in enumerate(lines):

        if line == "Ship To:":

            if index + 1 < len(lines):

                ship_to = lines[
                    index + 1
                ]

            break

        if line.startswith("Ship To:"):

            ship_to = line.replace(
                "Ship To:",
                "",
                1
            ).strip()

            break

    # --------------------------------------------------------
    # Customer PO
    #
    # In the PDF extraction, the PO appears after:
    #
    # Payment Terms
    # E27473
    # FOB
    # RESIDENTIAL
    # --------------------------------------------------------

    for index, line in enumerate(lines):

        if line == "Payment Terms":

            for candidate in lines[
                index + 1:index + 6
            ]:

                if candidate in (
                    "FOB",
                    "RESIDENTIAL",
                    "PPD-ADD",
                ):
                    continue

                if re.fullmatch(
                    r"[A-Za-z0-9][A-Za-z0-9\-]*",
                    candidate
                ):

                    po_number = candidate
                    break

            if po_number:
                break

    # --------------------------------------------------------
    # PO fallback using filename
    #
    # Example:
    #
    # Invoice_1170959_For_Your_Order_E27473_20251229.pdf
    #
    # PO = E27473
    # --------------------------------------------------------

    if (
        not po_number
        or po_number == "PPD-ADD"
    ):

        if pdf_path:

            filename = os.path.basename(
                pdf_path
            )

            match = re.search(
                r"For_Your_Order_([^_]+)_",
                filename
            )

            if match:

                po_number = match.group(1)

    # --------------------------------------------------------
    # Tracking Number
    # --------------------------------------------------------

    tracking_index = None

    for index, line in enumerate(lines):

        if (
            line == "Tracking/Pro Number"
            or "Tracking/Pro Number" in line
        ):

            tracking_index = index
            break

    if tracking_index is not None:

        for candidate in lines[
            tracking_index + 1:
        ]:

            match = re.search(
                r"\b1Z[A-Z0-9]+\b",
                candidate,
                re.IGNORECASE
            )

            if match:

                tracking_number = (
                    match.group(0)
                )

                break

            if re.fullmatch(
                r"\d{6,}",
                candidate
            ):

                tracking_number = candidate
                break

    # --------------------------------------------------------
    # Invoice Total
    # --------------------------------------------------------

    for index in range(
        len(lines) - 1,
        -1,
        -1
    ):

        line = lines[index]

        if line.startswith(
            "Invoice Total"
        ):

            amount = find_amount(line)

            if amount:

                invoice_total = amount
                break

            if index + 1 < len(lines):

                amount = find_amount(
                    lines[index + 1]
                )

                if amount:

                    invoice_total = amount
                    break

    return {
        "invoice_number": invoice_number,
        "invoice_date": invoice_date,
        "po_number": po_number,
        "customer": customer,
        "ship_to": ship_to,
        "tracking_number": tracking_number,
        "invoice_total": invoice_total,
    }


# ============================================================
# STANDARD INVOICE LINE ITEMS
# ============================================================

def extract_standard_line_items(lines):

    line_items = []

    # =========================================================
    # NORMAL PRODUCT ITEM PATTERN
    #
    # Example:
    # 1 6THHN-0201-01
    # 2 6THHN-0201
    # 3 6THHN-0201-03
    # =========================================================

    item_pattern = re.compile(
        r"^(\d+)\s+([A-Za-z0-9][A-Za-z0-9\-/\.]*)$"
    )

    item_indexes = []

    for index, line in enumerate(lines):

        match = item_pattern.fullmatch(line)

        if not match:
            continue

        line_number = match.group(1)
        item_number = match.group(2)

        # -----------------------------------------------------
        # Ignore quantity/unit rows such as:
        #
        # 15 FT
        # 1 EA
        # 250 FT
        # -----------------------------------------------------

        if item_number.upper() in (
            "FT",
            "EA",
            "MFT",
            "LB",
            "PCS",
        ):
            continue

        # -----------------------------------------------------
        # A genuine product row should have a price/unit
        # somewhere shortly after it.
        # -----------------------------------------------------

        found_price = False

        for j in range(
            index + 1,
            min(index + 6, len(lines))
        ):

            if re.fullmatch(
                r"[\d,]+\.\d+\s+\S+",
                lines[j]
            ):
                found_price = True
                break

        if found_price:
            item_indexes.append(index)

    # =========================================================
    # PARSE NORMAL PRODUCT ITEMS
    # =========================================================

    for position, index in enumerate(item_indexes):

        match = item_pattern.fullmatch(lines[index])

        if not match:
            continue

        line_number = match.group(1)
        item_number = match.group(2)

        # -----------------------------------------------------
        # Find unit price
        #
        # Example:
        # 1950.00000 MFT
        # -----------------------------------------------------

        price_index = None
        unit_price = None
        price_unit = None

        for j in range(
            index + 1,
            min(index + 6, len(lines))
        ):

            price_match = re.fullmatch(
                r"([\d,]+\.\d+)\s+(\S+)",
                lines[j]
            )

            if price_match:

                unit_price = price_match.group(1)
                price_unit = price_match.group(2)
                price_index = j

                break

        if price_index is None:
            continue

        # -----------------------------------------------------
        # Find line total
        #
        # Example:
        # 29.25
        # -----------------------------------------------------

        line_total = None
        line_total_index = None

        for j in range(
            price_index + 1,
            min(price_index + 5, len(lines))
        ):

            if re.fullmatch(
                r"[\d,]+\.\d{2}",
                lines[j]
            ):

                line_total = lines[j]
                line_total_index = j

                break

        if line_total is None:
            continue

        # -----------------------------------------------------
        # Find quantities
        #
        # Typical structure:
        #
        # 15
        # 15 FT
        # -----------------------------------------------------

        shipped_quantity = None
        ordered_quantity = None
        unit = None

        for j in range(
            line_total_index + 1,
            min(line_total_index + 7, len(lines))
        ):

            candidate = lines[j]

            # Shipped quantity
            if re.fullmatch(
                r"[\d,]+",
                candidate
            ):

                if shipped_quantity is None:
                    shipped_quantity = candidate

                continue

            # Ordered quantity + unit
            quantity_match = re.fullmatch(
                r"([\d,]+)\s+(\S+)",
                candidate
            )

            if quantity_match:

                ordered_quantity = quantity_match.group(1)
                unit = quantity_match.group(2)

                break

        # -----------------------------------------------------
        # Find description
        # -----------------------------------------------------

        description_start = line_total_index + 1

        for j in range(
            line_total_index + 1,
            min(line_total_index + 7, len(lines))
        ):

            candidate = lines[j]

            # Skip shipped quantity
            if re.fullmatch(
                r"[\d,]+",
                candidate
            ):

                description_start = j + 1
                continue

            # Skip ordered quantity + unit
            if re.fullmatch(
                r"[\d,]+\s+\S+",
                candidate
            ):

                description_start = j + 1
                break

        # -----------------------------------------------------
        # Description ends at the next product item.
        # -----------------------------------------------------

        if position + 1 < len(item_indexes):

            description_end = item_indexes[position + 1]

        else:

            description_end = len(lines)

        description_parts = []

        for candidate in lines[
            description_start:description_end
        ]:

            # Ignore PDF hyperlink text
            if candidate == "Click here for spec sheet":
                continue

            # Ignore packaging/quantity text such as:
            # 1 X 15'FT
            if re.match(
                r"^\d+\s+X\s+",
                candidate,
                re.IGNORECASE
            ):
                continue

            # -------------------------------------------------
            # IMPORTANT:
            # Stop description before freight/footer data.
            # -------------------------------------------------

            if candidate.startswith(
                (
                    "F1 FREIGHT",
                    "Product",
                    "Freight",
                    "Tax",
                    "Invoice Total",
                    "Payment Details",
                    "Amount Due",
                    "Shipping Method",
                    "Tracking/Pro Number",
                    "Page ",
                )
            ):
                break

            description_parts.append(candidate)

        description = " ".join(
            description_parts
        ).strip()

        # -----------------------------------------------------
        # Store product
        # -----------------------------------------------------

        line_items.append(
            {
                "line_number": line_number,
                "item_number": normalize_item_id(
                    item_number
                ),
                "description": description,
                "ordered_quantity": normalize_number(
                    ordered_quantity
                ),
                "shipped_quantity": normalize_number(
                    shipped_quantity
                ),
                "unit": unit,
                "unit_price": normalize_number(
                    unit_price
                ),
                "price_unit": price_unit,
                "line_total": normalize_number(
                    line_total
                ),
            }
        )

    # =========================================================
    # PARSE FREIGHT CHARGE
    #
    # Standard invoices can contain:
    #
    # F1 FREIGHT CHARGE
    # 219.18000 EA
    # 219.18
    # 1
    # 1 EA
    #
    # Or the PDF may combine some/all of these onto one line.
    # =========================================================

    for index, line in enumerate(lines):

        if not line.startswith(
            "F1 FREIGHT CHARGE"
        ):
            continue

        freight_price = None
        freight_unit = "EA"
        freight_total = None

        # -----------------------------------------------------
        # Case 1:
        # Everything is on the same line.
        #
        # F1 FREIGHT CHARGE 219.18000 EA 219.18
        # -----------------------------------------------------

        freight_match = re.search(
            r"F1\s+FREIGHT\s+CHARGE\s+"
            r"([\d,]+\.\d+)\s+(\S+)\s+"
            r"([\d,]+\.\d{2})",
            line,
            re.IGNORECASE
        )

        if freight_match:

            freight_price = freight_match.group(1)
            freight_unit = freight_match.group(2)
            freight_total = freight_match.group(3)

        # -----------------------------------------------------
        # Case 2:
        # Freight information is split across PDF lines.
        # -----------------------------------------------------

        else:

            for j in range(
                index,
                min(index + 6, len(lines))
            ):

                candidate = lines[j]

                price_match = re.search(
                    r"([\d,]+\.\d+)\s+"
                    r"([A-Za-z]+)\s+"
                    r"([\d,]+\.\d{2})",
                    candidate,
                    re.IGNORECASE
                )

                if price_match:

                    freight_price = price_match.group(1)
                    freight_unit = price_match.group(2)
                    freight_total = price_match.group(3)

                    break

        # -----------------------------------------------------
        # If price/total still wasn't found, look specifically
        # for decimal values around the freight row.
        # -----------------------------------------------------

        if (
            freight_price is None
            or freight_total is None
        ):

            nearby_values = []

            for j in range(
                index,
                min(index + 8, len(lines))
            ):

                candidate = lines[j]

                decimal_values = re.findall(
                    r"\b[\d,]+\.\d{2,5}\b",
                    candidate
                )

                nearby_values.extend(
                    decimal_values
                )

            # Usually the first decimal is the unit price
            # and the second is the extension/total.
            if len(nearby_values) >= 2:

                freight_price = nearby_values[0]
                freight_total = nearby_values[1]

        # -----------------------------------------------------
        # Only add freight if we successfully extracted it.
        # -----------------------------------------------------

        if (
            freight_price is None
            or freight_total is None
        ):
            continue

        # -----------------------------------------------------
        # Prevent duplicate freight entries.
        # -----------------------------------------------------

        if any(
            item.get("item_number") == "F1"
            for item in line_items
        ):
            continue

        # -----------------------------------------------------
        # Add freight as its own line item.
        # -----------------------------------------------------

        line_items.append(
            {
                "line_number": "F1",
                "item_number": "F1",
                "description": "FREIGHT CHARGE",
                "ordered_quantity": "1",
                "shipped_quantity": "1",
                "unit": "EA",
                "unit_price": normalize_number(
                    freight_price
                ),
                "price_unit": freight_unit,
                "line_total": normalize_number(
                    freight_total
                ),
            }
        )

    return line_items


def parse_standard_invoice(
    lines,
    pdf_path
):

    header = extract_standard_header(
        lines,
        pdf_path
    )

    line_items = extract_standard_line_items(
        lines
    )

    return {
        "invoice_format": "standard",
        **header,
        "line_items": line_items,
    }


# ============================================================
# COMMODITY CABLES HEADER
# ============================================================

def extract_commodity_header(lines):

    invoice_number = None
    invoice_date = None
    po_number = None
    customer = None
    ship_to = None
    sales_order = None
    tracking_number = None
    invoice_total = None

    # --------------------------------------------------------
    # Invoice Number
    # --------------------------------------------------------

    for index, line in enumerate(lines):

        if line == "Invoice #":

            if index + 1 < len(lines):

                invoice_number = (
                    lines[index + 1]
                )

            break

    # --------------------------------------------------------
    # Invoice Date
    # --------------------------------------------------------

    for index, line in enumerate(lines):

        if line == "Date":

            if index + 1 < len(lines):

                invoice_date = (
                    lines[index + 1]
                )

            break

    # --------------------------------------------------------
    # Customer
    # --------------------------------------------------------

    for index, line in enumerate(lines):

        if line == "Bill To":

            if index + 1 < len(lines):

                customer = (
                    lines[index + 1]
                )

            break

    # --------------------------------------------------------
    # Ship To
    # --------------------------------------------------------

    for index, line in enumerate(lines):

        if line == "Ship To":

            if index + 1 < len(lines):

                ship_to = (
                    lines[index + 1]
                )

            break

    # --------------------------------------------------------
    # Sales Order
    # --------------------------------------------------------

    for index, line in enumerate(lines):

        if line.startswith(
            "Sales Order #"
        ):

            sales_order = line[
                len("Sales Order #"):
            ].strip()

            break

        if line == "Sales Order #":

            if index + 1 < len(lines):

                sales_order = (
                    lines[index + 1]
                ).strip()

                break

    # --------------------------------------------------------
    # PO
    #
    # IMPORTANT:
    # Do NOT use PO#15830 from the Ship To address.
    # The invoice PO is the value after the standalone
    # "PO #" field.
    # --------------------------------------------------------

    for index, line in enumerate(lines):

        if line == "PO #":

            if index + 1 < len(lines):

                candidate = (
                    lines[index + 1]
                ).strip()

                if (
                    candidate
                    and candidate != "Tracking #"
                ):

                    po_number = candidate

            break

    # --------------------------------------------------------
    # Tracking
    # --------------------------------------------------------

    for index, line in enumerate(lines):

        if line == "Tracking #":

            if index + 1 < len(lines):

                candidate = (
                    lines[index + 1]
                ).strip()

                if candidate not in (
                    "Ship Via",
                    "Freight Terms",
                ):

                    tracking_number = candidate

            break

    # --------------------------------------------------------
    # Invoice Total
    #
    # Use the final Total section.
    # --------------------------------------------------------

    for index in range(
        len(lines) - 1,
        -1,
        -1
    ):

        if lines[index] == "Total":

            if index + 1 < len(lines):

                amount = find_amount(
                    lines[index + 1]
                )

                if amount:

                    invoice_total = amount
                    break

        if lines[index].startswith(
            "Total "
        ):

            amount = find_amount(
                lines[index]
            )

            if amount:

                invoice_total = amount
                break

    return {
        "invoice_number": invoice_number,
        "invoice_date": invoice_date,
        "po_number": po_number,
        "customer": customer,
        "ship_to": ship_to,
        "sales_order": sales_order,
        "tracking_number": tracking_number,
        "invoice_total": invoice_total,
    }


# ============================================================
# COMMODITY CABLES LINE ITEMS
# ============================================================

def extract_commodity_line_items_from_pdf(
    pdf_path
):

    import pymupdf

    line_items = []

    document = pymupdf.open(
        pdf_path
    )

    try:

        for page in document:

            words = page.get_text(
                "words"
            )

            # ------------------------------------------------
            # Group words by Y position
            # ------------------------------------------------

            rows = {}

            for word in words:

                x0, y0, x1, y1, text = (
                    word[:5]
                )

                key = round(y0 / 3) * 3

                rows.setdefault(
                    key,
                    []
                ).append(
                    (
                        x0,
                        y0,
                        x1,
                        y1,
                        text
                    )
                )

            # ------------------------------------------------
            # Process table rows
            # ------------------------------------------------

            for y, row_words in sorted(
                rows.items()
            ):

                row_words.sort(
                    key=lambda item: item[0]
                )

                row_text = " ".join(
                    item[4]
                    for item in row_words
                )

                # Skip table headers
                if (
                    "Item ID" in row_text
                    or "Description" in row_text
                    or "Sales Price" in row_text
                ):
                    continue

                # Skip footer rows
                if row_text in (
                    "Subtotal",
                    "Shipping Cost",
                    "Total",
                ):
                    continue

                # Need at least two decimal amounts
                amounts = [
                    item[4]
                    for item in row_words
                    if re.fullmatch(
                        r"[\d,]+\.\d{2}",
                        item[4]
                    )
                ]

                if len(amounts) < 2:
                    continue

                # ------------------------------------------------
                # Columns
                # ------------------------------------------------

                item_id_parts = []
                description_parts = []

                order = None
                backordered = None
                quantity = None
                sales_price = None
                line_total = None
                memo_parts = []

                for (
                    x0,
                    y0,
                    x1,
                    y1,
                    text,
                ) in row_words:

                    # Item ID
                    if 35 <= x0 < 110:

                        item_id_parts.append(
                            text
                        )

                    # Description
                    elif 110 <= x0 < 295:

                        description_parts.append(
                            text
                        )

                    # Order
                    elif 295 <= x0 < 350:

                        if re.fullmatch(
                            r"[\d,]+",
                            text
                        ):

                            order = text

                    # Backordered
                    elif 350 <= x0 < 370:

                        if re.fullmatch(
                            r"\d+",
                            text
                        ):

                            backordered = text

                    # Quantity
                    elif 370 <= x0 < 420:

                        if re.fullmatch(
                            r"[\d,]+",
                            text
                        ):

                            quantity = text

                    # Sales Price
                    elif 420 <= x0 < 460:

                        if re.fullmatch(
                            r"[\d,]+\.\d{2}",
                            text
                        ):

                            sales_price = text

                    # Total
                    elif 460 <= x0 < 505:

                        if re.fullmatch(
                            r"[\d,]+\.\d{2}",
                            text
                        ):

                            line_total = text

                    # Memo
                    elif x0 >= 505:

                        memo_parts.append(
                            text
                        )

                if line_total is None:
                    continue

                line_items.append(
                    {
                        "line_number": len(
                            line_items
                        ) + 1,
                        "item_number": normalize_item_id(
                            " ".join(
                                item_id_parts
                            )
                        ),
                        "description": " ".join(
                            description_parts
                        ).strip(),
                        "ordered_quantity": order,
                        "backordered_quantity": (
                            backordered
                        ),
                        "quantity": quantity,
                        "sales_price": normalize_number(
                            sales_price
                        ),
                        "line_total": normalize_number(
                            line_total
                        ),
                        "memo": " ".join(
                            memo_parts
                        ).strip() or None,
                    }
                )

    finally:

        document.close()

    return line_items


def parse_commodity_invoice(
    lines,
    pdf_path
):

    header = extract_commodity_header(
        lines
    )

    line_items = (
        extract_commodity_line_items_from_pdf(
            pdf_path
        )
    )

    return {
        "invoice_format": "commodity_cables",
        **header,
        "line_items": line_items,
    }


# ============================================================
# MAIN PARSER
# ============================================================

def parse_invoice(pdf_path):

    text = extract_text_from_pdf(
        pdf_path
    )

    lines = get_lines(text)

    # --------------------------------------------------------
    # Commodity Cables
    # --------------------------------------------------------

    if is_commodity_invoice(lines):

        return parse_commodity_invoice(
            lines,
            pdf_path
        )

    # --------------------------------------------------------
    # Standard
    # --------------------------------------------------------

    if is_standard_invoice(lines):

        return parse_standard_invoice(
            lines,
            pdf_path
        )

    # --------------------------------------------------------
    # Unknown
    # --------------------------------------------------------

    return {
        "invoice_format": "unknown",
        "invoice_number": None,
        "invoice_date": None,
        "po_number": None,
        "customer": None,
        "ship_to": None,
        "sales_order": None,
        "tracking_number": None,
        "invoice_total": None,
        "line_items": [],
    }


# ============================================================
# DIRECT TEST
# ============================================================

if __name__ == "__main__":

    invoice_dir = os.path.abspath(
        os.path.join(
            CURRENT_DIR,
            "..",
            "..",
            "data",
            "invoices"
        )
    )

    pdf_files = sorted(
        [
            os.path.join(
                invoice_dir,
                filename
            )
            for filename in os.listdir(
                invoice_dir
            )
            if filename.lower().endswith(
                ".pdf"
            )
        ]
    )

    for pdf_path in pdf_files:

        print(
            "\n"
            + "=" * 80
        )

        print(
            os.path.basename(pdf_path)
        )

        result = parse_invoice(
            pdf_path
        )

        print(result)