import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
import os

class DataManager:
    def __init__(self, csv_filename="interactive_session_log.csv"):
        self.csv_filename = csv_filename
    
    def load_historical_data(self):
        """Load historical data from CSV file"""
        try:
            if os.path.exists(self.csv_filename):
                df = pd.read_csv(self.csv_filename)
                if not df.empty:
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                    df['crash_time'] = pd.to_datetime(df['crash_time'])
                    df['multiplier'] = pd.to_numeric(df['multiplier'])
                return df
            return pd.DataFrame()
        except Exception as e:
            st.error(f"Error loading historical data: {e}")
            return pd.DataFrame()
    
    def filter_data_by_time_range(self, data, hours_back=24):
        """Filter data by time range"""
        if data.empty:
            return data
        
        cutoff_time = datetime.now() - timedelta(hours=hours_back)
        return data[data['timestamp'] >= cutoff_time]
    
    def filter_data_by_date_range(self, data, start_date, end_date):
        """Filter data by specific date range"""
        if data.empty:
            return data
        
        return data[
            (data['timestamp'].dt.date >= start_date) & 
            (data['timestamp'].dt.date <= end_date)
        ]
    
    def get_trend_data(self, data, interval='hour'):
        """Get aggregated trend data for specified interval"""
        if data.empty:
            return pd.DataFrame()
        
        try:
            if interval == 'hour':
                data['time_group'] = data['timestamp'].dt.floor('H')
            elif interval == 'minute':
                data['time_group'] = data['timestamp'].dt.floor('T')
            elif interval == 'quarter':
                data['time_group'] = data['timestamp'].dt.floor('15T')
            elif interval == 'five_min':
                data['time_group'] = data['timestamp'].dt.floor('5T')
            else:
                return data
            
            return data.groupby('time_group').agg({
                'multiplier': ['mean', 'min', 'max', 'count'],
                'duration_seconds': 'mean',
                'phase': lambda x: x.mode().iloc[0] if len(x.mode()) > 0 else 'unknown'
            }).reset_index()
        except Exception as e:
            st.error(f"Error creating trend data: {e}")
            return pd.DataFrame()
    
    def calculate_statistics(self, data):
        """Calculate comprehensive statistics from data"""
        if data.empty:
            return {}
        
        try:
            multipliers = data['multiplier']
            
            stats = {
                'total_rounds': len(data),
                'avg_multiplier': multipliers.mean(),
                'median_multiplier': multipliers.median(),
                'min_multiplier': multipliers.min(),
                'max_multiplier': multipliers.max(),
                'std_multiplier': multipliers.std(),
                'low_mult_count': len(multipliers[multipliers < 2.0]),
                'med_mult_count': len(multipliers[(multipliers >= 2.0) & (multipliers < 10.0)]),
                'high_mult_count': len(multipliers[multipliers >= 10.0]),
            }
            
            # Add percentage breakdowns
            total = stats['total_rounds']
            if total > 0:
                stats['low_mult_pct'] = (stats['low_mult_count'] / total) * 100
                stats['med_mult_pct'] = (stats['med_mult_count'] / total) * 100
                stats['high_mult_pct'] = (stats['high_mult_count'] / total) * 100
            
            # Phase statistics if available
            if 'phase' in data.columns:
                phase_counts = data['phase'].value_counts().to_dict()
                stats.update({f'phase_{k}': v for k, v in phase_counts.items()})
            
            # Duration statistics if available
            if 'duration_seconds' in data.columns:
                durations = data['duration_seconds']
                stats.update({
                    'avg_duration': durations.mean(),
                    'median_duration': durations.median(),
                    'min_duration': durations.min(),
                    'max_duration': durations.max()
                })
            
            return stats
        except Exception as e:
            st.error(f"Error calculating statistics: {e}")
            return {}
    
    def export_data(self, data, filename=None):
        """Export data to CSV file"""
        if data.empty:
            st.warning("No data to export")
            return None
        
        try:
            if not filename:
                filename = f"crash_simulation_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            
            data.to_csv(filename, index=False)
            return filename
        except Exception as e:
            st.error(f"Error exporting data: {e}")
            return None
    
    def get_data_summary(self, data):
        """Get a summary of the loaded data"""
        if data.empty:
            return "No data loaded"
        
        summary = {
            'total_records': len(data),
            'date_range': f"{data['timestamp'].min()} to {data['timestamp'].max()}",
            'columns': list(data.columns),
            'multiplier_range': f"{data['multiplier'].min():.2f} - {data['multiplier'].max():.2f}"
        }
        
        return summary
    
    def clean_data(self, data):
        """Clean and validate data"""
        if data.empty:
            return data
        
        # Remove invalid multipliers
        data = data[data['multiplier'] >= 1.0]
        
        # Remove rows with missing critical data
        data = data.dropna(subset=['timestamp', 'multiplier'])
        
        # Sort by timestamp
        data = data.sort_values('timestamp')
        
        return data
    
    def get_recent_performance(self, data, last_n_rounds=100):
        """Get performance metrics for recent rounds"""
        if data.empty:
            return {}
        
        recent_data = data.tail(last_n_rounds)
        return self.calculate_statistics(recent_data)
