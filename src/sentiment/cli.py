"""sentiment: train, evaluate and run the sentiment classifier."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .benchmark import HEADER, run
from .data import make_corpus, read_csv, split, write_csv
from .model import NaiveBayes

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA = ROOT / "data" / "reviews.csv"
DEFAULT_MODEL = ROOT / "models" / "naive-bayes.json"


def _rows(path: Path) -> list[tuple[str, str]]:
    if not path.exists():
        print(f"{path} not found — run `sentiment generate` first.", file=sys.stderr)
        raise SystemExit(2)
    return read_csv(path)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="sentiment", description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("generate", help="build the review corpus")
    g.add_argument("-n", type=int, default=2000)
    g.add_argument("--seed", type=int, default=17)
    g.add_argument("-o", "--output", type=Path, default=DEFAULT_DATA)

    t = sub.add_parser("train", help="train the from-scratch classifier and save it")
    t.add_argument("-d", "--data", type=Path, default=DEFAULT_DATA)
    t.add_argument("-o", "--model", type=Path, default=DEFAULT_MODEL)
    t.add_argument("--alpha", type=float, default=1.0)
    t.add_argument("--bigrams", action="store_true")

    b = sub.add_parser("benchmark", help="compare against scikit-learn on the same split")
    b.add_argument("-d", "--data", type=Path, default=DEFAULT_DATA)

    p = sub.add_parser("predict", help="classify text from arguments or standard input")
    p.add_argument("text", nargs="*")
    p.add_argument("-m", "--model", type=Path, default=DEFAULT_MODEL)
    p.add_argument("--explain", action="store_true", help="show the words that decided it")

    w = sub.add_parser("words", help="the most informative words the model learned")
    w.add_argument("-m", "--model", type=Path, default=DEFAULT_MODEL)
    w.add_argument("-n", type=int, default=15)

    args = ap.parse_args(argv)

    if args.cmd == "generate":
        path = write_csv(make_corpus(args.n, args.seed), args.output)
        print(f"wrote {args.n:,} labelled reviews to {path}")
        return 0

    if args.cmd == "train":
        x_train, y_train, x_test, y_test = split(_rows(args.data))
        model = NaiveBayes(alpha=args.alpha, tokenizer_options={"bigrams": args.bigrams} if args.bigrams else {})
        model.fit(x_train, y_train)
        print(f"trained on {len(x_train):,} reviews, vocabulary {len(model.vocabulary_):,}")
        print(f"train accuracy {model.score(x_train, y_train):.3f}   test accuracy {model.score(x_test, y_test):.3f}")
        model.save(args.model)
        print(f"saved {args.model}")
        return 0

    if args.cmd == "benchmark":
        x_train, y_train, x_test, y_test = split(_rows(args.data))
        print(f"{len(x_train):,} training reviews, {len(x_test):,} test reviews\n")
        print(HEADER)
        print("-" * len(HEADER))
        for r in run(x_train, y_train, x_test, y_test):
            print(r.row())
        return 0

    if not args.model.exists():
        print(f"{args.model} not found — run `sentiment train` first.", file=sys.stderr)
        return 2
    model = NaiveBayes.load(args.model)

    if args.cmd == "words":
        negative, positive = model.most_informative(args.n)
        print(f"{'most positive':<28} {'most negative':<28}")
        for (pw, ps), (nw, ns) in zip(positive, negative):
            print(f"{pw:<20} {ps:>6.2f}   {nw:<20} {ns:>6.2f}")
        return 0

    texts = [" ".join(args.text)] if args.text else [line.strip() for line in sys.stdin if line.strip()]
    for text in texts:
        probs = model.predict_proba(text)
        label = max(probs, key=probs.get)
        print(f"{label:>8}  {probs[label]:.1%}  {text}")
        if args.explain:
            for token, weight in model.explain(text):
                arrow = "positive" if weight > 0 else "negative"
                print(f"           {token:<20} {weight:+.2f} → {arrow}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
