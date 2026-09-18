"""Tokenisation built for short reviews.

Three details matter more than the classifier for this kind of text:

1. **Negation scope.** "not good" must not look like "good". Words after a
   negator are tagged until the next punctuation mark.
2. **Emphasis.** "loooove" and "LOVE" carry signal; both are normalised, and
   capitals are kept as a separate marker rather than thrown away.
3. **Emoticons and emoji** survive tokenisation instead of being stripped.
"""

from __future__ import annotations

import re
import unicodedata

NEGATORS = {"not", "no", "never", "none", "cannot", "cant", "wont", "dont", "doesnt", "didnt",
            "isnt", "arent", "wasnt", "werent", "aint", "hardly", "barely", "without", "neither", "nor"}
CLAUSE_END = {".", ",", "!", "?", ";", ":", "but", "however", "although", "though", "yet"}
# Punctuation worth keeping: "!" and "?" carry sentiment, "," and "." do not.
KEEP_PUNCT = {"!", "?"}
EMOTICON = re.compile(r"[:;=8xX][\-o\*']?[\)\]\(\[dDpP/\\\|@oO3]")
WORD = re.compile(r"[a-z0-9']+|[^\sa-z0-9']", re.IGNORECASE)
STOPWORDS = {"a", "an", "the", "of", "to", "and", "is", "was", "were", "be", "been", "it", "its",
             "this", "that", "for", "on", "in", "at", "as", "with", "i", "we", "they", "he", "she"}


def _squeeze(word: str) -> str:
    """loooove -> loove (keep a doubled letter as an emphasis marker)."""
    return re.sub(r"(.)\1{2,}", r"\1\1", word)


def tokenize(text: str, *, negation: bool = True, keep_stopwords: bool = True,
             bigrams: bool = False) -> list[str]:
    text = unicodedata.normalize("NFKC", str(text))
    tokens: list[str] = []
    negating = False
    for raw in WORD.findall(text) + EMOTICON.findall(text):
        lower = raw.lower()
        if lower in CLAUSE_END or (len(lower) == 1 and not lower.isalnum() and not EMOTICON.match(raw)):
            negating = False  # negation never crosses a clause boundary
            if raw in KEEP_PUNCT or EMOTICON.match(raw) or unicodedata.category(raw[0]).startswith("S"):
                tokens.append(raw)
            elif lower.isalpha():
                tokens.append(lower)  # keep contrast words like "but" as features
            continue
        if not keep_stopwords and lower in STOPWORDS and lower not in NEGATORS:
            continue
        token = _squeeze(lower.strip("'"))
        if not token:
            continue
        if raw.isupper() and len(raw) > 2:
            token += "_caps"
        tokens.append(f"not_{token}" if negating else token)
        if negation and lower in NEGATORS:
            negating = True
    if bigrams:
        # The offset list is one shorter by construction — that is what makes
        # these bigrams — so this zip must stop at the shorter one.
        tokens += [f"{a}_{b}" for a, b in zip(tokens, tokens[1:], strict=False)]
    return tokens
