# D6E Variance Analysis STF

予算対実績分析、期間比較、差異分解、ウォーターフォールチャート生成を行う Docker STF です。

**Docker Image**: `ghcr.io/d6e-ai/stf-variance-analysis:latest`

## LLM/AI エージェント向け使用方法

この Docker イメージを D6E AI エージェントから使用する場合、以下の手順で STF を作成してください。

### ステップ 1: STF の作成

```javascript
d6e_create_stf({
  name: "variance-analysis",
  description:
    "Analyze financial variances with budget vs actual and period comparisons",
});
```

### ステップ 2: STF バージョンの作成

```javascript
d6e_create_stf_version({
  stf_id: "{ステップ1で取得したstf_id}",
  version: "1.0.0",
  runtime: "docker",
  code: '{"image":"ghcr.io/d6e-ai/stf-variance-analysis:latest"}',
});
```

**重要**: `runtime`は必ず`"docker"`を指定し、`code`フィールドには JSON 文字列として`{"image":"ghcr.io/d6e-ai/stf-variance-analysis:latest"}`を設定してください。

### ステップ 3: ワークフローの作成

```javascript
d6e_create_workflow({
  name: "variance-analysis-workflow",
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
// ウォーターフォールチャート生成（データベース不要）
d6e_execute_workflow({
  workflow_id: "{workflow_id}",
  input: {
    operation: "generate_waterfall",
    start_value: 1000000,
    end_value: 1150000,
    drivers: [
      { name: "新規顧客", amount: 80000 },
      { name: "既存顧客拡大", amount: 50000 },
      { name: "価格改定", amount: 30000 },
      { name: "解約", amount: -10000 },
    ],
    title: "Q1売上ブリッジ",
  },
});

// 予算対実績分析
d6e_execute_workflow({
  workflow_id: "{workflow_id}",
  input: {
    operation: "analyze_budget_variance",
    period: "2025-01",
    budget_version: "ORIGINAL",
  },
});

// 期間比較分析
d6e_execute_workflow({
  workflow_id: "{workflow_id}",
  input: {
    operation: "analyze_period_variance",
    current_period: "2025-01",
    comparison_period: "2024-01",
  },
});
```

## サポートされている操作

| Operation                     | 必須パラメータ                                | オプション                                        | DB 必要 | 説明                           |
| ----------------------------- | --------------------------------------------- | ------------------------------------------------- | ------- | ------------------------------ |
| `generate_waterfall`          | `start_value`, `end_value`, `drivers`         | `title`                                           | ❌      | ウォーターフォールチャート生成 |
| `generate_variance_narrative` | `variance_item`                               | `additional_context`                              | ❌      | 差異説明文生成                 |
| `analyze_budget_variance`     | `period`                                      | `budget_version`, `account_type`, `department_id` | ✅      | 予算対実績分析                 |
| `analyze_period_variance`     | `current_period`, `comparison_period`         | `account_type`                                    | ✅      | 期間比較分析                   |
| `decompose_variance`          | `account_code`, `period`, `comparison_period` | `decomposition_type`                              | ✅      | 差異分解（価格/数量/構成）     |

## 入出力例

### ウォーターフォールチャート生成（データベース不要）

**入力**:

```json
{
  "operation": "generate_waterfall",
  "start_value": 1000000,
  "end_value": 1150000,
  "drivers": [
    { "name": "新規顧客獲得", "amount": 80000 },
    { "name": "既存顧客拡大", "amount": 50000 },
    { "name": "価格改定", "amount": 30000 },
    { "name": "解約", "amount": -10000 }
  ],
  "title": "Q1売上ブリッジ"
}
```

**出力**:

```json
{
  "output": {
    "status": "success",
    "operation": "generate_waterfall",
    "data": {
      "title": "Q1売上ブリッジ",
      "start_value": 1000000,
      "end_value": 1150000,
      "total_change": 150000,
      "bars": [
        { "label": "Starting Value", "value": 1000000, "bar_type": "total" },
        {
          "label": "新規顧客獲得",
          "value": 80000,
          "bar_type": "increase",
          "percentage_of_change": 0.533
        },
        {
          "label": "既存顧客拡大",
          "value": 50000,
          "bar_type": "increase",
          "percentage_of_change": 0.333
        },
        {
          "label": "価格改定",
          "value": 30000,
          "bar_type": "increase",
          "percentage_of_change": 0.2
        },
        {
          "label": "解約",
          "value": -10000,
          "bar_type": "decrease",
          "percentage_of_change": -0.067
        },
        { "label": "Ending Value", "value": 1150000, "bar_type": "total" }
      ],
      "text_representation": "WATERFALL: Q1売上ブリッジ\n\nStarting Value                            $1,000,000.00\n  |--[+] 新規顧客獲得                         $80,000.00\n  |--[+] 既存顧客拡大                         $50,000.00\n  |--[+] 価格改定                             $30,000.00\n  |--[-] 解約                                -$10,000.00\nEnding Value                              $1,150,000.00\n\nNet Change: $150,000.00 (15.0%)",
      "reconciliation": {
        "drivers_sum": 150000,
        "reconciles": true
      }
    }
  }
}
```

### 差異説明文生成（データベース不要）

**入力**:

```json
{
  "operation": "generate_variance_narrative",
  "variance_item": {
    "account_code": "6100",
    "account_name": "人件費",
    "actual": 500000,
    "budget": 450000,
    "variance_dollar": 50000,
    "variance_percent": 0.111,
    "is_favorable": false,
    "is_material": true
  },
  "additional_context": "1月中旬に3名のエンジニアを採用"
}
```

**出力**:

```json
{
  "output": {
    "status": "success",
    "data": {
      "narrative": {
        "headline": "人件費: Unfavorable variance of $50,000.00 (11.1%)",
        "summary": "Actual of $500,000.00 was $50,000.00 higher than budget of $450,000.00.",
        "outlook": "This variance should be monitored in upcoming periods.",
        "additional_context": "1月中旬に3名のエンジニアを採用"
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

### 予算対実績分析

**入力**:

```json
{
  "operation": "analyze_budget_variance",
  "period": "2025-01",
  "budget_version": "ORIGINAL",
  "account_type": "EXPENSE"
}
```

**出力**:

```json
{
  "output": {
    "status": "success",
    "data": {
      "analysis_type": "BUDGET_VS_ACTUAL",
      "period": "2025-01",
      "summary": {
        "total_actual": 1098000,
        "total_budget": 1044000,
        "total_variance_dollar": 54000,
        "total_variance_percent": 0.052,
        "material_variance_count": 3
      },
      "material_variances": [
        {
          "account_code": "6000",
          "account_name": "R&D - Salaries",
          "actual": 280000,
          "budget": 260000,
          "variance_dollar": 20000,
          "variance_percent": 0.077,
          "is_favorable": false,
          "is_material": true
        }
      ]
    }
  }
}
```

## 🤖 AI エージェントへのプロンプト

### 基本プロンプト（データベース不要）

```
D6Eで差異分析を行うDockerスキルを使用してください。

Docker Image: ghcr.io/d6e-ai/stf-variance-analysis:latest

使用手順:
1. d6e_create_stf でSTFを作成（name: "variance-analysis"）
2. d6e_create_stf_version で以下を指定:
   - runtime: "docker"
   - code: "{\"image\":\"ghcr.io/d6e-ai/stf-variance-analysis:latest\"}"
3. d6e_create_workflow でワークフローを作成
4. d6e_execute_workflow で実行

データベース不要の操作:
- "generate_waterfall": ウォーターフォールチャート（start_value, end_value, drivers必須）
- "generate_variance_narrative": 差異説明文（variance_item必須）

データベース必要な操作:
- "analyze_budget_variance": 予算対実績（period必須）
- "analyze_period_variance": 期間比較（current_period, comparison_period必須）
- "decompose_variance": 差異分解（account_code, period, comparison_period必須）

まずはウォーターフォールチャートで動作確認してください。
```

### ウォーターフォールチャートを作成するプロンプト

```
以下の売上変動要因でウォーターフォールチャートを作成してください。

前期売上: 10,000,000円
当期売上: 11,500,000円

変動要因:
- 新規顧客獲得: +800,000円
- 既存顧客アップセル: +500,000円
- 価格改定効果: +300,000円
- 解約: -100,000円

使用スキル:
- Docker Image: ghcr.io/d6e-ai/stf-variance-analysis:latest
- 操作: generate_waterfall

テキスト形式のウォーターフォールと、各要因が全体変動に占める割合を表示してください。
```

### 完全な実行例プロンプト（予算分析）

```
2025年1月の費用予算対実績分析を行ってください。

Docker Image: ghcr.io/d6e-ai/stf-variance-analysis:latest

実行ステップ:
1. STF作成（name: "variance-analysis", runtime: "docker"）

2. ポリシー設定:
   - ポリシーグループ作成
   - STFをグループに追加
   - 以下のテーブルへのSELECTポリシー作成:
     - accounts
     - chart_of_accounts
     - account_balances
     - budgets
     - fiscal_periods

3. ワークフロー作成・実行:
   - operation: "analyze_budget_variance"
   - period: "2025-01"
   - budget_version: "ORIGINAL"
   - account_type: "EXPENSE"

4. 分析結果:
   - 重要性基準を超えた差異のリスト
   - 各差異が有利か不利か
   - 推奨アクション

重要な差異については、generate_variance_narrative操作で説明文を生成してください。
```

## 重要性基準（Materiality Thresholds）

デフォルトの重要性基準（リクエストごとにカスタマイズ可能）:

| 勘定科目規模          | 金額基準 | 率基準 |
| --------------------- | -------- | ------ |
| > 1,000 万円          | 50 万円  | 5%     |
| 100 万円 - 1,000 万円 | 10 万円  | 10%    |
| < 100 万円            | 5 万円   | 15%    |

差異が**いずれかの基準**を超えた場合、重要な差異としてフラグされます。

## トラブルシューティング

### 予算データが見つからない

```
Error: No budget found for period 2025-01
```

**解決策**: `budgets`テーブルに該当期間・バージョンの予算データが存在することを確認してください。

### ポリシーエラー

```
Error: Policy violation - SELECT not allowed on table 'budgets'
```

**解決策**: STF に対して必要なテーブルへの SELECT ポリシーを設定してください。

## ローカルでのビルドとテスト

```bash
# ビルド
docker build -t stf-variance-analysis:latest .

# テスト（データベース不要）
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

## 関連ドキュメント

- [データベーススキーマ](../docs/DATABASE_SCHEMA.md)
- [サンプルデータ](../docs/SAMPLE_DATA.sql)
- [プロジェクト README](../README.md)
