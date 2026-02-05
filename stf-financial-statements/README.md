# D6E Financial Statements STF

GAAP 形式の財務諸表（損益計算書、貸借対照表、キャッシュフロー計算書、試算表）を生成する Docker STF です。

**Docker Image**: `ghcr.io/d6e-ai/stf-financial-statements:latest`

## LLM/AI エージェント向け使用方法

この Docker イメージを D6E AI エージェントから使用する場合、以下の手順で STF を作成してください。

### ステップ 1: STF の作成

```javascript
d6e_create_stf({
  name: "financial-statements",
  description:
    "Generate GAAP financial statements (Income Statement, Balance Sheet, Cash Flow)",
});
```

### ステップ 2: STF バージョンの作成

```javascript
d6e_create_stf_version({
  stf_id: "{ステップ1で取得したstf_id}",
  version: "1.0.0",
  runtime: "docker",
  code: '{"image":"ghcr.io/d6e-ai/stf-financial-statements:latest"}',
});
```

**重要**: `runtime`は必ず`"docker"`を指定し、`code`フィールドには JSON 文字列として`{"image":"ghcr.io/d6e-ai/stf-financial-statements:latest"}`を設定してください。

### ステップ 3: ワークフローの作成

```javascript
d6e_create_workflow({
  name: "financial-statements-workflow",
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
// 試算表の生成
d6e_execute_workflow({
  workflow_id: "{workflow_id}",
  input: {
    operation: "generate_trial_balance",
    period: "2025-01",
  },
});

// 損益計算書の生成（期間比較付き）
d6e_execute_workflow({
  workflow_id: "{workflow_id}",
  input: {
    operation: "generate_income_statement",
    period: "2025-01",
    comparison_period: "2024-01",
  },
});

// 貸借対照表の生成
d6e_execute_workflow({
  workflow_id: "{workflow_id}",
  input: {
    operation: "generate_balance_sheet",
    period: "2025-01",
  },
});

// キャッシュフロー計算書の生成
d6e_execute_workflow({
  workflow_id: "{workflow_id}",
  input: {
    operation: "generate_cash_flow",
    period: "2025-01",
  },
});
```

## サポートされている操作

| Operation                   | 必須パラメータ | オプション                           | 説明                             |
| --------------------------- | -------------- | ------------------------------------ | -------------------------------- |
| `generate_income_statement` | `period`       | `comparison_period`, `department_id` | 損益計算書生成                   |
| `generate_balance_sheet`    | `period`       | `comparison_period`                  | 貸借対照表生成                   |
| `generate_cash_flow`        | `period`       | `comparison_period`                  | キャッシュフロー計算書（間接法） |
| `generate_trial_balance`    | `period`       | -                                    | 試算表生成                       |

## 入出力例

### 損益計算書の生成

**入力**:

```json
{
  "operation": "generate_income_statement",
  "period": "2025-01",
  "comparison_period": "2024-01"
}
```

**出力**:

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
          "items": [
            {
              "account_code": "4000",
              "account_name": "Product Revenue",
              "current_amount": 820000,
              "comparison_amount": 750000
            }
          ],
          "total": 1340000,
          "comparison_total": 1200000,
          "variance": {
            "dollar_variance": 140000,
            "percentage_variance": 0.117
          }
        },
        "gross_profit": {
          "label": "Gross Profit",
          "total": 1175000,
          "margin": 0.877
        },
        "operating_income": {
          "label": "Operating Income",
          "total": 172000
        }
      }
    }
  }
}
```

### 試算表の生成

**入力**:

```json
{
  "operation": "generate_trial_balance",
  "period": "2025-01"
}
```

**出力**:

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
          "debit": 2600000,
          "credit": 0
        },
        {
          "account_code": "2000",
          "account_name": "Accounts Payable",
          "account_type": "LIABILITY",
          "debit": 0,
          "credit": 300000
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

## 🤖 AI エージェントへのプロンプト

### 基本プロンプト

```
D6Eで財務諸表を生成するDockerスキルを使用してください。

Docker Image: ghcr.io/d6e-ai/stf-financial-statements:latest

使用手順:
1. d6e_create_stf でSTFを作成（name: "financial-statements"）
2. d6e_create_stf_version で以下を指定:
   - runtime: "docker"
   - code: "{\"image\":\"ghcr.io/d6e-ai/stf-financial-statements:latest\"}"
3. d6e_create_workflow でワークフローを作成
4. d6e_execute_workflow で実行

サポートされている操作:
- "generate_income_statement": 損益計算書（period必須、comparison_periodオプション）
- "generate_balance_sheet": 貸借対照表（period必須）
- "generate_cash_flow": キャッシュフロー計算書（period必須）
- "generate_trial_balance": 試算表（period必須）

まずは operation: "generate_trial_balance", period: "2025-01" で試算表を生成してください。
```

### 損益計算書を作成するプロンプト

```
2025年1月の損益計算書を作成してください。前年同月と比較したいです。

使用スキル:
- Docker Image: ghcr.io/d6e-ai/stf-financial-statements:latest
- 操作: generate_income_statement
- パラメータ: period: "2025-01", comparison_period: "2024-01"

手順:
1. STFとワークフローを作成（runtime: "docker"）
2. account_balancesテーブルへのSELECTポリシーを設定
3. ワークフローを実行

結果は収益、売上総利益、営業利益のセクションごとに表示してください。
```

### 完全な実行例プロンプト

```
財務諸表を生成するためのセットアップを行い、2025年1月の試算表を作成してください。

Docker Image: ghcr.io/d6e-ai/stf-financial-statements:latest

実行ステップ:
1. STF作成（name: "financial-statements", runtime: "docker"）

2. ポリシー設定:
   - ポリシーグループ作成
   - STFをグループに追加
   - 以下のテーブルへのSELECTポリシー作成:
     - accounts
     - chart_of_accounts
     - account_balances
     - fiscal_periods

3. ワークフロー作成・実行:
   - operation: "generate_trial_balance"
   - period: "2025-01"

試算表を勘定科目別に表示し、借方・貸方の合計が一致しているか確認してください。
```

## データベース要件

この STF は以下のテーブルへのアクセスが必要です：

- `accounts` - 勘定科目マスタ
- `chart_of_accounts` - 勘定科目タイプ定義
- `account_balances` - 期末残高
- `fiscal_periods` - 会計期間
- `departments` - 部門（オプション）

スキーマの詳細は `docs/DATABASE_SCHEMA.md` を参照してください。

## トラブルシューティング

### ポリシーエラー

```
Error: Policy violation - SELECT not allowed on table 'account_balances'
```

**解決策**: STF に対してテーブルへの SELECT ポリシーを設定してください。

```javascript
// ポリシーグループ作成
d6e_create_policy_group({ name: "financial-statements-group" });

// STFをグループに追加
d6e_add_member_to_policy_group({
  policy_group_id: "{group_id}",
  member_type: "stf",
  member_id: "{stf_id}",
});

// ポリシー作成
d6e_create_policy({
  policy_group_id: "{group_id}",
  table_name: "account_balances",
  operation: "select",
  mode: "allow",
});
```

### 期間が見つからない

```
Error: No balance found for period 2025-01
```

**解決策**: `fiscal_periods`テーブルに該当期間が存在し、`account_balances`テーブルにデータがあることを確認してください。

## ローカルでのビルドとテスト

```bash
# ビルド
docker build -t stf-financial-statements:latest .

# テスト
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

## 関連ドキュメント

- [データベーススキーマ](../docs/DATABASE_SCHEMA.md)
- [サンプルデータ](../docs/SAMPLE_DATA.sql)
- [プロジェクト README](../README.md)
