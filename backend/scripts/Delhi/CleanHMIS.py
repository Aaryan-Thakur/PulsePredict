# import pandas as pd
# import os
# import glob
# import warnings

# # Suppress warnings
# warnings.filterwarnings("ignore")

# # ==========================================
# # 1. CONFIGURATION
# # ==========================================
# BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# # Points to: aarogya-suraksha/data/raw/HMIS
# RAW_DATA_PATH = os.path.abspath(os.path.join(BASE_DIR, "..", "..", "data", "raw", "HMIS"))
# OUTPUT_FILE = os.path.abspath(os.path.join(BASE_DIR, "..", "..", "data", "final", "Delhi_Master_Training_Data.csv"))

# # Mapping: { "Text to Search in Raw File" : "Clean Column Name for Model" }
# # Ensure these search terms exist in your raw Excel rows!
# DISEASE_MAPPING = {
#     'Patients registered at Emergency': 'Patients registered at Emergency Department',
#     'Emergency - Trauma': 'Trauma_and_Burns',
#     'Acute Caridiac Emergencies': 'Cardiac_and_Stroke',
#     'Respiratory infections': 'Respiratory_Admissions',
#     'Inpatient - Dengue': 'Total_Dengue_Cases',
#     'Inpatient - Malaria': 'Total_Malaria_Cases',
#     'Diarrhoea treated in Inpatients': 'Water_Borne_Diseases'
# }

# MONTH_MAP = {
#     'January': 1, 'February': 2, 'March': 3, 'April': 4, 'May': 5, 'June': 6,
#     'July': 7, 'August': 8, 'September': 9, 'October': 10, 'November': 11, 'December': 12
# }

# # ==========================================
# # 2. FILE READING UTILS
# # ==========================================
# def read_messy_file(file_path):
#     """Tries multiple engines to read the file."""
#     # 1. Try as Standard Excel
#     try:
#         return pd.read_excel(file_path, header=None)
#     except:
#         pass
    
#     # 2. Try as HTML (Common for government reports saved as .xls)
#     try:
#         dfs = pd.read_html(file_path)
#         if dfs: return dfs[0]
#     except:
#         pass
        
#     # 3. Try as CSV (Comma)
#     try:
#         return pd.read_csv(file_path, header=None)
#     except:
#         pass

#     # 4. Try as CSV (Tab separated)
#     try:
#         return pd.read_csv(file_path, sep='\t', header=None)
#     except:
#         pass
        
#     return None

# def find_public_column_and_header(df):
#     """
#     Scans the dataframe to find where the data actually starts.
#     We look for the 'Public [A]' column under '_Delhi'.
#     """
#     for r_idx, row in df.iterrows():
#         row_str = row.astype(str).values
#         # Check if this row looks like a header
#         if "Public [A]" in list(row_str):
#             # Iterate to find the *first* "Public [A]" (Delhi Total)
#             for c_idx, val in enumerate(row_str):
#                 if val.strip() == "Public [A]":
#                     return r_idx, c_idx
#     return None, None

# def extract_data(file_path, month_name, year):
#     df = read_messy_file(file_path)
    
#     if df is None:
#         print(f"  ❌ Could not read file format: {os.path.basename(file_path)}")
#         return None

#     # Find the magic coordinates
#     header_row_idx, public_col_idx = find_public_column_and_header(df)

#     if public_col_idx is None:
#         # print(f"  ⚠️ 'Public [A]' header not found in {os.path.basename(file_path)}")
#         return None

#     extracted = {}
#     extracted['Month'] = f"{year}-{MONTH_MAP[month_name]:02d}-01"

#     # Slice data below the header
#     data_slice = df.iloc[header_row_idx+1 : ]

#     # Iterate through our target diseases
#     for raw_keyword, clean_name in DISEASE_MAPPING.items():
#         found = False
        
#         # Search the first 5 columns for the disease name
#         # (Because sometimes it's in Col 0, sometimes Col 2)
#         for search_col in range(0, min(5, df.shape[1])):
#             match = data_slice[data_slice.iloc[:, search_col].astype(str).str.contains(raw_keyword, case=False, na=False)]
            
#             if not match.empty:
#                 val = str(match.iloc[0, public_col_idx]).replace(',', '').strip()
#                 extracted[clean_name] = pd.to_numeric(val, errors='coerce')
#                 found = True
#                 break
        
#         if not found:
#             extracted[clean_name] = 0

#     return extracted

# # ==========================================
# # 3. MAIN EXECUTION
# # ==========================================
# def main():
#     print(f"🚀 Starting HMIS Data Extraction...")
#     print(f"   Looking in: {RAW_DATA_PATH}")
    
#     if not os.path.exists(RAW_DATA_PATH):
#         print(f"❌ Error: Folder not found! Please create: {RAW_DATA_PATH}")
#         return

#     all_records = []
#     years = [2017, 2018, 2019]

#     for year in years:
#         year_path = os.path.join(RAW_DATA_PATH, str(year), "Delhi")
#         if not os.path.exists(year_path):
#             print(f"   ⚠️ Skipping {year} (Folder not found)")
#             continue
            
#         print(f"   Processing {year}...")
        
#         for month_name in MONTH_MAP.keys():
#             # Match files like "A - Delhi_April.xls" OR "Delhi_April.csv"
#             search_pattern = os.path.join(year_path, f"*{month_name}*")
#             found_files = glob.glob(search_pattern)
            
#             # Filter out non-data files if any
#             valid_files = [f for f in found_files if '.xls' in f or '.csv' in f]
            
#             if valid_files:
#                 record = extract_data(valid_files[0], month_name, year)
#                 if record:
#                     all_records.append(record)
#             else:
#                 pass # Silently skip missing months

#     # Save
#     if all_records:
#         final_df = pd.DataFrame(all_records)
#         final_df['Month'] = pd.to_datetime(final_df['Month'])
#         final_df = final_df.sort_values('Month')
        
#         # Ensure output folder exists
#         os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
#         final_df.to_csv(OUTPUT_FILE, index=False)
        
#         print("\n" + "="*40)
#         print(f"✅ SUCCESS! Extracted {len(final_df)} months.")
#         print(f"📁 Saved to: {OUTPUT_FILE}")
#         print("="*40)
#         print(final_df.head())
#     else:
#         print("\n❌ FAILURE: No data extracted. Check folder structure and file names.")

# if __name__ == "__main__":
#     main()