import pandas as pd

df = pd.read_csv("ml/travel_dataset.csv")

print("Total rows:", len(df))
print("Class distribution:\n", df['label'].value_counts())
print("Missing values:\n", df.isnull().sum())
print("Duplicate destinations:", df.duplicated(subset=['destination_name', 'country']).sum())
print("Sample rows:\n", df.sample(5))