"""
Analyzer Module
Performs comprehensive analysis on Porter driver performance data.
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class PorterAnalyzer:
    """Analyzes Porter driver performance data and generates insights."""
    
    def __init__(self, df: pd.DataFrame, config: dict):
        """
        Initialize analyzer with data and configuration.
        
        Args:
            df: DataFrame containing Porter driver data
            config: Configuration dictionary with thresholds
        """
        self.df = df.copy()
        self.config = config
        self.analysis_results = {}
        
        # Get thresholds from config
        self.min_orders_threshold = int(config.get('MIN_ORDERS_THRESHOLD', 5))
        self.idle_hours_warning = float(config.get('IDLE_HOURS_WARNING', 4))
        self.cancellation_rate_warning = float(config.get('CANCELLATION_RATE_WARNING', 15))
        
        # Standardize main metric columns
        self.orders_col = self._find_column(['orders_completed', 'total_orders', 'orders'])
        if self.orders_col:
            self.df['total_orders'] = self.df[self.orders_col]
        else:
            self.df['total_orders'] = 0
        
    def analyze_driver_performance(self) -> Dict[str, Any]:
        """
        Analyze individual driver performance metrics.
        
        Returns:
            Dictionary containing driver performance analysis
        """
        logger.info("Analyzing driver performance...")
        
        hours_col = self._find_column(['online_hours', 'duty_hours', 'idle_hours', 'hours'])
        
        results = {
            'total_drivers': len(self.df),
            'active_drivers': len(self.df),  # All recorded drivers in file are active drivers
            'drivers_over_12_hours': 0,
            'drivers_under_8_hours': 0,
            'drivers_8_to_12_hours': 0,
            'top_performers': [],
            'bottom_performers': [],
            'high_cancellation_drivers': [],
            'high_idle_time_drivers': [],
            'summary_stats': {}
        }

        # Duty/login hours categorization
        if hours_col and hours_col in self.df.columns:
            hours_series = pd.to_numeric(self.df[hours_col], errors='coerce').fillna(0)
            results['drivers_under_8_hours'] = int((hours_series < 8).sum())
            results['drivers_8_to_12_hours'] = int(((hours_series >= 8) & (hours_series <= 12)).sum())
            results['drivers_over_12_hours'] = int((hours_series > 12).sum())
        
        # Identify metric columns (flexible to handle different column names)
        orders_col = self._find_column(['orders_completed', 'total_orders', 'orders'])
        cancelled_col = self._find_column(['orders_cancelled', 'cancelled', 'driver_cancelled'])
        idle_hours_col = self._find_column(['idle_hours', 'idle_time'])
        cash_col = self._find_column(['cash_collected', 'cash', 'collection'])
        
        # Calculate derived metrics
        if self.orders_col:
            # Top performers by orders
            top_10 = self.df.nlargest(10, 'total_orders')
            results['top_performers'] = [
                {
                    'driver_name': row.get('driver_name', 'N/A'),
                    'driver_mobile': row.get('driver_mobile', 'N/A'),
                    'region': row.get('driver_geo_region', 'N/A'),
                    'orders': int(row['total_orders']),
                    'cash_collected': float(row.get(cash_col, 0)) if cash_col else 0
                }
                for _, row in top_10.iterrows()
            ]
            
            # Bottom performers (active but low orders)
            active_df = self.df[self.df['total_orders'] >= self.min_orders_threshold]
            if len(active_df) > 0:
                bottom_10 = active_df.nsmallest(min(10, len(active_df)), 'total_orders')
                results['bottom_performers'] = [
                    {
                        'driver_name': row.get('driver_name', 'N/A'),
                        'driver_mobile': row.get('driver_mobile', 'N/A'),
                        'region': row.get('driver_geo_region', 'N/A'),
                        'orders': int(row['total_orders'])
                    }
                    for _, row in bottom_10.iterrows()
                ]
        else:
            logger.warning("Orders column not found. Skipping order-based analysis.")
        
        # Cancellation analysis
        if self.orders_col and cancelled_col:
            self.df['cancellation_rate'] = (self.df[cancelled_col] / self.df['total_orders'] * 100).fillna(0)
            self.df['cancellation_rate'] = self.df['cancellation_rate'].replace([np.inf, -np.inf], 0)
            
            high_cancel = self.df[
                (self.df['cancellation_rate'] > self.cancellation_rate_warning) & 
                (self.df['total_orders'] >= self.min_orders_threshold)
            ]
            
            results['high_cancellation_drivers'] = [
                {
                    'driver_name': row.get('driver_name', 'N/A'),
                    'driver_mobile': row.get('driver_mobile', 'N/A'),
                    'region': row.get('driver_geo_region', 'N/A'),
                    'cancellation_rate': round(row['cancellation_rate'], 2),
                    'total_cancelled': int(row[cancelled_col])
                }
                for _, row in high_cancel.nlargest(10, 'cancellation_rate').iterrows()
            ]
        
        # Idle time analysis
        if idle_hours_col:
            high_idle = self.df[self.df[idle_hours_col] > self.idle_hours_warning]
            results['high_idle_time_drivers'] = [
                {
                    'driver_name': row.get('driver_name', 'N/A'),
                    'driver_mobile': row.get('driver_mobile', 'N/A'),
                    'region': row.get('driver_geo_region', 'N/A'),
                    'idle_hours': round(float(row[idle_hours_col]), 2)
                }
                for _, row in high_idle.nlargest(10, idle_hours_col).iterrows()
            ]
        
        # Summary statistics
        target_cols = [orders_col, cash_col, idle_hours_col, cancelled_col]
        target_cols = [c for c in target_cols if c is not None]
        
        results['summary_stats'] = {}
        for col in target_cols:
            try:
                # Standardize metric name in results
                result_key = col
                if col == self.orders_col:
                    result_key = 'total_orders'
                elif col == cash_col:
                    result_key = 'total_cash'
                
                if col in self.df.columns and pd.api.types.is_numeric_dtype(self.df[col]):
                    results['summary_stats'][result_key] = {
                        'mean': float(self.df[col].mean()),
                        'median': float(self.df[col].median()),
                        'std': float(self.df[col].std()),
                        'min': float(self.df[col].min()),
                        'max': float(self.df[col].max())
                    }
            except Exception as e:
                logger.warning(f"Could not calculate stats for column {col}: {str(e)}")
        
        self.analysis_results['driver_performance'] = results
        return results
    
    def analyze_location_performance(self) -> Dict[str, Any]:
        """
        Analyze performance by geographic region.
        
        Returns:
            Dictionary containing location-based analysis
        """
        logger.info("Analyzing location performance...")
        
        if 'driver_geo_region' not in self.df.columns:
            logger.warning("No driver_geo_region column found")
            return {}
        
        results = {
            'total_regions': self.df['driver_geo_region'].nunique(),
            'region_stats': []
        }
        
        # Find metric columns
        orders_col = self._find_column(['orders_completed', 'total_orders', 'orders'])
        cash_col = self._find_column(['cash_collected', 'cash', 'collection'])
        cancelled_col = self._find_column(['orders_cancelled', 'cancelled'])
        
        # Group by region
        region_groups = self.df.groupby('driver_geo_region')
        
        region_data = []
        for region, group in region_groups:
            stats = {
                'region': region,
                'driver_count': len(group),
                'total_orders': int(group['total_orders'].sum()) if self.orders_col else 0,
                'avg_orders_per_driver': float(group['total_orders'].mean()) if self.orders_col else 0,
                'total_cash': float(group[cash_col].sum()) if cash_col else 0,
                'avg_cash_per_driver': float(group[cash_col].mean()) if cash_col else 0,
                'total_cancelled': int(group[cancelled_col].sum()) if cancelled_col else 0,
                'cancellation_rate': 0
            }
            
            if self.orders_col and cancelled_col and stats['total_orders'] > 0:
                stats['cancellation_rate'] = round(
                    (stats['total_cancelled'] / stats['total_orders'] * 100), 2
                )
            
            region_data.append(stats)
        
        # Sort by total orders
        region_data.sort(key=lambda x: x['total_orders'], reverse=True)
        results['region_stats'] = region_data
        
        self.analysis_results['location_performance'] = results
        return results
    
    def compare_with_previous_day(self, previous_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Compare current data with previous day's data.
        
        Args:
            previous_df: DataFrame containing previous day's data
            
        Returns:
            Dictionary containing day-over-day comparison
        """
        logger.info("Performing day-over-day comparison...")
        
        results = {
            'overall_changes': {},
            'driver_changes': [],
            'region_changes': []
        }
        
        # Find metric columns
        orders_col = self._find_column(['orders_completed', 'total_orders', 'orders'])
        cash_col = self._find_column(['cash_collected', 'cash', 'collection'])
        
        # Overall metrics comparison
        if self.orders_col:
            # Check if self.orders_col in previous_df
            prev_orders_col = self._find_column_in_df(previous_df, ['orders_completed', 'total_orders', 'orders'])
            
            current_total_orders = self.df['total_orders'].sum()
            previous_total_orders = previous_df[prev_orders_col].sum() if prev_orders_col else 0
            change = current_total_orders - previous_total_orders
            pct_change = (change / previous_total_orders * 100) if previous_total_orders > 0 else 0
            
            results['overall_changes']['total_orders'] = {
                'current': int(current_total_orders),
                'previous': int(previous_total_orders),
                'change': int(change),
                'pct_change': round(pct_change, 2)
            }
        
        if cash_col:
            current_total_cash = self.df[cash_col].sum()
            previous_total_cash = previous_df[cash_col].sum()
            change = current_total_cash - previous_total_cash
            pct_change = (change / previous_total_cash * 100) if previous_total_cash > 0 else 0
            
            results['overall_changes']['total_cash'] = {
                'current': float(current_total_cash),
                'previous': float(previous_total_cash),
                'change': float(change),
                'pct_change': round(pct_change, 2)
            }
        
        # Driver count comparison
        results['overall_changes']['driver_count'] = {
            'current': len(self.df),
            'previous': len(previous_df),
            'change': len(self.df) - len(previous_df)
        }
        
        # Region-level comparison
        if 'driver_geo_region' in self.df.columns and self.orders_col:
            prev_orders_col = self._find_column_in_df(previous_df, ['orders_completed', 'total_orders', 'orders'])
            
            current_region = self.df.groupby('driver_geo_region')['total_orders'].sum()
            previous_region = previous_df.groupby('driver_geo_region')[prev_orders_col].sum() if prev_orders_col else pd.Series()
            
            for region in current_region.index:
                current_val = current_region.get(region, 0)
                previous_val = previous_region.get(region, 0)
                change = current_val - previous_val
                pct_change = (change / previous_val * 100) if previous_val > 0 else 0
                
                results['region_changes'].append({
                    'region': region,
                    'current_orders': int(current_val),
                    'previous_orders': int(previous_val),
                    'change': int(change),
                    'pct_change': round(pct_change, 2)
                })
            
            # Sort by absolute change
            results['region_changes'].sort(key=lambda x: abs(x['change']), reverse=True)
        
        self.analysis_results['day_over_day'] = results
        return results
    
    def generate_insights(self) -> List[str]:
        """
        Generate automated insights and recommendations.
        
        Returns:
            List of insight strings
        """
        logger.info("Generating insights...")
        
        insights = []
        
        # Driver performance insights
        if 'driver_performance' in self.analysis_results:
            perf = self.analysis_results['driver_performance']
            
            if perf.get('drivers_over_12_hours', 0) > 0:
                insights.append(
                    f"⏰ {perf['drivers_over_12_hours']} drivers logged in for 12+ hours (High Duty)"
                )
            if perf.get('drivers_under_8_hours', 0) > 0:
                insights.append(
                    f"⏳ {perf['drivers_under_8_hours']} drivers logged in for < 8 hours (Part Time)"
                )
            
            if perf['high_cancellation_drivers']:
                insights.append(
                    f"⚠️ {len(perf['high_cancellation_drivers'])} drivers have cancellation "
                    f"rates above {self.cancellation_rate_warning}% - requires attention"
                )
            
            if perf['high_idle_time_drivers']:
                insights.append(
                    f"⏱️ {len(perf['high_idle_time_drivers'])} drivers have idle time "
                    f"exceeding {self.idle_hours_warning} hours - potential efficiency issue"
                )
        
        # Location insights
        if 'location_performance' in self.analysis_results:
            loc = self.analysis_results['location_performance']
            
            if loc['region_stats']:
                top_region = loc['region_stats'][0]
                total_orders = top_region.get('total_orders', 0)
                insights.append(
                    f"🏆 Top performing region: {top_region['region']} with "
                    f"{total_orders} total orders"
                )
        
        # Day-over-day insights
        if 'day_over_day' in self.analysis_results:
            dod = self.analysis_results['day_over_day']
            
            if 'total_orders' in dod['overall_changes']:
                change = dod['overall_changes']['total_orders']
                direction = "📈 increased" if change['change'] > 0 else "📉 decreased"
                insights.append(
                    f"Total orders {direction} by {abs(change['change'])} "
                    f"({change['pct_change']:+.1f}%) compared to previous day"
                )
        
        return insights
    
    def _find_column(self, possible_names: List[str]) -> Optional[str]:
        """Find a column by checking multiple possible names in self.df."""
        return self._find_column_in_df(self.df, possible_names)

    def _find_column_in_df(self, df: pd.DataFrame, possible_names: List[str]) -> Optional[str]:
        """
        Find a column by checking multiple possible names in a specific DataFrame.
        """
        for name in possible_names:
            # Check exact match (case-insensitive)
            for col in df.columns:
                if col.lower() == name.lower():
                    return col
            
            # Check partial match
            for col in df.columns:
                if name.lower() in col.lower():
                    return col
        
        return None
    
    def get_all_results(self) -> Dict[str, Any]:
        """
        Get all analysis results.
        
        Returns:
            Dictionary containing all analysis results
        """
        return self.analysis_results
