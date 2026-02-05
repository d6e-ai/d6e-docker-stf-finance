# STF: Journal Entry Preparation

D6E Docker STF for preparing and validating journal entries.

## Overview

This STF handles journal entry workflows:

- **Create Journal Entry**: Build properly formatted entries with validation
- **Validate Entry**: Check business rules before posting
- **Calculate Depreciation**: Auto-generate depreciation entries
- **Calculate Prepaid Amortization**: Generate amortization entries
- **Generate Accrual**: Create standard accrual entries with auto-reversal

## Operations

### `create_journal_entry`

Create a new journal entry (in DRAFT status).

**Input:**

```json
{
  "operation": "create_journal_entry",
  "entry_date": "2025-01-31",
  "description": "Accrue January professional services",
  "entry_type": "ADJUSTING",
  "is_auto_reverse": true,
  "reverse_date": "2025-02-01",
  "created_by": "john.doe@company.com",
  "lines": [
    {
      "account_id": "uuid-expense-account",
      "department_id": "uuid-department",
      "debit_amount": 10000,
      "credit_amount": 0,
      "description": "Consulting services",
      "reference": "PO-2025-001"
    },
    {
      "account_id": "uuid-liability-account",
      "debit_amount": 0,
      "credit_amount": 10000,
      "description": "Accrued professional fees"
    }
  ]
}
```

**Output:**

```json
{
  "output": {
    "status": "success",
    "operation": "create_journal_entry",
    "data": {
      "entry_number": "JE-20250131120000-ABC123",
      "entry_date": "2025-01-31",
      "status": "DRAFT",
      "lines": [...],
      "totals": {
        "total_debits": 10000,
        "total_credits": 10000,
        "line_count": 2
      }
    }
  }
}
```

### `validate_journal_entry`

Validate an entry against business rules.

**Input:**

```json
{
  "operation": "validate_journal_entry",
  "entry": {
    "entry_number": "JE-20250131120000-ABC123",
    "description": "Test entry",
    "lines": [...]
  }
}
```

**Output:**

```json
{
  "output": {
    "status": "success",
    "data": {
      "entry_number": "JE-20250131120000-ABC123",
      "is_valid": true,
      "errors": [],
      "warnings": [
        {
          "code": "ROUND_NUMBER",
          "message": "Line 1: Amount $10,000.00 is a round number - verify this is not an estimate"
        }
      ]
    }
  }
}
```

### `calculate_depreciation`

Generate depreciation entries for a period.

**Input:**

```json
{
  "operation": "calculate_depreciation",
  "period": "2025-01",
  "asset_category": "EQUIPMENT"
}
```

### `calculate_prepaid_amortization`

Generate prepaid expense amortization.

**Input:**

```json
{
  "operation": "calculate_prepaid_amortization",
  "period": "2025-01"
}
```

### `generate_accrual_entry`

Create a standard accrual entry with auto-reversal.

**Input:**

```json
{
  "operation": "generate_accrual_entry",
  "accrual_type": "AP_ACCRUAL",
  "period": "2025-01",
  "amount": 15000,
  "description": "Unbilled consulting services",
  "expense_account_id": "uuid-consulting-expense",
  "liability_account_id": "uuid-accrued-liabilities",
  "department_id": "uuid-engineering",
  "reference": "Contract #12345"
}
```

### `list_pending_entries`

List entries pending approval.

**Input:**

```json
{
  "operation": "list_pending_entries",
  "period": "2025-01",
  "status": "DRAFT"
}
```

## Validation Rules

The STF validates:

1. **Balance Check**: Debits must equal credits
2. **Minimum Lines**: Entry must have at least 2 lines
3. **Single-sided Lines**: Each line has either debit or credit, not both
4. **Non-zero Amounts**: Lines cannot have zero amounts
5. **Description Required**: Entry must have a description
6. **Period Status**: Cannot post to hard-closed periods

## Entry Types

- `STANDARD`: Normal business transactions
- `ADJUSTING`: Period-end adjustments (accruals, deferrals)
- `CLOSING`: Year-end closing entries
- `REVERSING`: Reversal of prior entries

## Build & Test

```bash
docker build -t stf-journal-entry:latest .

echo '{
  "workspace_id": "test-ws",
  "stf_id": "test-stf",
  "caller": null,
  "api_url": "http://localhost:8080",
  "api_token": "test-token",
  "input": {
    "operation": "calculate_depreciation",
    "period": "2025-01"
  },
  "sources": {}
}' | docker run --rm -i stf-journal-entry:latest
```
