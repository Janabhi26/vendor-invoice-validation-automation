import json
import os
import sys

from src.email.email_client import build_validation_email
from src.extraction.invoice_parser import parse_invoice
from src.validation.validator import (
    PROJECT_ROOT,
    build_report_row,
    validate_invoice,
    validate_workbook,
)
from src.validation.workbook_reader import NassauWorkbookReader


def main():
    invoice_directory = os.path.join(
        PROJECT_ROOT,
        "data",
        "invoices",
    )

    workbook_path = os.environ.get(
        "NASSAU_WORKBOOK",
        os.path.join(
            PROJECT_ROOT,
            "data",
            "Nassau.xlsx",
        ),
    )

    pdf_files = sorted(
        filename
        for filename in os.listdir(invoice_directory)
        if filename.lower().endswith(".pdf")
    )

    if not pdf_files:
        print("TEST FAILED: No PDF invoices found.")
        sys.exit(1)

    passed_count = 0
    failed_count = 0
    workbook_found_count = 0
    workbook_not_found_count = 0
    workbook_mismatch_count = 0

    results = []
    report_rows = []

    workbook_reader = NassauWorkbookReader(
        workbook_path=workbook_path
    )

    try:
        for filename in pdf_files:
            file_path = os.path.join(
                invoice_directory,
                filename,
            )

            invoice = parse_invoice(file_path)

            invoice_result = validate_invoice(invoice)

            workbook_result = validate_workbook(
                invoice,
                workbook_reader,
            )

            report_rows.append(
                build_report_row(
                    invoice,
                    invoice_result,
                    workbook_result,
                )
            )

            results.append(
                (
                    filename,
                    invoice_result["passed"],
                    workbook_result["status"],
                )
            )

            if invoice_result["passed"]:
                passed_count += 1
            else:
                failed_count += 1

            if workbook_result["status"] == "PO NOT FOUND":
                workbook_not_found_count += 1
            elif workbook_result["status"] == "MISMATCH":
                workbook_mismatch_count += 1
            else:
                workbook_found_count += 1

    finally:
        workbook_reader.close()

    subject, message = build_validation_email(
        pdf_files=pdf_files,
        passed_count=passed_count,
        failed_count=failed_count,
        workbook_found_count=workbook_found_count,
        workbook_not_found_count=workbook_not_found_count,
        workbook_mismatch_count=workbook_mismatch_count,
        results=results,
    )

    payload = {
        "subject": subject,
        "recipients": [
            "jan.abhi007@gmail.com"
        ],
        "from_email": "matiasl@nassaunationalcable.com",
        "text": message,
    }

    print()
    print("=" * 64)
    print("MEETING SYSTEM TEST")
    print("=" * 64)

    print()
    print(f"PDF invoices processed : {len(pdf_files)}")
    print(f"Invoice validation     : {passed_count} passed / {failed_count} failed")
    print(f"POs found              : {workbook_found_count}")
    print(f"POs not found          : {workbook_not_found_count}")
    print(f"Workbook mismatches    : {workbook_mismatch_count}")

    print()
    print("EMAIL PAYLOAD")
    print("-" * 64)
    print(f"From    : {payload['from_email']}")
    print(f"To      : {payload['recipients'][0]}")
    print(f"Subject : {payload['subject']}")

    print()
    print("EMAIL BODY")
    print("-" * 64)
    print(payload["text"])

    print()
    print("JSON PAYLOAD")
    print("-" * 64)
    print(
        json.dumps(
            payload,
            indent=2,
        )
    )

    print()
    print("=" * 64)

    if failed_count == 0:
        print("✅ MEETING SYSTEM TEST PASSED")
    else:
        print("❌ MEETING SYSTEM TEST FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
