import importlib.util
import os
from pathlib import Path


LAMBDA_PATH = (
    Path(__file__).resolve().parents[1]
    / "lambda"
    / "lambda_function.py"
)


def load_lambda_module():
    spec = importlib.util.spec_from_file_location(
        "lambda_function",
        LAMBDA_PATH,
    )

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_lambda_handler_uploads_receipt(monkeypatch):
    lambda_function = load_lambda_module()

    monkeypatch.setenv("RECEIPT_BUCKET", "test-receipt-bucket")

    uploaded = {}

    def fake_put_object(**kwargs):
        uploaded.update(kwargs)

    lambda_function.s3_client.put_object = fake_put_object

    event = {
        "Order_id": "TEST-001",
        "Amount": "125.50",
        "Item": "Test Cable",
    }

    result = lambda_function.lambda_handler(event, None)

    assert result == {
        "statusCode": 200,
        "message": "Receipt processed successfully",
    }

    assert uploaded["Bucket"] == "test-receipt-bucket"
    assert uploaded["Key"] == "receipts/TEST-001.txt"
    assert uploaded["Body"] == (
        "OrderID: TEST-001\n"
        "Amount: $125.50\n"
        "Item: Test Cable"
    )


def test_lambda_handler_requires_receipt_bucket(monkeypatch):
    lambda_function = load_lambda_module()

    monkeypatch.delenv("RECEIPT_BUCKET", raising=False)

    event = {
        "Order_id": "TEST-002",
        "Amount": "50.00",
        "Item": "Test Product",
    }

    try:
        lambda_function.lambda_handler(event, None)
        assert False, "Expected ValueError"
    except ValueError as error:
        assert str(error) == "Missing required environment variable RECEIPT_BUCKET"
