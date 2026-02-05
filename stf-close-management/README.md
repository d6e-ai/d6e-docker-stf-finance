# STF: Close Management

D6E Docker STF for managing month-end close processes.

## Overview

This STF handles close management:

- **Initialize Close Tasks**: Set up standard close checklist for a period
- **Track Progress**: Monitor task completion and overall close health
- **Identify Blockers**: Find blocked tasks and dependencies
- **Generate Calendar**: Create close calendar with deadlines
- **Critical Path**: Identify tasks determining minimum close duration

## Operations

### `initialize_close_tasks`

Set up close tasks for a new period.

**Input:**

```json
{
  "operation": "initialize_close_tasks",
  "period": "2025-01",
  "period_end_date": "2025-01-31",
  "close_days": 5,
  "assignees": {
    "CASH": "treasury@company.com",
    "PAYROLL": "payroll@company.com",
    "RECONCILIATION": "accounting@company.com",
    "TAX": "tax@company.com",
    "REPORTING": "controller@company.com"
  }
}
```

**Output:**

```json
{
  "output": {
    "status": "success",
    "data": {
      "period": "2025-01",
      "schedule": {
        "T+1": {
          "date": "2025-02-03",
          "tasks": [...]
        },
        "T+2": {...},
        "T+3": {...},
        "T+4": {...},
        "T+5": {...}
      },
      "summary": {
        "total_tasks": 25,
        "tasks_by_category": {
          "CASH": 1,
          "RECONCILIATION": 5,
          "ACCRUALS": 2
        }
      }
    }
  }
}
```

### `update_task_status`

Update status of a specific task.

**Input:**

```json
{
  "operation": "update_task_status",
  "task_id": "uuid-task",
  "new_status": "COMPLETED",
  "notes": "Bank rec completed, no exceptions",
  "completed_by": "john.doe@company.com"
}
```

**Valid Statuses:**
- `NOT_STARTED`: Task not yet begun
- `IN_PROGRESS`: Task actively being worked
- `COMPLETED`: Task finished
- `BLOCKED`: Task cannot proceed

### `get_close_progress`

Get overall close progress and health status.

**Input:**

```json
{
  "operation": "get_close_progress",
  "period": "2025-01"
}
```

**Output:**

```json
{
  "output": {
    "status": "success",
    "data": {
      "period": "2025-01",
      "progress": {
        "total_tasks": 25,
        "completed": 15,
        "in_progress": 5,
        "not_started": 3,
        "blocked": 2,
        "completion_percentage": 60
      },
      "late_tasks": [...],
      "health": {
        "status": "NEEDS_ATTENTION",
        "message": "Close needs attention - some tasks behind schedule",
        "risk_factors": {
          "blocked_tasks": 2,
          "late_tasks": 1
        }
      }
    }
  }
}
```

### `identify_blockers`

Find blocked tasks and what's blocking them.

**Input:**

```json
{
  "operation": "identify_blockers",
  "period": "2025-01"
}
```

**Output:**

```json
{
  "output": {
    "status": "success",
    "data": {
      "blocked_tasks": [
        {
          "name": "Complete all balance sheet reconciliations",
          "status": "BLOCKED",
          "blocking_tasks": [
            {"name": "Complete bank reconciliation", "status": "IN_PROGRESS"}
          ]
        }
      ],
      "critical_blockers": [
        {
          "task_name": "Complete bank reconciliation",
          "blocking_count": 3
        }
      ],
      "recommendations": [
        "Priority: Complete 'Complete bank reconciliation' - it is blocking 3 other tasks"
      ]
    }
  }
}
```

### `generate_close_calendar`

Create close calendar with all deadlines.

**Input:**

```json
{
  "operation": "generate_close_calendar",
  "period": "2025-01",
  "period_end_date": "2025-01-31",
  "close_days": 5
}
```

**Output includes text calendar:**

```
CLOSE CALENDAR: 2025-01
Period End: 2025-01-31
Target Close: 2025-02-07
======================================================================

T+1 - 2025-02-03 (Monday)
----------------------------------------
  [ ] Record cash receipts and disbursements
  [ ] Post payroll entries
  [ ] Run AP accruals
  ...
  Milestones: All subledgers processed, Payroll entries posted

T+2 - 2025-02-04 (Tuesday)
...
```

### `get_critical_path`

Identify critical path for close process.

**Input:**

```json
{
  "operation": "get_critical_path",
  "period": "2025-01"
}
```

**Output:**

```json
{
  "output": {
    "status": "success",
    "data": {
      "critical_path": [
        "Run AP accruals",
        "Complete AP subledger reconciliation",
        "Complete all balance sheet reconciliations",
        "Post reconciliation adjustments",
        "Run preliminary trial balance",
        "Post tax provision entries",
        "Generate draft financial statements",
        "Perform detailed flux analysis",
        "Management review of financials",
        "Post final adjustments",
        "Finalize financial statements",
        "Lock period in system"
      ],
      "minimum_close_days": 5,
      "acceleration_opportunities": [
        "Automate depreciation and amortization entries",
        "Pre-reconcile accounts during the month"
      ]
    }
  }
}
```

## Standard Close Tasks

The STF includes 25 standard close tasks organized across 5 days:

| Day | Focus Areas |
|-----|-------------|
| T+1 | Cash entries, payroll, accruals, depreciation |
| T+2 | Revenue recognition, subledger reconciliations |
| T+3 | Balance sheet reconciliations, preliminary TB |
| T+4 | Tax provision, draft financials, management review |
| T+5 | Final adjustments, hard close, reporting |

## Task Categories

- `CASH`: Cash receipts and disbursements
- `PAYROLL`: Payroll entries and accruals
- `ACCRUALS`: AP and other accruals
- `DEPRECIATION`: Fixed asset depreciation
- `AMORTIZATION`: Prepaid expense amortization
- `INTERCOMPANY`: Intercompany transactions
- `RECONCILIATION`: Account reconciliations
- `REVENUE`: Revenue recognition
- `FX`: Foreign exchange
- `TAX`: Tax provision
- `EQUITY`: Equity roll-forward
- `REPORTING`: Financial statements
- `ANALYSIS`: Flux analysis
- `REVIEW`: Management review
- `ADJUSTMENTS`: Adjusting entries
- `CLOSE`: Period close
- `PROCESS`: Process improvement

## Build & Test

```bash
docker build -t stf-close-management:latest .

echo '{
  "workspace_id": "test-ws",
  "stf_id": "test-stf",
  "caller": null,
  "api_url": "http://localhost:8080",
  "api_token": "test-token",
  "input": {
    "operation": "generate_close_calendar",
    "period": "2025-01",
    "period_end_date": "2025-01-31",
    "close_days": 5
  },
  "sources": {}
}' | docker run --rm -i stf-close-management:latest
```
