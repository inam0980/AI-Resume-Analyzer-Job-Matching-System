"""
Minimal numpy-only TF-IDF vectorizer and logistic regression.

Drop-in replacements for the parts of scikit-learn this app uses, so the
server doesn't need scikit-learn + scipy (~160 MB). Outputs are dense arrays.
"""

import re
from collections import Counter

import numpy as np

ENGLISH_STOP_WORDS = frozenset("""
a about above across after afterwards again against all almost alone along already also
although always am among amongst an and another any anyhow anyone anything anyway anywhere
are around as at be became because become becomes becoming been before beforehand behind
being below beside besides between beyond both but by can cannot could did do does doing
done down due during each eg either else elsewhere enough etc even ever every everyone
everything everywhere except few for former formerly from further had has have having he
hence her here hereafter hereby herein hereupon hers herself him himself his how however i
ie if in indeed into is it its itself just keep last latter latterly least less made many
may me meanwhile might mine more moreover most mostly much must my myself namely neither
never nevertheless next no nobody none noone nor not nothing now nowhere of off often on
once one only onto or other others otherwise our ours ourselves out over own per perhaps
please put rather re same see seem seemed seeming seems several she should since so some
somehow someone something sometime sometimes somewhere still such than that the their
theirs them themselves then thence there thereafter thereby therefore therein thereupon
these they this those though through throughout thru thus to together too toward towards
under until up upon us very via was we well were what whatever when whence whenever where
whereafter whereas whereby wherein whereupon wherever whether which while whither who
whoever whole whom whose why will with within without would yet you your yours yourself
yourselves
""".split())

_TOKEN_RE = re.compile(r'(?u)\b\w\w+\b')


class TfidfVectorizer:
    def __init__(self, max_features=None, stop_words=None, ngram_range=(1, 1),
                 min_df=1, sublinear_tf=False):
        self.max_features = max_features
        self.stop_words = ENGLISH_STOP_WORDS if stop_words == 'english' else frozenset()
        self.ngram_range = ngram_range
        self.min_df = min_df
        self.sublinear_tf = sublinear_tf

    def _analyze(self, doc: str) -> list:
        tokens = [t for t in _TOKEN_RE.findall(doc.lower()) if t not in self.stop_words]
        lo, hi = self.ngram_range
        grams = []
        for n in range(lo, hi + 1):
            grams.extend(' '.join(tokens[i:i + n]) for i in range(len(tokens) - n + 1))
        return grams

    def fit_transform(self, docs) -> np.ndarray:
        counts = [Counter(self._analyze(d)) for d in docs]
        df = Counter(term for c in counts for term in c)
        terms = [t for t, n in df.items() if n >= self.min_df]
        if self.max_features:
            total = Counter()
            for c in counts:
                total.update(c)
            terms = sorted(terms, key=lambda t: (-total[t], t))[:self.max_features]
        if not terms:
            raise ValueError('empty vocabulary')
        self.vocabulary_ = {t: i for i, t in enumerate(sorted(terms))}
        n_docs = len(docs)
        dfs = np.array([df[t] for t in sorted(terms)], dtype=float)
        self.idf_ = np.log((1 + n_docs) / (1 + dfs)) + 1.0
        return self._vectorize(counts)

    def transform(self, docs) -> np.ndarray:
        return self._vectorize([Counter(self._analyze(d)) for d in docs])

    def _vectorize(self, counts) -> np.ndarray:
        X = np.zeros((len(counts), len(self.vocabulary_)))
        for row, c in enumerate(counts):
            for term, n in c.items():
                col = self.vocabulary_.get(term)
                if col is not None:
                    X[row, col] = n
        if self.sublinear_tf:
            X[X > 0] = 1 + np.log(X[X > 0])
        X *= self.idf_
        norms = np.linalg.norm(X, axis=1, keepdims=True)
        return X / np.where(norms == 0, 1, norms)

    def get_feature_names_out(self) -> np.ndarray:
        return np.array(sorted(self.vocabulary_, key=self.vocabulary_.get), dtype=object)


class LogisticRegression:
    """Binary L2-regularised logistic regression fitted by gradient descent."""

    def __init__(self, max_iter=1000, C=1.0, lr=0.5):
        self.max_iter = max_iter
        self.C = C
        self.lr = lr

    def fit(self, X, y):
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float)
        n, d = X.shape
        w = np.zeros(d)
        b = 0.0
        reg = 1.0 / (self.C * n)
        for _ in range(self.max_iter):
            p = 1.0 / (1.0 + np.exp(-(X @ w + b)))
            err = p - y
            w -= self.lr * (X.T @ err / n + reg * w)
            b -= self.lr * err.mean()
        self.coef_ = w.reshape(1, -1)
        self.intercept_ = np.array([b])
        return self
