from flask import Flask, render_template, request
import yfinance as yf
from google import genai
from dotenv import load_dotenv
import os
load_dotenv()

api_key=os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY not found")

client = genai.Client(api_key=api_key)

def format_indian_currency(value):

    if value is None:
        return "N/A"

    lakh_crore = value / 1000000000000

    if lakh_crore >= 1:
        return f"₹{lakh_crore:.2f} Lakh Crore"

    crore = value / 10000000

    return f"₹{crore:,.2f} Crore"


def format_percentage(value):

    if value is None:
        return "N/A"

    return f"{value * 100:.2f}%"

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/analyze", methods=["POST"])
def analyze():

    symbol = (request.form["symbol"].upper().strip())

    try:

        stock = yf.Ticker(symbol)

        try:
            info = stock.info
        except Exception:
            return "Unable to fetch company data. Please try again."

        name = info.get("longName")

        if not name:
            return "Invalid Stock Symbol"

        market_cap_raw = info.get("marketCap")
        pe_ratio = info.get("trailingPE")
        cash_raw = info.get("totalCash")
        debt_raw = info.get("totalDebt")
        profit_margin_raw = info.get("profitMargins")
        revenue_growth = info.get("revenueGrowth")

        market_cap = format_indian_currency(market_cap_raw)
        cash = format_indian_currency(cash_raw)
        debt = format_indian_currency(debt_raw)
        profit_margin = format_percentage(profit_margin_raw)
        revenue_growth = format_percentage(revenue_growth)

        if pe_ratio:
            pe_ratio = round(pe_ratio, 2)

        risk_score = 0

        if debt_raw and cash_raw:

            if debt_raw > cash_raw:
                risk_score += 4

        if pe_ratio and pe_ratio > 40:
            risk_score += 2

        if profit_margin_raw and profit_margin_raw < 0.10:
            risk_score += 2

        if market_cap_raw and market_cap_raw < 100000000000:
            risk_score += 1

        risk_score = min(risk_score, 10)

        reward_score = 10 - risk_score

        prompt = f"""
You are a beginner-friendly financial analyst.

Analyze the company using simple language.

Company: {name}

Market Cap: {market_cap}
PE Ratio: {pe_ratio}
Cash: {cash}
Debt: {debt}
Profit Margin: {profit_margin}

Risk Score: {risk_score}/10
Reward Score: {reward_score}/10

Rules:
- Do NOT use markdown.
- Do NOT use EMOJIS
- Do NOT use asterisks (*).
- Do NOT use bold text.
- Keep the response under 150 words.
- Use simple English.
- Explain things like talking to a beginner.
- Use short bullet points with • only.

Format:

📌 COMPANY OVERVIEW
(1-2 sentences)

💪 STRENGTHS
• Point 1
• Point 2
• Point 3

⚠️ RISKS
• Point 1
• Point 2

🎯 RISK & REWARD
(1-2 sentences)

✅ FINAL VERDICT
(2 short sentences)
"""
    
        try:

            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )

            ai_analysis = '\n' + response.text

        except Exception as e:

            import traceback
            traceback.print_exc()

            ai_analysis = f"Gemini Error: {e}"

        return render_template(
            "result.html",
            name=name,
            market_cap=market_cap,
            pe_ratio=pe_ratio,
            cash=cash,
            debt=debt,
            profit_margin=profit_margin,
            risk_score=risk_score,
            reward_score=reward_score,
            revenue_growth=revenue_growth,
            ai_analysis=ai_analysis
        )

    except Exception as e:

        return f"Error: {e}"
    

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000))
    )