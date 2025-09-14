#!/usr/bin/env python3
"""
Script file for long market analysis content
"""

MARKET_SCRIPT = """ABB India ABB as on September 14, 2025 — Sentiment: Positive. 
ABB India, a leading engineering company, has recently announced strong performance in financial results and secured a significant order worth Rs 173 crore to supply wind converters for projects scheduled in 2026. The company also celebrated its 30th year on the National Stock Exchange (NSE), marking an impressive 8,500% total shareholder return (TSR) growth. ABB's recent board meeting, planned for November 2025, will consider unaudited results for the quarter ended September 30, but market analysts have commented positively on its growth trajectory and operational expansion. Despite minor regulatory hurdles—a customs fine that is not expected to impact results—ABB continues to establish itself as an innovative leader in India's electrical engineering sector, positioning well for future growth.
— pause —

Adani Power ADANIPOWER as on September 14, 2025 — Sentiment: Positive. 
Adani Power, India's largest private thermal power producer, signed a 25-year Power Supply Agreement (PSA) with the Bihar government to deliver 2,400 megawatts (MW) from a new ultra supercritical power plant in Bhagalpur. The project, valued at 3 billion United States Dollars (USD), will be executed under the Design, Build, Finance, Own, and Operate (DBFOO) model. The plant aims to create thousands of direct and indirect jobs over the next five years and will help Bihar receive steady, affordable electricity. This positive development has been welcomed by both stakeholders and market analysts, signaling growth and technology expansion for Adani Power—especially as India works toward becoming a power-surplus nation.
— pause —

Persistent Systems PERSISTENT as on September 14, 2025 — Sentiment: Positive. 
Persistent Systems, an information technology company, saw its shares surge more than 5% this week due to strong financials and growing profits. For the most recent quarter, the company reported consolidated revenue of Rs 3,334 crore and continuing profit growth. Persistent's annual earnings also showed remarkable improvement, with net profit rising to Rs 1,400 crore and earnings per share (EPS) increasing to Rs 91.22. The company has little to no debt, and its management has engaged with investors and analysts this week regarding future prospects. This consistently strong financial performance, combined with positive investor sentiment, reflects Persistent Systems' ability to grow within the competitive IT services industry.
— pause —

Oil India Limited OIL as on September 14, 2025 — Sentiment: Neutral. 
Oil India Limited, a public sector oil and gas company, announced September 4 as the record date for a final dividend of Rs 1.50 per share, bringing the yearly payout to Rs 11.5 per share. Although the company's profit for the June 2025 quarter jumped by 44% to Rs 1,896 crore, revenue dropped 10% compared to last quarter. Operating margins also narrowed due to increased costs and weaker sales. Oil India will hold its Annual General Meeting (AGM) on September 18 through video conferencing and OAVM (other audio visual means). The news sentiment remains neutral overall, with mixed signals from profit increase but lower revenue and margins.
— pause —

PNB Housing Finance PNBHOUSING as on September 14, 2025 — Sentiment: Positive. 
PNB Housing Finance, which offers home loans and is registered with the National Housing Bank (NHB), reported a strong jump in net profit—rising 23% year-over-year to Rs 534 crore for the June 2025 quarter. Its net interest income and margins saw healthy growth, and gross non-performing assets (GNPA) improved to 1.06%, a sign of better loan quality. The company's board has approved raising up to Rs 5,000 crore through non-convertible debentures (NCDs), which are corporate bonds not exchangeable for shares. This move is intended to fuel future growth, and most financial analysts view it as encouraging for both investors and customers.
— pause —

Ksolves India KSOLVES as on September 14, 2025 — Sentiment: Positive. 
Ksolves India, a small-cap technology company and Salesforce consulting firm, reported strong financials for the June quarter. Revenue grew nearly 20% year-over-year and 13% from last quarter, while profit after tax (PAT) increased almost 10% quarter-over-quarter. The company declared its first interim dividend for this financial year and continues to be recognized for corporate governance and client service. Ksolves was recently nominated for the Odoo Best Partner India 2025 Award, highlighting its focus on software solutions and consulting for big data and artificial intelligence (AI). Management's positive message suggests continued growth, attracting investor interest and positive coverage in technology news."""

if __name__ == "__main__":
    print(f"Market Script Length: {len(MARKET_SCRIPT)} characters")
    print(f"Expected Videos: {MARKET_SCRIPT.count('— pause —') + 1}")
    print("\nScript Preview:")
    print(MARKET_SCRIPT[:200] + "...")