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
- **初回起動時の補完対応**: 2027年に初回起動しても2025-2026年のデータを自動補完

### 📢 充実した通知機能
- **初回起動通知**: 監視開始時に設定値を確認
- **閾値上抜け/下抜け通知**: リアルタイムで検知
- **週次リマインダー**: 閾値超過中は毎週土曜日に通知
- **Baseline更新通知**: 年度更新の成功を確認
- **エラー通知**: データ取得失敗やBaseline更新失敗を即座に把握

### 💱 円建て表示
- USD/JPY為替レートを自動取得
- 価格と配当を円換算して表示

## セットアップ

### 1. リポジトリの準備

```bash
# クローン
git clone https://github.com/your-username/etf-yield-monitor.git
cd etf-yield-monitor

# ディレクトリ構造
etf-yield-monitor/
├── .github/
│   └── workflows/
│       └── monitor.yml
├── src/
│   ├── etf_monitor.py
│   └── config.py
├── data/
│   └── state.json  # 自動生成
├── requirements.txt
└── README.md
```

### 2. Discord Webhook URLの取得

1. Discordサーバーで通知を受け取りたいチャンネルを開く
2. チャンネル設定 → 連携サービス → ウェブフック
3. 「新しいウェブフック」を作成
4. Webhook URLをコピー

### 3. GitHub Secretsの設定

1. GitHubリポジトリページで `Settings` → `Secrets and variables` → `Actions`
2. `New repository secret` をクリック
3. 以下を追加:
   - Name: `DISCORD_WEBHOOK_URL`
   - Value: (コピーしたWebhook URL)

### 4. requirements.txtの作成

```
yfinance==0.2.66
requests==2.31.0
```

### 5. GitHub Actionsの有効化

- `.github/workflows/monitor.yml` がリポジトリにあることを確認
- GitHub Actionsが自動的に有効化されます
- デフォルトで毎日UTC 21:00（JST 6:00）に実行

## 設定

### config.py

```python
ETFS = {
    "VYM": {
        "name": "Vanguard High Dividend Yield ETF",
        "inception_date": "2006-11-10",
        "baseline_years": 18,         # 2007-2024年
        "baseline_yield": 3.03,       # 過去18年の平均利回り
        "baseline_year_end": 2024,    # baselineの最終年
        "threshold_offset": 0.0,      # baseline + 0.0%で通知
    },
}
```

**追加説明:**
```
- `baseline_year_end`: baselineに含まれる最終年（重要！）

#### パラメータ説明

- `baseline_years`: baselineに含まれる年数
- `baseline_yield`: 過去の平均利回り（%）
- `threshold_offset`: baseline + この値が閾値になる
  - `0.0`: baseline以上で通知
  - `0.5`: baseline + 0.5%以上で通知

### 実行スケジュールの変更

`.github/workflows/monitor.yml` の `cron` を編集:

```yaml
schedule:
  # 毎日UTC 21:00（JST 6:00）
  - cron: '0 21 * * *'
```

### 手動実行

GitHub Actionsページで「Run workflow」ボタンをクリック

## 動作シナリオ

### シナリオ1: 2025年11月17日に初回起動

```
1. データ取得: TTM利回り 4.0%
2. 閾値計算: baseline 3.03% + offset 0.0% = 3.03%
3. 判定: 4.0% > 3.03% → above
4. Discord通知: "⚠️ 監視開始（閾値超過中）"
   - 次回リマインダー: 2025-11-22 (土曜日)
5. state.json保存:
   - status: "above"
   - last_year: 2025
   - last_reminded: 2025-11-17
```

### シナリオ2: 2025年12月31日に初回起動

```
1. データ取得: TTM利回り 2.8%
2. 閾値計算: 3.03%
3. 判定: 2.8% < 3.03% → below
4. Discord通知: "✅ 監視開始"
5. state.json保存:
   - status: "below"
   - last_year: 2025
```

### シナリオ3: 2026年1月1日（年越し）

```
1. 年度更新検知: last_year=2025, current_year=2026
2. 2025年実績を計算:
   - 2025年分配金総額: $3.35
   - 2025年12月31日株価: $95.00
   - 2025年利回り = 3.35 / 95.00 = 3.53%
3. Baseline更新:
   - 旧: 3.03% (18年)
   - 新: (3.03×18 + 3.53) / 19 = 3.06% (19年)
4. Discord通知: "📊 Baseline自動更新"
5. 新しい閾値: 3.06%
```

### シナリオ4: 2027年1月に初回起動（欠落補完）

```
1. 初回起動検知
2. config.py: baseline_years=18 → 最終年は2024年
3. 欠落検知: 2024 < 2027-1 → 2025-2026年が欠落
4. 自動補完開始:
   - 2025年データ取得 → baseline更新
   - 2026年データ取得 → baseline更新
5. Discord通知: "📊 Baseline自動更新"
   - 詳細: 初回起動時にデータ欠落を検知し、自動補完
6. 更新後のbaseline: 20年分（2007-2026年）
```

### シナリオ5: 土曜日の週次リマインダー

```
前提: aboveが継続中、last_reminded=2025-11-17

2025年11月23日（土曜日）の実行:
1. TTM利回り: 4.1%
2. 閾値: 3.03%
3. 判定: above継続 & 土曜日 & 7日経過
4. Discord通知: "📌 週次リマインダー"
5. last_reminded更新: 2025-11-23
```

## ロジックの特徴

### 年換算方式の問題を解決

**旧方式の問題:**
```
11月に初回起動（3回分配金済み）
→ 年換算: (3回分 × 365/320日) で推計
→ 4回目配当前: 過小評価
→ 年度更新時に不正確なyear_avgを使用
```

**新方式の解決:**
```
11月に初回起動
→ 年の途中では統計を取らない
→ 年越し時に実データから計算
  → 2025年分配金総額 ÷ 12/31株価
→ 常に正確
```

### Baselineの自動管理

- **年度更新**: 前年実績を自動計算してbaseline更新
- **欠落補完**: 長期停止後も過去データを自動取得
- **初回対応**: 初回起動時も欠落期間を自動検知・補完
- **state.json**: 更新後のbaselineを永続化

## 通知の種類

### 1. 監視開始（初回起動 - below）
```
✅ 監視開始 - VYM
色: 青
📊 配当利回り (TTM): 2.49%
🎯 閾値: 3.03%
ℹ️ Baseline: 3.03% (18年)
```

### 2. 監視開始（初回起動 - above）
```
⚠️ 監視開始（閾値超過中） - VYM
色: オレンジ
📊 配当利回り (TTM): 4.10%
🎯 閾値: 3.03%
ℹ️ Baseline: 3.03% (18年)
📅 次回リマインダー: 2025-11-22 (土曜日)
```

### 3. 閾値上抜け
```
🚀 利回り閾値上抜け！ - VYM
色: 緑
詳細: 閾値上抜け: 2.98% → 3.05%
```

### 4. 閾値下抜け
```
📉 利回り閾値下抜け - VYM
色: 赤
詳細: 閾値下抜け: 3.05% → 2.98%
```

### 5. 週次リマインダー
```
📌 週次リマインダー - VYM
色: 黄
詳細: 週次リマインダー（土曜日、継続14日目）
```

### 6. Baseline自動更新
```
📊 Baseline自動更新 - VYM
色: 紫
📈 更新前: 3.03% (18年)
📈 更新後: 3.08% (19年)
🎯 新しい閾値: 3.08%
```

### 7. データ取得失敗
```
❌ データ取得失敗 - VYM
色: 赤
詳細: yfinance APIの問題、またはティッカーシンボルの変更
```

### 8. Baseline更新失敗
```
❌ Baseline更新失敗 - VYM
色: オレンジ
ℹ️ 現在のBaseline: 3.03% (18年)
詳細: 2025年の実績データ取得に失敗
```

## トラブルシューティング

### 通知が来ない

1. GitHub Actionsが実行されているか確認
   - Actionsタブで実行履歴を確認
2. Discord Webhook URLが正しいか確認
   - Secretsの設定を確認
3. エラーログを確認
   - Actions実行ログで詳細を確認

### データ取得エラー

```
❌ データ取得失敗
```

**原因:**
- yfinance APIの一時的な障害
- ティッカーシンボルの変更
- ネットワークエラー

**対処:**
- 数時間後に自動的に再試行されます
- 継続する場合はティッカーシンボルを確認

### Baseline更新失敗

```
❌ Baseline更新失敗
```

**原因:**
- 過去データの取得失敗
- 分配金データの不足

**対処:**
- 翌年の年越し時に再試行されます
- 古いbaselineで監視は継続されます

## 開発者向け

### ローカルテスト

```bash
# 依存関係インストール
pip install -r requirements.txt

# 環境変数設定
export DISCORD_WEBHOOK_URL="your_webhook_url"

# 実行
cd src
python etf_monitor.py
```

### state.jsonの構造

```json
{
  "VYM": {
    "status": "above",
    "current_yield": 4.0,
    "threshold": 3.03,
    "last_trade_date": "2025-11-17",
    "last_year": 2025,
    "baseline": {
      "years": 18,
      "yield": 3.03
    },
    "last_checked": "2025-11-17",
    "last_notified": "2025-11-17",
    "last_reminded": "2025-11-17",
    "crossed_above_date": "2025-11-17"
  }
}
```

## ライセンス

MIT License

## 免責事項

このBotは情報提供のみを目的としており、投資助言ではありません。投資判断は自己責任で行ってください。