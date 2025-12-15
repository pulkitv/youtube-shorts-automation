#!/usr/bin/env python3
"""
Script file for long market analysis content
"""

MARKET_SCRIPT = """
Why a bottle of hair oil claims it is actually food.

If you pick up a blue bottle of Parachute coconut oil, you will notice something strange. Nowhere on the bottle does it say "Hair Oil." Instead, it says "Edible Oil" or contains a small green dot indicating it is vegetarian food. This isn't a printing mistake; it is a brilliant tax strategy.

In India, hair oil is classified as a cosmetic, which attracts a high luxury tax. However, edible oil is considered an essential food item and has a much lower tax rate. Marico, the company that owns Parachute, argued in court that since coconut oil is natural, it *can* technically be cooked with and eaten. Even though 99% of people put it on their heads, the court had to agree. By classifying it as food, they saved millions in taxes, keeping the price low enough to beat every competitor. They won by proving that what matters is not how customers use the product, but what is chemically inside the bottle.

Like and Subscribe so I can build more such interesting videos.

— pause —

How a dying music company got rich by selling a radio to your grandfather.

A few years ago, Saregama was in trouble. They owned the rights to thousands of classic songs by legends like Kishore Kumar and Lata Mangeshkar. But nobody bought CDs anymore, and young people just streamed music for free on YouTube or Spotify. Their greatest asset—their music library—was making zero money.

Then they realized they were targeting the wrong audience. The people who loved these old songs were elderly. They didn't know how to use Bluetooth, apps, or search bars. They wanted simplicity. So, Saregama launched "Carvaan." It looks like an old-school radio, has big chunky buttons, and comes pre-loaded with 5,000 songs. No internet required. You just turn a knob. It became the perfect gift for parents. They took dead intellectual property and packaged it into a simple hardware device, proving that sometimes the best technology is actually "low-tech."

Like and Subscribe so I can build more such interesting videos.
"""
if __name__ == "__main__":
    print(f"Market Script Length: {len(MARKET_SCRIPT)} characters")
    print(f"Expected Videos: {MARKET_SCRIPT.count('— pause —') + 1}")
    print("\nScript Preview:")
    print(MARKET_SCRIPT[:200] + "...")