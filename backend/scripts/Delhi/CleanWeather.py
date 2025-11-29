import pandas as pd
import numpy as np
import os
# ==========================================
# 1. CONFIGURATION
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
input_file = os.path.abspath(os.path.join(BASE_DIR, "..", "..", "data", "raw", "Weather","Delhi","kaggel_weather_2013_to_2024.csv"))
output_file = os.path.abspath(os.path.join(BASE_DIR, "..", "..", "data", "processed", "Delhi_Weather_Processed.csv"))
# ==========================================
# 2. LOAD & INSPECT
# ==========================================
print("Loading Weather Data...")
try:
    df = pd.read_csv(input_file)
except FileNotFoundError:
    print(f"❌ Error: Could not find '{input_file}'. Make sure it is in the folder.")
    exit()

# Convert DATE to datetime
df['DATE'] = pd.to_datetime(df['DATE'])

# Set as Index
df.set_index('DATE', inplace=True)

# ==========================================
# 3. IMPUTE MISSING VALUES (Seasonal Patch)
# ==========================================
# Even Kaggle datasets have gaps. We fix them using the 10-year seasonal average.
print("Checking for missing values...")

# Calculate long-term averages for each month (e.g., Avg Temp in Jan across 10 years)
seasonal_means = df.groupby(df.index.month)[['temp', 'humidity', 'windspeed', 'precip']].transform('mean')

# Fill NaNs with the seasonal average
df.fillna(seasonal_means, inplace=True)
df.fillna(method='ffill', inplace=True) # Fallback for edge cases

# ==========================================
# 4. AGGREGATE TO MONTHLY
# ==========================================
print("Aggregating to Monthly Level...")

# Logic: 
# - Temperature/Humidity/Wind = Average of the month
# - Rain = Sum of the month (Accumulated rainfall)
monthly_df = df.resample('MS').agg({
    'temp': 'mean',
    'humidity': 'mean',
    'windspeed': 'mean',
    'precip': 'sum'
})

# Rename columns to match your Model's expectations
monthly_df.columns = ['Monthly_Avg_Temp', 'Monthly_Avg_Humidity', 'Monthly_Avg_Wind', 'Rainfall_mm']

# ==========================================
# 5. FORMATTING & SAVING
# ==========================================
# Reset index to make 'Month' a column
monthly_df.index.name = 'Month'
monthly_df.reset_index(inplace=True)

# Filter for relevant years (2017 onwards) to keep file size clean
monthly_df = monthly_df[monthly_df['Month'].dt.year >= 2017]

print("\nProcessed Data Head:")
print(monthly_df.head())

# Save
monthly_df.to_csv(output_file, index=False)
print(f"\n✅ SUCCESS! Saved processed weather data to: {output_file}")