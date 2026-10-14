"""
Script to build comprehensive 3-month Master Dataset from historical files.
Filters out 3-wheelers ('3 Wheeler Electric') and saves to data/master_driver_data.csv.
"""

import os
import glob
import pandas as pd
from pathlib import Path

def build_master_dataset():
    base_dir = Path(__file__).parent
    historical_dir = base_dir / 'data' / 'historical'
    master_path = base_dir / 'data' / 'master_driver_data.csv'
    downloads_dir = Path(os.path.expanduser('~/Downloads'))

    files = list(historical_dir.glob('*.csv')) + list(historical_dir.glob('*.xlsx'))
    
    # Check for driver_details files in Downloads
    dl_files = list(downloads_dir.glob('driver_details*.csv')) + list(downloads_dir.glob('driver_details*.xlsx'))
    files.extend(dl_files)
    
    print(f"Found {len(files)} data files across historical folder and Downloads.")

    all_dfs = []
    
    for f in files:
        try:
            if str(f).endswith('.csv'):
                df = pd.read_csv(f)
            else:
                df = pd.read_excel(f)
                
            # Filter 3-wheelers
            if 'vehicle_type' in df.columns:
                df = df[df['vehicle_type'] != '3 Wheeler Electric']
                
            # Clean string columns
            str_cols = df.select_dtypes(include=['object']).columns
            for col in str_cols:
                df[col] = df[col].astype(str).str.strip()
                
            all_dfs.append(df)
            print(f"Processed {f.name}: {len(df)} 4-wheeler records")
        except Exception as e:
            print(f"Error reading {f.name}: {e}")

    if not all_dfs:
        print("No valid data files found.")
        return

    combined_df = pd.concat(all_dfs, ignore_index=True)
    
    # De-duplicate
    dedup_cols = [c for c in ['Date', 'driver_name', 'driver_mobile', 'vehicle_number'] if c in combined_df.columns]
    if dedup_cols:
        combined_df = combined_df.drop_duplicates(subset=dedup_cols, keep='last')
    else:
        combined_df = combined_df.drop_duplicates(keep='last')
        
    master_path.parent.mkdir(parents=True, exist_ok=True)
    combined_df.to_csv(master_path, index=False)
    
    print("=" * 60)
    print("Successfully created 3-Month Master Dataset!")
    print(f"Location: {master_path}")
    print(f"Total Records: {len(combined_df)}")
    print(f"Vehicle Types Included: {combined_df['vehicle_type'].unique() if 'vehicle_type' in combined_df.columns else 'All 4-Wheelers'}")
    print("=" * 60)

if __name__ == '__main__':
    build_master_dataset()
