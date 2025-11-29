import pandas as pd
import os

# Define paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DATA_PATH = os.path.abspath(os.path.join(BASE_DIR, "..", "..", "data", "processed"))
OUTPUT_FILE = os.path.abspath(os.path.join(BASE_DIR, "..", "..", "data", "final", "Delhi_Master_Dataset.csv"))

# Global variable to hold data between functions
master_df = None

def create_master_dataset():
    global master_df
    print("Loading datasets...")
    
    # 1. Load all CSV files
    # Note: Ensure these files are in the same directory as this script or update paths
    df_hospital = pd.read_csv(os.path.abspath(os.path.join(BASE_DIR, "..", "..", "data", "processed", "Delhi_Hospital_Data.csv"))) 
    df_events = pd.read_csv(os.path.abspath(os.path.join(BASE_DIR, "..", "..", "data", "processed", "Delhi_Major_Events_2017_2019.csv")))
    df_weather = pd.read_csv(os.path.abspath(os.path.join(BASE_DIR, "..", "..", "data", "processed", "Delhi_Weather_Processed.csv")))
    df_aqi = pd.read_csv(os.path.abspath(os.path.join(BASE_DIR, "..", "..", "data", "processed", "Delhi_AQI_Processed_2017_2019.csv")))
    df_trends = pd.read_csv(os.path.abspath(os.path.join(BASE_DIR, "..", "..", "data", "processed", "Delhi_Google_Trends_Health.csv")))

    # ---------------------------------------------------------
    # 2. Process Hospital Data (The Target)
    # ---------------------------------------------------------
    print("Processing Hospital Data...")
    
    # Reshape from Wide to Long format
    df_hospital_long = df_hospital.melt(
        id_vars=['Name'], 
        var_name='Date', 
        value_name='Patient_Count'
    )
    
    # Convert Date strings to proper Datetime objects
    df_hospital_long['Date'] = pd.to_datetime(df_hospital_long['Date'], format='%d-%m-%Y')

    # ---------------------------------------------------------
    # 3. Process External Data (The Features)
    # ---------------------------------------------------------
    print("Processing External Features...")

    # Standardize 'Date' column names and formats for merging
    df_events['Date'] = pd.to_datetime(df_events['Date'])
    
    df_weather['Month'] = pd.to_datetime(df_weather['Month'])
    df_weather.rename(columns={'Month': 'Date'}, inplace=True)
    
    df_aqi['Month'] = pd.to_datetime(df_aqi['Month'])
    df_aqi.rename(columns={'Month': 'Date'}, inplace=True)
    
    df_trends['date'] = pd.to_datetime(df_trends['date'])
    df_trends.rename(columns={'date': 'Date'}, inplace=True)

    # ---------------------------------------------------------
    # 4. Merge Everything (Left Join)
    # ---------------------------------------------------------
    print("Merging datasets...")
    
    master_df = df_hospital_long.merge(df_events, on='Date', how='left')
    master_df = master_df.merge(df_weather, on='Date', how='left')
    master_df = master_df.merge(df_aqi, on='Date', how='left')
    master_df = master_df.merge(df_trends, on='Date', how='left')

    # Clean up
    master_df.sort_values(by=['Date', 'Name'], inplace=True)
    master_df.fillna(method='ffill', inplace=True)
    print("Master dataset created in memory.")


def group_and_refine_data():
    global master_df
    print("Refining and Grouping Data...")
    
    if master_df is None:
        print("Error: Master DataFrame is empty. Did create_master_dataset() run?")
        return

    # 1. CLEAN UP NAMES
    name_map = {
        'Inpatient - Asthma, Chronic Obstructive Pulmonary Disease (COPD), Respiratory infections': 'Asthma_COPD',
        'Inpatient - Tuberculosis': 'Tuberculosis',
        'Inpatient - Dengue': 'Dengue',
        'Inpatient - Malaria': 'Malaria',
        'Inpatient - Pyrexia of unknown origin (PUO)': 'Fever_Unknown',
        'Inpatient - Diarrhea with dehydration': 'Diarrhea_Adult',
        'Childhood Diseases - Diarrhoea treated in Inpatients': 'Diarrhea_Child',
        'Inpatient - Typhoid': 'Typhoid',
        'Inpatient - Hepatitis': 'Hepatitis',
        'Emergency - Trauma ( accident, injury, poisoning etc)': 'Trauma',
        'Emergency - Acute Caridiac Emergencies': 'Cardiac',
        'Emergency - Burn': 'Burn',
        'Patients registered at Emergency Department': 'Total_Emergency_Footfall'
    }
    
    # Filter only for the rows present in our map
    df = master_df[master_df['Name'].isin(name_map.keys())].copy()
    
    # Apply the short names
    df['Short_Name'] = df['Name'].map(name_map)

    # 2. PIVOT THE TABLE
    print("Pivoting data to wide format...")
    
    # --- UPDATED FEATURE LIST ---
    # We must explicitly list every column we want to keep in the final file.
    # If it's not in this list (and not a pivot column), pandas drops it.
    feature_cols = [
        'Date', 
        # Weather & Environmental
        'Monthly_Avg_Temp', 'Rainfall_mm', 'Monthly_Avg_Humidity', 
        'Monthly_Avg_AQI', 'Days_Severe_AQI', 'Has_Diwali', 
        # Google Trends (ALL COLUMNS ADDED HERE)
        'asthma', 'dengue', 'fever', 'cough', 'cold', 
        'sore throat', 'loose motion', 'vomiting', 
        'stomach pain', 'chest pain', 'headache', 'fatigue'
    ]
    
    df_wide = df.pivot_table(
        index=feature_cols,
        columns='Short_Name',
        values='Patient_Count',
        aggfunc='sum'
    ).reset_index()

    # Fill NaNs before calculation
    df_wide.fillna(0, inplace=True)

    # 3. CREATE GROUPS
    print("Creating Disease Groups...")
    
    df_wide['Group_Respiratory'] = df_wide['Asthma_COPD'] + df_wide['Tuberculosis']
    df_wide['Group_Vector'] = df_wide['Dengue'] + df_wide['Malaria'] + df_wide['Fever_Unknown']
    df_wide['Group_Water'] = df_wide['Diarrhea_Adult'] + df_wide['Diarrhea_Child'] + df_wide['Typhoid'] + df_wide['Hepatitis']
    df_wide['Group_Trauma'] = df_wide['Trauma'] + df_wide['Cardiac'] + df_wide['Burn']

    # ---------------------------------------------------------
    # 4. NORMALIZE
    # ---------------------------------------------------------
    print("Normalizing data (Cases per 1000 Emergency Visits)...")
    
    denominator = df_wide['Total_Emergency_Footfall'].replace(0, 1)
    
    df_wide['Rate_Respiratory'] = (df_wide['Group_Respiratory'] / denominator) * 1000
    df_wide['Rate_Vector'] = (df_wide['Group_Vector'] / denominator) * 1000
    df_wide['Rate_Water'] = (df_wide['Group_Water'] / denominator) * 1000
    df_wide['Rate_Trauma'] = (df_wide['Group_Trauma'] / denominator) * 1000

    # 5. SAVE
    df_wide.to_csv(OUTPUT_FILE, index=False)
    
    print(f"Success! Grouped data saved to: {OUTPUT_FILE}")
    print("New Normalized Columns: ['Rate_Respiratory', 'Rate_Vector', 'Rate_Water', 'Rate_Trauma']")
    print(df_wide[['Date', 'Rate_Respiratory', 'Rate_Vector']].head())

if __name__ == "__main__":
    create_master_dataset()
    group_and_refine_data()