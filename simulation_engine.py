import random
import csv
import copy
from datetime import datetime, timedelta
from collections import deque
import threading
import time
import os
import pandas as pd

# Configuration from the original file
CONFIG = {
    "simulation": {
        "pause_between_rounds_seconds": 10,
        "forecast_duration_minutes": 5,
    },
    "crash_time_generation": {
        "low_mult_max_seconds": 5,
        "med_mult_max_seconds": 20,
        "high_mult_max_seconds": 120,
    },
    "quality_rules": {
        "hour": {
            "peak": {"hours": [9, 10, 14, 15, 20, 21], "weights": [0.4, 0.4, 0.2]},
            "medium": {"hours": [11, 12, 13, 16, 17, 18, 19], "weights": [0.3, 0.5, 0.2]},
            "off_peak": {"weights": [0.2, 0.4, 0.3, 0.1]},
        },
        "quarter": {
            "first": {"weights": [0.6, 0.4]},
            "last": {"weights": [0.4, 0.4, 0.2]},
            "middle": {"weights": [0.3, 0.5, 0.2]},
        },
        "five_min": {
            "even": {"weights": [0.6, 0.4]},
            "odd": {"weights": [0.4, 0.4, 0.2]},
        },
        "minute": {
            "special_9_early": "catastrophic",
            "special_9_late": {"weights": [0.3, 0.7]},
            "special_1_early": {"weights": [0.4, 0.6]},
            "special_1_late": {"weights": [0.6, 0.4]},
            "multiple_of_7": "catastrophic",
            "multiple_of_5": {"weights": [0.6, 0.4]},
            "multiple_of_3": {"weights": [0.6, 0.4]},
            "default": {"weights": [0.5, 0.5]},
        }
    },
    "multiplier_generation": {
        "special_minute_low_chance": 0.95,
        "good_phase_high_mult_chance": 0.7,
        "bad_phase_low_mult_chance": 0.7,
        "catastrophic_phase_low_mult_chance": 0.9,
    },
    "compensation": {
        "history_length": 5,
        "trigger_threshold": 4,
        "min_low_mults": 2,
        "max_low_mults": 4,
    },
    "output": {
        "csv_filename": "interactive_session_log.csv"
    }
}

class CrashSimulator:
    def __init__(self):
        self.hourly_trends = {}
        self.quarter_hour_trends = {}
        self.five_min_trends = {}
        self.minute_trends = {}
        self.session_data = []
        self.is_running = False
        self.is_paused = False
        self.current_round = 0
        self.current_multiplier = 1.00
        self.crash_time = None
        self.round_start_time = None
        self.callbacks = []
        
    def add_callback(self, callback):
        """Add callback function to be called on each simulation update"""
        self.callbacks.append(callback)
    
    def remove_callback(self, callback):
        """Remove callback function"""
        if callback in self.callbacks:
            self.callbacks.remove(callback)
    
    def _notify_callbacks(self, data):
        """Notify all registered callbacks with simulation data"""
        for callback in self.callbacks:
            try:
                callback(data)
            except Exception as e:
                print(f"Error in callback: {e}")

    @staticmethod
    def _get_time_intervals(time):
        return {
            'hour': f"{time.hour:02d}:00-{(time.hour+1)%24:02d}:00",
            'quarter': f"{time.hour:02d}:{(time.minute//15)*15:02d}-{time.hour:02d}:{min((time.minute//15)*15+15, 60):02d}",
            'five_min': f"{time.hour:02d}:{(time.minute//5)*5:02d}-{time.hour:02d}:{min((time.minute//5)*5+5, 60):02d}",
            'minute': f"{time.hour:02d}:{time.minute:02d}:00-{time.hour:02d}:{time.minute:02d}:59"
        }

    @staticmethod
    def _initialize_trend():
        return {
            'low_count': 0, 'med_count': 0, 'high_count': 0,
            'last_multipliers': deque(maxlen=10),
            'phase': 'normal',
            'compensation_mode': False, 'compensation_target': 0, 'compensation_count': 0
        }

    def _determine_interval_quality(self, interval_type, time):
        rules = CONFIG['quality_rules'][interval_type]
        if interval_type == 'hour':
            hour = time.hour
            if hour in rules['peak']['hours']: 
                return random.choices(['good', 'normal', 'bad'], weights=rules['peak']['weights'])[0]
            elif hour in rules['medium']['hours']: 
                return random.choices(['good', 'normal', 'bad'], weights=rules['medium']['weights'])[0]
            else: 
                return random.choices(['good', 'normal', 'bad', 'catastrophic'], weights=rules['off_peak']['weights'])[0]
        elif interval_type == 'quarter':
            q = time.minute // 15
            if q == 0: 
                return random.choices(['good', 'normal'], weights=rules['first']['weights'])[0]
            elif q == 3: 
                return random.choices(['normal', 'bad', 'catastrophic'], weights=rules['last']['weights'])[0]
            else: 
                return random.choices(['good', 'normal', 'bad'], weights=rules['middle']['weights'])[0]
        elif interval_type == 'five_min':
            b = time.minute // 5
            if b % 2 == 0: 
                return random.choices(['good', 'normal'], weights=rules['even']['weights'])[0]
            else: 
                return random.choices(['normal', 'bad', 'catastrophic'], weights=rules['odd']['weights'])[0]
        elif interval_type == 'minute':
            m, s = time.minute, time.second
            if m % 10 == 9: 
                return rules['special_9_early'] if s < 30 else random.choices(['bad', 'catastrophic'], weights=rules['special_9_late']['weights'])[0]
            if m % 10 == 1: 
                return random.choices(['bad', 'catastrophic'], weights=rules['special_1_early']['weights'])[0] if s < 30 else random.choices(['normal', 'bad'], weights=rules['special_1_late']['weights'])[0]
            if m % 7 == 0: 
                return rules['multiple_of_7']
            if m % 5 == 0: 
                return random.choices(['bad', 'catastrophic'], weights=rules['multiple_of_5']['weights'])[0]
            if m % 3 == 0: 
                return random.choices(['normal', 'bad'], weights=rules['multiple_of_3']['weights'])[0]
            return random.choices(['good', 'normal'], weights=rules['default']['weights'])[0]
        return 'normal'

    def _get_quality_multiplier(self, quality, time):
        gen_rules = CONFIG['multiplier_generation']
        minute, second = time.minute, time.second
        if (minute % 10 == 9 and second < 30) or (minute % 10 == 1 and second < 30):
            return round(random.uniform(1.00, 1.99), 2) if random.random() < gen_rules['special_minute_low_chance'] else round(random.uniform(2.00, 2.50), 2)
        if quality == 'good': 
            return round(random.uniform(2.00, 9.99), 2) if random.random() < gen_rules['good_phase_high_mult_chance'] else round(random.uniform(1.00, 1.99), 2)
        elif quality == 'normal':
            rand = random.random()
            if rand < 0.5: return round(random.uniform(1.00, 1.99), 2)
            elif rand < 0.8: return round(random.uniform(2.00, 3.00), 2)
            else: return round(random.uniform(3.01, 9.99), 2)
        elif quality == 'bad': 
            return round(random.uniform(1.00, 1.99), 2) if random.random() < gen_rules['bad_phase_low_mult_chance'] else round(random.uniform(2.00, 4.00), 2)
        elif quality == 'catastrophic': 
            return round(random.uniform(1.00, 1.99), 2) if random.random() < gen_rules['catastrophic_phase_low_mult_chance'] else round(random.uniform(2.00, 3.00), 2)
        return round(random.uniform(1.00, 1.99), 2)

    def _generate_crash_time(self, start, multiplier):
        crash_rules = CONFIG['crash_time_generation']
        if multiplier < 2.00: max_seconds = crash_rules['low_mult_max_seconds']
        elif multiplier < 10.00: max_seconds = crash_rules['med_mult_max_seconds']
        else: max_seconds = crash_rules['high_mult_max_seconds']
        return start + timedelta(seconds=random.uniform(1, max_seconds))

    def _update_all_trends(self, multiplier, time):
        intervals = self._get_time_intervals(time)
        for trend_attr, trend_key in [('hourly_trends', intervals['hour']), 
                                     ('quarter_hour_trends', intervals['quarter']), 
                                     ('five_min_trends', intervals['five_min']), 
                                     ('minute_trends', intervals['minute'])]:
            trend_dict = getattr(self, trend_attr)
            if trend_key not in trend_dict: 
                trend_dict[trend_key] = self._initialize_trend()
            trend = trend_dict[trend_key]
            
            if multiplier < 2.00: trend['low_count'] += 1
            elif multiplier < 10.00: trend['med_count'] += 1
            else: trend['high_count'] += 1
            
            trend['last_multipliers'].append(multiplier)

    def _generate_multiplier(self, time):
        intervals = self._get_time_intervals(time)
        
        for trend_attr, (trend_key, interval_type) in [('hourly_trends', (intervals['hour'], 'hour')), 
                                                       ('quarter_hour_trends', (intervals['quarter'], 'quarter')), 
                                                       ('five_min_trends', (intervals['five_min'], 'five_min')), 
                                                       ('minute_trends', (intervals['minute'], 'minute'))]:
            trend_dict = getattr(self, trend_attr)
            if trend_key not in trend_dict:
                trend_dict[trend_key] = self._initialize_trend()
                quality = self._determine_interval_quality(interval_type, time)
                trend_dict[trend_key]['phase'] = quality
        
        minute_trend = self.minute_trends[intervals['minute']]
        adapted_quality = self._adapt_quality_based_on_history('minute', time)
        if adapted_quality:
            minute_trend['phase'] = adapted_quality
        
        minute_quality = minute_trend['phase']
        base_multiplier = self._get_adaptive_multiplier(minute_quality, time, minute_trend)
        
        return round(base_multiplier, 2)

    def _adapt_quality_based_on_history(self, interval_type, time):
        trend = self._get_trend_for_interval(interval_type, time)
        
        if not trend or len(trend['last_multipliers']) < 3:
            return None
        
        recent_mults = trend['last_multipliers']
        avg_mult = sum(recent_mults) / len(recent_mults)
        low_count = sum(1 for m in recent_mults if m < 2.0)
        high_count = sum(1 for m in recent_mults if m >= 3.0)
        
        if avg_mult < 1.5 and low_count >= 3:
            return 'bad'
        elif avg_mult > 3.0 and high_count >= 2:
            return 'good'
        elif low_count >= 4:
            return 'catastrophic'
        
        return None

    def _get_trend_for_interval(self, interval_type, time):
        intervals = self._get_time_intervals(time)
        trend_attr_map = {
            'hour': 'hourly_trends',
            'quarter': 'quarter_hour_trends',
            'five_min': 'five_min_trends',
            'minute': 'minute_trends'
        }
        interval_key_map = {
            'hour': intervals['hour'],
            'quarter': intervals['quarter'],
            'five_min': intervals['five_min'],
            'minute': intervals['minute']
        }
        
        trend_dict = getattr(self, trend_attr_map[interval_type])
        return trend_dict.get(interval_key_map[interval_type])

    def _get_adaptive_multiplier(self, quality, time, trend):
        base_prob = CONFIG['multiplier_generation']['good_phase_high_mult_chance']
        
        if trend['low_count'] > trend['high_count'] * 2:
            base_prob += 0.2
        elif trend['high_count'] > trend['low_count'] * 2:
            base_prob -= 0.2
        
        return self._get_quality_multiplier_with_adjusted_prob(quality, time, base_prob)

    def _get_quality_multiplier_with_adjusted_prob(self, quality, time, adjusted_prob):
        return self._get_quality_multiplier(quality, time)

    def _log_to_csv(self, data):
        """Log simulation data to CSV file"""
        file_exists = os.path.isfile(CONFIG['output']['csv_filename'])
        
        with open(CONFIG['output']['csv_filename'], 'a', newline='') as csvfile:
            fieldnames = ['timestamp', 'round', 'multiplier', 'crash_time', 'duration_seconds', 'phase', 'compensation']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            if not file_exists:
                writer.writeheader()
            
            writer.writerow(data)

    def start_simulation(self):
        """Start the crash simulation"""
        if self.is_running:
            return
        
        self.is_running = True
        self.is_paused = False
        
        def run_simulation():
            while self.is_running:
                if not self.is_paused:
                    self._run_single_round()
                time.sleep(0.1)  # Small delay for real-time updates
        
        self.simulation_thread = threading.Thread(target=run_simulation, daemon=True)
        self.simulation_thread.start()

    def _run_single_round(self):
        """Run a single simulation round"""
        self.current_round += 1
        current_time = datetime.now()
        self.round_start_time = current_time
        
        # Generate multiplier and crash time
        multiplier = self._generate_multiplier(current_time)
        self.current_multiplier = multiplier
        self.crash_time = self._generate_crash_time(current_time, multiplier)
        
        # Update trends
        self._update_all_trends(multiplier, current_time)
        
        # Get current phase
        intervals = self._get_time_intervals(current_time)
        minute_trend = self.minute_trends.get(intervals['minute'], self._initialize_trend())
        current_phase = minute_trend.get('phase', 'normal')
        
        # Calculate duration
        duration = (self.crash_time - current_time).total_seconds()
        
        # Prepare data for logging and callbacks
        round_data = {
            'timestamp': current_time.isoformat(),
            'round': self.current_round,
            'multiplier': multiplier,
            'crash_time': self.crash_time.isoformat(),
            'duration_seconds': duration,
            'phase': current_phase,
            'compensation': minute_trend.get('compensation_mode', False)
        }
        
        # Log to CSV
        self._log_to_csv(round_data)
        
        # Add to session data
        self.session_data.append(round_data)
        
        # Notify callbacks
        self._notify_callbacks(round_data)
        
        # Wait for crash time or pause
        start_wait = time.time()
        while time.time() - start_wait < duration and self.is_running and not self.is_paused:
            time.sleep(0.1)
        
        # Pause between rounds
        if self.is_running and not self.is_paused:
            time.sleep(CONFIG['simulation']['pause_between_rounds_seconds'])

    def stop_simulation(self):
        """Stop the crash simulation"""
        self.is_running = False
        self.is_paused = False

    def pause_simulation(self):
        """Pause the crash simulation"""
        self.is_paused = True

    def resume_simulation(self):
        """Resume the crash simulation"""
        self.is_paused = False

    def get_session_stats(self):
        """Get statistics for the current session"""
        if not self.session_data:
            return {}
        
        multipliers = [float(d['multiplier']) for d in self.session_data]
        return {
            'total_rounds': len(self.session_data),
            'avg_multiplier': sum(multipliers) / len(multipliers),
            'min_multiplier': min(multipliers),
            'max_multiplier': max(multipliers),
            'low_mult_count': sum(1 for m in multipliers if m < 2.0),
            'med_mult_count': sum(1 for m in multipliers if 2.0 <= m < 10.0),
            'high_mult_count': sum(1 for m in multipliers if m >= 10.0)
        }

    def export_session_data(self, filename=None):
        """Export session data to CSV"""
        if not filename:
            filename = f"session_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        if self.session_data:
            df = pd.DataFrame(self.session_data)
            df.to_csv(filename, index=False)
            return filename
        return None

    def load_historical_data(self, filename=None):
        """Load historical data from CSV"""
        if not filename:
            filename = CONFIG['output']['csv_filename']
        
        try:
            if os.path.exists(filename):
                return pd.read_csv(filename)
            return pd.DataFrame()
        except Exception as e:
            print(f"Error loading historical data: {e}")
            return pd.DataFrame()

    def update_config(self, new_config):
        """Update simulation configuration"""
        global CONFIG
        CONFIG.update(new_config)
    
    @staticmethod
    def get_multiplier_color_category(multiplier):
        """Get color category for multiplier display"""
        if multiplier < 2.00: 
            return "grey"
        elif multiplier < 3.00: 
            return "green"
        elif multiplier < 4.00: 
            return "purple"
        elif multiplier < 10.00: 
            return "yellow"
        else: 
            return "cyan"

    @staticmethod
    def get_multiplier_color_category(multiplier):
        """Get color category for multiplier display"""
        if multiplier < 2.00: return "grey"
        if 2.00 <= multiplier < 3.00: return "green"
        if 3.01 <= multiplier < 4.00: return "purple"
        if 4.01 <= multiplier < 10.00: return "yellow"
        return "cyan"
