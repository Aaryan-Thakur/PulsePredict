import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import os

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_FILE = os.path.abspath(os.path.join(BASE_DIR, "..", "..", "data", "final", "Delhi_Master_Dataset.csv"))

def analyze_trauma():
    print("Loading Data...")
    df = pd.read_csv(INPUT_FILE)
    
    # 1. NORMALIZE THE SUB-TYPES
    # We need to look at specific rates, not the total lump sum
    denominator = df['Total_Emergency_Footfall'].replace(0, 1)
    
    df['Rate_Cardiac'] = (df['Cardiac'] / denominator) * 1000
    df['Rate_Burn'] = (df['Burn'] / denominator) * 1000
    df['Rate_Accident'] = (df['Trauma'] / denominator) * 1000 # 'Trauma' column usually implies accidents/injury

    # 2. DEFINE SUSPECTS (Features we think might be guilty)
    suspects = [
        'Monthly_Avg_Temp', 'Monthly_Avg_AQI', 'Rainfall_mm', 
        'Has_Diwali', 
        'chest pain', 'headache', 'fatigue' # Google Trends
    ]
    
    targets = ['Rate_Cardiac', 'Rate_Burn', 'Rate_Accident']

    # 3. RUN CORRELATION MATRIX
    print("\n🕵️ FORENSIC ANALYSIS: What correlates with Trauma?")
    print("-" * 60)
    
    # We calculate the correlation matrix
    analysis_df = df[targets + suspects]
    corr_matrix = analysis_df.corr()
    
    # Filter to only show how Targets correlate with Suspects
    target_corrs = corr_matrix.loc[targets, suspects]
    
    print(target_corrs.round(2))
    
    # 4. GENERATE HEATMAP VISUALIZATION
    plt.figure(figsize=(10, 6))
    sns.heatmap(target_corrs, annot=True, cmap='coolwarm', center=0, fmt=".2f")
    plt.title("Correlation: Environmental Factors vs. Acute Trauma")
    plt.tight_layout()
    plt.savefig("Trauma_Correlations.png")
    print("\n✅ Heatmap saved as 'Trauma_Correlations.png'")
    
    # 5. AUTOMATIC INSIGHT GENERATOR
    print("\n💡 AI INSIGHTS:")
    
    # Check Cardiac
    cardiac_aqi = target_corrs.loc['Rate_Cardiac', 'Monthly_Avg_AQI']
    cardiac_temp = target_corrs.loc['Rate_Cardiac', 'Monthly_Avg_Temp']
    cardiac_search = target_corrs.loc['Rate_Cardiac', 'chest pain']
    
    if cardiac_aqi > 0.3:
        print(f"  - ❤️ CARDIAC ALERT: Strong link to Pollution (Corr: {cardiac_aqi:.2f}). Smog causes heart attacks.")
    if cardiac_temp < -0.3:
        print(f"  - ❤️ CARDIAC ALERT: Strong link to Cold Weather (Corr: {cardiac_temp:.2f}). Winter induces vasoconstriction.")
    if cardiac_search > 0.3:
        print(f"  - ❤️ CARDIAC ALERT: People search 'Chest Pain' before arriving (Corr: {cardiac_search:.2f}).")

    # Check Burns
    burn_diwali = target_corrs.loc['Rate_Burn', 'Has_Diwali']
    if burn_diwali > 0.4:
        print(f"  - 🔥 BURN ALERT: Massive link to Diwali (Corr: {burn_diwali:.2f}). This is highly predictable.")

    # Check Accidents
    acc_rain = target_corrs.loc['Rate_Accident', 'Rainfall_mm']
    if abs(acc_rain) < 0.2:
        print(f"  - 🚗 ACCIDENT INSIGHT: Rainfall has little effect (Corr: {acc_rain:.2f}). Traffic accidents appear random or behavioral.")

if __name__ == "__main__":
    analyze_trauma()