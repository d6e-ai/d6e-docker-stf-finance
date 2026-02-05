# STF: Financial Statements Generator

D6E Docker STF for generating GAAP-formatted financial statements.

## Overview

This STF generates financial statements from GL data stored in the workspace database:

- **Income Statement (P&L)**: Revenue, expenses, and net income
- **Balance Sheet**: Assets, liabilities, and stockholders' equity
- **Cash Flow Statement**: Operating, investing, and financing activities
- **Trial Balance**: All accounts with debit/credit balances

## Operations

### `generate_income_statement`

Generates an income statement for the specified period.

**Input:**

```json
{
  "operation": "generate_income_statement",
  "period": "2025-01",
  "comparison_period": "2024-01",
  "department_id": "uuid-optional"
}
```

**Output:**

```json
{
  "output": {
    "status": "success",
    "operation": "generate_income_statement",
    "data": {
      "statement_type": "INCOME_STATEMENT",
      "period": "2025-01",
      "comparison_period": "2024-01",
      "sections": {
        "revenue": {
          "label": "Revenue",
          "items": [...],
          "total": 1000000,
          "comparison_total": 950000,
          "variance": {...}
        },
        "gross_profit": {...},
        "operating_expenses": {...},
        "operating_income": {...},
        "income_before_tax": {...}
      }
    }
  }
}
```

### `generate_balance_sheet`

Generates a balance sheet as of the period end.

**Input:**

```json
{
  "operation": "generate_balance_sheet",
  "period": "2025-01",
  "comparison_period": "2024-12"
}
```

**Output:**

```json
{
  "output": {
    "status": "success",
    "operation": "generate_balance_sheet",
    "data": {
      "statement_type": "BALANCE_SHEET",
      "period": "2025-01",
      "sections": {
        "current_assets": {...},
        "non_current_assets": {...},
        "total_assets": {...},
        "current_liabilities": {...},
        "non_current_liabilities": {...},
        "equity": {...},
        "total_liabilities_and_equity": {...}
      },
      "validation": {
        "balanced": true,
        "difference": 0
      }
    }
  }
}
```

### `generate_cash_flow`

Generates a cash flow statement using the indirect method.

**Input:**

```json
{
  "operation": "generate_cash_flow",
  "period": "2025-01"
}
```

**Output:**

```json
{
  "output": {
    "status": "success",
    "operation": "generate_cash_flow",
    "data": {
      "statement_type": "CASH_FLOW_STATEMENT",
      "method": "INDIRECT",
      "period": "2025-01",
      "sections": {
        "operating_activities": {
          "net_income": 150000,
          "adjustments": {...},
          "working_capital_changes": {...},
          "net_cash": 180000
        },
        "investing_activities": {...},
        "financing_activities": {...},
        "summary": {
          "net_change_in_cash": 50000
        }
      }
    }
  }
}
```

### `generate_trial_balance`

Generates a trial balance showing all account balances.

**Input:**

```json
{
  "operation": "generate_trial_balance",
  "period": "2025-01"
}
```

**Output:**

```json
{
  "output": {
    "status": "success",
    "operation": "generate_trial_balance",
    "data": {
      "statement_type": "TRIAL_BALANCE",
      "period": "2025-01",
      "items": [
        {
          "account_code": "1000",
          "account_name": "Cash",
          "account_type": "ASSET",
          "debit": 500000,
          "credit": 0
        }
      ],
      "totals": {
        "total_debits": 5000000,
        "total_credits": 5000000,
        "balanced": true
      }
    }
  }
}
```

## Database Requirements

This STF requires the following tables:

- `accounts` - Chart of accounts
- `chart_of_accounts` - Account type definitions
- `account_balances` - Period-end balances
- `fiscal_periods` - Accounting periods

See `docs/DATABASE_SCHEMA.md` for complete schema documentation.

## Build & Test

```bash
# Build
docker build -t stf-financial-statements:latest .

# Test
echo '{
  "workspace_id": "test-ws",
  "stf_id": "test-stf",
  "caller": null,
  "api_url": "http://localhost:8080",
  "api_token": "test-token",
  "input": {
    "operation": "generate_trial_balance",
    "period": "2025-01"
  },
  "sources": {}
}' | docker run --rm -i stf-financial-statements:latest
```

## Error Handling

Errors are returned in the standard D6E format:

```json
{
  "error": "Missing required field: period",
  "type": "ValidationError"
}
```
