"""Model settings preserved from the supplied experiment (no tuning on test data)."""
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from xgboost import XGBClassifier

def build_model(name: str, seed: int):
    if name == "logistic_regression":
        return make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000, random_state=seed))
    if name == "random_forest":
        return RandomForestClassifier(n_estimators=100, random_state=seed, n_jobs=1)
    if name == "svm":
        return make_pipeline(StandardScaler(), SVC(kernel="rbf", random_state=seed))
    if name == "xgboost":
        return XGBClassifier(n_estimators=200, max_depth=6, learning_rate=0.1,
                             random_state=seed, n_jobs=1, eval_metric="logloss")
    raise ValueError(f"Unknown model: {name}")
