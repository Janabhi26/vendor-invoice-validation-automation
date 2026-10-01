# Vendor Invoice Validation Automation

Automation for extracting and validating vendor invoice data from PDF invoices and comparing the extracted invoice data against the Nassau workbook.

The project also prepares a validation summary that can be sent through an AWS Lambda Function URL to the configured email service.

## Overview

The application processes vendor invoice PDFs through the following workflow:

```text
PDF Invoice
    ↓
Invoice Extraction
    ↓
Invoice Validation
    ↓
PO Lookup in Nassau Workbook
    ↓
Workbook Field Comparison
    ↓
CSV Validation Report
    ↓
Validation Email Payload
    ↓
AWS Lambda Function URL
    ↓
Email Service
```

The current implementation supports two invoice formats:

- Standard vendor invoices
- Commodity Cables invoices

## Features

- Extract invoice information from PDF files
- Identify supported invoice formats
- Extract invoice line items
- Validate invoice calculations
- Look up purchase orders in the Nassau workbook
- Compare invoice data with workbook data
- Generate a CSV validation report
- Build an email summary of validation results
- Send the email payload through an AWS Lambda Function URL
- Provide an S3 receipt-processing Lambda handler
- Provide automated tests for invoice, workbook, email, Lambda, and end-to-end validation

## Supported Invoice Data

The parser can extract:

- Invoice number
- Invoice date
- Customer
- Purchase order number
- Ship-to information
- Tracking number
- Invoice total
- Line items
- Product description
- Quantity
- Unit price
- Price unit
- Line total

Commodity Cables invoices can additionally contain:

- Sales order
- Backordered quantity
- Sales price
- Memo

## Invoice Validation

The invoice validator checks:

- Required invoice fields
- Line-item calculations
- Quantity × unit price
- MFT pricing
- Invoice total versus extracted line-item totals

For MFT pricing, the price represents the cost per 1,000 feet.

Example:

```text
15 FT × $1,950/MFT
= 15 × 1,950 / 1,000
= $29.25
```

## Workbook Validation

The workbook reader searches the configured Nassau workbook for the invoice purchase order.

The comparison uses the relevant workbook columns, including:

- PO
- QTY
- Product
- Cost/M
- Freight
- Tracking Number / Tracing Number
- Carrier
- Split Order PO#

Each field comparison can return:

- `MATCH`
- `MISMATCH`
- `NOT_COMPARABLE`

The overall workbook result can be:

- `MATCH`
- `MISMATCH`
- `PO NOT FOUND`

## CSV Validation Report

The validator generates a CSV report containing invoice validation and workbook comparison results.

The report is written to:

```text
data/output/
```

Generated output files are excluded from Git through `.gitignore`.

## Email Validation Workflow

After validation, the application builds an email summary containing:

- Total invoice count
- Passed invoice count
- Failed invoice count
- Purchase orders found in the workbook
- Purchase orders not found
- Workbook mismatch count
- Individual invoice results

The current email payload is sent to the configured AWS Lambda Function URL.

Example payload:

```json
{
  "subject": "Vendor Invoice Validation Result",
  "recipients": [
    "jan.abhi007@gmail.com"
  ],
  "from_email": "matiasl@nassaunationalcable.com",
  "text": "Validation summary..."
}
```

No email credentials or secrets are stored in the repository.

## AWS Lambda Integration

The project contains an S3 receipt-processing Lambda handler:

```text
lambda/lambda_function.py
```

The Lambda handler processes an order receipt and stores the receipt as a text file in an Amazon S3 bucket.

### Lambda Event

```json
{
  "Order_id": "TEST-001",
  "Amount": "125.50",
  "Item": "Test Cable"
}
```

### Required Environment Variable

```text
RECEIPT_BUCKET
```

This specifies the S3 bucket where receipts are stored.

### S3 Receipt

For the example event, the Lambda creates:

```text
receipts/TEST-001.txt
```

with:

```text
OrderID: TEST-001
Amount: $125.50
Item: Test Cable
```

### Lambda Response

A successful request returns:

```json
{
  "statusCode": 200,
  "message": "Receipt processed successfully"
}
```

The Lambda initializes the S3 client outside the handler and uses `put_object` to upload the receipt.

## AWS Email Function URL Status

The validation email client is configured to call the provided AWS Lambda Function URL.

The local validation workflow and email payload generation are working.

During local testing, the provided AWS Function URL returned:

```text
HTTP 403
AccessDeniedException
```

The AWS email endpoint therefore requires AWS-side access configuration to be resolved before real email delivery can be verified from the local application.

## Project Structure

```text
vendor-invoice-validation-automation/
│
├── lambda/
│   ├── lambda_function.py
│   └── requirements.txt
│
├── src/
│   ├── extraction/
│   │   ├── invoice_parser.py
│   │   ├── pdf_reader.py
│   │   └── requirements.txt
│   │
│   ├── validation/
│   │   ├── validator.py
│   │   ├── workbook_comparator.py
│   │   └── workbook_reader.py
│   │
│   └── email/
│       ├── email_client.py
│       └── local_email_function.py
│
├── tests/
│   ├── test_invoice_validation.py
│   ├── test_workbook_validation.py
│   ├── test_email_validation.py
│   ├── test_lambda_handler.py
│   └── meeting_system_test.py
│
├── data/
│   ├── invoices/
│   └── output/
│
├── requirements.txt
├── README.md
└── .gitignore
```

## Requirements

- Python 3
- PyMuPDF
- openpyxl
- pytest
- boto3 for the Lambda handler and AWS-related testing

## Setup

Create and activate the virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

Install the main dependencies:

```bash
pip install -r requirements.txt
```

Install the Lambda dependencies:

```bash
pip install -r lambda/requirements.txt
```

## Input Files

Place invoice PDFs in:

```text
data/invoices/
```

The Nassau workbook used for local validation is:

```text
data/Nassau.xlsx
```

The workbook is intentionally ignored by Git because it contains project data.

For workbook comparison testing, a separate personal test workbook can be used:

```text
data/Nassau_test.xlsx
```

Test workbooks should not replace or modify the real/current workbook.

## Running the Validator

From the project root:

```bash
python -u -m src.validation.validator
```

The validator processes the invoice PDFs, validates invoice data, compares available fields against the Nassau workbook, generates the CSV report, and builds the validation email payload.

A different workbook can be selected with:

```bash
NASSAU_WORKBOOK=/path/to/workbook.xlsx python -u -m src.validation.validator
```

## Running Tests

Run the complete test suite:

```bash
pytest -q
```

The latest full test run completed with:

```text
33 passed, 5 warnings
```

The warnings are PyMuPDF/Swig deprecation warnings and did not cause test failures.

### Lambda Tests

Run only the Lambda tests:

```bash
pytest -q tests/test_lambda_handler.py
```

The Lambda tests verify:

- Receipt content generation
- S3 upload parameters
- Receipt object key
- Successful Lambda response
- Required `RECEIPT_BUCKET` environment variable

No real S3 upload is performed by these tests.

## Meeting / End-to-End System Test

The meeting system test processes the real invoice dataset using the project parser and validation workflow and builds the same email payload that the application would send.

Run:

```bash
python -m tests.meeting_system_test
```

The test verifies:

- Invoice PDF processing
- Invoice validation
- Workbook lookup
- Validation summary generation
- Email payload generation

The test does not send the generated email to AWS.

## Current Validation Data

The current invoice dataset contains:

```text
12 invoice PDFs
```

The latest invoice-level validation result is:

```text
12 passed
0 failed
```

The current Nassau workbook test against the invoice dataset resulted in:

```text
POs found           : 0
POs not found       : 12
Workbook mismatches : 0
```

A separate personal test workbook has been used to demonstrate successful workbook field comparisons with controlled test data.

## Development

Before committing changes:

```bash
pytest -q
```

Check for whitespace errors:

```bash
git diff --check
```

Check the working tree:

```bash
git status
```

Review changes:

```bash
git diff
```

## Repository

GitHub repository:

https://github.com/Janabhi26/vendor-invoice-validation-automation
