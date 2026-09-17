# Sentiment Analyzer

[![CI](https://github.com/umer-78/sentiment-analyzer/actions/workflows/ci.yml/badge.svg)](https://github.com/umer-78/sentiment-analyzer/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

A **Naive Bayes text classifier written from scratch** — the counting, the
add-alpha smoothing, the log-space arithmetic — plus a tokeniser built for
reviews, an explanation of every prediction, and a benchmark against
scikit-learn on the same split.

```bash
$ sentiment predict --explain "The screen is lovely but the battery is hopeless"
positive  76.8%  The screen is lovely but the battery is hopeless
           hopeless             -1.13 → negative
           lovely               +1.07 → positive
           is                   +0.48 → positive
           but                  +0.21 → positive
           screen               +0.17 → positive
           the                  -0.07 → negative
```

## Why write the classifier by hand

The interesting part of sentiment analysis is not the classifier. It is the text:

| Problem | Handled by |
|---|---|
| `not good` must not look like `good` | negation tagging until the clause ends (`not_good`) |
| `loooove`, `LOVE` | repeated letters squeezed, capitals kept as a `_caps` marker |
| `:)` `👍` | emoticons and emoji survive tokenisation |
| `!` carries sentiment, `,` does not | punctuation filtered, not blanket-stripped |
| unseen words at prediction time | ignored, rather than allowed to zero a class |
| long documents | log-space sums, so no underflow at 5,000 words |

## Results

2,000 reviews, 75/25 split:

```text
1,500 training reviews, 500 test reviews

model                              accuracy  precision  recall     f1  seconds
------------------------------------------------------------------------------
from scratch (unigrams)               0.968      0.969   0.969  0.969     0.08
from scratch (+ bigrams)              0.972      0.970   0.977  0.973     0.11
from scratch (no negation handling)    0.964      0.962   0.969  0.966     0.09
scikit-learn MultinomialNB            0.968      0.969   0.969  0.969     0.10
scikit-learn TF-IDF + logistic        0.972      0.970   0.977  0.973     0.11
```

The from-scratch model matches scikit-learn's `MultinomialNB` to three decimals,
which is the point: it is the same algorithm, written out. TF-IDF with logistic
regression is slightly ahead, as expected.

Most informative words it learned:

```text
most positive                most negative               
recommended            4.01   zero                  -3.36
highly                 3.99   refund                -3.40
worth                  3.40   asked                 -3.40
rupee                  3.40   experience            -3.53
so                     3.37   not_again             -3.64
anyone                 3.35   not_recommend         -3.84
pleased                3.26   money                 -3.90
without                3.26   not_buy               -4.27
```

## Quick start

```bash
git clone https://github.com/umer-78/sentiment-analyzer.git
cd sentiment-analyzer
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

sentiment generate            # build data/reviews.csv
sentiment train               # train and save the model
sentiment benchmark           # compare with scikit-learn
sentiment predict "not bad at all, no complaints"
sentiment words               # strongest positive and negative words
echo "the app crashes constantly" | sentiment predict --explain
```

As a library:

```python
from sentiment import NaiveBayes

model = NaiveBayes(alpha=1.0).fit(texts, labels)
model.predict_proba("works exactly as described :)")   # {'positive': 0.99, 'negative': 0.01}
model.explain("slow and overpriced")                    # [('slow', -1.8), ('overpriced', -1.6)]
```

## About the data

`sentiment generate` builds the corpus from templates: positive and negative
openers, bodies and closers, mixed reviews, hard cases ("not bad at all", "looks
great, works badly"), filler sentences, typos, shouting, emoji — and **3% of
labels flipped**, because no hand-labelled corpus is perfect.

This is synthetic data. It shows the pipeline works; it does not prove the model
would hit 97% on real reviews, and it will not know words the templates never
used. To use it for real, point `sentiment train` at a CSV with `text,label`
columns from your own data.

## Known limitation

Contrast is not weighted. In *"the screen is lovely, but the battery is
hopeless"* a person reads the clause after "but" as the verdict; the model just
adds up evidence and leans positive. Fixing it properly needs clause-level
parsing or a model with word order, which is where this simple approach stops
and transformers begin.

## Tests

```bash
ruff check .
python -m pytest -q     # 18 tests
```

They check the tokeniser's negation scope and emphasis handling, that the
smoothing matches the textbook formula, that likelihoods sum to 1, that a
5,000-word document does not underflow, that accuracy clears the majority
baseline by a wide margin, and the whole CLI.

## License

[MIT](LICENSE)
