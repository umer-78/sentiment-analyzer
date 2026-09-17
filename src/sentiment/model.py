"""Multinomial Naive Bayes, written out in full.

Training is counting. Prediction is a sum of log probabilities:

    log P(class | doc) ∝ log P(class) + Σ log P(word | class)

with Laplace (add-alpha) smoothing so an unseen word does not zero a class out,
and log-space arithmetic so long documents do not underflow to zero.
"""

from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from .tokenize import tokenize


@dataclass
class NaiveBayes:
    alpha: float = 1.0
    min_count: int = 1
    tokenizer_options: dict = field(default_factory=dict)

    classes_: list[str] = field(default_factory=list)
    log_prior_: dict[str, float] = field(default_factory=dict)
    log_likelihood_: dict[str, dict[str, float]] = field(default_factory=dict)
    vocabulary_: set[str] = field(default_factory=set)
    _default: dict[str, float] = field(default_factory=dict)

    # ------------------------------------------------------------------ fitting
    def fit(self, documents: list[str], labels: list[str]) -> "NaiveBayes":
        if len(documents) != len(labels):
            raise ValueError("documents and labels must be the same length")
        if not documents:
            raise ValueError("no training data")
        counts: dict[str, Counter] = defaultdict(Counter)
        class_docs = Counter(labels)
        for doc, label in zip(documents, labels):
            counts[label].update(self._tokens(doc))

        total_counts = Counter()
        for c in counts.values():
            total_counts.update(c)
        self.vocabulary_ = {w for w, n in total_counts.items() if n >= self.min_count}
        self.classes_ = sorted(class_docs)
        n_docs = len(documents)
        v = len(self.vocabulary_)

        self.log_prior_ = {c: math.log(class_docs[c] / n_docs) for c in self.classes_}
        self.log_likelihood_ = {}
        self._default = {}
        for c in self.classes_:
            total = sum(n for w, n in counts[c].items() if w in self.vocabulary_)
            denom = total + self.alpha * v
            self.log_likelihood_[c] = {
                w: math.log((counts[c][w] + self.alpha) / denom) for w in self.vocabulary_
            }
            self._default[c] = math.log(self.alpha / denom)  # word seen in training but not in this class
        return self

    def _tokens(self, document: str) -> list[str]:
        return tokenize(document, **self.tokenizer_options)

    # --------------------------------------------------------------- prediction
    def log_scores(self, document: str) -> dict[str, float]:
        if not self.classes_:
            raise RuntimeError("fit() must be called before predicting")
        scores = dict(self.log_prior_)
        for token in self._tokens(document):
            if token not in self.vocabulary_:
                continue  # unknown words carry no evidence either way
            for c in self.classes_:
                scores[c] += self.log_likelihood_[c].get(token, self._default[c])
        return scores

    def predict_proba(self, document: str) -> dict[str, float]:
        scores = self.log_scores(document)
        top = max(scores.values())
        exp = {c: math.exp(s - top) for c, s in scores.items()}   # softmax in log space
        total = sum(exp.values())
        return {c: v / total for c, v in exp.items()}

    def predict(self, document: str) -> str:
        return max(self.log_scores(document).items(), key=lambda kv: kv[1])[0]

    def predict_many(self, documents: list[str]) -> list[str]:
        return [self.predict(d) for d in documents]

    def score(self, documents: list[str], labels: list[str]) -> float:
        preds = self.predict_many(documents)
        return sum(p == y for p, y in zip(preds, labels)) / len(labels)

    # ------------------------------------------------------------ explanations
    def most_informative(self, n: int = 15, positive: str | None = None, negative: str | None = None):
        """Words whose log-odds between two classes are the strongest."""
        if len(self.classes_) < 2:
            return []
        positive = positive or self.classes_[-1]
        negative = negative or self.classes_[0]
        odds = {
            w: self.log_likelihood_[positive].get(w, self._default[positive])
            - self.log_likelihood_[negative].get(w, self._default[negative])
            for w in self.vocabulary_
        }
        ranked = sorted(odds.items(), key=lambda kv: kv[1])
        return ranked[:n][::-1], ranked[-n:][::-1]

    def explain(self, document: str, top: int = 6):
        """Which tokens pushed this document towards the predicted class."""
        if len(self.classes_) != 2:
            raise ValueError("explain() supports two-class models")
        a, b = self.classes_
        rows = []
        for token in dict.fromkeys(self._tokens(document)):
            if token in self.vocabulary_:
                weight = (self.log_likelihood_[b].get(token, self._default[b])
                          - self.log_likelihood_[a].get(token, self._default[a]))
                rows.append((token, weight))
        rows.sort(key=lambda kv: abs(kv[1]), reverse=True)
        return rows[:top]

    # ------------------------------------------------------------- persistence
    def save(self, path: str | Path) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps({
            "alpha": self.alpha, "min_count": self.min_count,
            "tokenizer_options": self.tokenizer_options,
            "classes": self.classes_, "log_prior": self.log_prior_,
            "log_likelihood": self.log_likelihood_, "default": self._default,
        }))

    @classmethod
    def load(cls, path: str | Path) -> "NaiveBayes":
        d = json.loads(Path(path).read_text())
        model = cls(alpha=d["alpha"], min_count=d["min_count"], tokenizer_options=d["tokenizer_options"])
        model.classes_ = d["classes"]
        model.log_prior_ = d["log_prior"]
        model.log_likelihood_ = d["log_likelihood"]
        model._default = d["default"]
        model.vocabulary_ = set(next(iter(d["log_likelihood"].values())).keys())
        return model
