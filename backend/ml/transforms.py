"""
Shared transform functions used in the sklearn pipeline.
Defined here (not in train.py or __main__) so joblib can resolve
the reference when unpickling the saved model.
"""


def flatten_text(x):
    """TfidfVectorizer needs a 1-D series, not a DataFrame column.
    iloc[:, 0] always returns a Series, even with a single row.
    (squeeze() collapses to a scalar when n=1, breaking TF-IDF.)
    """
    if hasattr(x, "iloc"):
        return x.iloc[:, 0]
    return x
