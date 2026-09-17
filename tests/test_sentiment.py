import math

import pytest

from sentiment import NaiveBayes, tokenize
from sentiment.cli import main
from sentiment.data import make_corpus, read_csv, split, write_csv


# ------------------------------------------------------------------ tokeniser
def test_basic_tokenisation():
    assert tokenize("The battery lasts!") == ["the", "battery", "lasts", "!"]


def test_negation_is_scoped_to_the_clause():
    assert tokenize("not good") == ["not", "not_good"]
    assert tokenize("not good, but fast") == ["not", "not_good", "but", "fast"]
    assert "not_battery" not in tokenize("I did not like it. The battery is fine.")


def test_emphasis_and_capitals():
    assert tokenize("loooove") == ["loove"]
    assert tokenize("LOVE it") == ["love_caps", "it"]
    assert tokenize("love it") == ["love", "it"]


def test_emoticons_and_emoji_survive():
    assert ":)" in tokenize("great :)")
    assert "👍" in tokenize("great 👍")


def test_bigrams_and_stopword_removal():
    assert tokenize("very fast phone", bigrams=True)[-1] == "fast_phone"
    assert "the" not in tokenize("the phone", keep_stopwords=False)


# --------------------------------------------------------------------- corpus
def test_corpus_is_balanced_and_reproducible():
    rows = make_corpus(600, seed=3)
    labels = [y for _, y in rows]
    assert len(rows) == 600
    assert 0.4 < labels.count("positive") / len(labels) < 0.6
    assert make_corpus(50, seed=3) == make_corpus(50, seed=3)
    assert make_corpus(50, seed=3) != make_corpus(50, seed=4)


def test_corpus_round_trips_through_csv(tmp_path):
    rows = make_corpus(30, seed=1)
    path = write_csv(rows, tmp_path / "r.csv")
    assert read_csv(path) == rows


def test_split_keeps_every_row():
    xtr, ytr, xte, yte = split(make_corpus(200, seed=2), test_size=0.25)
    assert len(xtr) == 150 and len(xte) == 50
    assert len(ytr) == 150 and len(yte) == 50


# ---------------------------------------------------------------- the classifier
@pytest.fixture(scope="module")
def trained():
    xtr, ytr, xte, yte = split(make_corpus(1600, seed=11))
    return NaiveBayes().fit(xtr, ytr), xte, yte


def test_priors_and_likelihoods_are_probabilities():
    model = NaiveBayes().fit(["good great", "bad awful", "good fine"], ["pos", "neg", "pos"])
    assert model.log_prior_["pos"] == pytest.approx(math.log(2 / 3))
    for c in model.classes_:
        total = sum(math.exp(v) for v in model.log_likelihood_[c].values())
        assert total == pytest.approx(1.0, abs=0.02)


def test_add_alpha_smoothing_matches_the_formula():
    model = NaiveBayes(alpha=1.0).fit(["a a b", "c"], ["x", "y"])
    # class x: "a" twice, "b" once, vocabulary {a, b, c} -> (2+1)/(3+3)
    assert model.log_likelihood_["x"]["a"] == pytest.approx(math.log(3 / 6))
    assert model.log_likelihood_["x"]["c"] == pytest.approx(math.log(1 / 6))


def test_probabilities_sum_to_one_and_unknown_words_are_ignored():
    model = NaiveBayes().fit(["good", "bad"], ["pos", "neg"])
    probs = model.predict_proba("good")
    assert sum(probs.values()) == pytest.approx(1.0)
    assert model.predict_proba("zzz qqq") == pytest.approx(model.predict_proba(""))


def test_long_documents_do_not_underflow():
    model = NaiveBayes().fit(["good " * 5, "bad " * 5], ["pos", "neg"])
    probs = model.predict_proba("good " * 5000)
    assert all(math.isfinite(v) for v in probs.values())
    assert probs["pos"] > 0.99


def test_accuracy_beats_the_majority_baseline(trained):
    model, xte, yte = trained
    majority = max(yte.count("positive"), yte.count("negative")) / len(yte)
    assert model.score(xte, yte) > 0.9
    assert model.score(xte, yte) > majority + 0.3


def test_negation_changes_the_prediction(trained):
    model, _, _ = trained
    assert model.predict("I would recommend this") == "positive"
    assert model.predict("I would not recommend this") == "negative"


def test_most_informative_and_explain(trained):
    model, _, _ = trained
    negative, positive = model.most_informative(10)
    assert len(positive) == 10 and len(negative) == 10
    assert positive[0][1] > 0 > negative[0][1]
    rows = model.explain("terrible, would not recommend")
    assert rows and abs(rows[0][1]) > 0


def test_save_and_load_round_trip(trained, tmp_path):
    model, xte, _ = trained
    path = tmp_path / "m.json"
    model.save(path)
    reloaded = NaiveBayes.load(path)
    assert reloaded.predict_many(xte[:50]) == model.predict_many(xte[:50])


def test_errors_on_bad_input():
    with pytest.raises(ValueError):
        NaiveBayes().fit(["a"], ["x", "y"])
    with pytest.raises(ValueError):
        NaiveBayes().fit([], [])
    with pytest.raises(RuntimeError):
        NaiveBayes().predict("anything")


def test_cli_end_to_end(tmp_path, capsys):
    data = tmp_path / "r.csv"
    model = tmp_path / "m.json"
    assert main(["generate", "-n", "400", "-o", str(data)]) == 0
    assert main(["train", "-d", str(data), "-o", str(model)]) == 0
    assert main(["predict", "-m", str(model), "absolutely love this"]) == 0
    assert "positive" in capsys.readouterr().out
    assert main(["words", "-m", str(model), "-n", "3"]) == 0
    assert main(["benchmark", "-d", str(data)]) == 0
    assert "scikit-learn" in capsys.readouterr().out
    assert main(["predict", "-m", str(tmp_path / "missing.json"), "hi"]) == 2
