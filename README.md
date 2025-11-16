# ETF配当利回り監視Bot（円建て）

米国高配当ETFの配当利回りを円建てで監視し、閾値を超えたらDiscordに通知するBot

## 📊 監視対象ETF

- **VYM** - Vanguard High Dividend Yield ETF
- **HDV** - iShares Core High Dividend ETF
- **SPYD** - SPDR Portfolio S&P 500 High Dividend ETF
- **SCHD** - Schwab U.S. Dividend Equity ETF

## 🔔 通知ロジック

1. **上抜け通知**: 配当利回りが閾値を超えた瞬間に通知
2. **週次リマインダー**: 閾値超過が継続している間、週1回通知
3. **下抜け通知**: 閾値を下回った時に1回通知

## 🚀 セットアップ

### 1. Discord Webhookの作成

1. Discordサーバーで右クリック → **サーバー設定**
2. **連携サービス** → **ウェブフック** → **新しいウェブフック**
3. 名前を設定（例: ETF利回り監視Bot）
4. 通知先チャンネルを選択
5. **ウェブフックURLをコピー**

### 2. GitHubリポジトリの作成

```bash
# このディレクトリをGitHubにプッシュ
git init
git add .
git commit -m "Initial commit: ETF yield monitor bot"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/etf-yield-monitor.git
git push -u origin main
```

### 3. GitHub Secretsの設定

1. GitHubリポジトリページで **Settings** → **Secrets and variables** → **Actions**
2. **New repository secret** をクリック
3. 以下を登録:
   - **Name**: `DISCORD_WEBHOOK_URL`
   - **Secret**: （コピーしたWebhook URL）

### 4. 初回の状態ファイル作成

```bash
# dataディレクトリと空のstate.jsonを作成
mkdir -p data
echo "{}" > data/state.json
git add data/state.json
git commit -m "Add initial state file"
git push
```

## ⚙️ 設定のカスタマイズ

### 閾値の変更

`src/config.py` を編集:

```python
ETFS = {
    "VYM": {
        "name": "Vanguard High Dividend Yield ETF",
        "threshold": 4.0,  # ← ここを変更（%）
    },
    # ...
}
```

### 実行時刻の変更

`.github/workflows/monitor.yml` のcron設定を編集:

```yaml
schedule:
  # 米国市場終了後（日本時間朝6:00）に実行する場合
  - cron: '0 21 * * *'  # UTC 21:00 = JST 6:00
  
  # 日本時間23:00に実行する場合
  - cron: '0 14 * * *'  # UTC 14:00 = JST 23:00
```

### 週次リマインダー間隔の変更

`src/config.py` を編集:

```python
# 週次リマインダー間隔（日数）
REMINDER_INTERVAL_DAYS = 7  # ← ここを変更
```

## 🧪 ローカルでのテスト

```bash
# 依存ライブラリのインストール
pip install -r requirements.txt

# 環境変数を設定してテスト実行
export DISCORD_WEBHOOK_URL="your_webhook_url_here"
cd src
python etf_monitor.py
```

## 🎯 手動実行

GitHubリポジトリページで:
1. **Actions** タブをクリック
2. **ETF Yield Monitor** ワークフローを選択
3. **Run workflow** → **Run workflow** をクリック

## 📁 ファイル構成

```
etf-yield-monitor/
├── .github/workflows/
│   └── monitor.yml          # GitHub Actions設定
├── src/
│   ├── etf_monitor.py       # メインスクリプト
│   └── config.py            # 設定ファイル
├── data/
│   └── state.json           # 状態管理（自動更新）
├── .gitignore
├── requirements.txt
└── README.md
```

## 📊 通知メッセージの内容

- 配当利回り（%）
- 閾値
- 現在価格（USD / JPY）
- 年間配当額（USD / JPY）
- USD/JPY為替レート
- 通知理由（上抜け/下抜け/リマインダー）

## 🔧 トラブルシューティング

### GitHub Actionsが動かない

1. **Actions** タブで実行ログを確認
2. `DISCORD_WEBHOOK_URL` Secretが正しく設定されているか確認
3. `data/state.json` が存在するか確認

### データ取得エラー

- yfinanceはたまにレート制限に引っかかることがあります
- 数時間待ってから再実行してください

### 通知が来ない

1. Webhook URLが正しいか確認
2. Discordサーバーでボットに投稿権限があるか確認
3. ローカルで手動実行してテスト

## 📝 ライセンス

MIT License

## 🤝 貢献

Issue・Pull Request歓迎です！