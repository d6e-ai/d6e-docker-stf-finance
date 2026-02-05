# D6E Finance Docker STF Suite

財務・経理業務を D6E ワークフローで実行するための Docker STF スイートです。

## Docker Images

| STF                  | Docker Image                                     | 説明                                                   |
| -------------------- | ------------------------------------------------ | ------------------------------------------------------ |
| Financial Statements | `ghcr.io/d6e-ai/stf-financial-statements:latest` | 損益計算書、貸借対照表、キャッシュフロー計算書、試算表 |
| Journal Entry        | `ghcr.io/d6e-ai/stf-journal-entry:latest`        | 仕訳帳作成、減価償却、前払費用償却、未払費用計上       |
| Variance Analysis    | `ghcr.io/d6e-ai/stf-variance-analysis:latest`    | 予算対実績分析、期間比較、ウォーターフォールチャート   |
| Reconciliation       | `ghcr.io/d6e-ai/stf-reconciliation:latest`       | 銀行照合、GL 対補助元帳照合、会社間照合                |
| Close Management     | `ghcr.io/d6e-ai/stf-close-management:latest`     | 月次決算タスク管理、進捗追跡、ブロッカー特定           |

## クイックスタート（LLM/AI エージェント向け）

### ステップ 1: STF の作成

```javascript
d6e_create_stf({
  name: "financial-statements",
  description: "Generate GAAP financial statements",
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

**重要**: `runtime`は必ず`"docker"`を指定し、`code`フィールドには JSON 文字列として Docker イメージを設定してください。

### ステップ 3: ワークフローの作成

```javascript
d6e_create_workflow({
  name: "finance-workflow",
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
d6e_execute_workflow({
  workflow_id: "{workflow_id}",
  input: {
    operation: "generate_trial_balance",
    period: "2025-01",
  },
});
```

## 🤖 AI エージェントへのプロンプト

### 財務諸表を生成する

```
D6Eで2025年1月の財務諸表を生成してください。

Docker Image: ghcr.io/d6e-ai/stf-financial-statements:latest
操作: generate_trial_balance
パラメータ: period: "2025-01"

手順:
1. STF作成（runtime: "docker"）
2. ポリシー設定（accounts, account_balances等へのSELECT）
3. ワークフロー実行
```

### 決算カレンダーを作成する（データベース不要）

```
2025年1月の月次決算カレンダーを作成してください。

Docker Image: ghcr.io/d6e-ai/stf-close-management:latest
操作: generate_close_calendar
パラメータ:
- period: "2025-01"
- period_end_date: "2025-01-31"
- close_days: 5

このOperationはデータベース不要で動作します。
```

### ウォーターフォールチャートを作成する（データベース不要）

```
売上変動のウォーターフォールチャートを作成してください。

Docker Image: ghcr.io/d6e-ai/stf-variance-analysis:latest
操作: generate_waterfall
パラメータ:
- start_value: 10000000
- end_value: 11500000
- drivers: [
    {"name": "新規顧客", "amount": 800000},
    {"name": "価格改定", "amount": 300000},
    {"name": "解約", "amount": -100000}
  ]
- title: "Q1売上ブリッジ"
```

## プロジェクト構造

```
d6e-docker-stf-finance/
├── shared/                          # 共通ユーティリティ
│   └── utils.py                     # D6E API クライアント、入出力処理
├── stf-financial-statements/        # 財務諸表STF
│   ├── main.py
│   ├── Dockerfile
│   └── README.md
├── stf-journal-entry/               # 仕訳帳STF
│   ├── main.py
│   ├── Dockerfile
│   └── README.md
├── stf-variance-analysis/           # 差異分析STF
│   ├── main.py
│   ├── Dockerfile
│   └── README.md
├── stf-reconciliation/              # 照合STF
│   ├── main.py
│   ├── Dockerfile
│   └── README.md
├── stf-close-management/            # 決算管理STF
│   ├── main.py
│   ├── Dockerfile
│   └── README.md
├── docs/
│   ├── DATABASE_SCHEMA.md           # データベーススキーマ定義
│   └── SAMPLE_DATA.sql              # テスト用サンプルデータ
├── scripts/
│   └── build-all.sh                 # 一括ビルドスクリプト
└── .github/workflows/
    └── docker-publish.yml           # CI/CD（ghcr.io公開）
```

## 各 STF の操作一覧

### stf-financial-statements

| 操作                        | 説明                       | DB 必要 |
| --------------------------- | -------------------------- | ------- |
| `generate_income_statement` | 損益計算書生成             | ✅      |
| `generate_balance_sheet`    | 貸借対照表生成             | ✅      |
| `generate_cash_flow`        | キャッシュフロー計算書生成 | ✅      |
| `generate_trial_balance`    | 試算表生成                 | ✅      |

### stf-journal-entry

| 操作                             | 説明             | DB 必要 |
| -------------------------------- | ---------------- | ------- |
| `create_journal_entry`           | 仕訳帳作成       | ❌      |
| `validate_journal_entry`         | 仕訳検証         | ❌      |
| `calculate_depreciation`         | 減価償却計算     | ✅      |
| `calculate_prepaid_amortization` | 前払費用償却     | ✅      |
| `generate_accrual_entry`         | 未払費用仕訳生成 | ❌      |
| `list_pending_entries`           | 承認待ち一覧     | ✅      |

### stf-variance-analysis

| 操作                          | 説明                       | DB 必要 |
| ----------------------------- | -------------------------- | ------- |
| `generate_waterfall`          | ウォーターフォールチャート | ❌      |
| `generate_variance_narrative` | 差異説明文生成             | ❌      |
| `analyze_budget_variance`     | 予算対実績分析             | ✅      |
| `analyze_period_variance`     | 期間比較分析               | ✅      |
| `decompose_variance`          | 差異分解                   | ✅      |

### stf-reconciliation

| 操作                         | 説明               | DB 必要 |
| ---------------------------- | ------------------ | ------- |
| `create_bank_reconciliation` | 銀行照合           | ✅      |
| `create_gl_subledger_rec`    | GL 対補助元帳照合  | ✅      |
| `create_intercompany_rec`    | 会社間照合         | ✅      |
| `add_reconciling_item`       | 照合項目追加       | ✅      |
| `analyze_aging`              | エイジング分析     | ✅      |
| `get_reconciliation_status`  | 照合ステータス一覧 | ✅      |

### stf-close-management

| 操作                      | 説明                 | DB 必要 |
| ------------------------- | -------------------- | ------- |
| `generate_close_calendar` | 決算カレンダー生成   | ❌      |
| `initialize_close_tasks`  | 決算タスク初期化     | ❌      |
| `get_critical_path`       | クリティカルパス分析 | ❌      |
| `update_task_status`      | タスクステータス更新 | ✅      |
| `get_close_progress`      | 決算進捗取得         | ✅      |
| `identify_blockers`       | ブロッカー特定       | ✅      |

## データベース要件

データベースを使用する操作を実行する場合、以下のテーブルが必要です：

- `chart_of_accounts` - 勘定科目タイプ定義
- `accounts` - 勘定科目マスタ
- `departments` - 部門マスタ
- `fiscal_periods` - 会計期間
- `journal_entries` - 仕訳帳ヘッダ
- `journal_lines` - 仕訳明細
- `account_balances` - 期末残高
- `budgets` - 予算データ
- `reconciliations` - 照合レコード
- `reconciling_items` - 照合項目
- `close_tasks` - 決算タスク

詳細は [docs/DATABASE_SCHEMA.md](docs/DATABASE_SCHEMA.md) を参照してください。

## ポリシー設定

STF がデータベースにアクセスするには、ポリシー設定が必要です：

```javascript
// 1. ポリシーグループ作成
d6e_create_policy_group({ name: "finance-stf-group" });

// 2. STFをグループに追加
d6e_add_member_to_policy_group({
  policy_group_id: "{group_id}",
  member_type: "stf",
  member_id: "{stf_id}",
});

// 3. SELECTポリシー作成
d6e_create_policy({
  policy_group_id: "{group_id}",
  table_name: "account_balances",
  operation: "select",
  mode: "allow",
});
```

## ローカルでのビルド

```bash
# 全STFを一括ビルド
./scripts/build-all.sh

# 個別ビルド
cp -r shared stf-financial-statements/shared
cd stf-financial-statements
docker build -t stf-financial-statements:latest .
```

## テスト

```bash
# データベース不要の操作でテスト
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

## ドキュメント

- [データベーススキーマ](docs/DATABASE_SCHEMA.md)
- [サンプルデータ](docs/SAMPLE_DATA.sql)
- [stf-financial-statements README](stf-financial-statements/README.md)
- [stf-journal-entry README](stf-journal-entry/README.md)
- [stf-variance-analysis README](stf-variance-analysis/README.md)
- [stf-reconciliation README](stf-reconciliation/README.md)
- [stf-close-management README](stf-close-management/README.md)

## トラブルシューティング

### Docker イメージが見つからない

```bash
# ghcr.ioからpull
docker pull ghcr.io/d6e-ai/stf-financial-statements:latest
```

### ポリシーエラー

```
Error: Policy violation - SELECT not allowed on table 'xxx'
```

STF に対して必要なテーブルへの SELECT ポリシーを設定してください。

### 期間が見つからない

```
Error: No balance found for period 2025-01
```

`fiscal_periods`テーブルに該当期間が存在し、`account_balances`テーブルにデータがあることを確認してください。
