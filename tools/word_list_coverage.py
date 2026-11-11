#!/usr/bin/env python3
"""Pick the core accent word list from data and measure what it covers.

For each accent sound, words are ranked by how often that sound is heard in
them across everyday English (word frequency x times the sound occurs in the
word), so each row is the smallest set of words carrying the most of it.

    pip install -r tools/requirements.txt
    python tools/word_list_coverage.py              # rows, 8 words each
    python tools/word_list_coverage.py --per-row 20
    python tools/word_list_coverage.py --curve      # coverage vs list size

Frequencies come from wordfreq (English; it blends speech-like sources such
as film subtitles with written text). Pronunciations come from the CMU
Pronouncing Dictionary (American English).
"""
from __future__ import annotations

import argparse

import cmudict
import wordfreq

VOWELS = {"AA", "AE", "AH", "AO", "AW", "AY", "EH", "ER", "EY", "IH", "IY", "OW", "OY", "UH", "UW"}

# (row label, card) in the order of curriculum/accent/04_core_word_list.md
SOUNDS = {
    "th_voiced": ("TH /ð/ (voiced)", "SG05"),
    "th_breath": ("TH /θ/ (breath)", "SG04"),
    "v": ("V (teeth on lip)", "SG03"),
    "w": ("W (round lips)", "SG03"),
    "td": ("T/D at the ridge", "SG01"),
    "flap": ("Flap T", "CS03"),
    "puff": ("P/T/K with a puff", "SG02"),
    "r": ("R (not rolled or dropped)", "SG06"),
    "glide": ("Gliding vowels", "SG07"),
    "trap": ("TRAP /æ/", "SG08"),
    "dark_l": ("Dark L", "SG09"),
    "final": ("Clean final consonants", "SG10"),
}

# Words left out of a row: the sound is normally lost in connected speech,
# or the word only repeats another spelling of the same sound.
SKIP = {
    "puff": {"to", "too", "can", "could"},          # usually unstressed: little or no puff
    "trap": {"as", "at", "an", "can", "than", "that's"},  # usually reduced to "uh"
    "flap": {"didn't", "wouldn't", "couldn't", "shouldn't", "united"},  # not a flap in American speech
    "final": {"its"},                               # same sound as "it's"
    "glide": {"they"},                              # already in the TH row
}


def base(p: str) -> str:
    return p.rstrip("012")


def vowel(p: str | None) -> bool:
    return p is not None and base(p) in VOWELS


def count_sounds(ph: list[str]) -> dict[str, int]:
    """Count each accent sound in one American pronunciation (ARPAbet)."""
    c = dict.fromkeys(SOUNDS, 0)
    for i, p in enumerate(ph):
        b = base(p)
        prev = ph[i - 1] if i else None
        nxt = ph[i + 1] if i + 1 < len(ph) else None
        nxt2 = ph[i + 2] if i + 2 < len(ph) else None
        c["th_voiced"] += b == "DH"
        c["th_breath"] += b == "TH"
        c["v"] += b == "V"
        c["w"] += b == "W"
        if b in ("T", "D"):
            flap = (vowel(prev) or (prev and base(prev) == "R")) and vowel(nxt) and nxt[-1] == "0"
            onset = vowel(nxt) or (nxt and base(nxt) in ("R", "W") and vowel(nxt2))
            c["flap"] += bool(flap)
            c["td"] += bool(onset and not flap)
        if b in ("P", "T", "K") and not (prev and base(prev) == "S"):
            v = nxt if vowel(nxt) else (nxt2 if nxt and base(nxt) in ("L", "R", "W", "Y") and vowel(nxt2) else None)
            c["puff"] += bool(v and v[-1] in "12")
        c["r"] += b in ("R", "ER")
        c["glide"] += b in ("EY", "OW")
        # American "a" before m/n/ng is a different, raised sound, so it is not counted.
        c["trap"] += b == "AE" and p[-1] in "12" and not (nxt and base(nxt) in ("M", "N", "NG"))
        c["dark_l"] += b == "L" and not vowel(nxt)
    tail = 0
    for p in reversed(ph):
        if vowel(p):
            break
        tail += 1
    c["final"] += tail >= 2
    return c


def sound_weights(n_words: int = 50_000) -> dict[str, dict[str, float]]:
    pron = cmudict.dict()
    weights = {s: {} for s in SOUNDS}
    for w in wordfreq.top_n_list("en", n_words):
        if w not in pron:
            continue
        f = wordfreq.word_frequency(w, "en")
        for s, k in count_sounds(pron[w][0]).items():
            if k:
                weights[s][w] = f * k
    return weights


def pick_rows(weights, per_row: int):
    rows = {}
    for s, ws in weights.items():
        ranked = [w for w, _ in sorted(ws.items(), key=lambda kv: -kv[1]) if w not in SKIP.get(s, set())]
        words = ranked[:per_row]
        rows[s] = (words, sum(ws[w] for w in words) / sum(ws.values()))
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--per-row", type=int, default=8, help="words per sound (default 8)")
    ap.add_argument("--curve", action="store_true", help="show coverage for several list sizes")
    ap.add_argument("--top", type=int, metavar="N",
                    help="the N words that remove the most accent slips, all sounds together")
    args = ap.parse_args()
    weights = sound_weights()
    for s, skip in SKIP.items():  # a skipped word carries no slip for that sound
        for w in skip:
            weights[s].pop(w, None)
    if args.top:
        slips = {}
        for ws in weights.values():
            for w, v in ws.items():
                slips[w] = slips.get(w, 0.0) + v
        best = sorted(slips, key=slips.get, reverse=True)[:args.top]
        share = {s: sum(ws.values()) for s, ws in weights.items()}
        total = sum(share.values())
        print(f"Top {args.top} words remove {sum(slips[w] for w in best) / total * 100:.1f}% of all accent slips:")
        print(", ".join(best))
        print("\nShare of all slips by sound:",
              ", ".join(f"{SOUNDS[s][0]} {v / total * 100:.0f}%" for s, v in sorted(share.items(), key=lambda kv: -kv[1])))
        return
    if args.curve:
        print("words/row  distinct words  average share of each sound covered")
        for k in (5, 8, 10, 15, 20, 30, 50):
            rows = pick_rows(weights, k)
            distinct = len({w for words, _ in rows.values() for w in words})
            avg = sum(c for _, c in rows.values()) / len(rows)
            print(f"{k:>9}  {distinct:>14}  {avg * 100:5.0f}%")
        return
    rows = pick_rows(weights, args.per_row)
    for s, (words, cov) in rows.items():
        label, card = SOUNDS[s]
        print(f"{label:<28} {cov * 100:3.0f}%  {card}  {', '.join(words)}")
    distinct = len({w for words, _ in rows.values() for w in words})
    print(f"\n{distinct} distinct words; on average {sum(c for _, c in rows.values()) / len(rows) * 100:.0f}% of each sound covered")


if __name__ == "__main__":
    main()
