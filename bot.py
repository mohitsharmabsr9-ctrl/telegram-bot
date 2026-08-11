import os
import re
import threading
import yfinance as yf
import pandas as pd
import telebot
from flask import Flask

# Flask web server for Render health checks
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = threading.Thread(target=run)
    t.start()

keep_alive()

# Telegram Bot Token
TELEGRAM_BOT_TOKEN = "8650177978:AAFwygvU4vmvU-h_ML3MoGrHJ9LcBzn1jBE"
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

def clean_df(df):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

# Reliable NSE Market Pool
NSE_TICKERS = [
    "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS",
    "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", "LTIM.NS", "LT.NS",
    "AXISBANK.NS", "KOTAKBANK.NS", "TATAMOTORS.NS", "TATASTEEL.NS",
    "HINDUNILVR.NS", "ADANIENT.NS", "ADANIPORTS.NS", "BAJFINANCE.NS",
    "POWERGRID.NS", "NTPC.NS", "COALINDIA.NS", "ONGC.NS", "IOC.NS",
    "BPCL.NS", "GAIL.NS", "NMDC.NS", "SAIL.NS", "BHEL.NS",
    "IRFC.NS", "RVNL.NS", "IRCON.NS", "HUDCO.NS", "NHPC.NS",
    "SJVN.NS", "SUZLON.NS", "YESBANK.NS", "IDEA.NS", "ZOMATO.NS",
    "JIOFIN.NS", "PAYTM.NS", "AWL.NS", "SOUTHBANK.NS", "UCOBANK.NS",
    "IOB.NS", "CENTRALBK.NS", "BANKBARODA.NS", "PNB.NS", "CANBK.NS"
]

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    help_text = (
        "🤖 *Trading Signal Bot Active!*\n\n"
        "📍 *Available Commands:*\n"
        "• Type `NIFTY` or `BANKNIFTY` -> Get Live Option Signal (CE/PE, Entry, TG, SL)\n"
        "• Type `under 100`, `under 500` -> Get Top Momentum Stocks"
    )
    bot.reply_to(message, help_text, parse_mode='Markdown')

# NIFTY & BANKNIFTY Signal Handler
@bot.message_handler(func=lambda m: m.text and m.text.upper() in ['NIFTY', 'BANKNIFTY'])
def handle_index(message):
    try:
        index_name = message.text.upper()
        symbol = "^NSEI" if index_name == "NIFTY" else "^NSEBANK"
        
        bot.reply_to(message, f"📊 Fetching Live Analysis for {index_name}...")
        
        df = yf.download(symbol, period="5d", interval="15m", progress=False)
        df = clean_df(df)
        
        if df.empty:
            bot.reply_to(message, "⚠️ Market data abhi available nahi hai.")
            return

        cmp = float(df['Close'].iloc[-1])
        
        if index_name == "NIFTY":
            atm = round(cmp / 50) * 50
            sl_pts, tg_pts = 30, 60
        else:
            atm = round(cmp / 100) * 100
            sl_pts, tg_pts = 70, 150

        ema9 = df['Close'].ewm(span=9).mean().iloc[-1]
        
        if cmp >= ema9:
            signal = "BUY CALL (CE)"
            strike = f"{atm} CE"
            target = cmp + tg_pts
            sl = cmp - sl_pts
        else:
            signal = "BUY PUT (PE)"
            strike = f"{atm} PE"
            target = cmp - tg_pts
            sl = cmp + sl_pts

        response = (
            f"🎯 *{index_name} OPTION TRADE SIGNAL*\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"📊 *Index CMP:* `{cmp:.2f}`\n"
            f"💡 *Signal:* *{signal}*\n"
            f"🎯 *Suggested Strike:* `{strike}`\n\n"
            f"📥 *Entry Zone:* `{cmp - 10:.2f} - {cmp + 10:.2f}`\n"
            f"🎯 *Target:* `{target:.2f}`\n"
            f"🛑 *Stop Loss:* `{sl:.2f}`\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ *Note:* For paper trading & educational purpose only."
        )
        bot.reply_to(message, response, parse_mode='Markdown')

    except Exception as e:
        bot.reply_to(message, f"❌ Error analyzing {message.text}: {str(e)}")

# Stocks Under Price Handler
@bot.message_handler(func=lambda message: message.text and re.search(r'under\s+\d+', message.text, re.IGNORECASE))
def handle_under_price(message):
    match = re.search(r'\d+', message.text)
    if not match:
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
