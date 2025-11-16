"""
ETF監視Bot設定ファイル
"""

# 1年あたりの平均取引日数（米国市場）
AVERAGE_TRADING_DAYS_PER_YEAR = 252

# 監視対象ETF
ETFS = {
    "VYM": {
        "name": "Vanguard High Dividend Yield ETF",
        "inception_date": "2006-11-10",
        "baseline_years": 18,     # 2007-2024年
        "baseline_yield": 3.03,   # 2007-2024年の平均利回り（%）
        "threshold_offset": 0.3,  # 累積平均 + 0.3%で通知
        "current_year": 2025,
    },
    "HDV": {
        "name": "iShares Core High Dividend ETF",
        "inception_date": "2011-03-29",
        "baseline_years": 14,     # 2011-2024年
        "baseline_yield": 3.55,
        "threshold_offset": 0.3,
        "current_year": 2025,
    },
    "SPYD": {
        "name": "SPDR Portfolio S&P 500 High Dividend ETF",
        "inception_date": "2015-10-21",
        "baseline_years": 9,      # 2016-2024年
        "baseline_yield": 4.58,
        "threshold_offset": 0.4,
        "current_year": 2025,
    },
    "SCHD": {
        "name": "Schwab U.S. Dividend Equity ETF",
        "inception_date": "2011-10-20",
        "baseline_years": 14,     # 2011-2024年
        "baseline_yield": 3.50,
        "threshold_offset": 0.4,
        "current_year": 2025,
    },
}

# 週次リマインダー間隔（日数）
REMINDER_INTERVAL_DAYS = 7

# データファイルパス
STATE_FILE = "data/state.json"

# Discord Webhook URL（環境変数から取得）
# GitHub Actionsで DISCORD_WEBHOOK_URL をSecretに設定すること

# 計算方法:
# 1. 年内の平均を【取引日数ベース】で更新
#    year_avg = (前回のyear_avg × year_days + 今日の利回り) / (year_days + 1)
#
# 2. 累積平均を【取引日数ベース】で計算
#    baseline_days = baseline_years × 252日/年
#    cumulative_avg = (baseline_yield × baseline_days + year_avg × year_days) / (baseline_days + year_days)
#
# 3. 動的閾値を設定
#    threshold = cumulative_avg + threshold_offset
#
# 4. 年度更新時のbaseline更新は【年ベース】で計算
#    new_baseline_yield = (baseline_yield × baseline_years + year_avg) / (baseline_years + 1)
#    new_baseline_years = baseline_years + 1