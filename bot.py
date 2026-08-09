import telebot
import yfinance as yf
import pandas as pd
import requests
import re
import os
from flask import Flask
import threading

# Flask Keep-Alive Server
app = Flask('')

@app.route('/')
def home():
    return "Dynamic NSE Market Screener Bot is Active!"

def run():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = threading.Thread(target=run)
    t.start()

keep_alive()

# Telegram Bot Token (Render Environment Variable)
TELEGRAM_BOT_TOKEN = os.environ.get("8650177978:AAHDCRG6yWFgcv_C8ne_tPP1gLHLYAKsb9U")
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

def clean_df(df):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

# Reliable NSE Market Pool
NSE_TICKERS = [
    # Under ₹100 / Low Cap
    "YESBANK.NS", "SUZLON.NS", "IDFCFIRSTB.NS", "SOUTHBANK.NS", "UCOBANK.NS",
    "IOB.NS", "NHPC.NS", "IRFC.NS", "HUDCO.NS", "SJVN.NS", "SWSOLAR.NS",
    "PNB.NS", "IDEA.NS", "ZOMATO.NS", "JIOFIN.NS", "IOC.NS", "TATASTEEL.NS",
    # Mid & Large Cap
    "TATAMOTORS.NS", "RELIANCE.NS", "HDFCBANK.NS", "INFY.NS", "SBIN.NS",
    "ICICIBANK.NS", "ITC.NS", "COALINDIA.NS", "ONGC.NS", "BPCL.NS",
    "NTPC.NS", "POWERGRID.NS", "GAIL.NS", "FEDERALBNK.NS", "ASHOKLEY.NS",
    "TCS.NS", "BHARTIARTL.NS", "AXISBANK.NS", "WIPRO.NS", "LT.NS"
]

@bot.message_handler(func=lambda message: message.text and message.text.upper() in ['NIFTY', 'BANKNIFTY', 'NIFTY 50', 'BANK NIFTY'])
def handle_index(message):
    text = message.text.upper()
    ticker = "^NSEI" if "NIFTY" in text and "BANK" not in text else "^NSEBANK"
    index_name = "NIFTY 50" if ticker == "^NSEI" else "BANK NIFTY"
    
    bot.reply_to(message, f"⏳ **{index_name}** live analysis loading...")
    
    try:
        data = yf.download(ticker, period="5d", interval="1d", progress=False)
        if data.empty:
            bot.reply_to(message, f"❌ {index_name} ka data fetch nahi ho paya.")
            return

        data = clean_df(data)
        latest_close = float(data['Close'].iloc[-1])
        prev_close = float(data['Close'].iloc[-2]) if len(data) > 1 else latest_close
        change = latest_close - prev_close
        p_change = (change / prev_close) * 100

        high = float(data['High'].iloc[-1])
        low = float(data['Low'].iloc[-1])
        
        pivot = (high + low + latest_close) / 3
        r1 = (2 * pivot) - low
        s1 = (2 * pivot) - high

        reply = (
            f"📊 **{index_name} Technical Levels**\n\n"
            f"🔹 **CMP:** ₹{latest_close:.2f} ({'+' if change >= 0 else ''}{change:.2f} | {p_change:.2f}%)\n"
            f"📈 **Day High:** ₹{high:.2f}\n"
            f"📉 **Day Low:** ₹{low:.2f}\n\n"
            f"🎯 **Pivot Points:**\n"
            f"• **Resistance (R1):** ₹{r1:.2f}\n"
            f"• **Pivot Level:** ₹{pivot:.2f}\n"
            f"• **Support (S1):** ₹{s1:.2f}"
        )
        bot.reply_to(message, reply, parse_mode='Markdown')

    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.message_handler(func=lambda message: message.text and "under" in message.text.lower())
def handle_under_stocks(message):
    match = re.search(r'\d+', message.text)
    if not match:
        bot.reply_to(message, "❌ Format: `under 100` ya `under 500` bhein.")
        return
        
    max_price = float(match.group())
    bot.reply_to(message, f"🔍 Scanning Market for Best Stocks under ₹{int(max_price)}... (Please wait 3-5 seconds)")
    
    try:
        batch_data = yf.download(NSE_TICKERS, period="5d", interval="1d", group_by='ticker', progress=False)
        candidates = []
        
        for symbol in NSE_TICKERS:
            try:
                df = batch_data[symbol] if len(NSE_TICKERS) > 1 else batch_data
                df = df.dropna()
                if len(df) < 2:
                    continue
                
                df = clean_df(df)
                close = float(df['Close'].iloc[-1])
                prev_close = float(df['Close'].iloc[-2])
                
                if close <= max_price and close >= 2:
                    pct_change = ((close - prev_close) / prev_close) * 100
                    clean_symbol = symbol.replace('.NS', '')
                    
                    candidates.append({
                        'symbol': clean_symbol,
                        'price': close,
                        'change': pct_change
                    })
            except:
                continue

        if candidates:
            candidates.sort(key=lambda x: x['change'], reverse=True)
            top_5 = candidates[:5]
            
            response = f"🌟 **Top 5 Best Momentum Stocks Under ₹{int(max_price)}**\n\n"
            
            for index, stock in enumerate(top_5, 1):
                sym = stock['symbol']
                price = stock['price']
                chg = stock['change']
                
                sl = round(price * 0.97, 2)
                target = round(price * 1.06, 2)
                
                response += (
                    f"**{index}. {sym}**\n"
                    f"• **CMP:** ₹{price:.2f} ({'+' if chg >= 0 else ''}{chg:.2f}%)\n"
                    f"• **Target:** ₹{target}\n"
                    f"• **Stop Loss:** ₹{sl}\n\n"
                )
                
            bot.reply_to(message, response, parse_mode='Markdown')
        else:
            bot.reply_to(message, f"❌ ₹{int(max_price)} ke niche koi active stock nahi mila.")

    except Exception as e:
        bot.reply_to(message, f"❌ Scanning Error: {str(e)}")

print("🚀 Bot is running...")
bot.polling()
