# STF: Variance Analysis

D6E Docker STF for financial variance analysis.

## Overview

This STF performs variance analysis:

- **Budget vs Actual**: Compare actual results to budget
- **Period-over-Period**: Compare sequential periods
- **Variance Decomposition**: Break down into price/volume/mix effects
- **Waterfall Generation**: Create bridge chart data
- **Narrative Generation**: Template-based variance explanations

## Operations

### `analyze_budget_variance`

Compare actual results to budget with materiality flagging.

**Input:**

```json
{
  "operation": "analyze_budget_variance",
  "period": "2025-01",
  "budget_version": "ORIGINAL",
  "account_type": "EXPENSE",
  "department_id": "uuid-optional",
  "materiality_thresholds": {
    "large_accounts": { "dollar": 500000, "percentage": 0.05 },
    "medium_accounts": { "dollar": 100000, "percentage": 0.10 },
    "small_accounts": { "dollar": 50000, "percentage": 0.15 }
  }
}
```

**Output:**

```json
{
  "output": {
    "status": "success",
    "data": {
      "analysis_type": "BUDGET_VS_ACTUAL",
      "period": "2025-01",
      "summary": {
        "total_actual": 850000,
        "total_budget": 900000,
        "total_variance_dollar": -50000,
        "total_variance_percent": -0.0556,
        "material_variance_count": 3
      },
      "variances": [...],
      "material_variances": [
        {
          "account_code": "6100",
          "account_name": "Salaries",
          "actual": 500000,
          "budget": 450000,
          "variance_dollar": 50000,
          "variance_percent": 0.111,
          "is_favorable": false,
          "is_material": true
        }
      ]
    }
  }
}
```

### `analyze_period_variance`

Compare current period to prior period.

**Input:**

```json
{
  "operation": "analyze_period_variance",
  "current_period": "2025-02",
  "comparison_period": "2025-01",
  "account_type": "REVENUE"
}
```

### `decompose_variance`

Break down variance into contributing factors.

**Input:**

```json
{
  "operation": "decompose_variance",
  "account_code": "4100",
  "period": "2025-01",
  "comparison_period": "2024-01",
  "decomposition_type": "PRICE_VOLUME"
}
```

**Output:**

```json
{
  "output": {
    "status": "success",
    "data": {
      "account_code": "4100",
      "total_variance": 100000,
      "decomposition": {
        "type": "PRICE_VOLUME",
        "components": [
          {
            "name": "Volume Effect",
            "amount": 60000,
            "percentage_of_variance": 0.6,
            "description": "Change due to volume/quantity differences"
          },
          {
            "name": "Price Effect",
            "amount": 30000,
            "percentage_of_variance": 0.3
          },
          {
            "name": "Mix Effect",
            "amount": 10000,
            "percentage_of_variance": 0.1
          }
        ]
      }
    }
  }
}
```

### `generate_waterfall`

Create waterfall/bridge chart data.

**Input:**

```json
{
  "operation": "generate_waterfall",
  "start_value": 1000000,
  "end_value": 1150000,
  "drivers": [
    { "name": "Volume growth", "amount": 80000 },
    { "name": "Price increase", "amount": 50000 },
    { "name": "Mix shift", "amount": 30000 },
    { "name": "FX impact", "amount": -10000 }
  ],
  "title": "Q1 Revenue Bridge"
}
```

**Output:**

```json
{
  "output": {
    "status": "success",
    "data": {
      "title": "Q1 Revenue Bridge",
      "bars": [...],
      "text_representation": "WATERFALL: Q1 Revenue Bridge\n\nStarting Value           $1,000,000.00\n  |--[+] Volume growth      $80,000.00\n  ...",
      "reconciliation": {
        "drivers_sum": 150000,
        "reconciles": true
      }
    }
  }
}
```

### `generate_variance_narrative`

Generate narrative explanation for a variance.

**Input:**

```json
{
  "operation": "generate_variance_narrative",
  "variance_item": {
    "account_code": "6100",
    "account_name": "Salaries & Wages",
    "actual": 500000,
    "budget": 450000,
    "variance_dollar": 50000,
    "variance_percent": 0.111,
    "is_favorable": false,
    "is_material": true
  },
  "additional_context": "Headcount increased by 3 FTEs in mid-January"
}
```

**Output:**

```json
{
  "output": {
    "status": "success",
    "data": {
      "narrative": {
        "headline": "Salaries & Wages: Unfavorable variance of $50,000.00 (11.1%)",
        "summary": "Actual of $500,000.00 was $50,000.00 higher than budget of $450,000.00.",
        "outlook": "This variance should be monitored in upcoming periods."
      },
      "suggested_actions": [
        "Investigate root cause with business owner",
        "Document driver analysis for management review",
        "Assess impact on forecast and identify remediation steps"
      ]
    }
  }
}
```

## Materiality Thresholds

Default thresholds (configurable per request):

| Account Size | Dollar Threshold | Percentage Threshold |
|-------------|-----------------|---------------------|
| > $10M      | $500K           | 5%                  |
| $1M - $10M  | $100K           | 10%                 |
| < $1M       | $50K            | 15%                 |

A variance is flagged as material if it exceeds **either** threshold.

## Build & Test

```bash
docker build -t stf-variance-analysis:latest .

echo '{
  "workspace_id": "test-ws",
  "stf_id": "test-stf",
  "caller": null,
  "api_url": "http://localhost:8080",
  "api_token": "test-token",
  "input": {
    "operation": "generate_waterfall",
    "start_value": 1000000,
    "end_value": 1100000,
    "drivers": [
      {"name": "Sales Growth", "amount": 75000},
      {"name": "Price Increase", "amount": 25000}
    ],
    "title": "Revenue Bridge"
  },
  "sources": {}
}' | docker run --rm -i stf-variance-analysis:latest
```
