"""The review corpus.

Public review datasets (IMDb, Yelp, Amazon) come with licences that make
redistribution awkward, so this builds a corpus from templates instead: product
and app reviews in the style people actually write, including the cases that
break naive bag-of-words models —

* negation: "not good", "wouldn't recommend"
* contrast: "the screen is lovely, but the battery is hopeless"
* qualified praise: "not bad at all", "no complaints"
* emphasis: "LOVE it", "sooo slow", emoticons
* noise: typos, filler sentences, and 3% of labels flipped, because real
  review data is never perfectly labelled

Every sentence is assembled from pieces with a fixed seed, so the corpus is
reproducible, and the label comes from the pieces, not from a guess.
"""

from __future__ import annotations

import csv
import random
from pathlib import Path

POS_OPEN = ["Absolutely love this", "Really happy with it", "Exactly what I needed",
            "Works beautifully", "Best purchase this year", "Five stars", "Worth every rupee",
            "Better than I expected", "Delighted with this one", "So glad I bought it"]
NEG_OPEN = ["Very disappointed", "Complete waste of money", "Do not buy this", "Returned it the same week",
            "Regret this purchase", "One star", "Terrible experience", "Save your money",
            "Broke within a week", "Would not recommend"]
POS_BODY = ["the battery lasts all day", "setup took two minutes", "the build quality feels solid",
            "delivery arrived a day early", "the screen is bright and sharp", "support replied within an hour",
            "it is light and easy to carry", "the sound is surprisingly good", "the app is simple to use",
            "it fits perfectly", "the camera is sharp even at night", "charging is fast"]
NEG_BODY = ["the battery dies in two hours", "setup was a nightmare", "the plastic feels cheap",
            "delivery took three weeks", "the screen has dead pixels", "support never replied",
            "it is far too heavy", "the sound crackles at low volume", "the app crashes on every launch",
            "it does not fit at all", "the camera is blurry indoors", "it overheats while charging"]
POS_CLOSE = ["Highly recommended.", "Will buy again.", "Very pleased.", "No complaints at all.",
             "Exactly as described.", "Great value.", "Ten out of ten.",
             "I would recommend it to anyone.", "Recommend it without hesitation.",
             "Happy to recommend this one.", "Would buy it again tomorrow."]
NEG_CLOSE = ["Avoid.", "Never again.", "Very poor value.", "Deeply unimpressed.",
             "Asked for a refund.", "Not worth the price.", "Zero out of ten.",
             "I cannot recommend it.", "Would not buy it again.", "Hard to recommend at this price."]
INTENSIFIERS = ["really ", "absolutely ", "honestly ", "seriously ", "genuinely ", ""]
POS_EMOJI = [" :)", " :D", " 👍", ""]
NEG_EMOJI = [" :(", " :/", " 👎", ""]
POS_ADJ = ["lovely", "solid", "brilliant", "sturdy", "crisp", "smooth", "reliable", "generous",
           "responsive", "premium", "handy", "comfortable", "quiet", "quick"]
NEG_ADJ = ["hopeless", "flimsy", "sluggish", "noisy", "awkward", "clunky", "useless", "fragile",
           "unreliable", "cramped", "overpriced", "dim", "rough", "faulty"]
NOUNS = ["screen", "battery", "app", "case", "packaging", "charger", "speaker", "keyboard",
         "camera", "fan", "button", "cable", "stand", "finish"]
FILLER = ["Bought it last month.", "Used it daily for two weeks.", "Second one I have owned.",
          "Arrived in the original packaging.", "Comparing it with my old one.",
          "Ordered during the sale.", "My wife uses it more than I do."]

# Hard cases: the surface words point one way and the label goes the other.
HARD_POSITIVE = [
    "not bad at all, actually", "I was ready to hate it and I don't",
    "no problems so far", "hardly any complaints", "it isn't perfect but I love it",
    "cannot fault it", "doesn't disappoint", "never had an issue",
]
HARD_NEGATIVE = [
    "looks great, works badly", "the price is the only good thing",
    "not worth it", "I wanted to love this", "good idea, terrible execution",
    "not as described", "nice box, broken product", "does not do what it promises",
]


def make_corpus(n: int = 2000, seed: int = 17) -> list[tuple[str, str]]:
    """Return [(review_text, label)] with label in {"positive", "negative"}."""
    rng = random.Random(seed)
    rows: list[tuple[str, str]] = []
    while len(rows) < n:
        positive = rng.random() < 0.5
        opens, body, close = (POS_OPEN, POS_BODY, POS_CLOSE) if positive else (NEG_OPEN, NEG_BODY, NEG_CLOSE)
        other_body = NEG_BODY if positive else POS_BODY
        shape = rng.random()
        intens = rng.choice(INTENSIFIERS)
        adjectives = POS_ADJ if positive else NEG_ADJ
        other_adjectives = NEG_ADJ if positive else POS_ADJ
        if shape < 0.32:
            text = f"{rng.choice(opens)}. {intens.capitalize() if intens else ''}{rng.choice(body)}. {rng.choice(close)}"
        elif shape < 0.55:
            text = f"{rng.choice(body).capitalize()} and {rng.choice(body)}. {rng.choice(close)}"
        elif shape < 0.72:
            # mixed review: the label follows the clause after "but"
            text = f"{rng.choice(other_body).capitalize()}, but {rng.choice(body)}. {rng.choice(close)}"
        elif shape < 0.85:
            hard = rng.choice(HARD_POSITIVE if positive else HARD_NEGATIVE)
            text = f"{hard.capitalize()}. {rng.choice(body)}."
        elif shape < 0.90:
            text = f"{rng.choice(opens)} — {rng.choice(body)}{rng.choice(POS_EMOJI if positive else NEG_EMOJI)}"
        else:
            # adjective-driven: "the screen is lovely, the battery is hopeless"
            good = f"the {rng.choice(NOUNS)} is {rng.choice(adjectives)}"
            bad = f"the {rng.choice(NOUNS)} is {rng.choice(other_adjectives)}"
            text = (f"{good.capitalize()} and {rng.choice(body)}. {rng.choice(close)}" if rng.random() < 0.5
                    else f"{bad.capitalize()}, but {good}. {rng.choice(close)}")
        if rng.random() < 0.25:
            text = f"{rng.choice(FILLER)} {text}"
        if rng.random() < 0.15:  # typos
            i = rng.randrange(len(text))
            text = text[:i] + text[i + 1:]
        if rng.random() < 0.08:
            text = text.upper()
        if rng.random() < 0.1:
            text = text.replace("good", "gooood").replace("slow", "sloooow")
        label = "positive" if positive else "negative"
        if rng.random() < 0.03:  # mislabelled, as in any hand-labelled corpus
            label = "negative" if label == "positive" else "positive"
        rows.append((text.strip(), label))
    rng.shuffle(rows)
    return rows


def write_csv(rows: list[tuple[str, str]], path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["text", "label"])
        writer.writerows(rows)
    return path


def read_csv(path: str | Path) -> list[tuple[str, str]]:
    with Path(path).open(encoding="utf-8") as fh:
        return [(r["text"], r["label"]) for r in csv.DictReader(fh)]


def split(rows: list[tuple[str, str]], test_size: float = 0.25, seed: int = 0):
    rng = random.Random(seed)
    shuffled = rows[:]
    rng.shuffle(shuffled)
    cut = int(len(shuffled) * (1 - test_size))
    train, test = shuffled[:cut], shuffled[cut:]
    return ([t for t, _ in train], [y for _, y in train], [t for t, _ in test], [y for _, y in test])
