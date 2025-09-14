#!/usr/bin/env python3
"""
Script file for long market analysis content
"""

MARKET_SCRIPT = """ABB India as on September 14, 2025 — Sentiment: Positive. 
ABB India, a leading engineering company, has recently announced strong performance in financial results and secured a significant order worth Rs 173 crore to supply wind converters for projects scheduled in 2026. The company also celebrated its 30th year on the National Stock Exchange (NSE), marking an impressive 8,500% total shareholder return (TSR) growth. ABB's recent board meeting, planned for November 2025, will consider unaudited results for the quarter ended September 30, but market analysts have commented positively on its growth trajectory and operational expansion. Despite minor regulatory hurdles—a customs fine that is not expected to impact results—ABB continues to establish itself as an innovative leader in India's electrical engineering sector, positioning well for future growth.
— pause —

Adani Power as on September 14, 2025 — Sentiment: Positive. 
Adani Power, India's largest private thermal power producer, signed a 25-year Power Supply Agreement (PSA) with the Bihar government to deliver 2,400 megawatts (MW) from a new ultra supercritical power plant in Bhagalpur. The project, valued at 3 billion United States Dollars (USD), will be executed under the Design, Build, Finance, Own, and Operate (DBFOO) model. The plant aims to create thousands of direct and indirect jobs over the next five years and will help Bihar receive steady, affordable electricity. This positive development has been welcomed by both stakeholders and market analysts, signaling growth and technology expansion for Adani Power—especially as India works toward becoming a power-surplus nation.
— pause —
"""

if __name__ == "__main__":
    print(f"Market Script Length: {len(MARKET_SCRIPT)} characters")
    print(f"Expected Videos: {MARKET_SCRIPT.count('— pause —') + 1}")
    print("\nScript Preview:")
    print(MARKET_SCRIPT[:200] + "...")