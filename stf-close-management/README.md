# D6E Close Management STF

月次決算プロセスの管理（タスク追跡、依存関係、進捗モニタリング）を行う Docker STF です。

**Docker Image**: `ghcr.io/d6e-ai/stf-close-management:latest`

## LLM/AI エージェント向け使用方法

この Docker イメージを D6E AI エージェントから使用する場合、以下の手順で STF を作成してください。

### ステップ 1: STF の作成

```javascript
d6e_create_stf({
  name: "close-management",
  description:
    "Manage month-end close process with task tracking and dependencies",
});
```

### ステップ 2: STF バージョンの作成

```javascript
d6e_create_stf_version({
  stf_id: "{ステップ1で取得したstf_id}",
  version: "1.0.0",
  runtime: "docker",
  code: '{"image":"ghcr.io/d6e-ai/stf-close-management:latest"}',
});
```

**重要**: `runtime`は必ず`"docker"`を指定し、`code`フィールドには JSON 文字列として`{"image":"ghcr.io/d6e-ai/stf-close-management:latest"}`を設定してください。

### ステップ 3: ワークフローの作成

```javascript
d6e_create_workflow({
  name: "close-management-workflow",
  input_steps: [],
  stf_steps: [
    {
      stf_id: "{stf_id}",
      version: "1.0.0",
    },
  ],
  effect_steps: [],
});
```

### ステップ 4: ワークフローの実行

```javascript
// 決算カレンダー生成（データベース不要）
d6e_execute_workflow({
  workflow_id: "{workflow_id}",
  input: {
    operation: "generate_close_calendar",
    period: "2025-01",
    period_end_date: "2025-01-31",
    close_days: 5,
  },
});

// 決算タスク初期化（データベース不要）
d6e_execute_workflow({
  workflow_id: "{workflow_id}",
  input: {
    operation: "initialize_close_tasks",
    period: "2025-01",
    period_end_date: "2025-01-31",
    close_days: 5,
    assignees: {
      CASH: "treasury@company.com",
      RECONCILIATION: "accounting@company.com",
    },
  },
});

// クリティカルパス分析（データベース不要）
d6e_execute_workflow({
  workflow_id: "{workflow_id}",
  input: {
    operation: "get_critical_path",
    period: "2025-01",
  },
});
```

## サポートされている操作

| Operation                 | 必須パラメータ              | オプション                | DB 必要 | 説明                 |
| ------------------------- | --------------------------- | ------------------------- | ------- | -------------------- |
| `generate_close_calendar` | `period`, `period_end_date` | `close_days`              | ❌      | 決算カレンダー生成   |
| `initialize_close_tasks`  | `period`, `period_end_date` | `close_days`, `assignees` | ❌      | 決算タスク初期化     |
| `get_critical_path`       | `period`                    | -                         | ❌      | クリティカルパス分析 |
| `update_task_status`      | `task_id`, `new_status`     | `notes`, `completed_by`   | ✅      | タスクステータス更新 |
| `get_close_progress`      | `period`                    | -                         | ✅      | 決算進捗取得         |
| `identify_blockers`       | `period`                    | -                         | ✅      | ブロッカー特定       |

## 入出力例

### 決算カレンダー生成（データベース不要）

**入力**:

```json
{
  "operation": "generate_close_calendar",
  "period": "2025-01",
  "period_end_date": "2025-01-31",
  "close_days": 5
}
```

**出力**:

```json
{
  "output": {
    "status": "success",
    "operation": "generate_close_calendar",
    "data": {
      "period": "2025-01",
      "period_end_date": "2025-01-31",
      "close_start_date": "2025-02-03",
      "target_close_date": "2025-02-07",
      "days": [
        {
          "day": "T+1",
          "date": "2025-02-03",
          "day_of_week": "Monday",
          "task_count": 6,
          "tasks": [
            {"name": "Record cash receipts and disbursements", "category": "CASH"},
            {"name": "Post payroll entries", "category": "PAYROLL"},
            {"name": "Run AP accruals", "category": "ACCRUALS"}
          ],
          "milestones": ["All subledgers processed", "Payroll entries posted"]
        },
        {
          "day": "T+2",
          "date": "2025-02-04",
          "day_of_week": "Tuesday",
          "tasks": [...]
        }
      ],
      "text_format": "CLOSE CALENDAR: 2025-01\nPeriod End: 2025-01-31\nTarget Close: 2025-02-07\n======================================================================\n\nT+1 - 2025-02-03 (Monday)\n----------------------------------------\n  [ ] Record cash receipts and disbursements\n  [ ] Post payroll entries\n  [ ] Run AP accruals\n  [ ] Run fixed asset depreciation\n  [ ] Post prepaid amortization\n  [ ] Post intercompany transactions\n  Milestones: All subledgers processed, Payroll entries posted\n\nT+2 - 2025-02-04 (Tuesday)\n..."
    }
  }
}
```

### 決算タスク初期化（データベース不要）

**入力**:

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

**出力**:

```json
{
  "output": {
    "status": "success",
    "data": {
      "period": "2025-01",
      "schedule": {
        "T+1": {
          "date": "2025-02-03",
          "tasks": [
            {
              "id": "uuid-task-1",
              "name": "Record cash receipts and disbursements",
              "category": "CASH",
              "scheduled_day": 1,
              "due_date": "2025-02-03",
              "assigned_to": "treasury@company.com",
              "status": "NOT_STARTED",
              "dependencies": []
            }
          ]
        }
      },
      "summary": {
        "total_tasks": 25,
        "tasks_by_category": {
          "CASH": 1,
          "PAYROLL": 1,
          "ACCRUALS": 2,
          "RECONCILIATION": 5,
          "REPORTING": 4
        },
        "tasks_by_day": {
          "T+1": 6,
          "T+2": 6,
          "T+3": 5,
          "T+4": 5,
          "T+5": 3
        }
      }
    }
  }
}
```

### クリティカルパス分析（データベース不要）

**入力**:

```json
{
  "operation": "get_critical_path",
  "period": "2025-01"
}
```

**出力**:

```json
{
  "output": {
    "status": "success",
    "data": {
      "period": "2025-01",
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
      "path_length": 12,
      "minimum_close_days": 5,
      "acceleration_opportunities": [
        "Automate depreciation and amortization entries",
        "Pre-reconcile accounts during the month",
        "Implement continuous close practices",
        "Parallel process independent reconciliations"
      ]
    }
  }
}
```

## 🤖 AI エージェントへのプロンプト

### 基本プロンプト（データベース不要）

```
D6Eで月次決算管理を行うDockerスキルを使用してください。

Docker Image: ghcr.io/d6e-ai/stf-close-management:latest

使用手順:
1. d6e_create_stf でSTFを作成（name: "close-management"）
2. d6e_create_stf_version で以下を指定:
   - runtime: "docker"
   - code: "{\"image\":\"ghcr.io/d6e-ai/stf-close-management:latest\"}"
3. d6e_create_workflow でワークフローを作成
4. d6e_execute_workflow で実行

データベース不要の操作:
- "generate_close_calendar": 決算カレンダー生成（period, period_end_date必須）
- "initialize_close_tasks": 決算タスク初期化（period, period_end_date必須、assigneesオプション）
- "get_critical_path": クリティカルパス分析（period必須）

データベース必要な操作:
- "update_task_status": タスクステータス更新
- "get_close_progress": 進捗取得
- "identify_blockers": ブロッカー特定

まずは決算カレンダー生成で動作確認してください。
```

### 決算カレンダーを作成するプロンプト

```
2025年1月の月次決算カレンダーを作成してください。
期末日は2025年1月31日、5営業日でクローズします。

使用スキル:
- Docker Image: ghcr.io/d6e-ai/stf-close-management:latest
- 操作: generate_close_calendar

パラメータ:
- period: "2025-01"
- period_end_date: "2025-01-31"
- close_days: 5

結果には以下を含めてください:
- 各日のタスク一覧
- マイルストーン
- テキスト形式のカレンダー
```

### 完全な実行例プロンプト

```
2025年1月の月次決算を管理するためのセットアップを行ってください。

Docker Image: ghcr.io/d6e-ai/stf-close-management:latest

実行ステップ:
1. STF作成（name: "close-management", runtime: "docker"）

2. 決算タスクの初期化:
   - operation: "initialize_close_tasks"
   - period: "2025-01"
   - period_end_date: "2025-01-31"
   - close_days: 5
   - assignees:
     - CASH: treasury@company.com
     - PAYROLL: payroll@company.com
     - RECONCILIATION: accounting@company.com
     - TAX: tax@company.com
     - REPORTING: controller@company.com

3. クリティカルパス分析:
   - operation: "get_critical_path"
   - period: "2025-01"

4. 結果の表示:
   - 25タスクの一覧（日別）
   - 各担当者のタスク数
   - クリティカルパス上のタスク
   - 決算短縮のための改善提案

決算を効率化するためのアドバイスもお願いします。
```

## 標準決算タスク（25 タスク/5 日）

### T+1（期末翌営業日）

| タスク                                 | カテゴリ     | 依存関係 |
| -------------------------------------- | ------------ | -------- |
| Record cash receipts and disbursements | CASH         | なし     |
| Post payroll entries                   | PAYROLL      | なし     |
| Run AP accruals                        | ACCRUALS     | なし     |
| Run fixed asset depreciation           | DEPRECIATION | なし     |
| Post prepaid amortization              | AMORTIZATION | なし     |
| Post intercompany transactions         | INTERCOMPANY | なし     |

### T+2

| タスク                               | カテゴリ       | 依存関係        |
| ------------------------------------ | -------------- | --------------- |
| Complete bank reconciliation         | RECONCILIATION | Cash entries    |
| Post revenue recognition entries     | REVENUE        | なし            |
| Complete AR subledger reconciliation | RECONCILIATION | Revenue entries |
| Complete AP subledger reconciliation | RECONCILIATION | AP accruals     |
| Post FX revaluation entries          | FX             | なし            |
| Post remaining accrual entries       | ACCRUALS       | なし            |

### T+3

| タスク                                     | カテゴリ       | 依存関係                 |
| ------------------------------------------ | -------------- | ------------------------ |
| Complete all balance sheet reconciliations | RECONCILIATION | Bank rec, AR rec, AP rec |
| Complete intercompany reconciliation       | INTERCOMPANY   | IC transactions          |
| Post reconciliation adjustments            | ADJUSTMENTS    | BS recs                  |
| Run preliminary trial balance              | REPORTING      | Adjustments              |
| Perform preliminary flux analysis          | ANALYSIS       | Trial balance            |

### T+4

| タスク                              | カテゴリ  | 依存関係         |
| ----------------------------------- | --------- | ---------------- |
| Post tax provision entries          | TAX       | Trial balance    |
| Complete equity roll-forward        | EQUITY    | なし             |
| Generate draft financial statements | REPORTING | Tax, Equity      |
| Perform detailed flux analysis      | ANALYSIS  | Draft financials |
| Management review of financials     | REVIEW    | Flux analysis    |

### T+5

| タスク                        | カテゴリ    | 依存関係          |
| ----------------------------- | ----------- | ----------------- |
| Post final adjustments        | ADJUSTMENTS | Management review |
| Finalize financial statements | REPORTING   | Final adjustments |
| Lock period in system         | CLOSE       | Final statements  |
| Distribute reporting package  | REPORTING   | Period lock       |
| Conduct close retrospective   | PROCESS     | Distribution      |

## タスクステータス

| ステータス    | 説明                         |
| ------------- | ---------------------------- |
| `NOT_STARTED` | 未着手                       |
| `IN_PROGRESS` | 進行中                       |
| `COMPLETED`   | 完了                         |
| `BLOCKED`     | ブロック（依存タスク未完了） |

## トラブルシューティング

### タスクがブロックされている

`identify_blockers`操作でブロッカーを特定し、依存タスクから優先的に完了させてください。

### 決算が遅延している

`get_critical_path`で最短パスを確認し、クリティカルパス上のタスクを優先してください。

## ローカルでのビルドとテスト

```bash
# ビルド
docker build -t stf-close-management:latest .

# テスト（データベース不要）
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

## 関連ドキュメント

- [データベーススキーマ](../docs/DATABASE_SCHEMA.md)
- [サンプルデータ](../docs/SAMPLE_DATA.sql)
- [プロジェクト README](../README.md)
