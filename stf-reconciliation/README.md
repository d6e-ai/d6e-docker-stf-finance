# D6E Reconciliation STF

銀行照合、GL 対補助元帳照合、会社間照合を行う Docker STF です。

**Docker Image**: `ghcr.io/d6e-ai/stf-reconciliation:latest`

## LLM/AI エージェント向け使用方法

この Docker イメージを D6E AI エージェントから使用する場合、以下の手順で STF を作成してください。

### ステップ 1: STF の作成

```javascript
d6e_create_stf({
  name: "reconciliation",
  description: "Perform bank, GL-subledger, and intercompany reconciliations",
});
```

### ステップ 2: STF バージョンの作成

```javascript
d6e_create_stf_version({
  stf_id: "{ステップ1で取得したstf_id}",
  version: "1.0.0",
  runtime: "docker",
  code: '{"image":"ghcr.io/d6e-ai/stf-reconciliation:latest"}',
});
```

**重要**: `runtime`は必ず`"docker"`を指定し、`code`フィールドには JSON 文字列として`{"image":"ghcr.io/d6e-ai/stf-reconciliation:latest"}`を設定してください。

### ステップ 3: ワークフローの作成

```javascript
d6e_create_workflow({
  name: "reconciliation-workflow",
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
// 銀行照合
d6e_execute_workflow({
  workflow_id: "{workflow_id}",
  input: {
    operation: "create_bank_reconciliation",
    bank_account_id: "a0000001-0000-0000-0000-000000000001",
    period: "2025-01",
    bank_statement_balance: 2600000,
    bank_statement_date: "2025-01-31",
  },
});

// GL対補助元帳照合
d6e_execute_workflow({
  workflow_id: "{workflow_id}",
  input: {
    operation: "create_gl_subledger_rec",
    control_account_id: "a0000001-0000-0000-0000-000000000003",
    period: "2025-01",
    subledger_balance: 900000,
    subledger_source: "AR_AGING_REPORT",
  },
});

// 照合項目のエイジング分析
d6e_execute_workflow({
  workflow_id: "{workflow_id}",
  input: {
    operation: "analyze_aging",
    period: "2025-01",
  },
});
```

## サポートされている操作

| Operation                    | 必須パラメータ                                                               | オプション             | 説明                   |
| ---------------------------- | ---------------------------------------------------------------------------- | ---------------------- | ---------------------- |
| `create_bank_reconciliation` | `bank_account_id`, `period`, `bank_statement_balance`, `bank_statement_date` | -                      | 銀行照合作成           |
| `create_gl_subledger_rec`    | `control_account_id`, `period`, `subledger_balance`, `subledger_source`      | -                      | GL 対補助元帳照合      |
| `create_intercompany_rec`    | `entity_a_account_id`, `entity_b_account_id`, `period`                       | -                      | 会社間照合             |
| `add_reconciling_item`       | `reconciliation_id`, `item_date`, `description`, `amount`, `category`        | `reference`, `notes`   | 照合項目追加           |
| `analyze_aging`              | -                                                                            | `account_id`, `period` | 照合項目エイジング分析 |
| `get_reconciliation_status`  | `period`                                                                     | `reconciliation_type`  | 照合ステータス一覧     |

## 入出力例

### 銀行照合の作成

**入力**:

```json
{
  "operation": "create_bank_reconciliation",
  "bank_account_id": "a0000001-0000-0000-0000-000000000001",
  "period": "2025-01",
  "bank_statement_balance": 2600000,
  "bank_statement_date": "2025-01-31"
}
```

**出力**:

```json
{
  "output": {
    "status": "success",
    "operation": "create_bank_reconciliation",
    "data": {
      "reconciliation_type": "BANK",
      "account_code": "1000",
      "account_name": "Cash - Operating",
      "period": "2025-01",
      "bank_side": {
        "balance_per_bank": 2600000,
        "adjustments": [
          { "description": "Deposits in transit", "amount": 50000 },
          { "description": "Outstanding checks", "amount": -50000 }
        ],
        "adjusted_balance": 2600000
      },
      "gl_side": {
        "balance_per_gl": 2600000,
        "adjusted_balance": 2600000
      },
      "validation": {
        "difference": 0,
        "is_reconciled": true,
        "total_reconciling_items": 2
      },
      "text_format": "BANK RECONCILIATION - Cash - Operating (1000)\nPeriod: 2025-01  Statement Date: 2025-01-31\n============================================================\n\nBalance per bank statement:             $2,600,000.00\n  Add: Deposits in transit                  $50,000.00\n  Less: Outstanding checks                 -$50,000.00\nAdjusted bank balance:                  $2,600,000.00\n\nBalance per general ledger:             $2,600,000.00\nAdjusted GL balance:                    $2,600,000.00\n\n------------------------------------------------------------\nDifference:                                     $0.00\nStatus: RECONCILED"
    }
  }
}
```

### GL 対補助元帳照合

**入力**:

```json
{
  "operation": "create_gl_subledger_rec",
  "control_account_id": "a0000001-0000-0000-0000-000000000003",
  "period": "2025-01",
  "subledger_balance": 895000,
  "subledger_source": "AR_AGING_REPORT"
}
```

**出力**:

```json
{
  "output": {
    "status": "success",
    "data": {
      "reconciliation_type": "GL_SUBLEDGER",
      "account_code": "1100",
      "account_name": "Accounts Receivable",
      "gl_balance": 900000,
      "subledger_balance": 895000,
      "difference": 5000,
      "reconciling_items": [
        {
          "description": "Unidentified difference - requires investigation",
          "amount": 5000,
          "category": "INVESTIGATION",
          "status": "OPEN",
          "possible_causes": [
            "Manual journal entries to control account",
            "Subledger transactions pending interface",
            "Timing differences in batch posting",
            "System interface errors"
          ]
        }
      ],
      "validation": {
        "is_reconciled": false,
        "difference": 5000
      }
    }
  }
}
```

### 照合項目のエイジング分析

**入力**:

```json
{
  "operation": "analyze_aging",
  "period": "2025-01"
}
```

**出力**:

```json
{
  "output": {
    "status": "success",
    "data": {
      "analysis_date": "2025-02-05",
      "summary": {
        "total_items": 15,
        "total_amount": 75000,
        "items_requiring_escalation": 3
      },
      "age_buckets": [
        {"bucket": "Current (0-30)", "status": "CURRENT", "count": 8, "total": 25000, "percentage_of_total": 0.33},
        {"bucket": "Aging (31-60)", "status": "AGING", "count": 4, "total": 30000, "percentage_of_total": 0.40},
        {"bucket": "Overdue (61-90)", "status": "OVERDUE", "count": 2, "total": 15000, "percentage_of_total": 0.20},
        {"bucket": "Stale (90+)", "status": "STALE", "count": 1, "total": 5000, "percentage_of_total": 0.07}
      ],
      "escalation_items": [...]
    }
  }
}
```

## 🤖 AI エージェントへのプロンプト

### 基本プロンプト

```
D6Eで勘定照合を行うDockerスキルを使用してください。

Docker Image: ghcr.io/d6e-ai/stf-reconciliation:latest

使用手順:
1. d6e_create_stf でSTFを作成（name: "reconciliation"）
2. d6e_create_stf_version で以下を指定:
   - runtime: "docker"
   - code: "{\"image\":\"ghcr.io/d6e-ai/stf-reconciliation:latest\"}"
3. d6e_create_workflow でワークフローを作成
4. d6e_execute_workflow で実行

サポートされている操作:
- "create_bank_reconciliation": 銀行照合（bank_account_id, period, bank_statement_balance, bank_statement_date必須）
- "create_gl_subledger_rec": GL対補助元帳照合（control_account_id, period, subledger_balance, subledger_source必須）
- "create_intercompany_rec": 会社間照合（entity_a_account_id, entity_b_account_id, period必須）
- "add_reconciling_item": 照合項目追加
- "analyze_aging": エイジング分析
- "get_reconciliation_status": 照合ステータス一覧

銀行照合から試してください。
```

### 銀行照合を行うプロンプト

```
2025年1月末の現金勘定の銀行照合を行ってください。

使用スキル:
- Docker Image: ghcr.io/d6e-ai/stf-reconciliation:latest
- 操作: create_bank_reconciliation

パラメータ:
- bank_account_id: {現金勘定のUUID}
- period: "2025-01"
- bank_statement_balance: 2,600,000（銀行残高証明書の金額）
- bank_statement_date: "2025-01-31"

結果には以下を含めてください:
- 銀行残高と帳簿残高の比較
- 未決済小切手と未記帳入金の一覧
- 調整後残高の一致確認
- テキスト形式の照合表
```

### 完全な実行例プロンプト

```
売掛金の補助元帳照合を行い、差異があれば調査項目として記録してください。

Docker Image: ghcr.io/d6e-ai/stf-reconciliation:latest

実行ステップ:
1. STF作成（name: "reconciliation", runtime: "docker"）

2. ポリシー設定:
   - ポリシーグループ作成
   - STFをグループに追加
   - 以下のテーブルへのSELECTポリシー作成:
     - accounts
     - chart_of_accounts
     - account_balances
     - fiscal_periods
     - reconciliations
     - reconciling_items

3. GL対補助元帳照合の実行:
   - operation: "create_gl_subledger_rec"
   - control_account_id: {売掛金勘定のUUID}
   - period: "2025-01"
   - subledger_balance: {得意先元帳の合計額}
   - subledger_source: "AR_AGING_REPORT"

4. 差異がある場合:
   - 差異の原因候補を確認
   - 必要に応じてadd_reconciling_item操作で項目を追加
   - analyze_aging操作で未解決項目のエイジングを確認

結果をレポート形式で表示してください。
```

## 照合項目カテゴリ

| カテゴリ              | 説明                                   | アクション                   |
| --------------------- | -------------------------------------- | ---------------------------- |
| `TIMING`              | 通常のタイミング差異（未決済小切手等） | モニタリング、通常処理で解消 |
| `ADJUSTMENT_REQUIRED` | 修正仕訳が必要                         | 修正仕訳を起票               |
| `INVESTIGATION`       | 原因調査が必要                         | 調査して原因を特定           |

## エイジングバケット

| バケット | 日数  | ステータス | アクション                         |
| -------- | ----- | ---------- | ---------------------------------- |
| Current  | 0-30  | CURRENT    | モニタリング                       |
| Aging    | 31-60 | AGING      | 調査開始                           |
| Overdue  | 61-90 | OVERDUE    | 上長にエスカレーション             |
| Stale    | 90+   | STALE      | 経営層にエスカレーション、償却検討 |

## トラブルシューティング

### 勘定科目が見つからない

```
Error: No balance found for account xxx in period 2025-01
```

**解決策**:

- `accounts`テーブルに該当の勘定科目が存在することを確認
- `account_balances`テーブルに該当期間のデータがあることを確認

### 照合差異が発生

差異が発生した場合の一般的な原因：

1. **タイミング差異**: 未決済小切手、未記帳入金
2. **転記漏れ**: 銀行手数料、利息の未計上
3. **システムエラー**: インターフェース障害
4. **分類誤り**: 科目の誤り

## ローカルでのビルドとテスト

```bash
# ビルド
docker build -t stf-reconciliation:latest .

# テスト
echo '{
  "workspace_id": "test-ws",
  "stf_id": "test-stf",
  "caller": null,
  "api_url": "http://localhost:8080",
  "api_token": "test-token",
  "input": {
    "operation": "create_bank_reconciliation",
    "bank_account_id": "a0000001-0000-0000-0000-000000000001",
    "period": "2025-01",
    "bank_statement_balance": 2600000,
    "bank_statement_date": "2025-01-31"
  },
  "sources": {}
}' | docker run --rm -i stf-reconciliation:latest
```

## 関連ドキュメント

- [データベーススキーマ](../docs/DATABASE_SCHEMA.md)
- [サンプルデータ](../docs/SAMPLE_DATA.sql)
- [プロジェクト README](../README.md)
