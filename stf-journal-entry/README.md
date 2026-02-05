# D6E Journal Entry STF

仕訳帳の作成・検証、減価償却計算、前払費用償却、未払費用計上を行う Docker STF です。

**Docker Image**: `ghcr.io/d6e-ai/stf-journal-entry:latest`

## LLM/AI エージェント向け使用方法

この Docker イメージを D6E AI エージェントから使用する場合、以下の手順で STF を作成してください。

### ステップ 1: STF の作成

```javascript
d6e_create_stf({
  name: "journal-entry",
  description: "Prepare and validate journal entries for month-end close",
});
```

### ステップ 2: STF バージョンの作成

```javascript
d6e_create_stf_version({
  stf_id: "{ステップ1で取得したstf_id}",
  version: "1.0.0",
  runtime: "docker",
  code: '{"image":"ghcr.io/d6e-ai/stf-journal-entry:latest"}',
});
```

**重要**: `runtime`は必ず`"docker"`を指定し、`code`フィールドには JSON 文字列として`{"image":"ghcr.io/d6e-ai/stf-journal-entry:latest"}`を設定してください。

### ステップ 3: ワークフローの作成

```javascript
d6e_create_workflow({
  name: "journal-entry-workflow",
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
// 仕訳帳の作成
d6e_execute_workflow({
  workflow_id: "{workflow_id}",
  input: {
    operation: "create_journal_entry",
    entry_date: "2025-01-31",
    description: "Accrue January professional services",
    entry_type: "ADJUSTING",
    is_auto_reverse: true,
    reverse_date: "2025-02-01",
    lines: [
      {
        account_id: "expense-account-uuid",
        debit_amount: 10000,
        credit_amount: 0,
        description: "Consulting services",
      },
      {
        account_id: "liability-account-uuid",
        debit_amount: 0,
        credit_amount: 10000,
        description: "Accrued liabilities",
      },
    ],
  },
});

// 減価償却計算
d6e_execute_workflow({
  workflow_id: "{workflow_id}",
  input: {
    operation: "calculate_depreciation",
    period: "2025-01",
  },
});

// 前払費用償却
d6e_execute_workflow({
  workflow_id: "{workflow_id}",
  input: {
    operation: "calculate_prepaid_amortization",
    period: "2025-01",
  },
});
```

## サポートされている操作

| Operation                        | 必須パラメータ                                                                                  | オプション                                      | 説明             |
| -------------------------------- | ----------------------------------------------------------------------------------------------- | ----------------------------------------------- | ---------------- |
| `create_journal_entry`           | `entry_date`, `description`, `lines`                                                            | `entry_type`, `is_auto_reverse`, `reverse_date` | 仕訳帳作成       |
| `validate_journal_entry`         | `entry`                                                                                         | -                                               | 仕訳検証         |
| `calculate_depreciation`         | `period`                                                                                        | `asset_category`                                | 減価償却計算     |
| `calculate_prepaid_amortization` | `period`                                                                                        | -                                               | 前払費用償却計算 |
| `generate_accrual_entry`         | `accrual_type`, `period`, `amount`, `description`, `expense_account_id`, `liability_account_id` | `department_id`, `reference`                    | 未払費用仕訳生成 |
| `list_pending_entries`           | -                                                                                               | `period`, `status`                              | 承認待ち仕訳一覧 |

## 入出力例

### 仕訳帳の作成

**入力**:

```json
{
  "operation": "create_journal_entry",
  "entry_date": "2025-01-31",
  "description": "Accrue January consulting services",
  "entry_type": "ADJUSTING",
  "is_auto_reverse": true,
  "reverse_date": "2025-02-01",
  "lines": [
    {
      "account_id": "a0000001-0000-0000-0000-000000000083",
      "debit_amount": 15000,
      "credit_amount": 0,
      "description": "Professional services - January",
      "reference": "PO-2025-001"
    },
    {
      "account_id": "a0000001-0000-0000-0000-000000000023",
      "debit_amount": 0,
      "credit_amount": 15000,
      "description": "Accrued professional fees"
    }
  ]
}
```

**出力**:

```json
{
  "output": {
    "status": "success",
    "operation": "create_journal_entry",
    "data": {
      "entry_number": "JE-20250131120000-ABC123",
      "entry_date": "2025-01-31",
      "status": "DRAFT",
      "is_auto_reverse": true,
      "reverse_date": "2025-02-01",
      "lines": [...],
      "totals": {
        "total_debits": 15000,
        "total_credits": 15000,
        "line_count": 2
      }
    }
  }
}
```

### 仕訳の検証

**入力**:

```json
{
  "operation": "validate_journal_entry",
  "entry": {
    "entry_number": "JE-20250131120000-ABC123",
    "description": "Test entry",
    "lines": [
      { "debit_amount": 10000, "credit_amount": 0 },
      { "debit_amount": 0, "credit_amount": 10000 }
    ]
  }
}
```

**出力**:

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
      ],
      "error_count": 0,
      "warning_count": 1
    }
  }
}
```

### 減価償却計算

**入力**:

```json
{
  "operation": "calculate_depreciation",
  "period": "2025-01"
}
```

**出力**:

```json
{
  "output": {
    "status": "success",
    "data": {
      "entry_type": "DEPRECIATION",
      "period": "2025-01",
      "summary": {
        "total_depreciation": 10500,
        "asset_count": 4
      },
      "suggested_entry": {
        "entry_date": "2025-01-31",
        "description": "Monthly Depreciation - 2025-01",
        "lines": [...]
      },
      "detail_items": [
        {"description": "Building Depreciation", "amount": 5000},
        {"description": "Equipment Depreciation", "amount": 3000}
      ]
    }
  }
}
```

## 🤖 AI エージェントへのプロンプト

### 基本プロンプト

```
D6Eで仕訳帳を作成するDockerスキルを使用してください。

Docker Image: ghcr.io/d6e-ai/stf-journal-entry:latest

使用手順:
1. d6e_create_stf でSTFを作成（name: "journal-entry"）
2. d6e_create_stf_version で以下を指定:
   - runtime: "docker"
   - code: "{\"image\":\"ghcr.io/d6e-ai/stf-journal-entry:latest\"}"
3. d6e_create_workflow でワークフローを作成
4. d6e_execute_workflow で実行

サポートされている操作:
- "create_journal_entry": 仕訳作成（entry_date, description, lines必須）
- "validate_journal_entry": 仕訳検証（entry必須）
- "calculate_depreciation": 減価償却計算（period必須）
- "calculate_prepaid_amortization": 前払費用償却（period必須）
- "generate_accrual_entry": 未払費用仕訳生成
- "list_pending_entries": 承認待ち一覧

まずは減価償却計算を試してください: operation: "calculate_depreciation", period: "2025-01"
```

### 未払費用を計上するプロンプト

```
2025年1月末のコンサルティング費用50,000円を未払計上してください。自動リバースを設定します。

使用スキル:
- Docker Image: ghcr.io/d6e-ai/stf-journal-entry:latest
- 操作: generate_accrual_entry

パラメータ:
- accrual_type: "AP_ACCRUAL"
- period: "2025-01"
- amount: 50000
- description: "Unbilled consulting services - January"
- expense_account_id: {コンサルティング費用の勘定科目UUID}
- liability_account_id: {未払費用の勘定科目UUID}

この仕訳は2月1日に自動でリバースされます。
```

### 完全な実行例プロンプト

```
月次決算の減価償却仕訳を作成してください。

Docker Image: ghcr.io/d6e-ai/stf-journal-entry:latest

実行ステップ:
1. STF作成（name: "journal-entry", runtime: "docker"）

2. ポリシー設定:
   - ポリシーグループ作成
   - STFをグループに追加
   - 以下のテーブルへのSELECTポリシー作成:
     - accounts
     - fiscal_periods
     - account_balances

3. ワークフロー作成・実行:
   - operation: "calculate_depreciation"
   - period: "2025-01"

4. 結果の確認:
   - 減価償却額の合計
   - 資産カテゴリ別の明細
   - 推奨される仕訳エントリ

結果から実際の仕訳を作成する場合は、suggested_entryの内容をcreate_journal_entry操作で使用してください。
```

## 仕訳タイプ

| タイプ      | 説明                                 |
| ----------- | ------------------------------------ |
| `STANDARD`  | 通常の取引仕訳                       |
| `ADJUSTING` | 決算整理仕訳（未払費用、前払費用等） |
| `CLOSING`   | 決算振替仕訳                         |
| `REVERSING` | リバース仕訳                         |

## 検証ルール

STF は以下のルールで仕訳を検証します：

1. **貸借一致**: 借方合計 = 貸方合計
2. **最低行数**: 2 行以上
3. **単一サイド**: 各行は借方または貸方のいずれか一方のみ
4. **非ゼロ金額**: 金額が 0 の行は不可
5. **摘要必須**: 仕訳には摘要が必要
6. **概算警告**: 端数のないきれいな金額は警告

## トラブルシューティング

### 貸借不一致エラー

```
Error: Entry is not balanced. Debits: $15,000.00, Credits: $10,000.00
```

**解決策**: 借方合計と貸方合計が一致するように仕訳行を修正してください。

### 勘定科目が見つからない

```
Error: Invalid account IDs: a0000001-xxxx-xxxx-xxxx
```

**解決策**: `accounts`テーブルに存在する有効な勘定科目 UUID を使用してください。

## ローカルでのビルドとテスト

```bash
# ビルド
docker build -t stf-journal-entry:latest .

# テスト
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

## 関連ドキュメント

- [データベーススキーマ](../docs/DATABASE_SCHEMA.md)
- [サンプルデータ](../docs/SAMPLE_DATA.sql)
- [プロジェクト README](../README.md)
