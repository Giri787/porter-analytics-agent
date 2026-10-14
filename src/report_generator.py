"""
Report Generator Module
Creates visually appealing HTML email reports with charts and insights.
"""

import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import base64
from io import BytesIO
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging
import os

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generates HTML reports with visualizations for Porter analytics."""
    
    def __init__(self, analysis_results: Dict[str, Any], insights: List[str], integrity_results: Dict[str, Any] = None, monthly_results: Dict[str, Any] = None):
        """
        Initialize report generator.
        
        Args:
            analysis_results: Dictionary containing all analysis results
            insights: List of insight strings
            integrity_results: Dictionary containing integrity and productivity analysis
            monthly_results: Dictionary containing 1-2 month relational analysis
        """
        self.analysis_results = analysis_results
        self.insights = insights
        self.integrity_results = integrity_results or {}
        self.monthly_results = monthly_results or {}
        self.charts = {}
        
    def generate_charts(self) -> Dict[str, str]:
        """
        Generate all charts and return as base64 encoded strings.
        
        Returns:
            Dictionary mapping chart names to base64 encoded images
        """
        logger.info("Generating charts...")
        
        # Top performers chart
        if 'driver_performance' in self.analysis_results:
            perf = self.analysis_results['driver_performance']
            if perf.get('top_performers'):
                self.charts['top_performers'] = self._create_top_performers_chart(
                    perf['top_performers']
                )
        
        # Location performance chart
        if 'location_performance' in self.analysis_results:
            loc = self.analysis_results['location_performance']
            if loc.get('region_stats'):
                self.charts['location_performance'] = self._create_location_chart(
                    loc['region_stats']
                )
        
        # Day-over-day comparison chart
        if 'day_over_day' in self.analysis_results:
            dod = self.analysis_results['day_over_day']
            if dod.get('overall_changes'):
                self.charts['day_over_day'] = self._create_comparison_chart(dod)
        
        logger.info(f"Generated {len(self.charts)} charts")
        return self.charts
    
    def _create_top_performers_chart(self, top_performers: List[Dict]) -> str:
        """Create horizontal bar chart for top performers using matplotlib."""
        if not top_performers:
            return ""
        
        try:
            # Extract data
            names = [p['driver_name'][:20] for p in top_performers[:10]]
            orders = [p['orders'] for p in top_performers[:10]]
            
            # Create figure
            plt.figure(figsize=(10, 6))
            bars = plt.barh(names[::-1], orders[::-1], color='#3498db')
            plt.xlabel('Orders Completed')
            plt.title('Top 10 Drivers by Orders Completed')
            plt.grid(axis='x', linestyle='--', alpha=0.7)
            
            # Add value labels
            for bar in bars:
                width = bar.get_width()
                plt.text(width, bar.get_y() + bar.get_height()/2, 
                        f'{int(width)}', 
                        ha='left', va='center', fontweight='bold')
            
            plt.tight_layout()
            return self._fig_to_base64(plt.gcf())
            
        except Exception as e:
            logger.error(f"Error creating top performers chart: {str(e)}")
            return ""
    
    def _create_location_chart(self, region_stats: List[Dict]) -> str:
        """Create combined chart for location performance using matplotlib."""
        if not region_stats:
            return ""
        
        try:
            # Take top 10 regions by orders
            top_regions = sorted(region_stats, key=lambda x: x['total_orders'], reverse=True)[:10]
            
            regions = [r['region'] for r in top_regions]
            orders = [r['total_orders'] for r in top_regions]
            drivers = [r['driver_count'] for r in top_regions]
            
            fig, ax1 = plt.subplots(figsize=(10, 6))
            
            # Bar chart for orders
            ax1.bar(regions, orders, color='#3498db', label='Total Orders', alpha=0.7)
            ax1.set_xlabel('Region')
            ax1.set_ylabel('Total Orders', color='#3498db')
            ax1.tick_params(axis='y', labelcolor='#3498db')
            plt.xticks(rotation=45, ha='right')
            
            # Line chart for drivers
            ax2 = ax1.twinx()
            ax2.plot(regions, drivers, color='#e74c3c', marker='o', linewidth=2, label='Driver Count')
            ax2.set_ylabel('Driver Count', color='#e74c3c')
            ax2.tick_params(axis='y', labelcolor='#e74c3c')
            
            plt.title('Location Performance: Orders & Driver Count')
            plt.tight_layout()
            
            return self._fig_to_base64(plt.gcf())
            
        except Exception as e:
            logger.error(f"Error creating location chart: {str(e)}")
            return ""
    
    def _create_comparison_chart(self, dod_data: Dict) -> str:
        """Create comparison chart for day-over-day metrics using matplotlib."""
        changes = dod_data.get('overall_changes', {})
        
        if not changes:
            return ""
        
        try:
            metrics = []
            current_vals = []
            previous_vals = []
            
            if 'total_orders' in changes:
                metrics.append('Total Orders')
                current_vals.append(changes['total_orders']['current'])
                previous_vals.append(changes['total_orders']['previous'])
            
            if 'total_cash' in changes:
                metrics.append('Total Cash')
                current_vals.append(changes['total_cash']['current'])
                previous_vals.append(changes['total_cash']['previous'])
            
            if 'driver_count' in changes:
                metrics.append('Active Drivers')
                current_vals.append(changes['driver_count']['current'])
                previous_vals.append(changes['driver_count']['previous'])
            
            if not metrics:
                return ""
            
            x = range(len(metrics))
            width = 0.35
            
            fig, ax = plt.subplots(figsize=(10, 6))
            rects1 = ax.bar([i - width/2 for i in x], previous_vals, width, label='Previous Day', color='#95a5a6')
            rects2 = ax.bar([i + width/2 for i in x], current_vals, width, label='Current Day', color='#2ecc71')
            
            ax.set_ylabel('Value')
            ax.set_title('Day-over-Day Comparison')
            ax.set_xticks(x)
            ax.set_xticklabels(metrics)
            ax.legend()
            
            # Add labels
            def autolabel(rects):
                for rect in rects:
                    height = rect.get_height()
                    ax.annotate(f'{int(height)}',
                                xy=(rect.get_x() + rect.get_width() / 2, height),
                                xytext=(0, 3),  # 3 points vertical offset
                                textcoords="offset points",
                                ha='center', va='bottom')
            
            autolabel(rects1)
            autolabel(rects2)
            
            plt.tight_layout()
            return self._fig_to_base64(plt.gcf())
            
        except Exception as e:
            logger.error(f"Error creating comparison chart: {str(e)}")
            return ""
    
    def _fig_to_base64(self, fig) -> str:
        """Convert matplotlib figure to base64 encoded PNG."""
        try:
            buf = BytesIO()
            fig.savefig(buf, format='png', bbox_inches='tight')
            buf.seek(0)
            img_base64 = base64.b64encode(buf.read()).decode()
            plt.close(fig)  # Close the figure to free memory
            return f"data:image/png;base64,{img_base64}"
        except Exception as e:
            logger.error(f"Error converting figure to base64: {str(e)}")
            return ""
    
    def generate_html_report(self, report_date: str = None) -> str:
        """
        Generate complete HTML report.
        
        Args:
            report_date: Date string for the report (defaults to today)
            
        Returns:
            HTML string
        """
        if report_date is None:
            report_date = datetime.now().strftime('%Y-%m-%d')
        
        logger.info("Generating HTML report...")
        
        # Generate charts
        self.generate_charts()
        
        # Build HTML
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Porter Driver Performance Report - {report_date}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .header h1 {{
            margin: 0;
            font-size: 2em;
        }}
        .header p {{
            margin: 10px 0 0 0;
            opacity: 0.9;
        }}
        .insights {{
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 20px;
            margin-bottom: 30px;
            border-radius: 5px;
        }}
        .insights h2 {{
            margin-top: 0;
            color: #856404;
        }}
        .insights ul {{
            margin: 10px 0;
            padding-left: 20px;
        }}
        .insights li {{
            margin: 8px 0;
        }}
        .section {{
            background: white;
            padding: 25px;
            margin-bottom: 25px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .section h2 {{
            color: #667eea;
            margin-top: 0;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
        }}
        th {{
            background-color: #667eea;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 600;
        }}
        td {{
            padding: 10px 12px;
            border-bottom: 1px solid #e0e0e0;
        }}
        tr:hover {{
            background-color: #f5f5f5;
        }}
        .metric-card {{
            display: inline-block;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            margin: 10px;
            border-radius: 8px;
            min-width: 200px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .metric-card h3 {{
            margin: 0;
            font-size: 2em;
        }}
        .metric-card p {{
            margin: 5px 0 0 0;
            opacity: 0.9;
        }}
        .chart {{
            margin: 20px 0;
            text-align: center;
        }}
        .chart img {{
            max-width: 100%;
            height: auto;
            border-radius: 5px;
        }}
        .positive {{
            color: #28a745;
            font-weight: bold;
        }}
        .negative {{
            color: #dc3545;
            font-weight: bold;
        }}
        .warning {{
            background-color: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 10px;
            margin: 10px 0;
        }}
        .footer {{
            text-align: center;
            color: #666;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 Porter Driver Performance Report</h1>
        <p>Report Date: {report_date}</p>
        <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
"""
        
        # Add insights section
        if self.insights:
            html += """
    <div class="insights">
        <h2>🔍 Key Insights</h2>
        <ul>
"""
            for insight in self.insights:
                html += f"            <li>{insight}</li>\n"
            html += """
        </ul>
    </div>
"""
        
        # Add summary metrics
        html += self._generate_summary_section()
        
        # Add driver performance section
        html += self._generate_driver_performance_section()
        
        # Add location performance section
        html += self._generate_location_section()
        
        # Add day-over-day comparison
        html += self._generate_comparison_section()
        
        # Add integrity & productivity analysis section
        if self.integrity_results:
            html += self._generate_integrity_section()
            
        # Add monthly & relational analytics section
        if self.monthly_results:
            html += self._generate_monthly_relational_section()
        
        # Footer
        html += """
    <div class="footer">
        <p>This report was automatically generated by Porter Analytics Agent</p>
        <p>For questions or issues, please contact your analytics team</p>
    </div>
</body>
</html>
"""
        
        return html

    def _generate_summary_section(self) -> str:
        """Generate summary metrics section."""
        html = '    <div class="section">\n'
        html += '        <h2>📈 Summary Metrics</h2>\n'
        html += '        <div style="text-align: center;">\n'
        
        if 'driver_performance' in self.analysis_results:
            perf = self.analysis_results['driver_performance']
            html += f"""
            <div class="metric-card">
                <h3>{perf['active_drivers']}</h3>
                <p>Total Active Drivers</p>
            </div>
            <div class="metric-card">
                <h3>{perf.get('drivers_over_12_hours', 0)}</h3>
                <p>Logged in 12+ Hours</p>
            </div>
            <div class="metric-card">
                <h3>{perf.get('drivers_under_8_hours', 0)}</h3>
                <p>Logged in &lt; 8 Hours</p>
            </div>
            <div class="metric-card">
                <h3>{perf.get('drivers_8_to_12_hours', 0)}</h3>
                <p>Logged in 8-12 Hours</p>
            </div>
"""
        
        if 'location_performance' in self.analysis_results:
            loc = self.analysis_results['location_performance']
            html += f"""
            <div class="metric-card">
                <h3>{loc['total_regions']}</h3>
                <p>Active Regions</p>
            </div>
"""
        
        html += '        </div>\n'
        html += '    </div>\n'
        return html
    
    def _generate_driver_performance_section(self) -> str:
        """Generate driver performance section."""
        if 'driver_performance' not in self.analysis_results:
            return ""
        
        perf = self.analysis_results['driver_performance']
        html = '    <div class="section">\n'
        html += '        <h2>👥 Driver Performance</h2>\n'
        
        # Add top performers chart
        if 'top_performers' in self.charts:
            html += f'        <div class="chart"><img src="{self.charts["top_performers"]}" alt="Top Performers"></div>\n'
        
        # Top performers table
        if perf.get('top_performers'):
            html += """
        <h3>🏆 Top 10 Performers</h3>
        <table>
            <tr>
                <th>Rank</th>
                <th>Driver Name</th>
                <th>Mobile</th>
                <th>Region</th>
                <th>Orders</th>
                <th>Cash Collected</th>
            </tr>
"""
            for i, driver in enumerate(perf['top_performers'][:10], 1):
                html += f"""
            <tr>
                <td>{i}</td>
                <td>{driver['driver_name']}</td>
                <td>{driver['driver_mobile']}</td>
                <td>{driver['region']}</td>
                <td><strong>{driver['orders']}</strong></td>
                <td>₹{driver['cash_collected']:,.2f}</td>
            </tr>
"""
            html += '        </table>\n'
        
        # High cancellation drivers
        if perf.get('high_cancellation_drivers'):
            html += """
        <div class="warning">
            <h3>⚠️ High Cancellation Rate Drivers</h3>
            <table>
                <tr>
                    <th>Driver Name</th>
                    <th>Mobile</th>
                    <th>Region</th>
                    <th>Cancellation Rate</th>
                    <th>Total Cancelled</th>
                </tr>
"""
            for driver in perf['high_cancellation_drivers'][:10]:
                html += f"""
                <tr>
                    <td>{driver['driver_name']}</td>
                    <td>{driver['driver_mobile']}</td>
                    <td>{driver['region']}</td>
                    <td class="negative">{driver['cancellation_rate']}%</td>
                    <td>{driver['total_cancelled']}</td>
                </tr>
"""
            html += '            </table>\n'
            html += '        </div>\n'
        
        html += '    </div>\n'
        return html
    
    def _generate_location_section(self) -> str:
        """Generate location performance section."""
        if 'location_performance' not in self.analysis_results:
            return ""
        
        loc = self.analysis_results['location_performance']
        html = '    <div class="section">\n'
        html += '        <h2>📍 Location Performance</h2>\n'
        
        # Add location chart
        if 'location_performance' in self.charts:
            html += f'        <div class="chart"><img src="{self.charts["location_performance"]}" alt="Location Performance"></div>\n'
        
        # Region stats table
        if loc.get('region_stats'):
            html += """
        <table>
            <tr>
                <th>Region</th>
                <th>Drivers</th>
                <th>Total Orders</th>
                <th>Avg Orders/Driver</th>
                <th>Total Cash</th>
                <th>Cancellation Rate</th>
            </tr>
"""
            for region in loc['region_stats'][:15]:  # Top 15 regions
                html += f"""
            <tr>
                <td><strong>{region['region']}</strong></td>
                <td>{region['driver_count']}</td>
                <td>{region['total_orders']}</td>
                <td>{region['avg_orders_per_driver']:.1f}</td>
                <td>₹{region['total_cash']:,.2f}</td>
                <td>{region['cancellation_rate']:.1f}%</td>
            </tr>
"""
            html += '        </table>\n'
        
        html += '    </div>\n'
        return html
    
    def _generate_comparison_section(self) -> str:
        """Generate day-over-day comparison section."""
        if 'day_over_day' not in self.analysis_results:
            return ""
        
        dod = self.analysis_results['day_over_day']
        html = '    <div class="section">\n'
        html += '        <h2>📊 Day-over-Day Comparison</h2>\n'
        
        # Add comparison chart
        if 'day_over_day' in self.charts:
            html += f'        <div class="chart"><img src="{self.charts["day_over_day"]}" alt="Day-over-Day Comparison"></div>\n'
        
        # Overall changes
        if dod.get('overall_changes'):
            html += '        <h3>Overall Changes</h3>\n'
            html += '        <table>\n'
            html += '            <tr><th>Metric</th><th>Previous Day</th><th>Current Day</th><th>Change</th><th>% Change</th></tr>\n'
            
            for metric, data in dod['overall_changes'].items():
                if metric == 'driver_count':
                    continue  # Skip driver count in this table
                
                change_class = 'positive' if data.get('change', 0) > 0 else 'negative'
                change_symbol = '+' if data.get('change', 0) > 0 else ''
                
                html += f"""
            <tr>
                <td><strong>{metric.replace('_', ' ').title()}</strong></td>
                <td>{data.get('previous', 0):,.0f}</td>
                <td>{data.get('current', 0):,.0f}</td>
                <td class="{change_class}">{change_symbol}{data.get('change', 0):,.0f}</td>
                <td class="{change_class}">{data.get('pct_change', 0):+.1f}%</td>
            </tr>
"""
            html += '        </table>\n'
        
        # Region changes
        if dod.get('region_changes'):
            html += '        <h3>Top Region Changes</h3>\n'
            html += '        <table>\n'
            html += '            <tr><th>Region</th><th>Previous Orders</th><th>Current Orders</th><th>Change</th><th>% Change</th></tr>\n'
            
            for region in dod['region_changes'][:10]:
                change_class = 'positive' if region['change'] > 0 else 'negative'
                change_symbol = '+' if region['change'] > 0 else ''
                
                html += f"""
            <tr>
                <td><strong>{region['region']}</strong></td>
                <td>{region['previous_orders']}</td>
                <td>{region['current_orders']}</td>
                <td class="{change_class}">{change_symbol}{region['change']}</td>
                <td class="{change_class}">{region['pct_change']:+.1f}%</td>
            </tr>
"""
            html += '        </table>\n'
        
        html += '    </div>\n'
        return html

    def _generate_integrity_section(self) -> str:
        """Generate the Porter Driver Integrity & Productivity Analysis section."""
        html = '<div class="section" style="border-top: 5px solid #e74c3c;">\n'
        html += '    <h2 style="color: #c0392b;">🔎 Porter Driver Integrity & Productivity Analysis</h2>\n'
        
        integrity = self.integrity_results
        
        # Section Executive Summary
        activity = integrity.get('activity_summary', [])
        if activity:
            total_drivers = len(activity)
            avg_cancel = sum(d['cancel_pct'] for d in activity) / total_drivers
            avg_idle = sum(d['idle_pct'] for d in activity) / total_drivers
            risk_count = len(integrity.get('risk_flags', []))
            
            html += f"""
    <div class="insights">
        <h3>📊 Executive Summary</h3>
        <p><strong>Total Drivers Analyzed:</strong> {total_drivers}</p>
        <p><strong>Avg Cancel %:</strong> {avg_cancel:.1f}%</p>
        <p><strong>Avg Idle %:</strong> {avg_idle:.1f}%</p>
        <p><strong>High-Risk Drivers:</strong> {risk_count}</p>
    </div>
"""

        # Section 1: Driver Activity Summary Table
        if activity:
            html += """
    <h3>Section 1: Driver Activity Summary Table</h3>
    <div style="overflow-x: auto;">
        <table style="font-size: 0.85em;">
            <tr>
                <th>Driver</th>
                <th>Assigned</th>
                <th>Comp</th>
                <th>Cancel %</th>
                <th>Total KM</th>
                <th>Earnings</th>
                <th>Idle %</th>
                <th>KM/Order</th>
                <th>Orders/Hr</th>
            </tr>
"""
            for d in activity:
                html += f"""
            <tr>
                <td>{d['driver_name']}</td>
                <td>{d['total_orders']}</td>
                <td>{d['completed_orders']}</td>
                <td class="{'negative' if d['cancel_pct'] > 20 else ''}">{d['cancel_pct']}%</td>
                <td>{d['total_km']}</td>
                <td>₹{d['total_earnings']}</td>
                <td class="{'negative' if d['idle_pct'] > 40 else ''}">{d['idle_pct']}%</td>
                <td>{d['km_per_order']}</td>
                <td>{d['orders_per_hour']}</td>
            </tr>
"""
            html += "        </table>\n    </div>\n"

        # Section 2: Exception & Risk Flags
        risk_flags = integrity.get('risk_flags', [])
        if risk_flags:
            html += """
    <h3>🚨 Driver Risk Flags</h3>
    <table>
        <tr>
            <th>Driver</th>
            <th>Flags</th>
            <th>Key Metrics</th>
        </tr>
"""
            for r in risk_flags:
                html += f"""
        <tr>
            <td><strong>{r['driver_name']}</strong><br><small>{r['mobile']}</small></td>
            <td><ul style="margin:0; padding-left:15px;">{' '.join([f'<li>{f}</li>' for f in r['flags']])}</ul></td>
            <td><small>{r['metrics']}</small></td>
        </tr>
"""
            html += "    </table>\n"

        # Section 3: Rogue Delivery Detection
        rogue = integrity.get('rogue_detection', [])
        if rogue:
            html += """
    <div class="warning" style="background-color: #fdeaea;">
        <h3>🕵️ Rogue Delivery Detection</h3>
        <table>
            <tr>
                <th>Driver</th>
                <th>Cancel Count</th>
                <th>Idle KM</th>
                <th>Status</th>
            </tr>
"""
            for rg in rogue:
                html += f"""
            <tr>
                <td>{rg['driver_name']}</td>
                <td>{rg['partner_cancels']}</td>
                <td class="negative">{rg['idle_km']} KM</td>
                <td class="negative"><strong>{rg['status']}</strong></td>
            </tr>
"""
            html += "        </table>\n    </div>\n"

        # Section 4: Performance Ranking
        rankings = integrity.get('rankings', {})
        if rankings:
            html += '<div style="display: flex; gap: 20px;">'
            
            # Top 5
            html += '<div style="flex: 1;"><h3>✅ Top 5 Drivers</h3><ul>'
            for d in rankings.get('top_5', []):
                html += f"<li>{d['driver_name']} ({d['orders_per_hour']} orders/hr)</li>"
            html += '</ul></div>'
            
            # Bottom 5
            html += '<div style="flex: 1;"><h3>❌ Bottom 5 Drivers</h3><ul>'
            for d in rankings.get('bottom_5', []):
                html += f"<li>{d['driver_name']} ({d['idle_pct']}% idle)</li>"
            html += '</ul></div></div>'

        # Section 7: Daily Integrity Score
        scores = integrity.get('integrity_scores', [])
        if scores:
            html += """
    <h3>🔢 Daily Integrity Score</h3>
    <table>
        <tr>
            <th>Driver</th>
            <th>Score (0-100)</th>
            <th>Action</th>
        </tr>
"""
            for s in scores:
                status_class = 'negative' if s['score'] < 40 else 'warning' if s['score'] < 60 else 'positive'
                html += f"""
        <tr>
            <td>{s['driver_name']}</td>
            <td><strong>{s['score']}</strong></td>
            <td class="{status_class}">{s['status']}</td>
        </tr>
"""
            html += "    </table>\n"

        html += '</div>\n'
        return html

    def _generate_monthly_relational_section(self) -> str:
        """Generate 1-2 Month Relational & Shift Analytics section."""
        html = '    <div class="section">\n'
        html += '        <h2>📅 Monthly Relational & Shift Analytics</h2>\n'
        
        # 1. Shift Durations Breakdown
        shift_dur = self.monthly_results.get('shift_durations', {})
        if shift_dur:
            html += """
        <h3>⏱️ Driver Shift Duration Breakdown</h3>
        <table>
            <tr>
                <th>Shift Duration Category</th>
                <th>Driver Count</th>
                <th>Percentage (%)</th>
                <th>Avg. Cash Collected</th>
                <th>Avg. Orders Completed</th>
            </tr>
"""
            u8 = shift_dur.get('under_8_hours', {})
            b8_12 = shift_dur.get('between_8_12_hours', {})
            o12 = shift_dur.get('over_12_hours', {})

            html += f"""
            <tr>
                <td><strong>&lt; 8 Hours (Part-time / Short Shift)</strong></td>
                <td>{u8.get('count', 0)}</td>
                <td>{u8.get('pct', 0)}%</td>
                <td>₹{u8.get('avg_cash', 0)}</td>
                <td>{u8.get('avg_orders', 0)}</td>
            </tr>
            <tr>
                <td><strong>8 - 12 Hours (Standard Shift)</strong></td>
                <td>{b8_12.get('count', 0)}</td>
                <td>{b8_12.get('pct', 0)}%</td>
                <td>₹{b8_12.get('avg_cash', 0)}</td>
                <td>{b8_12.get('avg_orders', 0)}</td>
            </tr>
            <tr>
                <td><strong>12+ Hours (High Duty Shift)</strong></td>
                <td>{o12.get('count', 0)}</td>
                <td>{o12.get('pct', 0)}%</td>
                <td>₹{o12.get('avg_cash', 0)}</td>
                <td>{o12.get('avg_orders', 0)}</td>
            </tr>
        </table>
"""

        # 2. Relational Insights & Correlations
        relational = self.monthly_results.get('relational', {})
        corrs = relational.get('correlations', {})
        if corrs:
            html += f"""
        <h3>🔗 Duty Timing Correlations</h3>
        <div style="display: flex; gap: 15px; margin: 15px 0;">
            <div style="flex: 1; background: #eef2ff; padding: 15px; border-radius: 8px;">
                <h4 style="margin: 0; color: #4338ca;">Duty Hours vs Cash</h4>
                <p style="font-size: 1.4em; font-weight: bold; margin: 5px 0;">{corrs.get('hours_vs_cash', 0.0)}</p>
                <small>Positive correlation indicates longer shifts directly yield higher cash.</small>
            </div>
            <div style="flex: 1; background: #eef2ff; padding: 15px; border-radius: 8px;">
                <h4 style="margin: 0; color: #4338ca;">Duty Hours vs Notifications</h4>
                <p style="font-size: 1.4em; font-weight: bold; margin: 5px 0;">{corrs.get('hours_vs_notifications', 0.0)}</p>
                <small>Measures notification volume delivery relative to active hours.</small>
            </div>
        </div>
"""

        # 3. Location Breakdown (Location vs Notifications & Cash)
        loc_breakdown = relational.get('location_breakdown', [])
        if loc_breakdown:
            html += """
        <h3>📍 Location vs. Notifications & Cash Collection</h3>
        <table>
            <tr>
                <th>Region / Cluster</th>
                <th>Active Drivers</th>
                <th>Total Cash</th>
                <th>Avg. Cash / Driver</th>
                <th>Total Notifications</th>
                <th>Avg. Notifications / Driver</th>
            </tr>
"""
            for loc in loc_breakdown[:10]:
                html += f"""
            <tr>
                <td><strong>{loc['region']}</strong></td>
                <td>{loc['driver_count']}</td>
                <td>₹{loc['total_cash']}</td>
                <td>₹{loc['avg_cash']}</td>
                <td>{loc['total_notifications']}</td>
                <td>{loc['avg_notifications']}</td>
            </tr>
"""
            html += "        </table>\n"

        html += '    </div>\n'
        return html
    
    def save_report(self, filepath: str, html_content: str = None) -> bool:
        """
        Save HTML report to file.
        
        Args:
            filepath: Path to save the report
            html_content: HTML content (generates if not provided)
            
        Returns:
            True if saved successfully
        """
        try:
            if html_content is None:
                html_content = self.generate_html_report()
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logger.info(f"Report saved to: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving report: {str(e)}", exc_info=True)
            return False
