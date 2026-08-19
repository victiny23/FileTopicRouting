"""Picklable sklearn helpers shared by training notebooks and saved pipelines."""

from __future__ import annotations

from sklearn.base import BaseEstimator, ClassifierMixin, TransformerMixin
from sklearn.preprocessing import LabelEncoder
from xgboost import XGBClassifier


class ToDense(BaseEstimator, TransformerMixin):
    """Sparse matrix → dense ndarray for tree-based classifiers."""

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        return X.toarray() if hasattr(X, "toarray") else X


class XGBMulticlass(BaseEstimator, ClassifierMixin):
    """XGBoost multiclass head; encodes string topic labels for training."""

    def __init__(
        self,
        n_estimators=100,
        max_depth=6,
        learning_rate=0.3,
        random_state=42,
        n_jobs=-1,
        verbosity=0,
    ):
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.learning_rate = learning_rate
        self.random_state = random_state
        self.n_jobs = n_jobs
        self.verbosity = verbosity

    def fit(self, X, y):
        self._le = LabelEncoder()
        y_enc = self._le.fit_transform(y)
        self.classes_ = self._le.classes_
        self._clf = XGBClassifier(
            objective="multi:softprob",
            num_class=len(self.classes_),
            eval_metric="mlogloss",
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            learning_rate=self.learning_rate,
            random_state=self.random_state,
            n_jobs=self.n_jobs,
            verbosity=self.verbosity,
        )
        self._clf.fit(X, y_enc)
        return self

    def predict(self, X):
        return self._le.inverse_transform(self._clf.predict(X))

    def predict_proba(self, X):
        return self._clf.predict_proba(X)

    @property
    def feature_importances_(self):
        return self._clf.feature_importances_
