"""Compare the from-scratch model with scikit-learn baselines on the same split."""

from __future__ import annotations

import time
from dataclasses import dataclass

from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, precision_score, recall_score
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline

from .model import NaiveBayes
from .tokenize import tokenize


@dataclass
class Result:
    name: str
    accuracy: float
    precision: float
    recall: float
    f1: float
    seconds: float

    def row(self) -> str:
        return (f"{self.name:<34} {self.accuracy:>8.3f} {self.precision:>10.3f} "
                f"{self.recall:>7.3f} {self.f1:>6.3f} {self.seconds:>8.2f}")


HEADER = f"{'model':<34} {'accuracy':>8} {'precision':>10} {'recall':>7} {'f1':>6} {'seconds':>8}"


def _scores(name: str, y_true, y_pred, seconds: float) -> Result:
    kw = {"pos_label": "positive", "zero_division": 0}
    return Result(
        name=name,
        accuracy=sum(a == b for a, b in zip(y_true, y_pred, strict=True)) / len(y_true),
        precision=precision_score(y_true, y_pred, **kw),
        recall=recall_score(y_true, y_pred, **kw),
        f1=f1_score(y_true, y_pred, **kw),
        seconds=seconds,
    )


def run(x_train, y_train, x_test, y_test) -> list[Result]:
    results = []

    for label, options in (("from scratch (unigrams)", {}),
                           ("from scratch (+ bigrams)", {"bigrams": True}),
                           ("from scratch (no negation handling)", {"negation": False})):
        start = time.perf_counter()
        model = NaiveBayes(alpha=1.0, tokenizer_options=options).fit(x_train, y_train)
        preds = model.predict_many(x_test)
        results.append(_scores(label, y_test, preds, time.perf_counter() - start))

    sk_tokenizer = dict(tokenizer=tokenize, token_pattern=None, lowercase=False)
    for label, pipe in (
        ("scikit-learn MultinomialNB", Pipeline([("v", CountVectorizer(**sk_tokenizer)), ("m", MultinomialNB())])),
        ("scikit-learn TF-IDF + logistic", Pipeline([("v", TfidfVectorizer(**sk_tokenizer)),
                                                     ("m", LogisticRegression(max_iter=1000))])),
    ):
        start = time.perf_counter()
        pipe.fit(x_train, y_train)
        preds = pipe.predict(x_test)
        results.append(_scores(label, y_test, list(preds), time.perf_counter() - start))
    return results
