#!/usr/bin/env python3
"""
Script file for long market analysis content
"""

MARKET_SCRIPT = """
Why a tiny bottle of purple liquid destroyed a British monopoly.

For decades, if you wanted your white shirt to look bright, you used "Robin Blue." It was a blue powder sold by a massive British company. But it had a problem. You had to mix the powder in water, and if you didn't mix it perfectly, it left ugly blue patches on your shirt.

Then came a man named M.P. Ramachandran. He invented Ujala. Unlike Robin Blue, Ujala wasn't a powder; it was a liquid. It dissolved instantly in water with zero effort and left no patches. He went door-to-door in Kerala showing housewives how much easier it was. He didn't just sell a whitener; he sold "convenience." The giant British company was too slow to adapt from powder to liquid. Ujala conquered the entire Indian market simply by realizing that the customer didn't hate the product; they hated the mixing process.

Like and Subscribe so I can build more such interesting videos.

— pause —

How World War I accidentally created India's most famous soap.

In 1916, the world was at war. The Kingdom of Mysore faced a strange crisis. They had tons of sandalwood logs that they usually exported to Europe for perfume, but because of the war, ships stopped sailing. The wood was piling up and rotting. The King, Krishnaraja Wadiyar IV, had to do something to save his revenue.

He decided to extract the oil from the wood and turn it into soap. He didn't just make a cleaning product; he created "Mysore Sandal Soap," the only soap in the world made from 100% pure sandalwood oil. What started as a desperate attempt to use up excess inventory during a trade blockade became a luxury heritage brand. It proves that sometimes, your biggest business disaster can force you to create your most valuable product.

Like and Subscribe so I can build more such interesting videos."""
if __name__ == "__main__":
    print(f"Market Script Length: {len(MARKET_SCRIPT)} characters")
    print(f"Expected Videos: {MARKET_SCRIPT.count('— pause —') + 1}")
    print("\nScript Preview:")
    print(MARKET_SCRIPT[:200] + "...")