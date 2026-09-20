import json
import urllib.error
import urllib.request


DEFAULT_FUNCTION_URL = "http://127.0.0.1:8000/"

SENDER_EMAIL = "jan.abhi007@gmail.com"
RECIPIENT_EMAIL = "matiasl@nassaunationalcable.com"


def build_validation_email(
    pdf_files,
    passed_count,
    failed_count,
    workbook_found_count,
    workbook_not_found_count,
    workbook_mismatch_count,
    results,
):
    """
    Build the email subject and body from validation results.
    """

    subject = "Vendor Invoice Validation Result"

    lines = [
        "Vendor Invoice Validation Result",
        "",
        f"Total invoices: {len(pdf_files)}",
        f"Passed: {passed_count}",
        f"Failed: {failed_count}",
        "",
        "Workbook Summary",
        f"POs found: {workbook_found_count}",
        f"POs not found: {workbook_not_found_count}",
        f"Workbook mismatches: {workbook_mismatch_count}",
        "",
        "Invoice Results",
    ]

    for filename, passed, workbook_status in results:

        invoice_status = (
            "PASS"
            if passed
            else "FAIL"
        )

        lines.append(
            f"{invoice_status} | "
            f"{workbook_status} | "
            f"{filename}"
        )

    return subject, "\n".join(lines)


def send_validation_result(
    subject,
    message,
    function_url=DEFAULT_FUNCTION_URL,
):
    """
    Send a validation result to the local email Function URL.

    The JSON contract mirrors the Function URL format supplied
    by Matias.
    """

    payload = {
        "subject": subject,
        "recipients": [
            RECIPIENT_EMAIL
        ],
        "from_email": SENDER_EMAIL,
        "text": message,
    }

    data = json.dumps(
        payload
    ).encode("utf-8")

    request = urllib.request.Request(
        function_url,
        data=data,
        headers={
            "Content-Type": "application/json"
        },
        method="POST",
    )

    try:

        with urllib.request.urlopen(
            request,
            timeout=30,
        ) as response:

            response_body = (
                response
                .read()
                .decode("utf-8")
            )

            return {
                "success": True,
                "status_code": response.status,
                "response": response_body,
            }

    except urllib.error.HTTPError as error:

        response_body = (
            error
            .read()
            .decode(
                "utf-8",
                errors="replace",
            )
        )

        return {
            "success": False,
            "status_code": error.code,
            "response": response_body,
        }

    except urllib.error.URLError as error:

        return {
            "success": False,
            "status_code": None,
            "response": str(error),
        }


if __name__ == "__main__":

    subject, message = build_validation_email(
        pdf_files=[
            "example_invoice.pdf"
        ],
        passed_count=1,
        failed_count=0,
        workbook_found_count=1,
        workbook_not_found_count=0,
        workbook_mismatch_count=0,
        results=[
            (
                "example_invoice.pdf",
                True,
                "MATCH",
            )
        ],
    )

    result = send_validation_result(
        subject=subject,
        message=message,
    )

    print(
        json.dumps(
            result,
            indent=2,
        )
    )
