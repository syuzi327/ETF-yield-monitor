"""
ETF監視Bot設定ファイル
"""

# 監視対象ETF
ETFS = {
    "VYM": {
        "name": "Vanguard High Dividend Yield ETF",
        "threshold": 1.0,  # テスト用: 1%
    },
    "HDV": {
        "name": "iShares Core High Dividend ETF",
        "threshold": 1.0,
    },
    "SPYD": {
        "name": "SPDR Portfolio S&P 500 High Dividend ETF",
        "threshold": 1.0,
    },
    "SCHD": {
        "name": "Schwab U.S. Dividend Equity ETF",
        "threshold": 1.0,
    },
}

# 週次リマインダー間隔（日数）
REMINDER_INTERVAL_DAYS = 7

# データファイルパス
STATE_FILE = "data/state.json"

# Discord Webhook URL（環境変数から取得）
# GitHub Actionsで DISCORD_WEBHOOK_URL をSecretに設定すること