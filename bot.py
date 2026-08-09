import telebot
import yfinance as yf
import pandas as pd
import re

TELEGRAM_BOT_TOKEN = "8650177978:AAF1skxO0zeQCwsq22p-YNqqWo_Eb0QpTp4"
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

STOCK_POOL = {
    "TATA STEEL": "TATASTEEL.NS",
    "IOC": "IOC.NS",
    "COAL INDIA": "COALINDIA.NS",
    "ITC": "ITC.NS",
    "TATA MOTORS": "TATAMOTORS.NS",
    "ONGC": "ONGC.NS",
    "BPCL": "BPCL.NS",
    "NTPC": "NTPC.NS",
    "POWERGRID": "POWERGRID.NS",
    "GAIL": "GAIL.NS",
    "FEDERAL BANK": "FEDERALBNK.NS",
    "ASHOK LEYLAND": "ASHOKLEY.NS",
    "HDFCBANK": "HDFCBANK.NS",
    "ICICIBANK": "ICICIBANK.NS",
    "SBIN": "SBIN.NS",
    "RELIANCE": "RELIANCE.NS",
    "INFY": "INFY.NS",
    "TCS": "TCS.NS",
    "AXISBANK": "AXISBANK.NS",
    "BHARTIARTL": "BHARTIARTL.NS",
    "LT": "LT.NS",
    "WIPRO": "WIPRO.NS",
    "HCLTECH": "HCLTECH.NS"
}

# Fix DataFrame multi-index issue in newer yfinance versions
def clean_df(df):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

# Handle Index (NIFTY & BANKNIFTY)
@bot.message_handler(func=lambda message: message.text and message.text.upper() in ['NIFTY', 'BANKNIFTY', 'NIFTY 50', 'BANK NIFTY'])
def handle_index(message):
    text = message.text.upper()
    ticker = "^NSEI" if "NIFTY" in text and "BANK" not in text else "^NSEBANK"
    index_name = "NIFTY 50" if ticker == "^NSEI" else "BANK NIFTY"
    
    bot.reply_to(message, f"⏳ **{index_name}** ka technical analysis calculate ho raha hai...")
    
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
            f"📊 **{index_name} Analysis**\n\n"
            f"🔹 **CMP:** ₹{latest_close:.2f} ({'+' if change >= 0 else ''}{change:.2f} | {p_change:.2f}%)\n"
            f"📈 **Day High:** ₹{high:.2f}\n"
            f"📉 **Day Low:** ₹{low:.2f}\n\n"
            f"🎯 **Pivot Levels:**\n"
            f"• **Resistance (R1):** ₹{r1:.2f}\n"
            f"• **Pivot Point:** ₹{pivot:.2f}\n"
            f"• **Support (S1):** ₹{s1:.2f}"
        )
        bot.reply_to(message, reply, parse_mode='Markdown')

    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

# Handle "under XXX" stock queries
@bot.message_handler(func=lambda message: message.text and "under" in message.text.lower())
def handle_under_stocks(message):
    match = re.search(r'\d+', message.text)
    if not match:
        bot.reply_to(message, "❌ Kripya amount specify karein (e.g. `under 500`)")
        return
        
    max_price = float(match.group())
    bot.reply_to(message, f"⏳ ₹{int(max_price)} ke niche waale stocks scan ho rahe hain...")
    
    found_stocks = []
    
    for name, symbol in STOCK_POOL.items():
        try:
            df = yf.download(symbol, period="5d", interval="1d", progress=False)
            if df.empty:
                continue
            
            df = clean_df(df)
            close = float(df['Close'].iloc[-1])
            
            if close <= max_price:
                high = float(df['High'].iloc[-1])
                low = float(df['Low'].iloc[-1])
                sl = round(close * 0.98, 2)
                target = round(close * 1.04, 2)
                found_stocks.append(f"📌 **{name}**\n• CMP: ₹{close:.2f}\n• Target: ₹{target}\n• SL: ₹{sl}\n")
        except:
            continue

    if found_stocks:
        response = f"🎯 **Stocks Under ₹{int(max_price)}:**\n\n" + "\n".join(found_stocks[:5])
        bot.reply_to(message, response, parse_mode='Markdown')
    else:
        bot.reply_to(message, f"❌ ₹{int(max_price)} ke niche koi stock nahi mila.")

print("🚀 Level-Based Target/SL Bot is running...")
bot.polling()
