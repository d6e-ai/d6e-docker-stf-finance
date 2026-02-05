# STF: Account Reconciliation

D6E Docker STF for account reconciliation workflows.

## Overview

This STF handles reconciliation tasks:

- **Bank Reconciliation**: Compare GL cash to bank statement
- **GL-Subledger Reconciliation**: Compare control accounts to subledgers
- **Intercompany Reconciliation**: Verify IC balances net to zero
- **Reconciling Item Management**: Track and age outstanding items

## Operations

### `create_bank_reconciliation`

Create a bank reconciliation comparing GL to bank statement.

**Input:**

```json
{
  "operation": "create_bank_reconciliation",
  "bank_account_id": "uuid-cash-account",
  "period": "2025-01",
  "bank_statement_balance": 1250000,
  "bank_statement_date": "2025-01-31"
}
```

**Output:**

```json
{
  "output": {
    "status": "success",
    "data": {
      "reconciliation_type": "BANK",
      "account_code": "1000",
      "account_name": "Cash - Operating",
      "bank_side": {
        "balance_per_bank": 1250000,
        "adjustments": [...],
        "adjusted_balance": 1248000
      },
      "gl_side": {
        "balance_per_gl": 1248000,
        "adjusted_balance": 1248000
      },
      "reconciling_items": {
        "outstanding_checks": [...],
        "deposits_in_transit": [...]
      },
      "validation": {
        "is_reconciled": true,
        "difference": 0
      },
      "text_format": "BANK RECONCILIATION - Cash - Operating (1000)\n..."
    }
  }
}
```

### `create_gl_subledger_rec`

Reconcile GL control account to subledger.

**Input:**

```json
{
  "operation": "create_gl_subledger_rec",
  "control_account_id": "uuid-ar-control",
  "period": "2025-01",
  "subledger_balance": 500000,
  "subledger_source": "AR_AGING_REPORT"
}
```

**Output:**

```json
{
  "output": {
    "status": "success",
    "data": {
      "reconciliation_type": "GL_SUBLEDGER",
      "account_code": "1200",
      "account_name": "Accounts Receivable",
      "gl_balance": 502000,
      "subledger_balance": 500000,
      "difference": 2000,
      "reconciling_items": [
        {
          "description": "Unidentified difference",
          "amount": 2000,
          "category": "INVESTIGATION",
          "possible_causes": [
            "Manual journal entries to control account",
            "Subledger transactions pending interface"
          ]
        }
      ],
      "validation": {
        "is_reconciled": false
      }
    }
  }
}
```

### `create_intercompany_rec`

Reconcile intercompany balances between entities.

**Input:**

```json
{
  "operation": "create_intercompany_rec",
  "entity_a_account_id": "uuid-ic-receivable-from-b",
  "entity_b_account_id": "uuid-ic-payable-to-a",
  "period": "2025-01"
}
```

### `add_reconciling_item`

Add a reconciling item to an existing reconciliation.

**Input:**

```json
{
  "operation": "add_reconciling_item",
  "reconciliation_id": "uuid-reconciliation",
  "item_date": "2025-01-15",
  "description": "Outstanding check #5432",
  "amount": -5000,
  "category": "TIMING",
  "reference": "CHK-5432",
  "notes": "Payment to Vendor ABC"
}
```

### `analyze_aging`

Analyze aging of outstanding reconciling items.

**Input:**

```json
{
  "operation": "analyze_aging",
  "account_id": "uuid-optional",
  "period": "2025-01"
}
```

**Output:**

```json
{
  "output": {
    "status": "success",
    "data": {
      "summary": {
        "total_items": 15,
        "total_amount": 75000,
        "items_requiring_escalation": 3
      },
      "age_buckets": [
        {
          "bucket": "Current (0-30)",
          "status": "CURRENT",
          "count": 8,
          "total": 25000,
          "percentage_of_total": 0.33
        },
        {
          "bucket": "Aging (31-60)",
          "status": "AGING",
          "count": 4,
          "total": 30000,
          "percentage_of_total": 0.40
        },
        {
          "bucket": "Stale (90+)",
          "status": "STALE",
          "count": 3,
          "total": 20000,
          "percentage_of_total": 0.27
        }
      ],
      "escalation_items": [...]
    }
  }
}
```

### `get_reconciliation_status`

Get status of all reconciliations for a period.

**Input:**

```json
{
  "operation": "get_reconciliation_status",
  "period": "2025-01",
  "reconciliation_type": "BANK"
}
```

## Reconciling Item Categories

- `TIMING`: Normal processing timing (outstanding checks, deposits in transit)
- `ADJUSTMENT_REQUIRED`: Requires journal entry to correct
- `INVESTIGATION`: Unknown difference requiring research

## Age Buckets

| Bucket  | Days  | Status  | Action                 |
| ------- | ----- | ------- | ---------------------- |
| Current | 0-30  | CURRENT | Monitor                |
| Aging   | 31-60 | AGING   | Investigate            |
| Overdue | 61-90 | OVERDUE | Escalate to supervisor |
| Stale   | 90+   | STALE   | Escalate to management |

## Build & Test

```bash
docker build -t stf-reconciliation:latest .

echo '{
  "workspace_id": "test-ws",
  "stf_id": "test-stf",
  "caller": null,
  "api_url": "http://localhost:8080",
  "api_token": "test-token",
  "input": {
    "operation": "create_bank_reconciliation",
    "bank_account_id": "test-account-id",
    "period": "2025-01",
    "bank_statement_balance": 100000,
    "bank_statement_date": "2025-01-31"
  },
  "sources": {}
}' | docker run --rm -i stf-reconciliation:latest
```
