# Finance STF Database Schema

This document describes the database schema required for the D6E Finance STF suite.

## Overview

The schema is designed to support:
- Financial statement generation (Income Statement, Balance Sheet, Cash Flow)
- Journal entry preparation and posting
- Variance analysis (Budget vs Actual, Period-over-Period)
- Account reconciliation
- Month-end close management

## Entity Relationship Diagram (Text)

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   chart_of_     │     │    accounts     │     │   departments   │
│   accounts      │────▶│                 │◀────│                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
        ▼                      ▼                      ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ journal_entries │     │ account_balances│     │    budgets      │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │
        ▼
┌─────────────────┐
│ journal_lines   │
└─────────────────┘

┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ bank_statements │     │ reconciliations │     │  close_tasks    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

## Tables

### 1. chart_of_accounts

Master table defining account types and categories.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| account_type | VARCHAR(50) | ASSET, LIABILITY, EQUITY, REVENUE, EXPENSE |
| account_category | VARCHAR(100) | Sub-category (e.g., Current Asset, Operating Expense) |
| normal_balance | VARCHAR(10) | DEBIT or CREDIT |
| display_order | INTEGER | Order for financial statement presentation |
| created_at | TIMESTAMP | Creation timestamp |
| updated_at | TIMESTAMP | Last update timestamp |

```sql
CREATE TABLE chart_of_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_type VARCHAR(50) NOT NULL,
    account_category VARCHAR(100) NOT NULL,
    normal_balance VARCHAR(10) NOT NULL CHECK (normal_balance IN ('DEBIT', 'CREDIT')),
    display_order INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 2. accounts

Individual GL accounts.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| account_code | VARCHAR(20) | Account number (e.g., "1000", "4100") |
| account_name | VARCHAR(255) | Account description |
| chart_of_accounts_id | UUID | FK to chart_of_accounts |
| department_id | UUID | FK to departments (optional) |
| is_active | BOOLEAN | Whether account is active |
| is_control_account | BOOLEAN | Whether this is a control account with subledger |
| parent_account_id | UUID | FK to parent account for hierarchies |
| created_at | TIMESTAMP | Creation timestamp |
| updated_at | TIMESTAMP | Last update timestamp |

```sql
CREATE TABLE accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_code VARCHAR(20) NOT NULL UNIQUE,
    account_name VARCHAR(255) NOT NULL,
    chart_of_accounts_id UUID NOT NULL REFERENCES chart_of_accounts(id),
    department_id UUID REFERENCES departments(id),
    is_active BOOLEAN DEFAULT TRUE,
    is_control_account BOOLEAN DEFAULT FALSE,
    parent_account_id UUID REFERENCES accounts(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 3. departments

Cost centers / departments for expense allocation.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| department_code | VARCHAR(20) | Department code |
| department_name | VARCHAR(255) | Department name |
| parent_department_id | UUID | FK for department hierarchy |
| is_active | BOOLEAN | Whether department is active |
| created_at | TIMESTAMP | Creation timestamp |

```sql
CREATE TABLE departments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    department_code VARCHAR(20) NOT NULL UNIQUE,
    department_name VARCHAR(255) NOT NULL,
    parent_department_id UUID REFERENCES departments(id),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 4. fiscal_periods

Accounting periods for close tracking.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| period_name | VARCHAR(20) | Period name (e.g., "2025-01") |
| period_start | DATE | First day of period |
| period_end | DATE | Last day of period |
| fiscal_year | INTEGER | Fiscal year |
| fiscal_quarter | INTEGER | Fiscal quarter (1-4) |
| fiscal_month | INTEGER | Fiscal month (1-12) |
| status | VARCHAR(20) | OPEN, SOFT_CLOSE, HARD_CLOSE |
| closed_at | TIMESTAMP | When period was closed |
| closed_by | VARCHAR(255) | Who closed the period |

```sql
CREATE TABLE fiscal_periods (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    period_name VARCHAR(20) NOT NULL UNIQUE,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    fiscal_year INTEGER NOT NULL,
    fiscal_quarter INTEGER NOT NULL CHECK (fiscal_quarter BETWEEN 1 AND 4),
    fiscal_month INTEGER NOT NULL CHECK (fiscal_month BETWEEN 1 AND 12),
    status VARCHAR(20) DEFAULT 'OPEN' CHECK (status IN ('OPEN', 'SOFT_CLOSE', 'HARD_CLOSE')),
    closed_at TIMESTAMP,
    closed_by VARCHAR(255)
);
```

### 5. journal_entries

Header table for journal entries.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| entry_number | VARCHAR(50) | Unique entry identifier |
| entry_date | DATE | Transaction date |
| fiscal_period_id | UUID | FK to fiscal_periods |
| description | TEXT | Entry description |
| entry_type | VARCHAR(50) | STANDARD, ADJUSTING, CLOSING, REVERSING |
| source | VARCHAR(100) | Source system or manual |
| status | VARCHAR(20) | DRAFT, PENDING_APPROVAL, APPROVED, POSTED, REJECTED |
| is_auto_reverse | BOOLEAN | Whether entry auto-reverses |
| reverse_date | DATE | Date for auto-reversal |
| created_by | VARCHAR(255) | Preparer |
| approved_by | VARCHAR(255) | Approver |
| posted_at | TIMESTAMP | When entry was posted |
| created_at | TIMESTAMP | Creation timestamp |

```sql
CREATE TABLE journal_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entry_number VARCHAR(50) NOT NULL UNIQUE,
    entry_date DATE NOT NULL,
    fiscal_period_id UUID NOT NULL REFERENCES fiscal_periods(id),
    description TEXT NOT NULL,
    entry_type VARCHAR(50) NOT NULL CHECK (entry_type IN ('STANDARD', 'ADJUSTING', 'CLOSING', 'REVERSING')),
    source VARCHAR(100) DEFAULT 'MANUAL',
    status VARCHAR(20) DEFAULT 'DRAFT' CHECK (status IN ('DRAFT', 'PENDING_APPROVAL', 'APPROVED', 'POSTED', 'REJECTED')),
    is_auto_reverse BOOLEAN DEFAULT FALSE,
    reverse_date DATE,
    created_by VARCHAR(255) NOT NULL,
    approved_by VARCHAR(255),
    posted_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 6. journal_lines

Line items for journal entries.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| journal_entry_id | UUID | FK to journal_entries |
| line_number | INTEGER | Line sequence number |
| account_id | UUID | FK to accounts |
| department_id | UUID | FK to departments (optional) |
| debit_amount | DECIMAL(18,2) | Debit amount (0 if credit) |
| credit_amount | DECIMAL(18,2) | Credit amount (0 if debit) |
| description | TEXT | Line description |
| reference | VARCHAR(255) | Reference (PO#, Invoice#, etc.) |

```sql
CREATE TABLE journal_lines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    journal_entry_id UUID NOT NULL REFERENCES journal_entries(id) ON DELETE CASCADE,
    line_number INTEGER NOT NULL,
    account_id UUID NOT NULL REFERENCES accounts(id),
    department_id UUID REFERENCES departments(id),
    debit_amount DECIMAL(18,2) DEFAULT 0,
    credit_amount DECIMAL(18,2) DEFAULT 0,
    description TEXT,
    reference VARCHAR(255),
    CONSTRAINT check_debit_or_credit CHECK (
        (debit_amount > 0 AND credit_amount = 0) OR
        (credit_amount > 0 AND debit_amount = 0)
    )
);
```

### 7. account_balances

Period-end account balances (snapshot).

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| account_id | UUID | FK to accounts |
| fiscal_period_id | UUID | FK to fiscal_periods |
| beginning_balance | DECIMAL(18,2) | Balance at period start |
| debit_activity | DECIMAL(18,2) | Total debits in period |
| credit_activity | DECIMAL(18,2) | Total credits in period |
| ending_balance | DECIMAL(18,2) | Balance at period end |
| created_at | TIMESTAMP | Creation timestamp |

```sql
CREATE TABLE account_balances (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID NOT NULL REFERENCES accounts(id),
    fiscal_period_id UUID NOT NULL REFERENCES fiscal_periods(id),
    beginning_balance DECIMAL(18,2) DEFAULT 0,
    debit_activity DECIMAL(18,2) DEFAULT 0,
    credit_activity DECIMAL(18,2) DEFAULT 0,
    ending_balance DECIMAL(18,2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(account_id, fiscal_period_id)
);
```

### 8. budgets

Budget data by account and period.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| account_id | UUID | FK to accounts |
| department_id | UUID | FK to departments (optional) |
| fiscal_period_id | UUID | FK to fiscal_periods |
| budget_version | VARCHAR(50) | Version (e.g., "ORIGINAL", "REVISED_Q2") |
| budget_amount | DECIMAL(18,2) | Budgeted amount |
| notes | TEXT | Budget notes |
| created_at | TIMESTAMP | Creation timestamp |

```sql
CREATE TABLE budgets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID NOT NULL REFERENCES accounts(id),
    department_id UUID REFERENCES departments(id),
    fiscal_period_id UUID NOT NULL REFERENCES fiscal_periods(id),
    budget_version VARCHAR(50) DEFAULT 'ORIGINAL',
    budget_amount DECIMAL(18,2) NOT NULL,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(account_id, department_id, fiscal_period_id, budget_version)
);
```

### 9. bank_statements

Bank statement data for reconciliation.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| bank_account_id | UUID | FK to accounts (cash account) |
| statement_date | DATE | Statement date |
| beginning_balance | DECIMAL(18,2) | Opening balance |
| ending_balance | DECIMAL(18,2) | Closing balance |
| created_at | TIMESTAMP | Creation timestamp |

```sql
CREATE TABLE bank_statements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bank_account_id UUID NOT NULL REFERENCES accounts(id),
    statement_date DATE NOT NULL,
    beginning_balance DECIMAL(18,2) NOT NULL,
    ending_balance DECIMAL(18,2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(bank_account_id, statement_date)
);
```

### 10. bank_transactions

Individual bank statement line items.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| bank_statement_id | UUID | FK to bank_statements |
| transaction_date | DATE | Transaction date |
| description | TEXT | Bank description |
| amount | DECIMAL(18,2) | Amount (positive = credit, negative = debit) |
| transaction_type | VARCHAR(50) | CHECK, DEPOSIT, WIRE, FEE, INTEREST, etc. |
| reference | VARCHAR(255) | Check number or reference |
| is_reconciled | BOOLEAN | Whether matched to GL |
| reconciled_journal_line_id | UUID | FK to journal_lines if matched |

```sql
CREATE TABLE bank_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bank_statement_id UUID NOT NULL REFERENCES bank_statements(id),
    transaction_date DATE NOT NULL,
    description TEXT,
    amount DECIMAL(18,2) NOT NULL,
    transaction_type VARCHAR(50) NOT NULL,
    reference VARCHAR(255),
    is_reconciled BOOLEAN DEFAULT FALSE,
    reconciled_journal_line_id UUID REFERENCES journal_lines(id)
);
```

### 11. reconciliations

Reconciliation records.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| account_id | UUID | FK to accounts |
| fiscal_period_id | UUID | FK to fiscal_periods |
| reconciliation_type | VARCHAR(50) | BANK, GL_SUBLEDGER, INTERCOMPANY |
| gl_balance | DECIMAL(18,2) | GL ending balance |
| external_balance | DECIMAL(18,2) | Bank/subledger/IC balance |
| reconciling_items_total | DECIMAL(18,2) | Sum of reconciling items |
| adjusted_balance | DECIMAL(18,2) | Adjusted balance (should match) |
| status | VARCHAR(20) | DRAFT, IN_PROGRESS, COMPLETED, APPROVED |
| prepared_by | VARCHAR(255) | Preparer |
| approved_by | VARCHAR(255) | Approver |
| completed_at | TIMESTAMP | Completion timestamp |

```sql
CREATE TABLE reconciliations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID NOT NULL REFERENCES accounts(id),
    fiscal_period_id UUID NOT NULL REFERENCES fiscal_periods(id),
    reconciliation_type VARCHAR(50) NOT NULL CHECK (reconciliation_type IN ('BANK', 'GL_SUBLEDGER', 'INTERCOMPANY')),
    gl_balance DECIMAL(18,2) NOT NULL,
    external_balance DECIMAL(18,2) NOT NULL,
    reconciling_items_total DECIMAL(18,2) DEFAULT 0,
    adjusted_balance DECIMAL(18,2),
    status VARCHAR(20) DEFAULT 'DRAFT' CHECK (status IN ('DRAFT', 'IN_PROGRESS', 'COMPLETED', 'APPROVED')),
    prepared_by VARCHAR(255),
    approved_by VARCHAR(255),
    completed_at TIMESTAMP,
    UNIQUE(account_id, fiscal_period_id, reconciliation_type)
);
```

### 12. reconciling_items

Individual reconciling items.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| reconciliation_id | UUID | FK to reconciliations |
| item_date | DATE | Date of item |
| description | TEXT | Item description |
| amount | DECIMAL(18,2) | Amount (signed) |
| category | VARCHAR(50) | TIMING, ADJUSTMENT_REQUIRED, INVESTIGATION |
| status | VARCHAR(20) | OPEN, CLEARED, ADJUSTED |
| age_days | INTEGER | Days outstanding |
| reference | VARCHAR(255) | Reference (check#, invoice#, etc.) |
| notes | TEXT | Notes |

```sql
CREATE TABLE reconciling_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reconciliation_id UUID NOT NULL REFERENCES reconciliations(id) ON DELETE CASCADE,
    item_date DATE NOT NULL,
    description TEXT NOT NULL,
    amount DECIMAL(18,2) NOT NULL,
    category VARCHAR(50) NOT NULL CHECK (category IN ('TIMING', 'ADJUSTMENT_REQUIRED', 'INVESTIGATION')),
    status VARCHAR(20) DEFAULT 'OPEN' CHECK (status IN ('OPEN', 'CLEARED', 'ADJUSTED')),
    age_days INTEGER,
    reference VARCHAR(255),
    notes TEXT
);
```

### 13. close_tasks

Month-end close task tracking.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| fiscal_period_id | UUID | FK to fiscal_periods |
| task_name | VARCHAR(255) | Task name |
| task_description | TEXT | Detailed description |
| task_category | VARCHAR(50) | Category (ACCRUALS, RECONCILIATION, etc.) |
| scheduled_day | INTEGER | Target close day (T+1, T+2, etc.) |
| dependency_task_ids | UUID[] | Array of task IDs this depends on |
| assigned_to | VARCHAR(255) | Assignee |
| status | VARCHAR(20) | NOT_STARTED, IN_PROGRESS, COMPLETED, BLOCKED |
| due_date | TIMESTAMP | Due date |
| completed_at | TIMESTAMP | Completion timestamp |
| notes | TEXT | Notes |

```sql
CREATE TABLE close_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fiscal_period_id UUID NOT NULL REFERENCES fiscal_periods(id),
    task_name VARCHAR(255) NOT NULL,
    task_description TEXT,
    task_category VARCHAR(50) NOT NULL,
    scheduled_day INTEGER NOT NULL,
    dependency_task_ids UUID[],
    assigned_to VARCHAR(255),
    status VARCHAR(20) DEFAULT 'NOT_STARTED' CHECK (status IN ('NOT_STARTED', 'IN_PROGRESS', 'COMPLETED', 'BLOCKED')),
    due_date TIMESTAMP,
    completed_at TIMESTAMP,
    notes TEXT
);
```

## Indexes

Recommended indexes for performance:

```sql
-- Accounts
CREATE INDEX idx_accounts_code ON accounts(account_code);
CREATE INDEX idx_accounts_chart ON accounts(chart_of_accounts_id);

-- Journal Entries
CREATE INDEX idx_journal_entries_date ON journal_entries(entry_date);
CREATE INDEX idx_journal_entries_period ON journal_entries(fiscal_period_id);
CREATE INDEX idx_journal_entries_status ON journal_entries(status);

-- Journal Lines
CREATE INDEX idx_journal_lines_entry ON journal_lines(journal_entry_id);
CREATE INDEX idx_journal_lines_account ON journal_lines(account_id);

-- Account Balances
CREATE INDEX idx_account_balances_account ON account_balances(account_id);
CREATE INDEX idx_account_balances_period ON account_balances(fiscal_period_id);

-- Budgets
CREATE INDEX idx_budgets_account ON budgets(account_id);
CREATE INDEX idx_budgets_period ON budgets(fiscal_period_id);

-- Reconciliations
CREATE INDEX idx_reconciliations_account ON reconciliations(account_id);
CREATE INDEX idx_reconciliations_period ON reconciliations(fiscal_period_id);

-- Close Tasks
CREATE INDEX idx_close_tasks_period ON close_tasks(fiscal_period_id);
CREATE INDEX idx_close_tasks_status ON close_tasks(status);
```

## Views (Optional)

### v_trial_balance

```sql
CREATE VIEW v_trial_balance AS
SELECT 
    fp.period_name,
    a.account_code,
    a.account_name,
    coa.account_type,
    coa.account_category,
    ab.ending_balance,
    CASE WHEN coa.normal_balance = 'DEBIT' THEN ab.ending_balance ELSE 0 END as debit_balance,
    CASE WHEN coa.normal_balance = 'CREDIT' THEN ab.ending_balance ELSE 0 END as credit_balance
FROM account_balances ab
JOIN accounts a ON ab.account_id = a.id
JOIN chart_of_accounts coa ON a.chart_of_accounts_id = coa.id
JOIN fiscal_periods fp ON ab.fiscal_period_id = fp.id;
```

### v_income_statement

```sql
CREATE VIEW v_income_statement AS
SELECT 
    fp.period_name,
    coa.account_category,
    a.account_code,
    a.account_name,
    CASE 
        WHEN coa.account_type = 'REVENUE' THEN -ab.ending_balance
        WHEN coa.account_type = 'EXPENSE' THEN ab.ending_balance
    END as amount
FROM account_balances ab
JOIN accounts a ON ab.account_id = a.id
JOIN chart_of_accounts coa ON a.chart_of_accounts_id = coa.id
JOIN fiscal_periods fp ON ab.fiscal_period_id = fp.id
WHERE coa.account_type IN ('REVENUE', 'EXPENSE');
```
