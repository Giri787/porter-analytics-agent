"""
Integrity Analyzer Module
Implements advanced productivity metrics, risk flags, and integrity scoring for Porter drivers.
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class IntegrityAnalyzer:
    """Analyzes driver integrity and productivity based on Porter summary reports."""
    
    def __init__(self, df: pd.DataFrame, config: dict):
        self.df = df.copy()
        self.config = config
        self.results = {}
        
    def run_analysis(self) -> Dict[str, Any]:
        """Run all integrity analysis sections."""
        logger.info("Running Integrity & Productivity Analysis...")
        
        # 1. Driver Activity Summary
        self.results['activity_summary'] = self._analyze_activity()
        
        # 2. Risk Flags
        self.results['risk_flags'] = self._detect_risk_flags()
        
        # 3. Rogue Delivery Detection
        self.results['rogue_detection'] = self._detect_rogue_behavior()
        
        # 4. Performance Ranking (Top/Bottom 5)
        self.results['rankings'] = self._generate_rankings()
        
        # 5. Integrity Scoring
        self.results['integrity_scores'] = self._calculate_integrity_scores()
        
        return self.results

    def _analyze_activity(self) -> List[Dict[str, Any]]:
        """Section 1: Driver Activity Summary."""
        summary = []
        for _, row in self.df.iterrows():
            # Basic fields
            orders_assigned = float(row.get('allocated_orders', 0))
            orders_completed = float(row.get('completed_orders', 0))
            partner_cancels = float(row.get('partner_cancellation', 0))
            
            # Calculate cancellation %
            cancel_pct = (partner_cancels / orders_assigned * 100) if orders_assigned > 0 else 0
            
            # Time Metrics
            first_login = row.get('first_recorded_login_time')
            last_login = row.get('last_recorded_login_time')
            
            working_window = float(row.get('total_login_time_in_hrs', 0))
            active_time = float(row.get('time_spent_orders_in_hrs', 0))
            idle_time = float(row.get('time_spent_idle_in_hrs', 0))
            
            idle_pct = (idle_time / working_window * 100) if working_window > 0 else 0
            
            # KM Metrics
            total_km = float(row.get('total_distance_in_kms', 0))
            km_per_order = (total_km / orders_completed) if orders_completed > 0 else 0
            
            # Earnings
            total_earnings = float(row.get('trip_fare', 0))
            earnings_per_km = (total_earnings / total_km) if total_km > 0 else 0
            
            orders_per_hour = (orders_completed / working_window) if working_window > 0 else 0
            
            summary.append({
                'driver_name': row.get('driver_name', 'N/A'),
                'mobile': row.get('driver_mobile', 'N/A'),
                'total_orders': int(orders_assigned),
                'completed_orders': int(orders_completed),
                'partner_cancels': int(partner_cancels),
                'cancel_pct': round(cancel_pct, 2),
                'total_km': round(total_km, 2),
                'total_earnings': round(total_earnings, 2),
                'first_activity': first_login,
                'last_activity': last_login,
                'working_window': round(working_window, 2),
                'active_time': round(active_time, 2),
                'idle_time': round(idle_time, 2),
                'idle_pct': round(idle_pct, 2),
                'km_per_order': round(km_per_order, 2),
                'earnings_per_km': round(earnings_per_km, 2),
                'orders_per_hour': round(orders_per_hour, 2),
                'missed_notif_pct': float(row.get('pct_notifs_missed_overall', 0))
            })
        return summary

    def _detect_risk_flags(self) -> List[Dict[str, Any]]:
        """Section 2: Exception & Risk Flags."""
        risk_drivers = []
        activity_data = self.results.get('activity_summary', [])
        
        # Fleet average for KM per order
        km_per_order_vals = [d['km_per_order'] for d in activity_data if d['completed_orders'] > 0]
        fleet_avg_km = np.mean(km_per_order_vals) if km_per_order_vals else 0
        
        for driver in activity_data:
            flags = []
            
            # Flag 1 & 2: Cancellations
            if driver['cancel_pct'] > 30:
                flags.append("🚨 Very High Cancellation Risk (>30%)")
            elif driver['cancel_pct'] > 20:
                flags.append("⚠️ High Partner Cancellation (>20%)")
                
            # Flag 3: Rogue Pattern - High KM, Low Orders
            if driver['total_km'] > 50 and driver['completed_orders'] < 3 and driver['cancel_pct'] > 15:
                flags.append("🕵️ Rogue Pattern: High KM, Low Orders")
                
            # Flag 4: Idle Leakage
            if driver['idle_pct'] > 40:
                flags.append("⏱️ Idle Leakage (>40%)")
                
            # Flag 5: Suspicious KM Movement
            if driver['km_per_order'] > (fleet_avg_km * 1.5) and driver['completed_orders'] > 0:
                flags.append("📍 Suspicious KM per Order (Fleet Deviation)")
            elif driver['total_km'] > 20 and driver['total_earnings'] < (driver['total_km'] * 5): # Very low earnings per KM
                flags.append("💰 High KM but Low Earnings")
                
            # Flag 6: Acceptance Manipulation (Proxy)
            if driver['missed_notif_pct'] > 50:
                flags.append("📵 High Notif Miss Rate (Acceptance Manipulation Proxy)")
                
            if flags:
                risk_drivers.append({
                    'driver_name': driver['driver_name'],
                    'mobile': driver['mobile'],
                    'flags': flags,
                    'metrics': f"Cancel: {driver['cancel_pct']}%, Idle: {driver['idle_pct']}%, KM/Order: {driver['km_per_order']}"
                })
        
        return risk_drivers

    def _detect_rogue_behavior(self) -> List[Dict[str, Any]]:
        """Section 3: Rogue Delivery Detection Logic."""
        rogue_drivers = []
        for _, row in self.df.iterrows():
            partner_cancels = float(row.get('partner_cancellation', 0))
            idle_km = float(row.get('distance_travelled_while_idle_in_kms', 0))
            
            # Logic: Cancellation exists AND significant idle KM movement
            if partner_cancels > 0 and idle_km > 5:
                rogue_drivers.append({
                    'driver_name': row.get('driver_name'),
                    'mobile': row.get('driver_mobile'),
                    'partner_cancels': int(partner_cancels),
                    'idle_km': round(idle_km, 2),
                    'status': "⚠ Potential Off-Platform Delivery Risk"
                })
        return rogue_drivers

    def _generate_rankings(self) -> Dict[str, List[Dict]]:
        """Section 4: Top & Bottom Performance."""
        activity = self.results.get('activity_summary', [])
        if not activity:
            return {'top_5': [], 'bottom_5': []}
            
        # Filter for active drivers (at least 1 hour window)
        active_list = [d for d in activity if d['working_window'] > 1]
        
        # Sort for Top 5 (High Orders/hr, Low Cancel, Low Idle)
        # Using a simple rank index: Orders_per_hr - (Cancel/100) - (Idle/100)
        top_5 = sorted(active_list, 
                      key=lambda x: (x['orders_per_hour'] - (x['cancel_pct']/100) - (x['idle_pct']/100)), 
                      reverse=True)[:5]
                      
        # Sort for Bottom 5 (High Idle, High Cancel, Low Orders/hr)
        bottom_5 = sorted(active_list, 
                         key=lambda x: (x['idle_pct'] + x['cancel_pct'] - (x['orders_per_hour']*10)), 
                         reverse=True)[:5]
                         
        return {'top_5': top_5, 'bottom_5': bottom_5}

    def _calculate_integrity_scores(self) -> List[Dict[str, Any]]:
        """Section 7: Daily Integrity Score."""
        scores = []
        activity_data = self.results.get('activity_summary', [])
        
        for driver in activity_data:
            # 30% Cancellation % (Lower is better)
            # Max penalty at 50% cancellation
            cancel_score = max(0, 100 - (driver['cancel_pct'] * 2))
            
            # 20% Idle % (Lower is better)
            idle_score = max(0, 100 - (driver['idle_pct']))
            
            # 15% Acceptance Lag (Proxy via Notif Miss %)
            acc_score = max(0, 100 - (driver['missed_notif_pct']))
            
            # 15% KM per Order deviation
            km_score = 100 if driver['km_per_order'] < 15 else 50 # Simplified proxy
            
            # 20% Earnings consistency
            earn_score = 100 if driver['total_earnings'] > 500 else 50
            
            final_score = (
                (cancel_score * 0.30) +
                (idle_score * 0.20) +
                (acc_score * 0.15) +
                (km_score * 0.15) +
                (earn_score * 0.20)
            )
            
            status = "Immediate Intervention" if final_score < 40 else \
                     "Needs Review" if final_score < 60 else "Good"
            
            scores.append({
                'driver_name': driver['driver_name'],
                'mobile': driver['mobile'],
                'score': round(final_score, 1),
                'status': status
            })
            
        return sorted(scores, key=lambda x: x['score'])
