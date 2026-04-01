import pandas as pd

print("Program started...")

# --- LOAD FILE ---
file_name = "usaspending_awards.csv.xlsm"
df = pd.read_excel(file_name)

print("Total rows loaded:", len(df))

# --- CONTRACT SIZE ONLY ---
df["current_total_value_of_award"] = pd.to_numeric(
    df["current_total_value_of_award"], errors="coerce"
).fillna(0)

MIN_VALUE = 5_000_000
MAX_VALUE = 50_000_000

df = df[
    (df["current_total_value_of_award"] >= MIN_VALUE) &
    (df["current_total_value_of_award"] <= MAX_VALUE)
]

print("After size filter:", len(df))

# --- SORT RESULTS ---
df = df.sort_values(
    by="current_total_value_of_award",
    ascending=False
)

# --- SAVE OUTPUT ---
output_file = "filtered_opportunities.csv"
df.to_csv(output_file, index=False)

print(f"Saved as {output_file}")

# --- SHOW SAMPLE OUTPUT ---
columns_to_show = [
    "recipient_name",
    "awarding_agency_name",
    "current_total_value_of_award",
    "naics_code",
    "prime_award_base_transaction_description"
]

available_cols = [col for col in columns_to_show if col in df.columns]

print("\nTop results:")
print(df[available_cols].head(10))

print("\nDONE ✅")