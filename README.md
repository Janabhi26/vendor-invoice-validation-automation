# Vendor Invoice Validation Automation

Automation for extracting and validating vendor invoice data from PDF invoices.

## Overview

This project processes vendor invoice PDFs, identifies the invoice format, extracts important invoice information and line items, and validates the extracted data.

The current implementation supports two invoice formats:

- Standard vendor invoices
- Commodity Cables invoices

The validation process checks required invoice fields, line-item calculations, and the final invoice total.

## Supported Invoice Formats

### 1. Standard Invoices

Standard invoices contain fields such as:

- Invoice number
- Invoice date
- Customer
- Purchase order (PO) number
- Ship-to information
- Tracking number
- Line items
- Unit price
- Price unit
- Invoice total

The parser also handles:

- Multiple product line items
- MFT pricing
- Freight charges
- `F1 FREIGHT CHARGE` line items

For MFT pricing, the price represents the cost per 1,000 feet.

For example:

```text
15 FT × $1,950 per MFT
= 15 × 1,950 / 1,000
= $29.25