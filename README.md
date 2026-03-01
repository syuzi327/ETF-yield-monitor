# ETF配当利回り監視Bot

米国高配当ETF（VYM, HDV, SPYD, SCHD）の配当利回りを監視し、設定した閾値を超えた際にDiscordへ通知するGitHub Actionsベースの自動監視Bot。

## 特徴

### 🎯 シンプルで正確な閾値計算
- **年度内固定の閾値**: baseline利回り（過去平均）+ オフセットで計算
- **TTM方式**: 過去365日の実績配当で利回りを計算（信頼性が高い）
- **初回起動タイミング非依存**: 年の途中で起動しても正確

### 🔄 自動Baseline更新
- **年越し時の自動更新**: 前年実績を自動計算してbaselineに反映
- **欠落データの自動補完**: 長期停止後も過去データを自動取得して更新
- **初回起動時の補完対応**: 2027年に初回起動しても2025〜2026年のデータを自動補完

### 📢 充実した通知機能
- **初回起動通知**: 監視開始時に設定値を確認
- **閾値上抜け/下抜け通知**: リアルタイムで検知
- **週次リマインダー**: 閾値超過中は毎週土曜日に通知（上抜け時比・前週比付き）
- **Baseline更新通知**: 年度更新の成功を確認
- **エラー通知**: データ取得失敗やBaseline更新失敗を即座に把握

### 💱 円建て表示
- USD/JPY為替レートを自動取得
- 価格と配当を円換算して表示

---

## セットアップ

### 1. リポジトリの準備

```bash
git clone https://github.com/your-username/etf-yield-monitor.git
cd etf-yield-monitor
```

```
etf-yield-monitor/
├── .github/
│   └── workflows/
│       └── monitor.yml
├── src/
│   ├── etf_monitor.py
│   └── config.py
├── data/
│   └── state.json      # 自動生成
├── requirements.txt
└── README.md
```

### 2. Discord Webhook URLの取得

1. Discordサーバーで通知を受け取りたいチャンネルを開く
2. チャンネル設定 → 連携サービス → ウェブフック
3. 「新しいウェブフック」を作成してURLをコピー

### 3. GitHub Secretsの設定

1. GitHubリポジトリ → `Settings` → `Secrets and variables` → `Actions`
2. `New repository secret` をクリック
3. 以下を追加:
   - Name: `DISCORD_WEBHOOK_URL`
   - Value: コピーしたWebhook URL

### 4. GitHub Actionsの有効化

`.github/workflows/monitor.yml` がリポジトリにあれば自動的に有効化されます。
デフォルトで毎日 **UTC 22:00（JST 7:00）** に実行されます。

---

## 設定

### config.py

```python
ETFS = {
    "VYM": {
        "name": "Vanguard High Dividend Yield ETF",
        "inception_date": "2006-11-10",
        "baseline_years": 18,         # baselineに含まれる年数（2007〜2024年）
        "baseline_yield": 3.03,       # 過去の平均利回り（%）
        "baseline_year_end": 2024,    # baselineの最終年（重要）
        "threshold_offset": 0.0,      # baseline + この値が閾値
    },
}
```

#### パラメータ説明

| パラメータ | 説明 |
|---|---|
| `baseline_years` | baselineに含まれる年数 |
| `baseline_yield` | 過去の平均利回り（%） |
| `baseline_year_end` | baselineに含まれる最終年（自動補完の起点になるため必須） |
| `threshold_offset` | `0.0` → baseline以上で通知 / `0.5` → baseline+0.5%以上で通知 |

### 実行スケジュールの変更

`.github/workflows/monitor.yml` の `cron` を編集:

```yaml
schedule:
  # 毎日UTC 22:00（JST 7:00）
  - cron: '0 22 * * *'
```

### 手動実行

GitHubのActionsタブで「Run workflow」ボタンをクリック

---

## 動作シナリオ

### シナリオ1: 初回起動（below）

```
TTM利回り 2.8% < 閾値 3.03%
→ Discord: "✅ 監視開始"
→ state: status=below
```

### シナリオ2: 初回起動（above）

```
TTM利回り 4.0% > 閾値 3.03%
→ Discord: "⚠️ 監視開始（閾値超過中）"（次回リマインダー日付き）
→ state: status=above, crossed_above_date=今日
```

### シナリオ3: 年越し時のBaseline自動更新

```
last_year=2025, current_year=2026 を検知
→ 2025年分配金総額 ÷ 12/31株価 = 3.53%
→ Baseline更新: 3.03%(18年) → 3.06%(19年)
→ Discord: "📊 Baseline自動更新"
→ 新しい閾値: 3.06%
```

### シナリオ4: 長期停止後の欠落補完（初回起動）

```
config: baseline_year_end=2024, 実際の起動=2027年
→ 欠落検知: 2025〜2026年のデータが不足
→ 2025年・2026年を順番に自動取得してbaseline更新
→ Discord: "📊 Baseline自動更新"
```

### シナリオ5: 土曜日の週次リマインダー

```
above継続中、土曜日、前回リマインダーから7日以上経過
→ Discord: "📌 週次リマインダー"
   - 上抜け時比（利回り・価格）
   - 前週比（利回り・価格）← 2回目以降
```

---

## 通知の種類

### ✅ 監視開始（below）
```
色: 青
📊 配当利回り (TTM): 2.49%
🎯 閾値: 3.03%
ℹ️ Baseline: 3.03% (18年)
```

### ⚠️ 監視開始（above）
```
色: オレンジ
📊 配当利回り (TTM): 4.10%
🎯 閾値: 3.03%
ℹ️ Baseline: 3.03% (18年)
📅 次回リマインダー: 2026-03-07 (土曜日)
```

### 🚀 閾値上抜け
```
色: 緑
詳細: 閾値上抜け: 2.98% → 3.05%
```

### 📉 閾値下抜け
```
色: 赤
詳細: 閾値下抜け: 3.05% → 2.98%
```

### 📌 週次リマインダー
```
色: 黄
詳細: 週次リマインダー（土曜日、継続14日目）
📊 上抜け時比（利回り）: 3.52% → 3.65%（+0.13%）
📊 上抜け時比（価格）:  ¥4,500 → ¥4,350（-150）
📅 前週比（利回り）:   3.58% → 3.65%（+0.07%）  ← 2回目以降
📅 前週比（価格）:     ¥4,400 → ¥4,350（-50）    ← 2回目以降
```

### 📊 Baseline自動更新
```
色: 紫
📈 更新前: 3.03% (18年)
📈 更新後: 3.06% (19年)
🎯 新しい閾値: 3.06%
```

### ❌ データ取得失敗 / Baseline更新失敗
```
色: 赤 / オレンジ
詳細: エラー内容
```

---

## ロジックの特徴

### TTM方式で年度途中の歪みを回避

年の途中では分配金の回数が揃っていないため、単純に年換算すると誤差が生じます。
TTM（Trailing Twelve Months）方式では常に「直近365日の実績配当 ÷ 現在株価」で計算するため、起動タイミングに関わらず正確です。

### Baselineの自動管理

| タイミング | 動作 |
|---|---|
| 年越し初回実行 | 前年の実績（分配金総額 ÷ 年末株価）を加重平均に反映 |
| 欠落検知（長期停止後） | 不足している年を順番に自動取得して補完 |
| state.json | 更新後のbaselineを永続化（手動変更不要） |

---

## ローカル実行

```bash
# 依存関係インストール
pip install -r requirements.txt

# 環境変数設定（Windowsの場合は set）
export DISCORD_WEBHOOK_URL="your_webhook_url"

# 実行
cd src
python etf_monitor.py
```

---

## state.json の構造

```json
{
  "VYM": {
    "status": "above",
    "current_yield": 4.0,
    "price_usd": 95.00,
    "dividend_usd": 3.80,
    "threshold": 3.03,
    "last_trade_date": "2026-03-01",
    "last_year": 2026,
    "baseline": {
      "years": 19,
      "yield": 3.03
    },
    "last_checked": "2026-03-01",
    "last_notified": "2026-03-01",
    "last_reminded": "2026-03-01",
    "crossed_above_date": "2026-02-15",
    "crossed_above_yield": 3.10,
    "crossed_above_price_jpy": 14250.0,
    "last_reminded_yield": 3.08,
    "last_reminded_price_jpy": 14300.0
  }
}
```

---

## トラブルシューティング

### 通知が来ない

1. GitHub Actionsが実行されているか → Actionsタブで実行履歴を確認
2. Discord Webhook URLが正しいか → Secretsの設定を確認
3. エラーログを確認 → Actions実行ログで詳細を確認

### データ取得エラー（❌ データ取得失敗）

**原因:** yfinance APIの一時的な障害 / ティッカーシンボルの変更 / ネットワークエラー
**対処:** 数時間後に自動再試行。継続する場合はティッカーシンボルを確認。

### Baseline更新失敗（❌ Baseline更新失敗）

**原因:** 過去データの取得失敗 / 分配金データの不足
**対処:** 翌年の年越し時に再試行。古いbaselineで監視は継続されます。

---

## ライセンス

MIT License

## 免責事項

このBotは情報提供のみを目的としており、投資助言ではありません。投資判断は自己責任で行ってください。
