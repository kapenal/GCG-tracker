"""Kana-focused Japanese -> Korean transcription.

Notes:
- Keeps ASCII letters/numbers/symbols as-is.
- Converts hiragana/katakana phonetically to Hangul syllables.
- Kanji are left unchanged (no dictionary translation).
"""

from __future__ import annotations

import re

SMALL_KANA = "ャュョァィゥェォ"
NASAL_MARK = "_N_"

PAIR_MAP = {
    "キャ": "캬",
    "キュ": "큐",
    "キョ": "쿄",
    "シャ": "샤",
    "シュ": "슈",
    "ショ": "쇼",
    "チャ": "차",
    "チュ": "추",
    "チョ": "초",
    "ニャ": "냐",
    "ニュ": "뉴",
    "ニョ": "뇨",
    "ヒャ": "햐",
    "ヒュ": "휴",
    "ヒョ": "효",
    "ミャ": "먀",
    "ミュ": "뮤",
    "ミョ": "묘",
    "リャ": "랴",
    "リュ": "류",
    "リョ": "료",
    "ギャ": "갸",
    "ギュ": "규",
    "ギョ": "교",
    "ジャ": "자",
    "ジュ": "주",
    "ジョ": "조",
    "ビャ": "뱌",
    "ビュ": "뷰",
    "ビョ": "뵤",
    "ピャ": "퍄",
    "ピュ": "퓨",
    "ピョ": "표",
    "ヴァ": "바",
    "ヴィ": "비",
    "ヴェ": "베",
    "ヴォ": "보",
}

SINGLE_MAP = {
    "ア": "아",
    "イ": "이",
    "ウ": "우",
    "エ": "에",
    "オ": "오",
    "カ": "카",
    "キ": "키",
    "ク": "쿠",
    "ケ": "케",
    "コ": "코",
    "サ": "사",
    "シ": "시",
    "ス": "스",
    "セ": "세",
    "ソ": "소",
    "タ": "타",
    "チ": "치",
    "ツ": "츠",
    "テ": "테",
    "ト": "토",
    "ナ": "나",
    "ニ": "니",
    "ヌ": "누",
    "ネ": "네",
    "ノ": "노",
    "ハ": "하",
    "ヒ": "히",
    "フ": "후",
    "ヘ": "헤",
    "ホ": "호",
    "マ": "마",
    "ミ": "미",
    "ム": "무",
    "メ": "메",
    "モ": "모",
    "ヤ": "야",
    "ユ": "유",
    "ヨ": "요",
    "ラ": "라",
    "リ": "리",
    "ル": "루",
    "レ": "레",
    "ロ": "로",
    "ワ": "와",
    "ヲ": "오",
    "ン": NASAL_MARK,
    "ガ": "가",
    "ギ": "기",
    "グ": "구",
    "ゲ": "게",
    "ゴ": "고",
    "ザ": "자",
    "ジ": "지",
    "ズ": "즈",
    "ゼ": "제",
    "ゾ": "조",
    "ダ": "다",
    "ヂ": "지",
    "ヅ": "즈",
    "デ": "데",
    "ド": "도",
    "バ": "바",
    "ビ": "비",
    "ブ": "부",
    "ベ": "베",
    "ボ": "보",
    "パ": "파",
    "ピ": "피",
    "プ": "푸",
    "ペ": "페",
    "ポ": "포",
    "ァ": "아",
    "ィ": "이",
    "ゥ": "우",
    "ェ": "에",
    "ォ": "오",
    "ャ": "야",
    "ュ": "유",
    "ョ": "요",
    "ヴ": "부",
}

GEMINATE_HEAD = {
    "카": "까",
    "키": "끼",
    "쿠": "꾸",
    "케": "께",
    "코": "꼬",
    "타": "따",
    "치": "찌",
    "츠": "쯔",
    "테": "떼",
    "토": "또",
    "파": "빠",
    "피": "삐",
    "푸": "뿌",
    "페": "뻬",
    "포": "뽀",
    "사": "싸",
    "시": "씨",
    "스": "쓰",
    "세": "쎄",
    "소": "쏘",
}


def _to_katakana(text: str) -> str:
    out = []
    for ch in text:
        code = ord(ch)
        if 0x3041 <= code <= 0x3096:
            out.append(chr(code + 0x60))
        else:
            out.append(ch)
    return "".join(out)


def _is_hangul_syllable(ch: str) -> bool:
    code = ord(ch)
    return 0xAC00 <= code <= 0xD7A3


def _has_jong(ch: str) -> bool:
    return _is_hangul_syllable(ch) and ((ord(ch) - 0xAC00) % 28) != 0


def _choseong_index(ch: str) -> int:
    return (ord(ch) - 0xAC00) // 588


def _add_jong(ch: str, jong_idx: int) -> str:
    if not _is_hangul_syllable(ch) or _has_jong(ch):
        return ch
    base = ord(ch) - 0xAC00
    return chr(0xAC00 + (base // 28) * 28 + jong_idx)


def _merge_nasal_tokens(tokens: list[str]) -> list[str]:
    merged: list[str] = []
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok != NASAL_MARK:
            merged.append(tok)
            i += 1
            continue

        next_tok = tokens[i + 1] if i + 1 < len(tokens) else None
        if merged:
            prev = merged[-1]
            # If next syllable starts with ㅇ (vowel-initial), keep standalone ㄴ.
            next_is_vowel_initial = (
                bool(next_tok)
                and len(next_tok) == 1
                and _is_hangul_syllable(next_tok)
                and _choseong_index(next_tok) == 11
            )
            if (
                len(prev) == 1
                and _is_hangul_syllable(prev)
                and not _has_jong(prev)
                and not next_is_vowel_initial
            ):
                merged[-1] = _add_jong(prev, 4)  # ㄴ
            else:
                merged.append("ㄴ")
        else:
            merged.append("ㄴ")
        i += 1
    return merged


def _apply_word_end_batchim(text: str) -> str:
    chars = list(text)
    out: list[str] = []
    for i, ch in enumerate(chars):
        if ch in ("무", "루") and out:
            prev = out[-1]
            next_ch = chars[i + 1] if i + 1 < len(chars) else ""
            boundary = (not next_ch) or (not _is_hangul_syllable(next_ch))
            if _is_hangul_syllable(prev) and not _has_jong(prev) and boundary:
                out[-1] = _add_jong(prev, 16 if ch == "무" else 8)  # ㅁ / ㄹ
                continue
        out.append(ch)
    return "".join(out)


def to_korean_name(text: str) -> str:
    src = _to_katakana(text)
    out: list[str] = []
    i = 0
    geminate = False

    while i < len(src):
        ch = src[i]

        if ch in ("ッ",):
            geminate = True
            i += 1
            continue

        if ch == "ー":
            # Ignore long vowel mark for readability.
            i += 1
            continue

        token = None
        if i + 1 < len(src) and src[i + 1] in SMALL_KANA:
            pair = src[i : i + 2]
            token = PAIR_MAP.get(pair)
            if token:
                i += 2
            else:
                token = SINGLE_MAP.get(ch)
                i += 1
        else:
            token = SINGLE_MAP.get(ch)
            i += 1

        if token:
            if geminate:
                token = GEMINATE_HEAD.get(token, token)
            out.append(token)
            geminate = False
        else:
            out.append(ch)
            geminate = False

    merged = _merge_nasal_tokens(out)
    result = "".join(merged)
    result = _apply_word_end_batchim(result)
    # normalize duplicate spaces created around punctuation boundaries
    return re.sub(r"\s{2,}", " ", result).strip()
