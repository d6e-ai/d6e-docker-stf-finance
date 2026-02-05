# D6E Finance STF Suite

Docker-based State Transition Functions (STFs) for financial workflows on the D6E platform.

## Overview

This repository contains 5 Docker STFs implementing financial workflows based on the [Anthropic Knowledge Work Plugins - Finance](https://github.com/anthropics/knowledge-work-plugins/tree/main/finance):

| STF                          | Description                          | Key Operations                                            |
| ---------------------------- | ------------------------------------ | --------------------------------------------------------- |
| **stf-financial-statements** | Generate GAAP financial statements   | Income Statement, Balance Sheet, Cash Flow, Trial Balance |
| **stf-journal-entry**        | Prepare and validate journal entries | Create entries, depreciation, amortization, accruals      |
| **stf-variance-analysis**    | Analyze financial variances          | Budget vs Actual, Period comparison, Waterfall charts     |
| **stf-reconciliation**       | Reconcile accounts                   | Bank rec, GL-Subledger, Intercompany                      |
| **stf-close-management**     | Manage month-end close               | Task tracking, dependencies, progress monitoring          |

## Quick Start

### 1. Build All Images

```bash
./scripts/build-all.sh
```

Or build individually:

```bash
cd stf-financial-statements
docker build -t stf-financial-statements:latest .
```

### 2. Test an STF

```bash
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

## Project Structure

```
d6e-docker-stf-finance/
├── docs/
│   ├── DATABASE_SCHEMA.md    # Database schema documentation
│   └── SAMPLE_DATA.sql       # Test data for development
├── shared/
│   └── utils.py              # Shared utilities for all STFs
├── stf-financial-statements/ # Financial statement generation
├── stf-journal-entry/        # Journal entry preparation
├── stf-variance-analysis/    # Variance analysis
├── stf-reconciliation/       # Account reconciliation
├── stf-close-management/     # Close process management
├── scripts/
│   └── build-all.sh          # Build all Docker images
└── README.md
```

## Database Requirements

All STFs require access to the workspace database with the schema defined in `docs/DATABASE_SCHEMA.md`.

Key tables:

- `chart_of_accounts` - Account type definitions
- `accounts` - Individual GL accounts
- `departments` - Cost centers
- `fiscal_periods` - Accounting periods
- `journal_entries` / `journal_lines` - Transactions
- `account_balances` - Period-end snapshots
- `budgets` - Budget data
- `reconciliations` / `reconciling_items` - Reconciliation tracking
- `close_tasks` - Close task management

## STF Input/Output Format

### Input (via stdin)

```json
{
  "workspace_id": "UUID",
  "stf_id": "UUID",
  "caller": "UUID | null",
  "api_url": "http://api:8080",
  "api_token": "internal_token",
  "input": {
    "operation": "operation_name",
    ...parameters
  },
  "sources": {
    "previous_step": { "output": {...} }
  }
}
```

### Output (via stdout)

**Success:**

```json
{
  "output": {
    "status": "success",
    "operation": "operation_name",
    "data": {...}
  }
}
```

**Error:**

```json
{
  "error": "Error message",
  "type": "ErrorType"
}
```

## Operations Summary

### stf-financial-statements

| Operation                   | Required Params | Description                           |
| --------------------------- | --------------- | ------------------------------------- |
| `generate_income_statement` | `period`        | Generate P&L with optional comparison |
| `generate_balance_sheet`    | `period`        | Generate balance sheet                |
| `generate_cash_flow`        | `period`        | Generate cash flow (indirect method)  |
| `generate_trial_balance`    | `period`        | Generate trial balance                |

### stf-journal-entry

| Operation                        | Required Params                         | Description                      |
| -------------------------------- | --------------------------------------- | -------------------------------- |
| `create_journal_entry`           | `entry_date`, `description`, `lines`    | Create new journal entry         |
| `validate_journal_entry`         | `entry`                                 | Validate entry against rules     |
| `calculate_depreciation`         | `period`                                | Generate depreciation entries    |
| `calculate_prepaid_amortization` | `period`                                | Generate amortization entries    |
| `generate_accrual_entry`         | `accrual_type`, `period`, `amount`, ... | Create accrual with auto-reverse |
| `list_pending_entries`           | -                                       | List entries pending approval    |

### stf-variance-analysis

| Operation                     | Required Params                               | Description                   |
| ----------------------------- | --------------------------------------------- | ----------------------------- |
| `analyze_budget_variance`     | `period`                                      | Compare actual to budget      |
| `analyze_period_variance`     | `current_period`, `comparison_period`         | Period-over-period analysis   |
| `decompose_variance`          | `account_code`, `period`, `comparison_period` | Price/volume/mix breakdown    |
| `generate_waterfall`          | `start_value`, `end_value`, `drivers`         | Create waterfall chart data   |
| `generate_variance_narrative` | `variance_item`                               | Generate variance explanation |

### stf-reconciliation

| Operation                    | Required Params                                                              | Description                    |
| ---------------------------- | ---------------------------------------------------------------------------- | ------------------------------ |
| `create_bank_reconciliation` | `bank_account_id`, `period`, `bank_statement_balance`, `bank_statement_date` | Bank rec                       |
| `create_gl_subledger_rec`    | `control_account_id`, `period`, `subledger_balance`, `subledger_source`      | GL-SL rec                      |
| `create_intercompany_rec`    | `entity_a_account_id`, `entity_b_account_id`, `period`                       | IC rec                         |
| `add_reconciling_item`       | `reconciliation_id`, `item_date`, `description`, `amount`, `category`        | Add rec item                   |
| `analyze_aging`              | -                                                                            | Analyze reconciling item aging |
| `get_reconciliation_status`  | `period`                                                                     | Get all rec status             |

### stf-close-management

| Operation                 | Required Params             | Description            |
| ------------------------- | --------------------------- | ---------------------- |
| `initialize_close_tasks`  | `period`, `period_end_date` | Set up close tasks     |
| `update_task_status`      | `task_id`, `new_status`     | Update task status     |
| `get_close_progress`      | `period`                    | Get overall progress   |
| `identify_blockers`       | `period`                    | Find blocked tasks     |
| `generate_close_calendar` | `period`, `period_end_date` | Create close calendar  |
| `get_critical_path`       | `period`                    | Identify critical path |

## Development

### Adding a New STF

1. Create directory: `stf-new-function/`
2. Copy structure from existing STF
3. Implement `main.py` with operation handlers
4. Create `Dockerfile`, `requirements.txt`, `README.md`
5. Add to `scripts/build-all.sh`

### Testing Locally

```bash
# Build
docker build -t my-stf:latest .

# Test with sample input
cat test-input.json | docker run --rm -i my-stf:latest

# Debug mode
docker run --rm -it --entrypoint /bin/bash my-stf:latest
```

## License

MIT License - See LICENSE file for details.

## References

- [D6E Platform Documentation](https://docs.d6e.ai)
- [Anthropic Knowledge Work Plugins - Finance](https://github.com/anthropics/knowledge-work-plugins/tree/main/finance)
