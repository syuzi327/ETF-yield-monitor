"""
ETF配当利回り監視Bot（円建て）
"""

import os
import json
import yfinance as yf
import requests
from datetime import datetime, timedelta
from pathlib import Path
from config import ETFS, REMINDER_INTERVAL_DAYS, STATE_FILE


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
    """状態ファイルを読み込み"""
    state_path = Path(STATE_FILE)
    if state_path.exists():
        with open(state_path, "r", encoding="utf-8") as f:
            return json.load(f)
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
        threshold = config["threshold"]
        
        print(f"配当利回り: {current_yield}% (閾値: {threshold}%)")
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