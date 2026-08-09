import telebot
import yfinance as yf
import pandas as pd
import re

TELEGRAM_BOT_TOKEN = "8650177978:AAF0sf-wP3ZH5OcHCo0RAbiJRsIZlNp89e8"
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

STOCK_POOL = {
    "TATA STEEL": "TATASTEEL.NS",
    "IOC": "IOC.NS",
    "COAL INDIA": "COALINDIA.NS",
    "ITC": "ITC.NS",
    "TATA MOTORS": "TATAMOTORS.NS",
    "SBIN": "SBIN.NS",
    "AXIS BANK": "AXISBANK.NS",
    "ICICI BANK": "ICICIBANK.NS",
    "INFY": "INFY.NS",
    "RELIANCE": "RELIANCE.NS",
    "L&T": "LT.NS",
    "BAJFINANCE": "BAJFINANCE.NS",
    "MARUTI": "MARUTI.NS",
    "ULTRACEMCO": "ULTRACEMCO.NS",
    "TCS": "TCS.NS"
}

def calculate_indicators(symbol):
    df = yf.download(tickers=symbol, period="5d", interval="5m", progress=False)
    if df.empty:
        return None
    
    close_price = df['Close'].iloc[:, 0] if isinstance(df['Close'], pd.DataFrame) else df['Close']
    
    ema9 = close_price.ewm(span=9, adjust=False).mean()
    ema21 = close_price.ewm(span=21, adjust=False).mean()
    
    delta = close_price.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    return {
        'price': float(close_price.iloc[-1]),
        'ema9': float(ema9.iloc[-1]),
        'ema21': float(ema21.iloc[-1]),
        'rsi': float(rsi.iloc[-1])
    }

@bot.message_handler(func=lambda message: True)
def process_signal(message):
    text = message.text.upper().strip()
    
    numbers = re.findall(r'\d+', text)
    if "UNDER" in text or "BELOW" in text or numbers:
        if numbers and text not in ["NIFTY", "BANKNIFTY"]:
            max_price = float(numbers[0])
            bot.reply_to(message, f"⏳ ₹{max_price:.0f} ke niche waale stocks ka exact Buy/Target/SL levels calculate ho raha hai...")
            
            matching_stocks = []
            
            for name, ticker in STOCK_POOL.items():
                try:
                    data = calculate_indicators(ticker)
                    if data and data['price'] <= max_price:
                        matching_stocks.append((name, data))
                        if len(matching_stocks) == 5:
                            break
                except Exception:
                    continue
            
            if not matching_stocks:
                bot.send_message(message.chat.id, f"❌ ₹{max_price:.0f} ke niche koi stock nahi mila.")
                return

            report = f"🔥 **TOP STOCKS UNDER ₹{max_price:.0f} (WITH TARGET/SL)** 🔥\n─────────────────────────\n"
            for name, data in matching_stocks:
                price = data['price']
                rsi = data['rsi']
                ema9 = data['ema9']
                ema21 = data['ema21']
                
                # Dynamic SL & Target calculation (1.5% Risk-Reward)
                sl_val = round(price * 0.01, 2)       # 1% Stop Loss
                t1_val = round(price * 0.015, 2)     # 1.5% Target 1
                t2_val = round(price * 0.03, 2)      # 3% Target 2
                
                if ema9 > ema21 and rsi > 50:
                    action = "🟢 BUY"
                    entry = f"Around ₹{price:.2f}"
                    sl = f"₹{price - sl_val:.2f}"
                    targets = f"T1: ₹{price + t1_val:.2f} | T2: ₹{price + t2_val:.2f}"
                elif ema9 < ema21 and rsi < 50:
                    action = "🔴 SHORT SELL"
                    entry = f"Around ₹{price:.2f}"
                    sl = f"₹{price + sl_val:.2f}"
                    targets = f"T1: ₹{price - t1_val:.2f} | T2: ₹{price - t2_val:.2f}"
                else:
                    action = "🟡 SIDEWAYS (NO ENTRY)"
                    entry = "N/A"
                    sl = "N/A"
                    targets = "N/A"
                    
                report += f"📌 **{name}**\n• CMP: ₹{price:.2f}\n• Action: {action}\n• Entry: {entry}\n• SL: {sl}\n• Targets: {targets}\n─────────────────────────\n"
            
            bot.send_message(message.chat.id, report, parse_mode='Markdown')
            return

    if text == "BANKNIFTY":
        symbol = "^NSEBANK"
        step = 100
        sl_pts = 35
    elif text == "NIFTY":
        symbol = "^NSEI"
        step = 50
        sl_pts = 15
    else:
        bot.reply_to(message, "⚠️ Direct likhein: **under 400**, **under 1000**, **NIFTY**, ya **BANKNIFTY**")
        return

    try:
        data = calculate_indicators(symbol)
        if not data:
            bot.reply_to(message, "❌ Data fetch error.")
            return

        price = data['price']
        ema9 = data['ema9']
        ema21 = data['ema21']
        rsi = data['rsi']
        atm_strike = round(price / step) * step
        
        if ema9 > ema21 and rsi > 50:
            signal_type = "BUY CALL (CE)"
            instrument = f"{text} {atm_strike} CE"
            status = "🟢 BULLISH BREAKOUT"
        elif ema9 < ema21 and rsi < 50:
            signal_type = "BUY PUT (PE)"
            instrument = f"{text} {atm_strike} PE"
            status = "🔴 BEARISH BREAKDOWN"
        else:
            signal_type = "NO TRADE (SIDEWAYS)"
            instrument = "N/A"
            status = "🟡 NEUTRAL / CONSOLIDATION"

        reply = f"""
📊 **ACCURATE ALGO SIGNAL: {text}**
─────────────────────────
📍 **Spot Price:** {price:.2f}
📈 **Trend Status:** {status}
🎯 **Action:** {signal_type}
🏷️ **Suggested Instrument:** {instrument}
─────────────────────────
🔍 **Indicators Data:**
• **RSI (14):** {rsi:.1f}
• **EMA 9 vs 21:** {'Above' if ema9 > ema21 else 'Below'}
─────────────────────────
🛑 **SL:** {sl_pts} Points
🎯 **Target:** {sl_pts * 2} Points (1:2 RR)
"""
        bot.reply_to(message, reply, parse_mode='Markdown')
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

print("🚀 Level-Based Target/SL Bot is running...")
bot.polling()