import pandas as pd
import numpy as np
import joblib
from datetime import datetime

from sklearn.model_selection import (
    train_test_split,
    StratifiedKFold,
    cross_val_score,
    RandomizedSearchCV
)

from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder, LabelEncoder
from sklearn.impute import SimpleImputer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import FunctionTransformer

# Top-level function for flattening text (for pickling compatibility)
def flatten_text(x):
    return x.squeeze()

from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC

from sklearn.metrics import accuracy_score, f1_score

import warnings
warnings.filterwarnings("ignore")

# -----------------------
# LOAD DATA
# -----------------------
df = pd.read_csv("ml/travel_dataset.csv")

df["family_friendly"] = df["family_friendly"].astype(int)

# -----------------------
# TEXT FEATURE ENGINEERING
# -----------------------
df["text"] = df["description"].fillna("") + " " + df["key_activities"].fillna("")

features = [
    "avg_cost_per_day",
    "family_friendly",
    "text"
]

target = "label"

# Encode labels
label_encoder = LabelEncoder()
df[target] = label_encoder.fit_transform(df[target])

# FORCE SAFE DF (IMPORTANT FIX)
X = df[features].copy()
y = df[target]

# -----------------------
# TRAIN / TEST SPLIT
# -----------------------
X_train, X_test, y_train, y_test = train_test_split(
    X, y,
    test_size=0.2,
    random_state=42,
    stratify=y
)

# -----------------------
# PREPROCESSOR
# -----------------------
def build_preprocessor():

    numeric_features = ["avg_cost_per_day"]
    binary_features = ["family_friendly"]
    categorical_features = ["country", "destination_name"]

    # FIXED TEXT PIPELINE (flatten to 1D for TfidfVectorizer)
    text_features = ["text"]
    text_pipeline = Pipeline([
        ("flatten", FunctionTransformer(flatten_text, validate=False)),
        ("tfidf", TfidfVectorizer(
            max_features=300,
            stop_words="english"
        ))
    ])

    numeric_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="mean")),
        ("scaler", StandardScaler())
    ])

    binary_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent"))
    ])

    categorical_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False))
    ])

    return ColumnTransformer([
        ("num", numeric_pipeline, numeric_features),
        ("bin", binary_pipeline, binary_features),
        ("cat", categorical_pipeline, categorical_features),
        ("txt", text_pipeline, text_features)
    ])

# -----------------------
# MODELS
# -----------------------
models = {
    "log_reg": (
        LogisticRegression(max_iter=1000),
        {"clf__C": [0.1, 1, 10]}
    ),

    "rf": (
        RandomForestClassifier(random_state=42),
        {
            "clf__n_estimators": [100, 200],
            "clf__max_depth": [None, 10, 20]
        }
    ),

    "svm": (
        SVC(),
        {
            "clf__C": [0.5, 1, 2],
            "clf__kernel": ["linear", "rbf"]
        }
    )
}

# -----------------------
# CV SETUP
# -----------------------
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

results_log = []

best_model = None
best_score = 0
best_name = ""

# -----------------------
# TRAIN LOOP
# -----------------------
for name, (model, params) in models.items():

    print(f"\nTraining: {name}")

    pipeline = Pipeline([
        ("preprocessor", build_preprocessor()),
        ("clf", model)
    ])

    search = RandomizedSearchCV(
        pipeline,
        param_distributions=params,
        n_iter=5,
        scoring="f1_macro",
        cv=cv,
        random_state=42,
        n_jobs=-1
    )

    search.fit(X_train, y_train)

    best_estimator = search.best_estimator_

    cv_scores = cross_val_score(
        best_estimator,
        X_train,
        y_train,
        cv=cv,
        scoring="f1_macro"
    )

    y_pred = best_estimator.predict(X_test)

    acc = accuracy_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred, average="macro")

    print("Best Params:", search.best_params_)
    print(f"CV F1: {cv_scores.mean():.3f} ± {cv_scores.std():.3f}")
    print(f"Test Accuracy: {acc:.3f}")
    print(f"Test Macro F1: {f1:.3f}")

    results_log.append({
        "model": name,
        "best_params": str(search.best_params_),
        "cv_f1_mean": cv_scores.mean(),
        "cv_f1_std": cv_scores.std(),
        "test_accuracy": acc,
        "test_f1_macro": f1,
        "timestamp": datetime.now().isoformat()
    })

    if f1 > best_score:
        best_score = f1
        best_model = best_estimator
        best_name = name

# -----------------------
# SAVE RESULTS
# -----------------------
pd.DataFrame(results_log).to_csv("ml_results.csv", index=False)

print("\n======================")
print(f"BEST MODEL: {best_name}")
print(f"BEST F1 SCORE: {best_score:.3f}")
print("======================")

joblib.dump(best_model, "travel_model.joblib")
joblib.dump(label_encoder, "label_encoder.joblib")

print("Model saved successfully.")