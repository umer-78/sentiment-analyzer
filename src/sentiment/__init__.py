"""Sentiment analysis with a from-scratch Naive Bayes classifier."""

from .model import NaiveBayes
from .tokenize import tokenize

__all__ = ["NaiveBayes", "tokenize"]
__version__ = "1.0.0"
