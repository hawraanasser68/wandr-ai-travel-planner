"""
ML Classifier Training Script
-------------------------------
Classifies destinations into 6 travel styles:
  Adventure | Relaxation | Culture | Budget | Luxury | Family

Features used (justified):
  - avg_cost_per_day  : strongest numeric signal — Budget <$50, Luxury >$400
  - family_friendly   : direct binary signal for Family vs Adventure
  - country           : geographic context (encoded with OneHot, unknown=ignore)
  - text              : description + key_activities via TF-IDF

Deliberately EXCLUDED:
  - destination_name  : would cause data leakage — names like "Cusco Backpacker"
                        directly encode the label.

Run from backend/:
  python -m ml.train
"""

import warnings
from datetime import datetime
from pathlib import Path

import joblib
import pandas as pd
from classifier.transforms import flatten_text  # noqa: F401 — must be importable for pickle
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    f1_score,
)
from sklearn.model_selection import (
    RandomizedSearchCV,
    StratifiedKFold,
    cross_val_score,
    train_test_split,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import (
    FunctionTransformer,
    LabelEncoder,
    OneHotEncoder,
    StandardScaler,
)
from sklearn.svm import SVC

warnings.filterwarnings("ignore")

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
DATASET_PATH = BASE_DIR / "datasets" / "travel_dataset.csv"
ARTIFACTS_DIR = BASE_DIR.parent / "artifacts"
ARTIFACTS_DIR.mkdir(exist_ok=True)
RESULTS_PATH = ARTIFACTS_DIR / "ml_results.csv"
MODEL_PATH = ARTIFACTS_DIR / "travel_model.joblib"
ENCODER_PATH = ARTIFACTS_DIR / "label_encoder.joblib"


def build_preprocessor() -> ColumnTransformer:
    """
    Assembles the feature preprocessing pipeline.
    All preprocessing lives inside the pipeline to prevent leakage.
    """
    # TF-IDF on the combined text field (description + activities)
    # max_features=300 keeps dimensionality manageable for a small dataset
    text_pipeline = Pipeline([
        ("flatten", FunctionTransformer(flatten_text, validate=False)),
        ("tfidf", TfidfVectorizer(max_features=300, stop_words="english")),
    ])

    return ColumnTransformer([
        ("num", Pipeline([
            ("impute", SimpleImputer(strategy="mean")),
            ("scale", StandardScaler()),
        ]), ["avg_cost_per_day"]),

        ("bin", SimpleImputer(strategy="most_frequent"), ["family_friendly"]),

        ("cat", Pipeline([
            ("impute", SimpleImputer(strategy="most_frequent")),
            # handle_unknown="ignore" so unseen countries at inference don't crash
            ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]), ["country"]),

        ("txt", text_pipeline, ["text"]),
    ])


def train_and_save() -> None:
    # ── Load & engineer ──────────────────────────────────────────────────────
    df = pd.read_csv(DATASET_PATH)
    df["family_friendly"] = df["family_friendly"].astype(int)
    df["text"] = df["description"].fillna("") + " " + df["key_activities"].fillna("")

    # destination_name is intentionally excluded (see module docstring)
    FEATURES = ["avg_cost_per_day", "family_friendly", "country", "text"]
    TARGET = "label"

    label_encoder = LabelEncoder()
    df[TARGET] = label_encoder.fit_transform(df[TARGET])

    X = df[FEATURES].copy()
    y = df[TARGET]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # ── Model candidates ─────────────────────────────────────────────────────
    candidates = {
        "logistic_regression": (
            LogisticRegression(
                max_iter=1000,
                class_weight="balanced",   # handles imbalance
                random_state=42,
            ),
            {"clf__C": [0.01, 0.1, 1, 10]},
        ),
        "random_forest": (
            RandomForestClassifier(
                class_weight="balanced",
                random_state=42,
            ),
            {
                "clf__n_estimators": [100, 200],
                "clf__max_depth": [5, 10, 20],
                "clf__min_samples_leaf": [2, 5],
            },
        ),
        "svm": (
            # probability=True enables predict_proba — required for agent integration
            SVC(probability=True, class_weight="balanced", random_state=42),
            {
                "clf__C": [0.5, 1, 2],
                "clf__kernel": ["linear", "rbf"],
            },
        ),
    }

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    results_log = []
    best_model = None
    best_score = 0.0
    best_name = ""

    # ── Training loop ─────────────────────────────────────────────────────────
    for name, (estimator, params) in candidates.items():
        print(f"\n── Training: {name} ──")

        pipeline = Pipeline([
            ("preprocessor", build_preprocessor()),
            ("clf", estimator),
        ])

        search = RandomizedSearchCV(
            pipeline,
            param_distributions=params,
            n_iter=5,
            scoring="f1_macro",
            cv=cv,
            random_state=42,
            n_jobs=-1,
        )
        search.fit(X_train, y_train)
        best_est = search.best_estimator_

        cv_scores = cross_val_score(
            best_est, X_train, y_train, cv=cv, scoring="f1_macro"
        )
        y_pred = best_est.predict(X_test)

        acc = accuracy_score(y_test, y_pred)
        f1 = f1_score(y_test, y_pred, average="macro")

        print(f"Best params : {search.best_params_}")
        print(f"CV F1       : {cv_scores.mean():.3f} ± {cv_scores.std():.3f}")
        print(f"Test Acc    : {acc:.3f}  |  Test Macro F1: {f1:.3f}")

        # Per-class metrics — the brief requires this, not just averages
        print("\nPer-class report:")
        print(
            classification_report(
                y_test,
                y_pred,
                target_names=label_encoder.classes_,
            )
        )

        results_log.append({
            "model": name,
            "best_params": str(search.best_params_),
            "cv_f1_mean": round(cv_scores.mean(), 4),
            "cv_f1_std": round(cv_scores.std(), 4),
            "test_accuracy": round(acc, 4),
            "test_f1_macro": round(f1, 4),
            "timestamp": datetime.now().isoformat(),
        })

        gap = f1_score(y_train, best_est.predict(X_train), average="macro") - cv_scores.mean()
        if gap > 0.05:
            print(f"  ⚠ possible overfit (gap={gap:.3f})")

        if cv_scores.mean() > best_score:
            best_score = cv_scores.mean()
            best_model = best_est
            best_name = name

    # ── Save ─────────────────────────────────────────────────────────────────
    pd.DataFrame(results_log).to_csv(RESULTS_PATH, index=False)

    print(f"\n{'='*40}")
    print(f"BEST MODEL : {best_name}  (Macro F1 = {best_score:.3f})")
    print(f"{'='*40}")

    joblib.dump(best_model, MODEL_PATH)
    joblib.dump(label_encoder, ENCODER_PATH)
    print(f"Saved → {MODEL_PATH}")
    print(f"Saved → {ENCODER_PATH}")


if __name__ == "__main__":
    train_and_save()
