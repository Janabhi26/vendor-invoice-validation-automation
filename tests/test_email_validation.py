from src.email.email_client import (
    build_validation_email,
    send_validation_result,
)


def test_validation_email_contains_correct_information(monkeypatch):
    pdf_files = [
        "invoice_001.pdf",
        "invoice_002.pdf",
    ]

    results = [
        ("invoice_001.pdf", True, "MATCH"),
        ("invoice_002.pdf", False, "MISMATCH"),
    ]

    subject, message = build_validation_email(
        pdf_files=pdf_files,
        passed_count=1,
        failed_count=1,
        workbook_found_count=2,
        workbook_not_found_count=0,
        workbook_mismatch_count=1,
        results=results,
    )

    captured = {}

    def fake_urlopen(request, timeout=30):
        captured["url"] = request.full_url
        captured["method"] = request.get_method()
        captured["headers"] = dict(request.headers)
        captured["body"] = request.data.decode("utf-8")

        class FakeResponse:
            status = 200

            def read(self):
                return b'{"success": true}'

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_value, traceback):
                return False

        return FakeResponse()

    monkeypatch.setattr(
        "src.email.email_client.urllib.request.urlopen",
        fake_urlopen,
    )

    result = send_validation_result(
        subject=subject,
        message=message,
    )

    assert result["success"] is True
    assert result["status_code"] == 200

    assert captured["method"] == "POST"
    assert captured["headers"]["Content-type"] == "application/json"

    import json

    payload = json.loads(captured["body"])

    assert payload["subject"] == "Vendor Invoice Validation Result"
    assert payload["recipients"] == ["jan.abhi007@gmail.com"]
    assert payload["from_email"] == "matiasl@nassaunationalcable.com"
    assert payload["text"] == message

    assert "Total invoices: 2" in payload["text"]
    assert "Passed: 1" in payload["text"]
    assert "Failed: 1" in payload["text"]
    assert "POs found: 2" in payload["text"]
    assert "POs not found: 0" in payload["text"]
    assert "Workbook mismatches: 1" in payload["text"]

    assert "PASS | MATCH | invoice_001.pdf" in payload["text"]
    assert "FAIL | MISMATCH | invoice_002.pdf" in payload["text"]
