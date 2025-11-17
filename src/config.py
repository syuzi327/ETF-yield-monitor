"""
ETF監視Bot設定ファイル（最終版）

ロジック:
- 閾値 = baseline_yield + threshold_offset（年度内固定）
- baseline更新は年越し初回実行時に自動実行（前年の実績を計算して反映）
- 前年の利回り = その年の分配金総額 ÷ 年末の株価
- 欠落期間がある場合は自動補完（初回起動時も対応）
- 週次リマインダーは毎週土曜日に送信
"""

# 監視対象ETF
ETFS = {
    "VYM": {
        "name": "Vanguard High Dividend Yield ETF",
        "inception_date": "2006-11-10",
        "baseline_years": 18,         # 2007-2024年
        "baseline_yield": 3.03,       # 2007-2024年の平均利回り（%）
        "baseline_year_end": 2024,    # baselineの最終年
        "threshold_offset": 0.0,      # baseline + 0.0%で通知
    },
    "HDV": {
        "name": "iShares Core High Dividend ETF",
        "inception_date": "2011-03-29",
        "baseline_years": 14,         # 2011-2024年
        "baseline_yield": 3.55,
        "baseline_year_end": 2024,
        "threshold_offset": 0.0,
    },
    "SPYD": {
        "name": "SPDR Portfolio S&P 500 High Dividend ETF",
        "inception_date": "2015-10-21",
        "baseline_years": 9,          # 2016-2024年
        "baseline_yield": 4.58,
        "baseline_year_end": 2024,
        "threshold_offset": 0.0,
    },
    "SCHD": {
        "name": "Schwab U.S. Dividend Equity ETF",
        "inception_date": "2011-10-20",
        "baseline_years": 14,         # 2011-2024年
        "baseline_yield": 3.50,
        "baseline_year_end": 2024,
        "threshold_offset": 0.0,
    },
}

# データファイルパス
STATE_FILE = "data/state.json"

# Discord Webhook URL（環境変数から取得）
# GitHub Actionsで DISCORD_WEBHOOK_URL をSecretに設定すること