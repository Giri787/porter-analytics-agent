"""
Data Processor Module
Handles loading, cleaning, and preprocessing Porter driver data from Excel files.
"""

import pandas as pd
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class DataProcessor:
    """Processes Porter driver performance data from Excel files."""
    
    # Define expected columns and their data types
    EXPECTED_COLUMNS = {
        'Date': 'datetime',
        'driver_name': 'str',
        'driver_mobile': 'str',
        'driver_geo_region': 'str',
        'vehicle_number': 'str',
        'vehicle_type': 'str',
    }
    
    def __init__(self):
        """Initialize data processor."""
        self.df = None
        self.metadata = {}
        
    def load_data(self, filepath: str) -> bool:
        """
        Load data from Excel or CSV file.
        
        Args:
            filepath: Path to data file
            
        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            logger.info(f"Loading data file: {filepath}")
            
            # Check file extension
            if filepath.lower().endswith('.csv'):
                self.df = pd.read_csv(filepath)
            else:
                self.df = pd.read_excel(filepath)
            
            logger.info(f"Loaded {len(self.df)} rows and {len(self.df.columns)} columns")
            
            # Store metadata
            self.metadata = {
                'filepath': filepath,
                'load_time': datetime.now(),
                'total_rows': len(self.df),
                'total_columns': len(self.df.columns),
                'columns': list(self.df.columns)
            }
            
            return True
            
        except Exception as e:
            logger.error(f"Error loading data file: {str(e)}", exc_info=True)
            return False

    def filter_vehicle_type(self, exclude_type: str = "3 Wheeler Electric") -> bool:
        """
        Filter out specific vehicle types (e.g., 3-wheelers).
        
        Args:
            exclude_type: Vehicle type to exclude
            
        Returns:
            True if filtering successful (or not needed), False on error
        """
        try:
            if self.df is None:
                return False
                
            if 'vehicle_type' not in self.df.columns:
                logger.warning("vehicle_type column not found, skipping filter")
                return True
                
            initial_count = len(self.df)
            
            # Filter out the specific type
            self.df = self.df[self.df['vehicle_type'] != exclude_type]
            
            filtered_count = len(self.df)
            removed = initial_count - filtered_count
            
            if removed > 0:
                logger.info(f"Filtered out {removed} rows of vehicle type '{exclude_type}'")
            
            return True
            
        except Exception as e:
            logger.error(f"Error filtering vehicle type: {str(e)}", exc_info=True)
            return False

    
    def clean_data(self) -> bool:
        """
        Clean and preprocess the data.
        
        Returns:
            True if cleaning successful, False otherwise
        """
        try:
            if self.df is None:
                logger.error("No data loaded. Call load_excel() first.")
                return False
            
            logger.info("Cleaning data...")
            initial_rows = len(self.df)
            
            # Convert Date column to datetime if it exists
            if 'Date' in self.df.columns:
                self.df['Date'] = pd.to_datetime(self.df['Date'], errors='coerce')
            
            # Strip whitespace from string columns
            string_columns = self.df.select_dtypes(include=['object']).columns
            for col in string_columns:
                self.df[col] = self.df[col].astype(str).str.strip()
            
            # Convert numeric columns (handle any that might be stored as strings)
            numeric_patterns = ['hours', 'kms', 'collected', 'balance', 'orders', 
                              'cancelled', 'notifications', 'incentive', 'penalty']
            
            for col in self.df.columns:
                if any(pattern in col.lower() for pattern in numeric_patterns):
                    self.df[col] = pd.to_numeric(self.df[col], errors='coerce')
            
            # Fill NaN values in numeric columns with 0
            numeric_cols = self.df.select_dtypes(include=['float64', 'int64']).columns
            self.df[numeric_cols] = self.df[numeric_cols].fillna(0)
            
            # Remove completely empty rows
            self.df = self.df.dropna(how='all')
            
            final_rows = len(self.df)
            removed_rows = initial_rows - final_rows
            
            if removed_rows > 0:
                logger.info(f"Removed {removed_rows} empty rows")
            
            logger.info("Data cleaning completed")
            return True
            
        except Exception as e:
            logger.error(f"Error cleaning data: {str(e)}", exc_info=True)
            return False
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """
        Get summary statistics of the dataset.
        
        Returns:
            Dictionary containing summary statistics
        """
        if self.df is None:
            return {}
        
        stats = {
            'total_drivers': len(self.df),
            'total_columns': len(self.df.columns),
            'date_range': None,
            'unique_regions': 0,
            'unique_vehicle_types': 0,
        }
        
        # Date range
        if 'Date' in self.df.columns:
            stats['date_range'] = {
                'start': self.df['Date'].min(),
                'end': self.df['Date'].max()
            }
        
        # Unique regions
        if 'driver_geo_region' in self.df.columns:
            stats['unique_regions'] = self.df['driver_geo_region'].nunique()
            stats['regions'] = self.df['driver_geo_region'].unique().tolist()
        
        # Unique vehicle types
        if 'vehicle_type' in self.df.columns:
            stats['unique_vehicle_types'] = self.df['vehicle_type'].nunique()
            stats['vehicle_types'] = self.df['vehicle_type'].unique().tolist()
        
        return stats
    
    def get_dataframe(self) -> Optional[pd.DataFrame]:
        """
        Get the processed DataFrame.
        
        Returns:
            Processed DataFrame or None if not loaded
        """
        return self.df
    
    def update_master_sheet(self, master_filepath: str) -> bool:
        """
        Append current processed 4-wheeler data to a single master file for long-term record keeping.
        
        Args:
            master_filepath: Path to the master dataset CSV/Excel file
            
        Returns:
            True if updated successfully, False otherwise
        """
        try:
            if self.df is None or len(self.df) == 0:
                logger.warning("No data available to append to master sheet.")
                return False
                
            master_path = Path(master_filepath)
            master_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Filter out 3-wheelers again strictly
            clean_df = self.df.copy()
            if 'vehicle_type' in clean_df.columns:
                clean_df = clean_df[clean_df['vehicle_type'] != '3 Wheeler Electric']
                
            if master_path.exists():
                if str(master_path).endswith('.csv'):
                    existing_df = pd.read_csv(master_path)
                else:
                    existing_df = pd.read_excel(master_path)
                    
                combined_df = pd.concat([existing_df, clean_df], ignore_index=True)
            else:
                combined_df = clean_df

            # Remove exact row duplicates
            dedup_subset = [c for c in ['Date', 'driver_name', 'driver_mobile', 'vehicle_number'] if c in combined_df.columns]
            if dedup_subset:
                combined_df = combined_df.drop_duplicates(subset=dedup_subset, keep='last')
            else:
                combined_df = combined_df.drop_duplicates(keep='last')
                
            if str(master_path).endswith('.csv'):
                combined_df.to_csv(master_path, index=False)
            else:
                combined_df.to_excel(master_path, index=False)
                
            logger.info(f"Updated Master Sheet ({len(combined_df)} total records) at: {master_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating master sheet: {str(e)}", exc_info=True)
            return False
