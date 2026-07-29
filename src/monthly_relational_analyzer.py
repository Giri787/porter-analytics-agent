"""
Monthly & Relational Analytics Module
Analyzes 1-2 month driver datasets to find correlations between:
- Shift Timings (First login, Last login, Active hours) vs. Cash Collected
- Shift Timings vs. Notifications
- Location / Region vs. Notifications
- Location / Region vs. Cash Collected
- Shift Duration Categories (< 8 hours, 8-12 hours, 12+ hours)
"""

import pandas as pd
import numpy as np
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class MonthlyRelationalAnalyzer:
    """Analyzes multi-day and multi-month driver performance and relational metrics."""

    def __init__(self, historical_df: pd.DataFrame, config: dict):
        """
        Initialize the analyzer with a combined historical DataFrame.
        
        Args:
            historical_df: Merged DataFrame spanning 30-60 days of driver records
            config: Agent configuration dictionary
        """
        self.df = historical_df.copy()
        self.config = config
        self.results = {}
        self._preprocess_columns()

    def _find_column(self, possible_names: List[str]) -> Optional[str]:
        """Find matching column name flexibly."""
        for name in possible_names:
            for col in self.df.columns:
                if col.lower() == name.lower():
                    return col
            for col in self.df.columns:
                if name.lower() in col.lower():
                    return col
        return None

    def _preprocess_columns(self):
        """Standardize core metric column names."""
        self.orders_col = self._find_column(['orders_completed', 'total_orders', 'orders']) or 'orders'
        self.cash_col = self._find_column(['cash_collected', 'cash', 'collection']) or 'cash_collected'
        self.notif_col = self._find_column(['notifications', 'notification_count', 'notifs']) or 'notifications'
        self.hours_col = self._find_column(['online_hours', 'duty_hours', 'idle_hours', 'hours']) or 'hours'
        self.region_col = self._find_column(['driver_geo_region', 'region', 'location', 'cluster']) or 'driver_geo_region'
        self.first_login_col = self._find_column(['first_login_time', 'first_login', 'login_time', 'start_time'])
        self.last_login_col = self._find_column(['last_login_time', 'last_login', 'logout_time', 'end_time'])

        # Ensure numeric types
        for col in [self.orders_col, self.cash_col, self.notif_col, self.hours_col]:
            if col in self.df.columns:
                self.df[col] = pd.to_numeric(self.df[col], errors='coerce').fillna(0)

        # Vehicle type filtering if present
        if 'vehicle_type' in self.df.columns:
            self.df = self.df[self.df['vehicle_type'] != '3 Wheeler Electric']

    def analyze_shift_durations(self) -> Dict[str, Any]:
        """
        Categorize drivers by active/duty hours:
        - < 8 hours (Short shift)
        - 8 to 12 hours (Standard shift)
        - 12+ hours (High duty shift)
        """
        if self.hours_col not in self.df.columns:
            return {}

        df_hours = self.df[self.hours_col]
        
        under_8 = self.df[df_hours < 8]
        between_8_12 = self.df[(df_hours >= 8) & (df_hours <= 12)]
        over_12 = self.df[df_hours > 12]

        total = len(self.df)
        
        summary = {
            'total_active_drivers': total,
            'under_8_hours': {
                'count': len(under_8),
                'pct': round((len(under_8) / total * 100), 1) if total > 0 else 0,
                'avg_cash': round(float(under_8[self.cash_col].mean()), 2) if self.cash_col in under_8.columns and len(under_8) > 0 else 0,
                'avg_orders': round(float(under_8[self.orders_col].mean()), 2) if self.orders_col in under_8.columns and len(under_8) > 0 else 0,
            },
            'between_8_12_hours': {
                'count': len(between_8_12),
                'pct': round((len(between_8_12) / total * 100), 1) if total > 0 else 0,
                'avg_cash': round(float(between_8_12[self.cash_col].mean()), 2) if self.cash_col in between_8_12.columns and len(between_8_12) > 0 else 0,
                'avg_orders': round(float(between_8_12[self.orders_col].mean()), 2) if self.orders_col in between_8_12.columns and len(between_8_12) > 0 else 0,
            },
            'over_12_hours': {
                'count': len(over_12),
                'pct': round((len(over_12) / total * 100), 1) if total > 0 else 0,
                'avg_cash': round(float(over_12[self.cash_col].mean()), 2) if self.cash_col in over_12.columns and len(over_12) > 0 else 0,
                'avg_orders': round(float(over_12[self.orders_col].mean()), 2) if self.orders_col in over_12.columns and len(over_12) > 0 else 0,
            }
        }
        return summary

    def analyze_relational_correlations(self) -> Dict[str, Any]:
        """
        Calculates cross-variable correlations and breakdowns:
        1. Timing vs Cash Collected
        2. Timing vs Notifications
        3. Location vs Notifications
        4. Location vs Cash Collected
        """
        relational = {}

        # 1. Location vs Cash & Notifications
        if self.region_col in self.df.columns:
            location_grouped = self.df.groupby(self.region_col).agg(
                driver_count=(self.region_col, 'count'),
                total_cash=(self.cash_col, 'sum'),
                avg_cash=(self.cash_col, 'mean'),
                total_notifications=(self.notif_col, 'sum'),
                avg_notifications=(self.notif_col, 'mean'),
                total_orders=(self.orders_col, 'sum'),
                avg_orders=(self.orders_col, 'mean')
            ).reset_index()

            location_stats = []
            for _, row in location_grouped.iterrows():
                location_stats.append({
                    'region': str(row[self.region_col]),
                    'driver_count': int(row['driver_count']),
                    'total_cash': round(float(row['total_cash']), 2),
                    'avg_cash': round(float(row['avg_cash']), 2),
                    'total_notifications': int(row['total_notifications']),
                    'avg_notifications': round(float(row['avg_notifications']), 1),
                    'total_orders': int(row['total_orders']),
                    'avg_orders': round(float(row['avg_orders']), 1),
                })
            
            # Sort regions by total cash descending
            location_stats.sort(key=lambda x: x['total_cash'], reverse=True)
            relational['location_breakdown'] = location_stats

        # 2. Duty Hours vs Cash & Notifications Correlations
        if self.hours_col in self.df.columns:
            corr_cash = float(self.df[self.hours_col].corr(self.df[self.cash_col])) if self.cash_col in self.df.columns else 0.0
            corr_notif = float(self.df[self.hours_col].corr(self.df[self.notif_col])) if self.notif_col in self.df.columns else 0.0
            corr_orders = float(self.df[self.hours_col].corr(self.df[self.orders_col])) if self.orders_col in self.df.columns else 0.0
            
            relational['correlations'] = {
                'hours_vs_cash': round(corr_cash, 3) if not np.isnan(corr_cash) else 0.0,
                'hours_vs_notifications': round(corr_notif, 3) if not np.isnan(corr_notif) else 0.0,
                'hours_vs_orders': round(corr_orders, 3) if not np.isnan(corr_orders) else 0.0,
            }

        # 3. Login Timings (First Login & Last Login) Analysis
        if self.first_login_col and self.first_login_col in self.df.columns:
            try:
                self.df['first_login_dt'] = pd.to_datetime(self.df[self.first_login_col], errors='coerce')
                self.df['login_hour'] = self.df['first_login_dt'].dt.hour
                
                login_hour_group = self.df.groupby('login_hour').agg(
                    driver_count=('login_hour', 'count'),
                    avg_cash=(self.cash_col, 'mean'),
                    avg_notifs=(self.notif_col, 'mean')
                ).reset_index()
                
                hourly_stats = []
                for _, row in login_hour_group.iterrows():
                    if not np.isnan(row['login_hour']):
                        hourly_stats.append({
                            'hour': int(row['login_hour']),
                            'hour_label': f"{int(row['login_hour']):02d}:00",
                            'driver_count': int(row['driver_count']),
                            'avg_cash': round(float(row['avg_cash']), 2),
                            'avg_notifications': round(float(row['avg_notifs']), 1)
                        })
                relational['login_hour_stats'] = hourly_stats
            except Exception as e:
                logger.warning(f"Could not parse login hour: {str(e)}")

        return relational

    def run_full_analysis(self) -> Dict[str, Any]:
        """Execute complete monthly and relational analytics suite."""
        logger.info("Executing Monthly & Relational Analysis...")
        self.results['shift_durations'] = self.analyze_shift_durations()
        self.results['relational'] = self.analyze_relational_correlations()
        self.results['total_records_analyzed'] = len(self.df)
        return self.results
