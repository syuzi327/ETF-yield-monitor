"""
ETF配当利回り監視Bot（円建て）
"""

import os
import json
import yfinance as yf
import requests
from datetime import datetime, timedelta
from pathlib import Path
from config import ETFS, REMINDER_INTERVAL_DAYS, STATE_FILE, AVERAGE_TRADING_DAYS_PER_YEAR


def get_etf_data(ticker):
    """ETFの配当利回りと価格を取得"""
    try:
        etf = yf.Ticker(ticker)
        info = etf.info
        
        # 配当利回り（%）
        dividend_yield = info.get("dividendYield", 0) * 100 if info.get("dividendYield") else 0
        
        # 現在価格（USD）
        current_price = info.get("currentPrice") or info.get("regularMarketPrice", 0)
        
        # 配当額（USD）
        dividend_rate = info.get("dividendRate", 0)
        
        # 最新の価格データの日付を取得（取引日判定用）
        history = etf.history(period="1d")
        if not history.empty:
            last_trade_date = history.index[-1].date().isoformat()
        else:
            last_trade_date = None
        
        return {
            "yield": round(dividend_yield, 2),
            "price_usd": round(current_price, 2),
            "dividend_usd": round(dividend_rate, 2),
            "last_trade_date": last_trade_date,
        }
    except Exception as e:
        print(f"{ticker} データ取得エラー: {e}")
        return None


def get_year_to_date_average(ticker, year, start_date=None):
    """
    年初来（または指定期間）の平均配当利回りを取得
    
    Args:
        ticker: ETFティッカーシンボル
        year: 対象年
        start_date: 開始日（指定しない場合は年初から）
    """
    try:
        from datetime import datetime
        
        etf = yf.Ticker(ticker)
        
        if start_date:
            start = start_date
        else:
            start = f"{year}-01-01"
        
        end_date = datetime.now().strftime("%Y-%m-%d")
        
        print(f"  📊 {year}年のデータを取得中... ({start} ～ {end_date})")
        
        # 履歴データ取得
        history = etf.history(start=start, end=end_date)
        
        if history.empty:
            print(f"  ⚠️ データ取得失敗、当日の利回りを使用")
            return None
        
        # 配当利回りを計算（配当額 / 株価）
        info = etf.info
        current_dividend = info.get("dividendRate", 0)
        
        if current_dividend > 0:
            # 各日の株価に対する配当利回りを計算
            yields = (current_dividend / history["Close"]) * 100
            avg_yield = yields.mean()
            trading_days = len(history)
            
            print(f"  ✅ 取得完了: 平均利回り {avg_yield:.2f}%, 取引日数 {trading_days}日")
            return {
                "avg_yield": round(avg_yield, 2),
                "trading_days": trading_days
            }
        else:
            print(f"  ⚠️ 配当データなし、当日の利回りを使用")
            return None
            
    except Exception as e:
        print(f"  ⚠️ データ取得エラー: {e}")
        return None


def backfill_missing_years(ticker, last_year, current_year, baseline_years, baseline_yield):
    """
    欠落した年度のデータを遡って補完
    
    Args:
        ticker: ETFティッカーシンボル
        last_year: 最後に記録された年
        current_year: 現在の年
        baseline_years: 現在のbaseline年数
        baseline_yield: 現在のbaseline利回り
    
    Returns:
        dict: 更新後のbaseline情報
    """
    print(f"  🔄 欠落データの補完を開始...")
    
    updated_baseline_years = baseline_years
    updated_baseline_yield = baseline_yield
    
    # 欠落した年を順番に処理
    for year in range(last_year + 1, current_year):
        print(f"  📅 {year}年のデータを補完中...")
        
        ytd_data = get_year_to_date_average(ticker, year)
        
        if ytd_data:
            year_avg = ytd_data["avg_yield"]
            # baselineを更新
            updated_baseline_yield = (updated_baseline_yield * updated_baseline_years + year_avg) / (updated_baseline_years + 1)
            updated_baseline_years += 1
            print(f"  ✅ {year}年: 平均 {year_avg:.2f}% → Baseline更新: {updated_baseline_yield:.2f}% ({updated_baseline_years}年)")
        else:
            print(f"  ⚠️ {year}年: データ取得失敗 - スキップ")
    
    return {
        "years": updated_baseline_years,
        "yield": round(updated_baseline_yield, 2)
    }


def calculate_dynamic_threshold(ticker, current_yield, etf_data, config, state):
    """
    加重平均方式で動的閾値を計算
    
    計算式:
    1. 今年の平均 = (前回平均 × 経過日数 + 今日の利回り) / (経過日数 + 1)
    2. 累積平均 = (baseline_yield × baseline_years + 今年の平均) / (baseline_years + 1)
    3. 閾値 = 累積平均 + offset
    """
    from datetime import datetime
    
    today = datetime.now().date()
    current_year = config["current_year"]
    threshold_offset = config["threshold_offset"]
    last_trade_date = etf_data.get("last_trade_date")
    
    # state.jsonからbaselineを取得（更新済みの値を優先）
    if ticker in state and "baseline" in state[ticker]:
        baseline_years = state[ticker]["baseline"]["years"]
        baseline_yield = state[ticker]["baseline"]["yield"]
    else:
        # 初回はconfigから取得
        baseline_years = config["baseline_years"]
        baseline_yield = config["baseline_yield"]
    
    # state.jsonから今年のデータを取得
    if ticker in state and "year_data" in state[ticker]:
        year_data = state[ticker]["year_data"]
        year_avg = year_data.get("year_avg", current_yield)
        year_days = year_data.get("year_days", 0)
        tracked_year = year_data.get("year", current_year)
        last_update_date = state[ticker].get("last_trade_date")
        
        # 取引日チェック: 前回と同じ日付なら更新しない（土日・祝日対策）
        if last_trade_date and last_trade_date == last_update_date:
            print(f"  💤 取引なし（前回: {last_update_date}）- データ更新スキップ")
            # 取引日数ベースで累積平均計算
            baseline_days = baseline_years * AVERAGE_TRADING_DAYS_PER_YEAR
            total_days = baseline_days + year_days
            cumulative_avg = (baseline_yield * baseline_days + year_avg * year_days) / total_days
            return {
                "threshold": round(cumulative_avg + threshold_offset, 2),
                "cumulative_avg": round(cumulative_avg, 2),
                "year_avg": round(year_avg, 2),
                "year_days": year_days,
                "year": current_year,
                "baseline_years": baseline_years,
                "baseline_yield": baseline_yield,
                "updated": False,
            }
        
        # 年が変わった場合（複数年飛ばした場合も対応）
        if tracked_year < current_year:
            years_gap = current_year - tracked_year
            print(f"  🎊 新年度移行: {tracked_year} → {current_year} ({years_gap}年分)")
            
            # 前年のデータで baseline を更新
            new_baseline_yield = (baseline_yield * baseline_years + year_avg) / (baseline_years + 1)
            new_baseline_years = baseline_years + 1
            
            print(f"  📊 {tracked_year}年で更新: {baseline_yield:.2f}% ({baseline_years}年) → {new_baseline_yield:.2f}% ({new_baseline_years}年)")
            
            baseline_years = new_baseline_years
            baseline_yield = new_baseline_yield
            
            # 複数年飛ばした場合は欠落データを補完
            if years_gap > 1:
                print(f"  ⚠️ {years_gap - 1}年分のデータが欠落 → 自動補完を試行")
                backfilled = backfill_missing_years(ticker, tracked_year, current_year, baseline_years, baseline_yield)
                baseline_years = backfilled["years"]
                baseline_yield = backfilled["yield"]
            
            # 新年度の年初来データを取得
            ytd_data = get_year_to_date_average(ticker, current_year)
            if ytd_data:
                year_avg = ytd_data["avg_yield"]
                year_days = ytd_data["trading_days"]
            else:
                year_avg = current_yield
                year_days = 1
        else:
            # 同じ年内での更新
            # 欠落期間チェック（年度途中で長期間停止していた場合）
            if year_days > 0:
                # 前回のチェック日から今日までの期間を確認
                from datetime import datetime
                last_checked = state[ticker].get("last_checked")
                if last_checked:
                    last_date = datetime.fromisoformat(last_checked).date()
                    today_date = datetime.now().date()
                    days_gap = (today_date - last_date).days
                    
                    # 7日以上空いていたら欠落データを補完
                    if days_gap > 7:
                        print(f"  ⚠️ {days_gap}日間のデータ欠落を検知 → 補完を試行")
                        
                        # 欠落期間のデータを取得
                        gap_start = (last_date + timedelta(days=1)).isoformat()
                        gap_data = get_year_to_date_average(ticker, current_year, start_date=gap_start)
                        
                        if gap_data:
                            # 欠落期間の平均と既存の平均を統合
                            total_days = year_days + gap_data["trading_days"]
                            year_avg = (year_avg * year_days + gap_data["avg_yield"] * gap_data["trading_days"]) / total_days
                            year_days = total_days
                            print(f"  ✅ 補完完了: {gap_data['trading_days']}取引日分を追加")
            
            # 今年の平均を更新（加重平均）
            year_avg = (year_avg * year_days + current_yield) / (year_days + 1)
            year_days += 1
    else:
        # 初回実行: 年初来の平均を取得
        print(f"  🆕 初回実行 - 年初来データを取得します")
        ytd_data = get_year_to_date_average(ticker, current_year)
        
        if ytd_data:
            year_avg = ytd_data["avg_yield"]
            year_days = ytd_data["trading_days"]
        else:
            # 年初来データ取得失敗時は当日のみ
            year_avg = current_yield
            year_days = 1
    
    # 累積平均を計算（取引日数ベース）
    baseline_days = baseline_years * AVERAGE_TRADING_DAYS_PER_YEAR
    total_days = baseline_days + year_days
    cumulative_avg = (baseline_yield * baseline_days + year_avg * year_days) / total_days
    
    # 動的閾値
    dynamic_threshold = cumulative_avg + threshold_offset
    
    return {
        "threshold": round(dynamic_threshold, 2),
        "cumulative_avg": round(cumulative_avg, 2),
        "year_avg": round(year_avg, 2),
        "year_days": year_days,
        "year": current_year,
        "baseline_years": baseline_years,  # 更新後の値を返す
        "baseline_yield": round(baseline_yield, 2),  # 更新後の値を返す
        "updated": True,
    }


def get_exchange_rate():
    """USD/JPY為替レートを取得"""
    try:
        usdjpy = yf.Ticker("USDJPY=X")
        rate = usdjpy.history(period="1d")["Close"].iloc[-1]
        return round(rate, 2)
    except Exception as e:
        print(f"為替レート取得エラー: {e}")
        return None


def get_etf_data(ticker):
    """ETFの配当利回りと価格を取得"""
    try:
        etf = yf.Ticker(ticker)
        info = etf.info
        
        # 配当利回り（%）
        dividend_yield = info.get("dividendYield", 0) * 100 if info.get("dividendYield") else 0
        
        # 現在価格（USD）
        current_price = info.get("currentPrice") or info.get("regularMarketPrice", 0)
        
        # 配当額（USD）
        dividend_rate = info.get("dividendRate", 0)
        
        return {
            "yield": round(dividend_yield, 2),
            "price_usd": round(current_price, 2),
            "dividend_usd": round(dividend_rate, 2),
        }
    except Exception as e:
        print(f"{ticker} データ取得エラー: {e}")
        return None


def load_state():
    """状態ファイルを読み込み（エラー保護付き）"""
    state_path = Path(STATE_FILE)
    if state_path.exists():
        try:
            with open(state_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            print(f"⚠️ state.jsonが壊れています: {e}")
            print(f"   バックアップを作成して初期化します...")
            
            # 壊れたファイルをバックアップ
            backup_path = state_path.with_suffix(".json.backup")
            import shutil
            shutil.copy(state_path, backup_path)
            print(f"   バックアップ: {backup_path}")
            
            # 空の状態で初期化
            return {}
        except Exception as e:
            print(f"⚠️ state.json読み込みエラー: {e}")
            return {}
    return {}


def save_state(state):
    """状態ファイルを保存"""
    state_path = Path(STATE_FILE)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def should_notify(ticker, current_yield, threshold, state):
    """
    通知すべきかを判定
    
    Returns:
        tuple: (should_notify: bool, notification_type: str, reason: str)
    """
    today = datetime.now().date().isoformat()
    
    # 初回実行
    if ticker not in state:
        return False, "initial", "初回実行"
    
    prev_state = state[ticker]
    prev_status = prev_state.get("status", "below")
    prev_yield = prev_state.get("current_yield", 0)
    prev_threshold = prev_state.get("threshold", threshold)
    last_notified = prev_state.get("last_notified")
    last_reminded = prev_state.get("last_reminded")
    
    # 閾値変更検知
    threshold_changed = prev_threshold != threshold
    
    if threshold_changed:
        print(f"⚠️ 閾値変更検知: {prev_threshold}% → {threshold}%")
        
        # 閾値変更後の状態を再評価
        # 前回: below, 今回: above → 上抜け通知
        if prev_status == "below" and current_yield >= threshold:
            return True, "crossed_above", f"閾値変更後の上抜け: {current_yield}% (閾値: {prev_threshold}%→{threshold}%)"
        
        # 前回: above, 今回: below → 下抜け通知
        if prev_status == "above" and current_yield < threshold:
            return True, "crossed_below", f"閾値変更後の下抜け: {current_yield}% (閾値: {prev_threshold}%→{threshold}%)"
        
        # 両方above or 両方below → 状態維持、通知なし
        # ただし、aboveのままなら次回週次リマインダーがリセットされる
        return False, "threshold_changed", f"閾値変更（状態維持）: {prev_threshold}%→{threshold}%"
    
    # 通常の上抜け検知
    if prev_status == "below" and current_yield >= threshold:
        return True, "crossed_above", f"閾値上抜け: {prev_yield}% → {current_yield}%"
    
    # 通常の下抜け検知
    if prev_status == "above" and current_yield < threshold:
        return True, "crossed_below", f"閾値下抜け: {prev_yield}% → {current_yield}%"
    
    # 閾値超過中の週次リマインダー
    if prev_status == "above" and current_yield >= threshold:
        if last_reminded:
            last_reminded_date = datetime.fromisoformat(last_reminded).date()
            days_since_reminder = (datetime.now().date() - last_reminded_date).days
            
            if days_since_reminder >= REMINDER_INTERVAL_DAYS:
                return True, "reminder", f"週次リマインダー（継続{days_since_reminder}日目）"
    
    return False, None, "通知不要"


def create_discord_embed(notification_type, ticker, etf_data, exchange_rate, threshold, reason):
    """Discord埋め込みメッセージを作成"""
    
    # 色の設定
    color_map = {
        "crossed_above": 0x00FF00,  # 緑（上抜け）
        "crossed_below": 0xFF0000,  # 赤（下抜け）
        "reminder": 0xFFFF00,       # 黄（リマインダー）
    }
    
    # タイトルの設定
    title_map = {
        "crossed_above": "🚀 利回り閾値上抜け！",
        "crossed_below": "📉 利回り閾値下抜け",
        "reminder": "📌 週次リマインダー",
    }
    
    etf_name = ETFS[ticker]["name"]
    price_jpy = round(etf_data["price_usd"] * exchange_rate, 2)
    dividend_jpy = round(etf_data["dividend_usd"] * exchange_rate, 2)
    
    embed = {
        "title": f"{title_map[notification_type]} - {ticker}",
        "description": f"**{etf_name}**",
        "color": color_map[notification_type],
        "fields": [
            {
                "name": "📊 配当利回り",
                "value": f"**{etf_data['yield']}%**",
                "inline": True
            },
            {
                "name": "🎯 閾値",
                "value": f"{threshold}%",
                "inline": True
            },
            {
                "name": "💵 現在価格（USD）",
                "value": f"${etf_data['price_usd']}",
                "inline": True
            },
            {
                "name": "💴 現在価格（JPY）",
                "value": f"¥{price_jpy:,.0f}",
                "inline": True
            },
            {
                "name": "💰 年間配当（USD）",
                "value": f"${etf_data['dividend_usd']}",
                "inline": True
            },
            {
                "name": "💰 年間配当（JPY）",
                "value": f"¥{dividend_jpy:,.0f}",
                "inline": True
            },
            {
                "name": "🌐 為替レート",
                "value": f"1 USD = ¥{exchange_rate}",
                "inline": False
            },
            {
                "name": "📝 詳細",
                "value": reason,
                "inline": False
            }
        ],
        "timestamp": datetime.now().isoformat(),
        "footer": {
            "text": "ETF利回り監視Bot"
        }
    }
    
    return embed


def send_discord_notification(embed):
    """Discord Webhookで通知を送信"""
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    
    if not webhook_url:
        print("⚠️ DISCORD_WEBHOOK_URL が設定されていません")
        return False
    
    payload = {
        "embeds": [embed]
    }
    
    try:
        response = requests.post(webhook_url, json=payload)
        response.raise_for_status()
        print("✅ Discord通知送信成功")
        return True
    except Exception as e:
        print(f"❌ Discord通知送信失敗: {e}")
        return False


def main():
    """メイン処理"""
    print(f"=== ETF利回り監視開始: {datetime.now()} ===\n")
    
    # 為替レート取得
    exchange_rate = get_exchange_rate()
    if not exchange_rate:
        print("❌ 為替レート取得失敗。処理を中断します。")
        return
    
    print(f"💱 USD/JPY: ¥{exchange_rate}\n")
    
    # 状態ファイル読み込み
    state = load_state()
    
    # 各ETFを監視
    for ticker, config in ETFS.items():
        print(f"--- {ticker} ({config['name']}) ---")
        
        # ETFデータ取得
        etf_data = get_etf_data(ticker)
        if not etf_data:
            print(f"⚠️ {ticker} のデータ取得失敗\n")
            continue
        
        current_yield = etf_data["yield"]
        last_trade_date = etf_data.get("last_trade_date")
        
        # 動的閾値を計算
        threshold_data = calculate_dynamic_threshold(ticker, current_yield, etf_data, config, state)
        threshold = threshold_data["threshold"]
        cumulative_avg = threshold_data["cumulative_avg"]
        year_avg = threshold_data["year_avg"]
        
        # データが更新されなかった場合（土日・祝日）
        if not threshold_data.get("updated", True):
            print(f"閾値: {threshold}% (前回から変更なし)\n")
            continue
        
        print(f"配当利回り: {current_yield}%")
        print(f"今年平均: {year_avg}% ({threshold_data['year_days']}取引日)")
        print(f"累積平均: {cumulative_avg}% (閾値: {threshold}%)")
        print(f"価格: ${etf_data['price_usd']} (¥{etf_data['price_usd'] * exchange_rate:,.0f})")
        
        # 通知判定
        should_send, notification_type, reason = should_notify(
            ticker, current_yield, threshold, state
        )
        
        print(f"判定: {reason}")
        
        if should_send:
            # Discord通知送信
            embed = create_discord_embed(
                notification_type, ticker, etf_data, exchange_rate, threshold, reason
            )
            send_discord_notification(embed)
        
        # 状態更新
        today = datetime.now().date().isoformat()
        
        # 現在のステータス判定
        new_status = "above" if current_yield >= threshold else "below"
        
        # 状態オブジェクト作成
        new_state = {
            "status": new_status,
            "current_yield": current_yield,
            "threshold": threshold,
            "cumulative_avg": cumulative_avg,
            "last_trade_date": last_trade_date,  # 取引日を保存
            "baseline": {  # baseline情報を永続化
                "years": threshold_data["baseline_years"],
                "yield": threshold_data["baseline_yield"],
            },
            "year_data": {
                "year": threshold_data["year"],
                "year_avg": year_avg,
                "year_days": threshold_data["year_days"],
            },
            "last_checked": today,
        }
        
        # 前回の状態を引き継ぐ
        if ticker in state:
            prev_state = state[ticker]
            new_state["last_notified"] = prev_state.get("last_notified")
            new_state["last_reminded"] = prev_state.get("last_reminded")
            new_state["crossed_above_date"] = prev_state.get("crossed_above_date")
        
        # 通知を送った場合の更新
        if should_send:
            new_state["last_notified"] = today
            
            if notification_type == "crossed_above":
                new_state["crossed_above_date"] = today
                new_state["last_reminded"] = today
            elif notification_type == "reminder":
                new_state["last_reminded"] = today
            elif notification_type == "crossed_below":
                new_state["crossed_above_date"] = None
                new_state["last_reminded"] = None
        
        # 閾値変更時の特別処理
        if notification_type == "threshold_changed":
            # 閾値が変更されたが通知は不要な場合
            # above状態が維持される場合は、週次リマインダーをリセット
            if new_status == "above":
                new_state["last_reminded"] = today  # 週次カウンターをリセット
        
        state[ticker] = new_state
        print()
    
    # 状態保存
    save_state(state)
    print("=== 監視完了 ===")


if __name__ == "__main__":
    main()