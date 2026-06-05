import re
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

URL = "https://yuyu-tei.jp/sell/gcg/s/gd01"
html = httpx.get(URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=60).text

# Find rarity section patterns
for pat in [r"Card List</h3>", r"class=\"card-product", r"LR\+\+ Card List"]:
    print(pat, len(re.findall(pat, html)))

idx = html.find("Card List")
print("\n--- sample around first Card List ---")
print(html[max(0, idx - 200) : idx + 400])

# h3 sections
h3s = re.findall(r"<h3[^>]*>([^<]*Card List[^<]*)</h3>", html)
print("\nh3 Card List headers:", h3s[:12])
