import pandas as pd
import numpy as np
import os 
# ==========================================
# 1. CONFIGURATION
# ==========================================
# Map years to their specific filenames

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Points to: aarogya-suraksha/data/raw/HMIS
RAW_DATA_PATH = os.path.abspath(os.path.join(BASE_DIR, "..", "..", "data", "raw", "AQI","Delhi"))
OUTPUT_FILE = os.path.abspath(os.path.join(BASE_DIR, "..", "..", "data", "processed", "Delhi_AQI_Processed_2017_2019.csv"))

files = {
    2017: 'AQI_daily_city_level_delhi_2017_delhi_2017.csv',
    2018: 'AQI_daily_city_level_delhi_2018_delhi_2018.csv',
    2019: 'AQI_daily_city_level_delhi_2019_delhi_2019.csv',
    2023: 'AQI_daily_city_level_delhi_2023_delhi_2023.csv',
    2024: 'AQI_daily_city_level_delhi_2024_delhi_2024.csv'
}


# ==========================================
# 2. PROCESSING FUNCTION
# ==========================================
def process_year_df(file_path, year):
    file_path = os.path.join(RAW_DATA_PATH, file_path)
    print(f"Processing {year}...")
    try:
        # Read CSV
        df = pd.read_csv(file_path)
    except FileNotFoundError:
        print(f"❌ Error: File not found for {year}: {file_path}")
        return pd.DataFrame()

    # Normalize column names (Handle 'Date' vs 'Day')
    if 'Date' in df.columns:
        df = df.rename(columns={'Date': 'Day'})
    
    # Clean 'Day' column (remove footer rows like "Average", "Min")
    df['Day'] = pd.to_numeric(df['Day'], errors='coerce')
    df = df.dropna(subset=['Day'])
    
    # Keep only valid month columns
    valid_months = ['January', 'February', 'March', 'April', 'May', 'June', 
                    'July', 'August', 'September', 'October', 'November', 'December']
    cols_to_keep = ['Day'] + [c for c in df.columns if c in valid_months]
    df = df[cols_to_keep]
    
    # Melt: Convert Matrix (Wide) to Time Series (Long)
    melted = df.melt(id_vars=['Day'], var_name='Month', value_name='AQI')
    
    # Create proper Date objects
    # String format: "1-January-2017"
    melted['Date_Str'] = melted['Day'].astype(int).astype(str) + '-' + melted['Month'] + '-' + str(year)
    
    # Convert to datetime (Force errors='coerce' to handle Feb 30 etc.)
    melted['Datetime'] = pd.to_datetime(melted['Date_Str'], format='%d-%B-%Y', errors='coerce')
    
    # Drop invalid dates
    melted = melted.dropna(subset=['Datetime'])
    melted = melted.sort_values('Datetime')
    
    # Ensure AQI is numeric
    melted['AQI'] = pd.to_numeric(melted['AQI'], errors='coerce')
    
    return melted[['Datetime', 'AQI']]

# ==========================================
# 3. EXECUTION PIPELINE
# ==========================================

# A. Load All Years
dfs = []
for year, fname in files.items():
    processed_df = process_year_df(fname, year)
    if not processed_df.empty:
        dfs.append(processed_df)

# Combine into one big timeline
master_df = pd.concat(dfs).sort_values('Datetime')
master_df.set_index('Datetime', inplace=True)

print(f"\nTotal Daily Records Loaded: {len(master_df)}")

# B. Build the "Seasonal Master Template"
# We calculate the average AQI for every month (Jan, Feb...) using ALL 5 years of data
# This gives us the "True Shape" of Delhi's pollution season
seasonal_means = master_df.groupby(master_df.index.month)['AQI'].mean()
print("\nSeasonal Means (Delhi Template):")
print(seasonal_means)

# C. Impute Missing Data (The Smart Way)
def impute_gaps(df_subset, seasonal_template):
    df_subset = df_subset.copy()
    df_subset.set_index('Datetime', inplace=True)
    
    # 1. Linear Interpolation for small gaps (1-2 days)
    df_subset['AQI_Filled'] = df_subset['AQI'].interpolate(method='time', limit=2)
    
    # 2. Seasonal Patch for big gaps
    # Look up the missing month in our Seasonal Template and fill it
    fill_values = df_subset.index.month.map(seasonal_template)
    df_subset['AQI_Filled'] = df_subset['AQI_Filled'].fillna(fill_series_from_map(df_subset.index, seasonal_template))
    
    # 3. Fallback
    df_subset['AQI_Filled'] = df_subset['AQI_Filled'].fillna(method='ffill').fillna(method='bfill')
    
    return df_subset

def fill_series_from_map(index, mapper):
    return pd.Series(index.month.map(mapper), index=index)

# Filter only Training Years (2017, 2018, 2019)
training_raw = pd.concat([
    process_year_df(files[2017], 2017),
    process_year_df(files[2018], 2018),
    process_year_df(files[2019], 2019)
]).sort_values('Datetime')

# Apply Imputation
training_filled = impute_gaps(training_raw, seasonal_means)

# D. Aggregate to Monthly Features
# We create the 3 key columns: Avg, Max, and "Severe Days" count
monthly_features = training_filled.resample('MS').agg({
    'AQI_Filled': ['mean', 'max']
})
monthly_features.columns = ['Monthly_Avg_AQI', 'Monthly_Max_AQI']

# Add "Days > 300" (Severe Smog Days)
monthly_features['Days_Severe_AQI'] = training_filled['AQI_Filled'].resample('MS').apply(lambda x: (x > 300).sum())

# Reset index for saving
monthly_features.index.name = 'Month'
monthly_features = monthly_features.reset_index()

# E. Save
monthly_features.to_csv(OUTPUT_FILE, index=False)
print(f"\n✅ SUCCESS! Processed file saved as: {OUTPUT_FILE}")
print(monthly_features.head())