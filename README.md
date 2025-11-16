# ETF配当利回り監視Bot（円建て）

米国高配当ETFの配当利回りを円建てで監視し、**動的閾値**を超えたらDiscordに通知するBot

## 📊 監視対象ETF

- **VYM** - Vanguard High Dividend Yield ETF
- **HDV** - iShares Core High Dividend ETF
- **SPYD** - SPDR Portfolio S&P 500 High Dividend ETF
- **SCHD** - Schwab U.S. Dividend Equity ETF

## 🔔 通知ロジック

1. **上抜け通知**: 配当利回りが動的閾値を超えた瞬間に通知
2. **週次リマインダー**: 閾値超過が継続している間、週1回通知
3. **下抜け通知**: 閾値を下回った時に1回通知

## 🎯 動的閾値システム

### 完全自動の閾値更新

このBotは**年次メンテナンス不要**の動的閾値システムを採用しています。

#### 計算方式

```python
# 例: VYM (2025年11月16日時点)
baseline_years = 18        # 2007-2024年
baseline_yield = 3.03%     # その期間の平均利回り
year_2025_avg = 2.95%      # 2025年の平均（毎日更新、取引日数ベース）
year_2025_days = 220       # 実際の取引日数

# 累積平均を計算（取引日数ベース）
baseline_days = 18 × 252 = 4,536日
cumulative_avg = (3.03% × 4536 + 2.95% × 220) / 4756 = 3.02%

# 動的閾値
threshold = 3.02% + 0.3% = 3.32%
```

**重要:** 累積平均は取引日数ベースで計算されるため、年初の数日間でも閾値が安定します。

#### 年初の安定性

```python
# 2026年1月2日（初日のみ）
baseline_days = 19 × 252 = 4,788日
year_days = 1
year_avg = 1.80%  # 暴落した1日

cumulative_avg = (3.03% × 4788 + 1.80% × 1) / 4789 = 3.0297%
# 変動: わずか0.0003% → 安定 ✅
```

#### 主な特徴

- ✅ **初回起動時**: 年初来の全データを遡って取得
- ✅ **毎日実行時**: 取引日のみ更新（土日祝日は自動スキップ）
- ✅ **年度移行**: 自動で前年データをbaselineに統合
- ✅ **データ欠落補完**: 長期停止後も自動で欠落期間を補完
- ✅ **複数年飛び越え**: 2年以上の欠落も遡って補完

### データ補完機能

**年度途中の欠落（7日以上）**
```
最終実行: 2025年8月15日
再起動: 2025年11月16日
→ 8月16日～11月15日の欠落分を自動補完
```

**年度を飛び越えた場合**
```
最終実行: 2025年12月
再起動: 2027年5月
→ 2026年全体を遡って補完 + 2027年1-4月を補完
```

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

### 閾値オフセットの変更

`src/config.py` を編集:

```python
ETFS = {
    "VYM": {
        "name": "Vanguard High Dividend Yield ETF",
        "baseline_years": 18,
        "baseline_yield": 3.03,
        "threshold_offset": 0.3,  # ← ここを変更（%）
        "current_year": 2025,
    },
    # ...
}
```

**推奨値:**
- `0.2-0.3`: 頻繁に通知（少しでも高利回りで通知）
- `0.4-0.5`: 控えめに通知（明確な買い場のみ）

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

### 初回実行時の動作

```
--- VYM (Vanguard High Dividend Yield ETF) ---
🆕 初回実行 - 年初来データを取得します
📊 2025年のデータを取得中... (2025-01-01 ～ 2025-11-16)
✅ 取得完了: 平均利回り 2.95%, 取引日数 220日
配当利回り: 2.95%
今年平均: 2.95% (220取引日)
累積平均: 3.02% (閾値: 3.32%)
価格: $141.23 (¥21,184)
判定: 初回実行
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
│   └── monitor.yml          # GitHub Actions設定（毎日自動実行）
├── src/
│   ├── etf_monitor.py       # メインスクリプト
│   └── config.py            # 設定ファイル（閾値など）
├── data/
│   └── state.json           # 状態管理（自動更新）
├── .gitignore
├── requirements.txt
└── README.md
```

## 📊 state.jsonの構造

```json
{
  "VYM": {
    "status": "below",
    "current_yield": 2.95,
    "threshold": 3.32,
    "cumulative_avg": 3.02,
    "last_trade_date": "2025-11-14",
    "baseline": {
      "years": 18,
      "yield": 3.03
    },
    "year_data": {
      "year": 2025,
      "year_avg": 2.95,
      "year_days": 220
    },
    "last_checked": "2025-11-16",
    "last_notified": "2025-11-10",
    "last_reminded": null,
    "crossed_above_date": null
  }
}
```

**各フィールドの説明:**
- `cumulative_avg`: 取引日数ベースで計算された累積平均
- `baseline`: 過去年度の平均（年ベースで更新）
- `year_data.year_days`: 実際の取引日数（土日祝除外）

## 📊 通知メッセージの内容

- 配当利回り（%）
- 動的閾値と累積平均
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
- 長期停止後の再起動時は自動でデータ補完されます

### 通知が来ない

1. Webhook URLが正しいか確認
2. Discordサーバーでボットに投稿権限があるか確認
3. ローカルで手動実行してテスト
4. 閾値設定が適切か確認（高すぎないか）

### state.jsonが壊れた場合

自動でバックアップが作成され、初期状態で再起動します:
```
⚠️ state.jsonが壊れています: ...
   バックアップを作成して初期化します...
   バックアップ: data/state.json.backup
```

## 🔄 年度更新について

**完全自動 - 何もする必要なし！**

### 年度更新時の処理（12月31日 → 1月1日）

```python
# 2025年のデータでbaseline更新（年ベース）
new_baseline_yield = (3.03% × 18年 + 3.10%) / 19年 = 3.033%
new_baseline_years = 19

# 2026年の累積平均計算は取引日数ベース
baseline_days = 19 × 252 = 4,788日
cumulative_avg = (3.033% × 4788 + year_avg × year_days) / (4788 + year_days)
```

**ポイント:**
- baseline更新は**年ベース**（各年を均等に扱う）
- 累積平均計算は**取引日数ベース**（年初の変動に強い）
- `config.py` の編集不要

## 💡 ベストプラクティス

### 推奨設定

```python
# 頻繁に通知が欲しい場合
"threshold_offset": 0.2  # 累積平均 + 0.2%

# バランス型（おすすめ）
"threshold_offset": 0.3  # 累積平均 + 0.3%

# 本当の買い場のみ
"threshold_offset": 0.5  # 累積平均 + 0.5%
```

### 実行時刻の選択

- **推奨**: UTC 21:00（JST 6:00）- 米国市場終了後
- **代替**: UTC 14:00（JST 23:00）- 日本の夜

### データの信頼性

- 初回起動時: 約15秒（年初来データ取得）
- 通常実行: 約5-10秒
- 欠落補完時: 約20-45秒（欠落期間による）

すべてGitHub Actions無料枠内です（月2,000分）

## 🛡️ セキュリティ

- Discord Webhook URLはGitHub Secretsで暗号化保存
- コード内にAPIキーや機密情報は含まれません
- state.jsonには個人の投資額や保有銘柄情報は含まれません

## 📝 ライセンス

MIT License

## 🤝 貢献

Issue・Pull Request歓迎です！

## 🆕 更新履歴

### v2.1 - 取引日数ベース計算
- 累積平均を取引日数ベースで計算（年初の変動に強い）
- baseline更新は年ベース（各年を均等に扱う）
- 年初1日目でも閾値が安定

### v2.0 - 動的閾値システム
- 完全自動の閾値更新機能
- データ欠落自動補完
- 年度移行自動処理
- 取引日ベースの正確なカウント

### v1.0 - 初版
- 基本的な利回り監視機能
- Discord通知
- 固定閾値