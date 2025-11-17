"""
ETF監視Bot設定ファイル（最終版）

ロジック:
- 閾値 = baseline_yield + threshold_offset（年度内固定）
- baseline更新は年越し初回実行時に自動実行（前年の実績を計算して反映）
- 前年の利回り = その年の分配金総額 ÷ 年末の株価
- 欠落期間がある場合は自動補完
"""

# 監視対象ETF
ETFS = {
    "VYM": {
        "name": "Vanguard High Dividend Yield ETF",
        "inception_date": "2006-11-10",
        "baseline_years": 18,     # 2007-2024年
        "baseline_yield": 3.03,   # 2007-2024年の平均利回り（%）
        "threshold_offset": 0.0,  # baseline + 0.0%で通知
        "current_year": 2025,
    },
    "HDV": {
        "name": "iShares Core High Dividend ETF",
        "inception_date": "2011-03-29",
        "baseline_years": 14,     # 2011-2024年
        "baseline_yield": 3.55,
        "threshold_offset": 0.0,
        "current_year": 2025,
    },
    "SPYD": {
        "name": "SPDR Portfolio S&P 500 High Dividend ETF",
        "inception_date": "2015-10-21",
        "baseline_years": 9,      # 2016-2024年
        "baseline_yield": 4.58,
        "threshold_offset": 0.0,
        "current_year": 2025,
    },
    "SCHD": {
        "name": "Schwab U.S. Dividend Equity ETF",
        "inception_date": "2011-10-20",
        "baseline_years": 14,     # 2011-2024年
        "baseline_yield": 3.50,
        "threshold_offset": 0.0,
        "current_year": 2025,
    },
}

# 週次リマインダー間隔（日数）
REMINDER_INTERVAL_DAYS = 7

# データファイルパス
STATE_FILE = "data/state.json"

# Discord Webhook URL（環境変数から取得）
# GitHub Actionsで DISCORD_WEBHOOK_URL をSecretに設定すること

# === 最終版の仕組み ===
#
# 1. 毎日の動作
#    - TTM方式で信頼性の高い利回りを取得
#    - 閾値は年度内固定（baseline + offset）
#    - 年の途中では統計計算なし
#
# 2. 年度更新時（自動）
#    - 前年のデータを実データから計算
#      前年利回り = その年の分配金総額 ÷ 年末株価
#    - new_baseline = (baseline × years + 前年利回り) / (years + 1)
#    - 更新後のbaselineはstate.jsonに保存され、以降使用される
#
# 3. 欠落期間の自動補完
#    - 複数年飛ばした場合、過去データを取得して順次反映
#    - 例: 2023年に停止 → 2026年に再開
#      → 2024年と2025年のデータを自動取得してbaseline更新
#
# 4. 年換算方式の問題を完全排除
#    - 年の途中でyear_avgを計算しない
#    - 年越し時に「分配金総額÷年末株価」で計算
#    - 初回起動タイミングの影響なし、常に正確