"""Preview Japanese -> Korean card name translations."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.jp_to_ko import to_korean_name  # noqa: E402

SAMPLES = [
    "ガンダム",
    "ガンダム(パラレル)",
    "ユニコーンガンダム（デストロイモード）",
    "シャア専用ゲルググ",
    "ウイングガンダムゼロ",
    "フリーダムガンダム",
    "立てよ国民！",
    "魔女と花嫁",
    "ガンダム・エアリアル（改修型）",
]


def main() -> None:
    print("=== samples ===")
    for name in SAMPLES:
        print(f"{name} -> {to_korean_name(name)}")

    latest = ROOT / "data" / "latest.json"
    if latest.exists():
        data = json.loads(latest.read_text(encoding="utf-8"))
        names = sorted({c["name"] for c in data["cards"]})
        missing = [n for n in names if to_korean_name(n) == n]
        print(f"\n=== stats ({len(names)} unique names) ===")
        print(f"unchanged: {len(missing)}")
        if missing[:15]:
            print("examples still unchanged:")
            for n in missing[:15]:
                print(f"  {n}")


if __name__ == "__main__":
    main()
