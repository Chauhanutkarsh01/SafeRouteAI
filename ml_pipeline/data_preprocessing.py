import pandas as pd
import numpy as np
import os
import hashlib
import glob

def preprocess_and_aggregate_data(crime_csv, mobility_csv, image_dir, output_pkl):
    print("Loading crime data...")
    df = pd.read_csv(crime_csv, on_bad_lines='skip')
    
    # Drop rows without Lat/Lon
    df = df.dropna(subset=['LATITUDE', 'LONGITUDE'])
    df.columns = df.columns.str.strip()
    
    print("Converting dates... this may take a moment.")
    df['Datetime'] = pd.to_datetime(df['DATE  OF OCCURRENCE'], format='%m/%d/%Y %I:%M:%S %p', errors='coerce')
    df = df.dropna(subset=['Datetime'])
    
    # Extract features
    df['HourOfDay'] = df['Datetime'].dt.hour
    df['DayOfWeek'] = df['Datetime'].dt.dayofweek
    
    # Create spatial grid
    df['Grid_Lat'] = df['LATITUDE'].round(3)
    df['Grid_Lon'] = df['LONGITUDE'].round(3)
    
    print("Aggregating into spatio-temporal clusters...")
    aggregated = df.groupby(['Grid_Lat', 'Grid_Lon', 'HourOfDay', 'DayOfWeek']).size().reset_index(name='CrimeCount')
    
    # Calculate a RiskScore from CrimeCount.
    aggregated['RiskScore_Raw'] = np.log1p(aggregated['CrimeCount'])
    max_risk = aggregated['RiskScore_Raw'].max()
    aggregated['RiskScore'] = (aggregated['RiskScore_Raw'] / max_risk) * 100
    aggregated = aggregated.drop(columns=['RiskScore_Raw'])
    
    print("Loading mobility data...")
    df_mob = pd.read_csv(mobility_csv, on_bad_lines='skip')
    df_mob['date'] = pd.to_datetime(df_mob['date'], errors='coerce')
    df_mob = df_mob.dropna(subset=['date'])
    df_mob['DayOfWeek'] = df_mob['date'].dt.dayofweek
    
    # Filter for US / Illinois to proxy the region
    df_mob_il = df_mob[df_mob['sub_region_1'] == 'Illinois']
    
    mobility_cols = [
        'retail_and_recreation_percent_change_from_baseline', 
        'grocery_and_pharmacy_percent_change_from_baseline', 
        'parks_percent_change_from_baseline', 
        'transit_stations_percent_change_from_baseline', 
        'workplaces_percent_change_from_baseline', 
        'residential_percent_change_from_baseline'
    ]
    
    # Group by DayOfWeek to get average mobility per day
    mob_agg = df_mob_il.groupby('DayOfWeek')[mobility_cols].mean().reset_index()
    mob_agg = mob_agg.fillna(0) # Failsafe
    
    print("Merging mobility data into primary dataset...")
    # Map mob_agg into aggregated
    aggregated = pd.merge(aggregated, mob_agg, on='DayOfWeek', how='left')
    
    # Fill any remaining NaNs with 0
    aggregated = aggregated.fillna(0)
    
    print("Mapping CNN proxy images...")
    # Fetch list of available proxy images
    images = glob.glob(os.path.join(image_dir, "*.jpeg"))
    
    def assign_image(lat, lon):
        if not images:
            return ""
        # Hash the coordinate to a deterministic integer
        coord_str = f"{lat}_{lon}"
        idx = int(hashlib.md5(coord_str.encode('utf-8')).hexdigest(), 16) % len(images)
        return images[idx]
    
    aggregated['ImagePath'] = aggregated.apply(lambda row: assign_image(row['Grid_Lat'], row['Grid_Lon']), axis=1)
    
    print(f"Aggregated down to {aggregated.shape[0]} samples.")
    
    # Save the aggregated dataset
    aggregated.to_pickle(output_pkl)
    print(f"Preprocessed hybrid data saved to {output_pkl}")

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    crime_path = os.path.join(current_dir, "..", "database", "Crimes_-_One_year_prior_to_present_20260401.csv")
    mobility_path = os.path.join(current_dir, "..", "database", "Google_Mobility_Data", "2022_US_Region_Mobility_Report.csv")
    image_dir = os.path.join(current_dir, "..", "database", "County_Wise_Nightlight_Images_Dataset", "dataset", "dataset")
    output_path = os.path.join(current_dir, "hybrid_aggregated_data.pkl")
    
    preprocess_and_aggregate_data(crime_path, mobility_path, image_dir, output_path)
