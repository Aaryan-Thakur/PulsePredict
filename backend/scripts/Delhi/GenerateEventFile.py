import pandas as pd
import os
# 1. Create Monthly Timeline (2017-2019)
dates = pd.date_range(start='2017-01-01', end='2019-12-01', freq='MS')
df = pd.DataFrame({'Date': dates})

# 2. Define Event Dates (Month, Year)
# Note: These shift every year
diwali_dates = [(10, 2017), (11, 2018), (10, 2019)]
holi_dates = [(3, 2017), (3, 2018), (3, 2019)]
dussehra_dates = [(9, 2017), (10, 2018), (10, 2019)]

# Eid happens multiple times a year (Fitr & Adha), we flag months containing either
eid_dates = [
    (6, 2017), (9, 2017), 
    (6, 2018), (8, 2018),
    (6, 2019), (8, 2019)
]

# 3. Helper Function to Flag Events
def check_event(row, date_list):
    # Returns 1 if the (Month, Year) exists in the provided list
    return 1 if (row['Date'].month, row['Date'].year) in date_list else 0

# 4. Apply Logic for Variable Events
df['Has_Diwali'] = df.apply(lambda x: check_event(x, diwali_dates), axis=1)
df['Has_Holi'] = df.apply(lambda x: check_event(x, holi_dates), axis=1)
df['Has_Dussehra'] = df.apply(lambda x: check_event(x, dussehra_dates), axis=1)
df['Has_Eid'] = df.apply(lambda x: check_event(x, eid_dates), axis=1)

# 5. Apply Logic for Fixed Events & Seasons
# Independence Day is always August (Month 8)
df['Has_Independence_Day'] = df['Date'].apply(lambda x: 1 if x.month == 8 else 0)

# Republic Day is always January (Month 1)
df['Has_Republic_Day'] = df['Date'].apply(lambda x: 1 if x.month == 1 else 0)

# Crop Burning Season (Stubble Burning)
# Typically peaks in October (10) and November (11) in Delhi
df['Has_Crop_Burning'] = df['Date'].apply(lambda x: 1 if x.month in [10, 11] else 0)

output_filename = 'Delhi_Major_Events_2017_2019.csv'
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.abspath(os.path.join(BASE_DIR, "..", "..", "data", "processed", output_filename))
# 6. Save to CSV
df.to_csv(OUTPUT_FILE, index=False)

print(f"File '{OUTPUT_FILE}' generated successfully.")
print(df.head(12)) # Preview the first year