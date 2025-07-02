import random
import csv
import argparse
import copy
from datetime import datetime, timedelta
from collections import deque
import os

# ==============================================================================
# CONFIGURATION CENTRALE
# ==============================================================================

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
            "peak": {"hours": [9, 10, 14, 15, 20, 21], "weights": [0.4, 0.4, 0.2]}, # good, normal, bad
            "medium": {"hours": [11, 12, 13, 16, 17, 18, 19], "weights": [0.3, 0.5, 0.2]}, # good, normal, bad
            "off_peak": {"weights": [0.2, 0.4, 0.3, 0.1]}, # good, normal, bad, catastrophic
        },
        "quarter": {
            "first": {"weights": [0.6, 0.4]}, # good, normal
            "last": {"weights": [0.4, 0.4, 0.2]}, # normal, bad, catastrophic
            "middle": {"weights": [0.3, 0.5, 0.2]}, # good, normal, bad
        },
        "five_min": {
            "even": {"weights": [0.6, 0.4]}, # good, normal
            "odd": {"weights": [0.4, 0.4, 0.2]}, # normal, bad, catastrophic
        },
        "minute": {
            "special_9_early": "catastrophic",
            "special_9_late": {"weights": [0.3, 0.7]}, # bad, catastrophic
            "special_1_early": {"weights": [0.4, 0.6]}, # bad, catastrophic
            "special_1_late": {"weights": [0.6, 0.4]}, # normal, bad
            "multiple_of_7": "catastrophic",
            "multiple_of_5": {"weights": [0.6, 0.4]}, # bad, catastrophic
            "multiple_of_3": {"weights": [0.6, 0.4]}, # normal, bad
            "default": {"weights": [0.5, 0.5]}, # good, normal
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

# ==============================================================================
# CLASSES AUXILIAIRES
# ==============================================================================

class bcolors:
    GREY = '\033[90m'
    GREEN = '\033[92m'
    PURPLE = '\033[95m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    ENDC = '\033[0m'
    WARNING = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    ORANGE = '\033[38;5;208m'  # Ajout de la couleur orange

# ==============================================================================
# CLASSE DE BASE DU SIMULATEUR
# ==============================================================================

class CrashSimulator:
    @staticmethod
    def _get_multiplier_color(multiplier):
        if multiplier < 2.00: return bcolors.GREY
        if 2.00 <= multiplier < 3.00: return bcolors.GREEN
        if 3.01 <= multiplier < 4.00: return bcolors.PURPLE
        if 4.01 <= multiplier < 10.00: return bcolors.YELLOW
        return bcolors.CYAN

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
            if hour in rules['peak']['hours']: return random.choices(['good', 'normal', 'bad'], weights=rules['peak']['weights'])[0]
            elif hour in rules['medium']['hours']: return random.choices(['good', 'normal', 'bad'], weights=rules['medium']['weights'])[0]
            else: return random.choices(['good', 'normal', 'bad', 'catastrophic'], weights=rules['off_peak']['weights'])[0]
        elif interval_type == 'quarter':
            q = time.minute // 15
            if q == 0: return random.choices(['good', 'normal'], weights=rules['first']['weights'])[0]
            elif q == 3: return random.choices(['normal', 'bad', 'catastrophic'], weights=rules['last']['weights'])[0]
            else: return random.choices(['good', 'normal', 'bad'], weights=rules['middle']['weights'])[0]
        elif interval_type == 'five_min':
            b = time.minute // 5
            if b % 2 == 0: return random.choices(['good', 'normal'], weights=rules['even']['weights'])[0]
            else: return random.choices(['normal', 'bad', 'catastrophic'], weights=rules['odd']['weights'])[0]
        elif interval_type == 'minute':
            m, s = time.minute, time.second
            if m % 10 == 9: return rules['special_9_early'] if s < 30 else random.choices(['bad', 'catastrophic'], weights=rules['special_9_late']['weights'])[0]
            if m % 10 == 1: return random.choices(['bad', 'catastrophic'], weights=rules['special_1_early']['weights'])[0] if s < 30 else random.choices(['normal', 'bad'], weights=rules['special_1_late']['weights'])[0]
            if m % 7 == 0: return rules['multiple_of_7']
            if m % 5 == 0: return random.choices(['bad', 'catastrophic'], weights=rules['multiple_of_5']['weights'])[0]
            if m % 3 == 0: return random.choices(['normal', 'bad'], weights=rules['multiple_of_3']['weights'])[0]
            return random.choices(['good', 'normal'], weights=rules['default']['weights'])[0]
        return 'normal'

    def _get_quality_multiplier(self, quality, time):
        gen_rules = CONFIG['multiplier_generation']
        minute, second = time.minute, time.second
        if (minute % 10 == 9 and second < 30) or (minute % 10 == 1 and second < 30):
            return round(random.uniform(1.00, 1.99), 2) if random.random() < gen_rules['special_minute_low_chance'] else round(random.uniform(2.00, 2.50), 2)
        if quality == 'good': return round(random.uniform(2.00, 9.99), 2) if random.random() < gen_rules['good_phase_high_mult_chance'] else round(random.uniform(1.00, 1.99), 2)
        elif quality == 'normal':
            rand = random.random()
            if rand < 0.5: return round(random.uniform(1.00, 1.99), 2)
            elif rand < 0.8: return round(random.uniform(2.00, 3.00), 2)
            else: return round(random.uniform(3.01, 9.99), 2)
        elif quality == 'bad': return round(random.uniform(1.00, 1.99), 2) if random.random() < gen_rules['bad_phase_low_mult_chance'] else round(random.uniform(2.00, 4.00), 2)
        elif quality == 'catastrophic': return round(random.uniform(1.00, 1.99), 2) if random.random() < gen_rules['catastrophic_phase_low_mult_chance'] else round(random.uniform(2.00, 3.00), 2)
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
            
            # Compte les multiplicateurs par catégorie
            if multiplier < 2.00: trend['low_count'] += 1
            elif multiplier < 10.00: trend['med_count'] += 1
            else: trend['high_count'] += 1
            
            # Stocke les 10 derniers multiplicateurs
            trend['last_multipliers'].append(multiplier)

    def _generate_multiplier(self, time):
        intervals = self._get_time_intervals(time)
        
        # Initialise les tendances si nécessaire
        for trend_attr, (trend_key, interval_type) in [('hourly_trends', (intervals['hour'], 'hour')), 
                                                       ('quarter_hour_trends', (intervals['quarter'], 'quarter')), 
                                                       ('five_min_trends', (intervals['five_min'], 'five_min')), 
                                                       ('minute_trends', (intervals['minute'], 'minute'))]:
            trend_dict = getattr(self, trend_attr)
            if trend_key not in trend_dict:
                trend_dict[trend_key] = self._initialize_trend()
                quality = self._determine_interval_quality(interval_type, time)
                trend_dict[trend_key]['phase'] = quality
        
        # NOUVEAU: Utilise les données réelles pour ajuster la qualité
        minute_trend = self.minute_trends[intervals['minute']]
        
        # Adapte la qualité selon l'historique
        adapted_quality = self._adapt_quality_based_on_history('minute', time)
        if adapted_quality:
            minute_trend['phase'] = adapted_quality
        
        # Utilise la qualité adaptée
        minute_quality = minute_trend['phase']
        
        # NOUVEAU: Ajuste les probabilités selon les tendances
        base_multiplier = self._get_adaptive_multiplier(minute_quality, time, minute_trend)
        
        return round(base_multiplier, 2)

    def _adapt_quality_based_on_history(self, interval_type, time):
        """Adapte la qualité selon l'historique des données réelles."""
        trend = self._get_trend_for_interval(interval_type, time)
        
        if not trend or len(trend['last_multipliers']) < 3:
            return None  # Pas assez de données
        
        recent_mults = trend['last_multipliers']
        avg_mult = sum(recent_mults) / len(recent_mults)
        low_count = sum(1 for m in recent_mults if m < 2.0)
        high_count = sum(1 for m in recent_mults if m >= 3.0)
        
        # Règles d'adaptation
        if avg_mult < 1.5 and low_count >= 3:
            return 'bad'  # Force une phase mauvaise
        elif avg_mult > 3.0 and high_count >= 2:
            return 'good'  # Force une phase bonne
        elif low_count >= 4:
            return 'catastrophic'  # Force une phase catastrophique
        
        return None  # Garde la qualité actuelle

    def _get_adaptive_multiplier(self, quality, time, trend):
        """Génère un multiplicateur avec probabilités ajustées selon l'historique."""
        base_prob = CONFIG['multiplier_generation']['good_phase_high_mult_chance']
        
        # Ajuste selon l'historique récent
        if trend['low_count'] > trend['high_count'] * 2:
            # Trop de multiplicateurs bas récemment → augmente les chances de multiplicateurs élevés
            base_prob += 0.2
            print(f"{bcolors.CYAN}📈 Compensation: augmentation probabilité multiplicateurs élevés{bcolors.ENDC}")
        
        elif trend['high_count'] > trend['low_count'] * 2:
            # Trop de multiplicateurs élevés récemment → augmente les chances de multiplicateurs bas
            base_prob -= 0.2
            print(f"{bcolors.CYAN}📉 Compensation: augmentation probabilité multiplicateurs bas{bcolors.ENDC}")
        
        # Applique les probabilités ajustées
        return self._get_quality_multiplier_with_adjusted_prob(quality, time, base_prob)

    def _get_quality_multiplier_with_adjusted_prob(self, quality, time, adjusted_prob):
        """Version modifiée de _get_quality_multiplier avec probabilités ajustées."""
        gen_rules = CONFIG['multiplier_generation']
        minute, second = time.minute, time.second
        
        # Règles spéciales pour minutes particulières (inchangées)
        if (minute % 10 == 9 and second < 30) or (minute % 10 == 1 and second < 30):
            return round(random.uniform(1.00, 1.99), 2) if random.random() < gen_rules['special_minute_low_chance'] else round(random.uniform(2.00, 2.50), 2)
        
        # Ajuste selon la qualité avec probabilités modifiées
        if quality == 'good':
            return round(random.uniform(2.00, 9.99), 2) if random.random() < adjusted_prob else round(random.uniform(1.00, 1.99), 2)
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

    def _get_trend_for_interval(self, interval_type, time):
        """Récupère la tendance pour un intervalle donné."""
        intervals = self._get_time_intervals(time)
        trend_key = intervals[interval_type]
        
        if interval_type == 'hour':
            return self.hourly_trends.get(trend_key)
        elif interval_type == 'quarter':
            return self.quarter_hour_trends.get(trend_key)
        elif interval_type == 'five_min':
            return self.five_min_trends.get(trend_key)
        elif interval_type == 'minute':
            return self.minute_trends.get(trend_key)
        
        return None

    def _check_compensation_needed(self, interval_type, time):
        trend = self._get_trend_for_interval(interval_type, time)
        
        # Si trop de multiplicateurs bas consécutifs
        if trend['low_count'] >= CONFIG['compensation']['trigger_threshold']:
            return True
        return False

    def analyze_multiplier_time_correlation(self, real_multiplier, real_crash_time, start_time):
        """Analyse la corrélation entre multiplicateur et temps de crash."""
        actual_duration = (real_crash_time - start_time).total_seconds()
        
        # Ajuste les paramètres selon les données réelles
        if real_multiplier < 2.00:
            self._update_crash_time_params('low', actual_duration)
        elif real_multiplier < 10.00:
            self._update_crash_time_params('med', actual_duration)
        else:
            self._update_crash_time_params('high', actual_duration)

    def detect_temporal_patterns(self, real_crash_time):
        """Détecte des patterns dans les heures de crash."""
        hour = real_crash_time.hour
        minute = real_crash_time.minute
        second = real_crash_time.second
        
        # Analyse des patterns
        if hour in [9, 10, 14, 15, 20, 21]:  # Heures de pointe
            self._update_peak_hour_patterns(real_crash_time)
        elif minute % 5 == 0:  # Minutes multiples de 5
            self._update_five_minute_patterns(real_crash_time)

    def _store_crash_time_data(self, category, actual_duration, real_multiplier):
        """Stocke les données de temps de crash pour analyse."""
        if not hasattr(self, 'crash_time_data'):
            self.crash_time_data = {
                'low': {'durations': [], 'multipliers': []},
                'med': {'durations': [], 'multipliers': []},
                'high': {'durations': [], 'multipliers': []}
            }
        
        # Stocke les données par catégorie
        self.crash_time_data[category]['durations'].append(actual_duration)
        self.crash_time_data[category]['multipliers'].append(real_multiplier)
        
        # Garde seulement les 20 dernières valeurs par catégorie
        if len(self.crash_time_data[category]['durations']) > 20:
            self.crash_time_data[category]['durations'].pop(0)
            self.crash_time_data[category]['multipliers'].pop(0)
        
        # Sauvegarde dans CSV pour analyse externe
        self._write_to_csv(
            self.current_time,
            "crash_time_data",
            real_multiplier,
            f"Category: {category}, Duration: {actual_duration:.1f}s"
        )

    def _analyze_multiplier_time_correlation(self, real_multiplier, real_crash_time, start_time=None):
        """Analyse et ajuste les paramètres selon les données réelles."""
        if start_time is None:
            start_time = self.current_time
        
        actual_duration = (real_crash_time - start_time).total_seconds()
        
        # Catégorise le multiplicateur
        if real_multiplier < 2.00:
            category = 'low'
            max_expected = CONFIG['crash_time_generation']['low_mult_max_seconds']
        elif real_multiplier < 10.00:
            category = 'med'
            max_expected = CONFIG['crash_time_generation']['med_mult_max_seconds']
        else:
            category = 'high'
            max_expected = CONFIG['crash_time_generation']['high_mult_max_seconds']
        
        # Analyse de la performance
        if actual_duration > max_expected:
            print(f"{bcolors.YELLOW}⚠️ Temps de crash plus long que prévu pour {category} ({actual_duration:.1f}s > {max_expected}s){bcolors.ENDC}")
        elif actual_duration < max_expected * 0.3:
            print(f"{bcolors.PURPLE}⚡ Temps de crash plus court que prévu pour {category} ({actual_duration:.1f}s < {max_expected*0.3:.1f}s){bcolors.ENDC}")
        else:
            print(f"{bcolors.GREEN}✓ Temps de crash dans les limites attendues pour {category} ({actual_duration:.1f}s){bcolors.ENDC}")
        
        # Stocke pour ajustement futur
        self._store_crash_time_data(category, actual_duration, real_multiplier)

    def _update_crash_time_parameters(self, real_multiplier, real_crash_time):
        """Met à jour les paramètres de génération de temps de crash."""
        actual_duration = (real_crash_time - self.current_time).total_seconds()
        
        # Ajuste dynamiquement les paramètres
        if real_multiplier < 2.00:
            self._adjust_crash_time_param('low_mult_max_seconds', actual_duration)
        elif real_multiplier < 10.00:
            self._adjust_crash_time_param('med_mult_max_seconds', actual_duration)
        else:
            self._adjust_crash_time_param('high_mult_max_seconds', actual_duration)

    def _adjust_crash_time_param(self, param_name, actual_duration):
        """Ajuste un paramètre de temps de crash avec apprentissage."""
        current_max = CONFIG['crash_time_generation'][param_name]
        
        # Apprentissage simple: moyenne mobile
        if not hasattr(self, 'crash_time_history'):
            self.crash_time_history = {}
        
        if param_name not in self.crash_time_history:
            self.crash_time_history[param_name] = []
        
        self.crash_time_history[param_name].append(actual_duration)
        
        # Garde seulement les 10 dernières valeurs
        if len(self.crash_time_history[param_name]) > 10:
            self.crash_time_history[param_name].pop(0)
        
        # Calcule la nouvelle moyenne
        if len(self.crash_time_history[param_name]) >= 3:
            new_max = sum(self.crash_time_history[param_name]) / len(self.crash_time_history[param_name])
            # Ajuste progressivement (pas de changement brutal)
            adjusted_max = current_max * 0.9 + new_max * 0.1
            CONFIG['crash_time_generation'][param_name] = round(adjusted_max, 1)
            
            print(f"{bcolors.CYAN}🔄 Ajustement {param_name}: {current_max}s → {adjusted_max:.1f}s{bcolors.ENDC}")

    def show_crash_time_analysis(self):
        """Affiche l'analyse des temps de crash collectés."""
        if not hasattr(self, 'crash_time_data'):
            print("Aucune donnée de temps de crash disponible.")
            return
        
        print(f"\n{bcolors.BOLD}=== ANALYSE DES TEMPS DE CRASH ==={bcolors.ENDC}")
        
        for category in ['low', 'med', 'high']:
            if self.crash_time_data[category]['durations']:
                durations = self.crash_time_data[category]['durations']
                multipliers = self.crash_time_data[category]['multipliers']
                
                avg_duration = sum(durations) / len(durations)
                avg_multiplier = sum(multipliers) / len(multipliers)
                min_duration = min(durations)
                max_duration = max(durations)
                
                print(f"\n{bcolors.UNDERLINE}{category.upper()}{bcolors.ENDC} ({len(durations)} échantillons):")
                print(f"  Durée moyenne: {avg_duration:.1f}s")
                print(f"  Multiplicateur moyen: {avg_multiplier:.2f}x")
                print(f"  Plage: {min_duration:.1f}s - {max_duration:.1f}s")
                
                # Comparaison avec les paramètres actuels
                param_name = f"{category}_mult_max_seconds"
                current_param = CONFIG['crash_time_generation'][param_name]
                print(f"  Paramètre actuel: {current_param}s")
                
                if abs(avg_duration - current_param) > current_param * 0.2:
                    print(f"  {bcolors.YELLOW}⚠️ Écart significatif avec le paramètre actuel{bcolors.ENDC}")

# ==============================================================================
# CLASSE PRINCIPALE DU SIMULATEUR INTERACTIF
# ==============================================================================

class InteractivePredictor(CrashSimulator):
    def __init__(self, start_time):
        # Initialise la session avec l'heure de départ et les structures de tendances
        self.current_time = start_time
        self.hourly_trends = {}
        self.quarter_hour_trends = {}
        self.five_min_trends = {}
        self.minute_trends = {}
        self.last_predictions = []  # Historique des dernières prédictions
        self.prediction_history = []  # Historique complet des prédictions
        # Charge les données historiques et prépare le fichier CSV
        self._load_historical_data()
        self._setup_csv()

    def _setup_csv(self):
        # Crée le fichier CSV pour enregistrer la session et écrit l'en-tête
        self.csv_filename = CONFIG['output']['csv_filename']
        with open(self.csv_filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "event_type", "multiplier", "comment"])
        self._write_to_csv(self.current_time, "session_start", 0, f"Session started at {self.current_time}")

    def _write_to_csv(self, timestamp, event_type, multiplier, comment):
        # Ajoute une ligne au fichier CSV pour tracer les événements de la session
        with open(self.csv_filename, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([timestamp, event_type, multiplier, comment])

    def _get_multiplier_color(self, multiplier):
        """Retourne la couleur appropriée selon la valeur du multiplicateur."""
        # Palette de couleurs pour chaque plage de multiplicateur
        if multiplier < 1.51:
            return bcolors.RED  # Rouge pour multiplicateurs < 1.51
        elif 1.51 <= multiplier < 2.00:
            return bcolors.ORANGE  # Orange pour multiplicateurs 1.51-1.99
        elif 2.00 <= multiplier < 3.00:
            return bcolors.GREEN  # Vert pour multiplicateurs 2.00-2.99
        elif 3.00 <= multiplier < 4.00:
            return bcolors.YELLOW  # Jaune pour multiplicateurs 3.00-3.99
        elif 4.00 <= multiplier < 10.00:
            return bcolors.PURPLE  # Violet pour multiplicateurs 4.00-9.99
        else:  # multiplier >= 10.00
            return bcolors.BLUE  # Bleu pour multiplicateurs >= 10.00

    def _get_multiplier_ball(self, multiplier):
        """Retourne la boule colorée appropriée selon la valeur du multiplicateur."""
        # Emoji boule pour chaque plage de multiplicateur
        if multiplier < 1.51:
            return "🔴"  # Rouge pour multiplicateurs < 1.51
        elif 1.51 <= multiplier < 2.00:
            return "🟠"  # Orange pour multiplicateurs 1.51-1.99
        elif 2.00 <= multiplier < 3.00:
            return "🟢"  # Vert pour multiplicateurs 2.00-2.99
        elif 3.00 <= multiplier < 4.00:
            return "🟡"  # Jaune pour multiplicateurs 3.00-3.99
        elif 4.00 <= multiplier < 10.00:
            return "🟣"  # Violet pour multiplicateurs 4.00-9.99
        else:  # multiplier >= 10.00
            return "🔵"  # Bleu pour multiplicateurs >= 10.00

    def _format_multiplier(self, multiplier):
        """Formate un multiplicateur avec sa couleur et sa boule appropriées."""
        color = self._get_multiplier_color(multiplier)
        ball = self._get_multiplier_ball(multiplier)
        return f"{ball} {color}{multiplier:.2f}x{bcolors.ENDC}"

    def generate_forecast(self):
        """Génère et affiche les prédictions pour les 5 prochaines minutes."""
        print(f"\n{bcolors.BOLD}📊 PRÉDICTIONS POUR LES 5 PROCHAINES MINUTES{bcolors.ENDC}")
        print(f"{bcolors.CYAN}Heure de début: {self.current_time.strftime('%H:%M:%S')}{bcolors.ENDC}")
        print("-" * 80)
        forecast_end_time = self.current_time + timedelta(minutes=CONFIG['simulation']['forecast_duration_minutes'])
        temp_time = self.current_time
        round_number = 1
        last_minute = None
        while temp_time < forecast_end_time:
            multiplier = self._generate_multiplier(temp_time)
            crash_time = self._generate_crash_time(temp_time, multiplier)
            colored_multiplier = self._format_multiplier(multiplier)
            # Ajoute une ligne discontinue si on change de minute de début
            if last_minute is not None and temp_time.minute != last_minute:
                print("--------------------")
            last_minute = temp_time.minute
            # Affichage sans le texte 'Multiplicateur:'
            print(f"Tour {round_number:2d} | {temp_time.strftime('%H:%M:%S')} → {crash_time.strftime('%H:%M:%S')} | {colored_multiplier}")
            temp_time = crash_time + timedelta(seconds=CONFIG['simulation']['pause_between_rounds_seconds'])
            round_number += 1
        print("-" * 80)

    def apply_real_result_with_crash_time(self, real_multiplier, real_crash_time):
        """Met à jour l'état avec multiplicateur ET heure de crash réels."""
        # Affiche le résultat réel saisi par l'utilisateur
        colored_multiplier = self._format_multiplier(real_multiplier)
        print(f"{bcolors.GREEN}>>> Résultat réel: {colored_multiplier} à {real_crash_time.strftime('%H:%M:%S')}{bcolors.ENDC}")
        # Analyse la corrélation entre le multiplicateur et le temps de crash
        self._analyze_multiplier_time_correlation(real_multiplier, real_crash_time)
        # Met à jour les tendances statistiques
        self._update_all_trends(real_multiplier, self.current_time)
        # Ajuste les paramètres de génération de crash selon le feedback
        self._update_crash_time_parameters(real_multiplier, real_crash_time)
        # Enregistre le résultat dans le CSV
        self._write_to_csv(self.current_time, "real_result", real_multiplier, f"Crash at {real_crash_time.strftime('%H:%M:%S')}")
        # Met à jour l'heure interne pour le prochain tour
        self.current_time = real_crash_time + timedelta(seconds=CONFIG['simulation']['pause_between_rounds_seconds'])
        print(f"{bcolors.CYAN}>>> Prochaine prédiction à partir de: {self.current_time.strftime('%H:%M:%S')}{bcolors.ENDC}")

    def apply_real_result(self, real_multiplier):
        """Met à jour l'état avec le multiplicateur réel (sans heure de crash précise)."""
        colored_multiplier = self._format_multiplier(real_multiplier)
        print(f"{bcolors.GREEN}>>> Résultat réel: {colored_multiplier}{bcolors.ENDC}")
        # Met à jour les tendances statistiques
        self._update_all_trends(real_multiplier, self.current_time)
        # Enregistre le résultat dans le CSV
        self._write_to_csv(self.current_time, "real_result", real_multiplier, "User provided feedback")
        # Calcule l'heure de crash simulée et met à jour l'heure interne
        crash_time = self._generate_crash_time(self.current_time, real_multiplier)
        self.current_time = crash_time + timedelta(seconds=CONFIG['simulation']['pause_between_rounds_seconds'])
        print(f"{bcolors.CYAN}>>> Prochaine prédiction à partir de: {self.current_time.strftime('%H:%M:%S')}{bcolors.ENDC}")

    def _show_analysis(self):
        """Affiche les statistiques et tendances actuelles sur les multiplicateurs."""
        print(f"\n{bcolors.BOLD}📈 ANALYSE DES TENDANCES{bcolors.ENDC}")
        print("=" * 60)
        # Affiche la légende des couleurs utilisée pour les multiplicateurs
        print(f"{bcolors.BOLD}🎨 LÉGENDE DES COULEURS:{bcolors.ENDC}")
        print(f"  🔴 < 1.51x (Rouge) - Crash très rapide")
        print(f"   1.51-1.99x (Orange) - Crash rapide")
        print(f"  🟢 2.00-2.99x (Vert) - Crash modéré")
        print(f"   3.00-3.99x (Jaune) - Crash moyen-élevé")
        print(f"   4.00-9.99x (Violet) - Crash élevé")
        print(f"  🔵 ≥ 10.00x (Bleu) - Crash très élevé")
        print("-" * 60)
        # Pour chaque période, affiche les statistiques de distribution des multiplicateurs
        for period, trend_dict in [("Heure", self.hourly_trends), ("15min", self.quarter_hour_trends), 
                                 ("5min", self.five_min_trends), ("Minute", self.minute_trends)]:
            if trend_dict:
                print(f"\n{bcolors.CYAN}{period}:{bcolors.ENDC}")
                for trend in trend_dict.values():
                    # Vérifie que les clés existent, sinon saute cette entrée
                    if not all(k in trend for k in ['low_count', 'med_count', 'high_count', 'last_multipliers']):
                        continue
                    total = trend['low_count'] + trend['med_count'] + trend['high_count']
                    if total > 0:
                        low_pct = (trend['low_count'] / total) * 100
                        med_pct = (trend['med_count'] / total) * 100
                        high_pct = (trend['high_count'] / total) * 100
                        print(f"  < 2.00x: {bcolors.RED}{trend['low_count']} ({low_pct:.1f}%){bcolors.ENDC}")
                        print(f"  2.00-9.99x: {bcolors.GREEN}{trend['med_count']} ({med_pct:.1f}%){bcolors.ENDC}")
                        print(f"  ≥ 10.00x: {bcolors.BLUE}{trend['high_count']} ({high_pct:.1f}%){bcolors.ENDC}")
                        if trend['last_multipliers']:
                            print(f"  Derniers: ", end="")
                            for mult in list(trend['last_multipliers'])[-5:]:  # 5 derniers
                                colored_mult = self._format_multiplier(mult)
                                print(f"{colored_mult} ", end="")
                            print()
        print("=" * 60)

    def _show_comparison(self, old_prediction, new_prediction, real_result):
        """Affiche la comparaison entre ancienne et nouvelle prédiction et le résultat réel."""
        print(f"\n{bcolors.BOLD}🔄 COMPARAISON PRÉDICTIONS{bcolors.ENDC}")
        print("=" * 60)
        # Affiche l'ancienne prédiction colorée
        old_colored = self._format_multiplier(old_prediction)
        print(f"Ancienne prédiction: {old_colored}")
        # Affiche la nouvelle prédiction colorée
        new_colored = self._format_multiplier(new_prediction)
        print(f"Nouvelle prédiction:  {new_colored}")
        # Affiche le résultat réel coloré
        real_colored = self._format_multiplier(real_result)
        print(f"Résultat réel:       {real_colored}")
        # Calcule et affiche l'amélioration ou la dégradation de la prédiction
        old_error = abs(old_prediction - real_result)
        new_error = abs(new_prediction - real_result)
        if new_error < old_error:
            improvement = ((old_error - new_error) / old_error) * 100
            print(f"{bcolors.GREEN}✅ Amélioration: {improvement:.1f}%{bcolors.ENDC}")
        elif new_error > old_error:
            degradation = ((new_error - old_error) / old_error) * 100
            print(f"{bcolors.RED}❌ Dégradation: {degradation:.1f}%{bcolors.ENDC}")
        else:
            print(f"{bcolors.YELLOW}➡️ Aucun changement{bcolors.ENDC}")
        print("=" * 60)

    def _load_historical_data(self):
        """Charge les données historiques depuis le CSV."""
        csv_filename = CONFIG['output']['csv_filename']
        
        if not os.path.exists(csv_filename):
            print(f"{bcolors.YELLOW}Aucun fichier historique trouvé. Démarrage d'une nouvelle session.{bcolors.ENDC}")
            return
        
        try:
            with open(csv_filename, 'r', newline='') as f:
                reader = csv.DictReader(f)
                
                historical_data = []
                for row in reader:
                    if row['event_type'] in ['real_result', 'real_result_with_crash_time']:
                        historical_data.append({
                            'timestamp': datetime.fromisoformat(row['timestamp']),
                            'multiplier': float(row['multiplier']),
                            'comment': row['comment']
                        })
                
                print(f"{bcolors.GREEN}Chargement de {len(historical_data)} données historiques{bcolors.ENDC}")
                
                # Applique les données historiques aux tendances
                for data in historical_data:
                    self._update_all_trends(data['multiplier'], data['timestamp'])
                    
                # Affiche un résumé des données chargées
                self._show_historical_summary(historical_data)
                
        except Exception as e:
            print(f"{bcolors.WARNING}Erreur lors du chargement des données historiques: {e}{bcolors.ENDC}")

    def _show_historical_summary(self, historical_data):
        """Affiche un résumé des données historiques chargées."""
        if not historical_data:
            return
        
        print(f"\n{bcolors.CYAN}=== RÉSUMÉ DES DONNÉES HISTORIQUES ==={bcolors.ENDC}")
        
        # Statistiques générales
        multipliers = [data['multiplier'] for data in historical_data]
        avg_multiplier = sum(multipliers) / len(multipliers)
        min_multiplier = min(multipliers)
        max_multiplier = max(multipliers)
        
        print(f"Nombre de tours: {len(historical_data)}")
        print(f"Multiplicateur moyen: {avg_multiplier:.2f}x")
        print(f"Plage: {min_multiplier:.2f}x - {max_multiplier:.2f}x")
        
        # Analyse par catégorie
        low_count = sum(1 for m in multipliers if m < 2.0)
        med_count = sum(1 for m in multipliers if 2.0 <= m < 10.0)
        high_count = sum(1 for m in multipliers if m >= 10.0)
        
        print(f"Répartition:")
        print(f"  Bas (<2x): {low_count} ({low_count/len(multipliers)*100:.1f}%)")
        print(f"  Moyen (2-10x): {med_count} ({med_count/len(multipliers)*100:.1f}%)")
        print(f"  Élevé (≥10x): {high_count} ({high_count/len(multipliers)*100:.1f}%)")
        
        # Analyse temporelle
        if len(historical_data) > 1:
            first_time = historical_data[0]['timestamp']
            last_time = historical_data[-1]['timestamp']
            duration = last_time - first_time
            print(f"Période: {first_time.strftime('%H:%M:%S')} - {last_time.strftime('%H:%M:%S')}")
            print(f"Durée totale: {duration}")

    def _load_crash_time_data(self):
        """Charge les données de temps de crash depuis le CSV."""
        csv_filename = CONFIG['output']['csv_filename']
        
        if not os.path.exists(csv_filename):
            return
        
        try:
            with open(csv_filename, 'r', newline='') as f:
                reader = csv.DictReader(f)
                
                crash_data = {
                    'low': {'durations': [], 'multipliers': []},
                    'med': {'durations': [], 'multipliers': []},
                    'high': {'durations': [], 'multipliers': []}
                }
                
                for row in reader:
                    if row['event_type'] == 'crash_time_data':
                        # Parse le commentaire pour extraire les données
                        comment = row['comment']
                        if 'Category:' in comment and 'Duration:' in comment:
                            category = comment.split('Category: ')[1].split(',')[0]
                            duration_str = comment.split('Duration: ')[1].split('s')[0]
                            
                            try:
                                duration = float(duration_str)
                                multiplier = float(row['multiplier'])
                                
                                crash_data[category]['durations'].append(duration)
                                crash_data[category]['multipliers'].append(multiplier)
                            except ValueError:
                                continue
                
                # Applique les données de temps de crash
                self.crash_time_data = crash_data
                
                # Ajuste les paramètres selon l'historique
                self._adjust_parameters_from_history()
                
        except Exception as e:
            print(f"{bcolors.WARNING}Erreur lors du chargement des données de temps de crash: {e}{bcolors.ENDC}")

    def _adjust_parameters_from_history(self):
        """Ajuste les paramètres selon les données historiques."""
        if not hasattr(self, 'crash_time_data'):
            return
        
        for category in ['low', 'med', 'high']:
            if self.crash_time_data[category]['durations']:
                durations = self.crash_time_data[category]['durations']
                avg_duration = sum(durations) / len(durations)
                
                param_name = f"{category}_mult_max_seconds"
                current_param = CONFIG['crash_time_generation'][param_name]
                
                # Ajuste si l'écart est significatif
                if abs(avg_duration - current_param) > current_param * 0.3:
                    CONFIG['crash_time_generation'][param_name] = round(avg_duration, 1)
                    print(f"{bcolors.CYAN}🔄 Ajustement historique {param_name}: {current_param}s → {avg_duration:.1f}s{bcolors.ENDC}")

    def _get_cycle_alternation_pattern(self, time):
        """Détermine le pattern d'alternance des cycles selon l'heure."""
        hour = time.hour
        minute = time.minute
        
        # Pattern d'alternance : change selon l'heure
        if hour % 2 == 0:  # Heures paires (0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22)
            return self._get_even_hour_pattern(minute)
        else:  # Heures impaires (1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23)
            return self._get_odd_hour_pattern(minute)

    def _get_even_hour_pattern(self, minute):
        """Pattern pour les heures paires."""
        cycle_phase = minute % 5
        
        if cycle_phase == 0:  # XX:00, XX:05, XX:10, etc.
            return {
                'cycle_type': 'favorable',
                'minute_1_quality': 'good',      # Minutes se terminant par 1 = bonnes
                'minute_9_quality': 'bad',       # Minutes se terminant par 9 = mauvaises
                'cycle_boost': 0.2
            }
        elif cycle_phase == 4:  # XX:04, XX:09, XX:14, etc.
            return {
                'cycle_type': 'defavorable',
                'minute_1_quality': 'bad',       # Minutes se terminant par 1 = mauvaises
                'minute_9_quality': 'good',      # Minutes se terminant par 9 = bonnes
                'cycle_penalty': 0.2
            }
        else:  # Phases intermédiaires
            return {
                'cycle_type': 'neutral',
                'minute_1_quality': 'normal',
                'minute_9_quality': 'normal',
                'cycle_boost': 0.0
            }

    def _get_odd_hour_pattern(self, minute):
        """Pattern pour les heures impaires (INVERSE des heures paires)."""
        cycle_phase = minute % 5
        
        if cycle_phase == 0:  # XX:00, XX:05, XX:10, etc.
            return {
                'cycle_type': 'defavorable',
                'minute_1_quality': 'bad',       # Minutes se terminant par 1 = mauvaises
                'minute_9_quality': 'good',      # Minutes se terminant par 9 = bonnes
                'cycle_penalty': 0.2
            }
        elif cycle_phase == 4:  # XX:04, XX:09, XX:14, etc.
            return {
                'cycle_type': 'favorable',
                'minute_1_quality': 'good',      # Minutes se terminant par 1 = bonnes
                'minute_9_quality': 'bad',       # Minutes se terminant par 9 = mauvaises
                'cycle_boost': 0.2
            }
        else:  # Phases intermédiaires
            return {
                'cycle_type': 'neutral',
                'minute_1_quality': 'normal',
                'minute_9_quality': 'normal',
                'cycle_boost': 0.0
            }

    def _determine_interval_quality_with_alternation(self, interval_type, time):
        """Détermine la qualité en tenant compte de l'alternance des cycles."""
        if interval_type != 'minute':
            return self._determine_interval_quality(interval_type, time)
        
        minute, second = time.minute, time.second
        
        # Récupère le pattern d'alternance
        alternation_pattern = self._get_cycle_alternation_pattern(time)
        
        # Minutes se terminant par 9
        if minute % 10 == 9:
            if second < 30:
                return alternation_pattern['minute_9_quality']
            else:
                # Deuxième moitié de la minute : plus défavorable
                if alternation_pattern['minute_9_quality'] == 'good':
                    return random.choices(['good', 'normal'], weights=[0.7, 0.3])[0]
                else:
                    return random.choices(['bad', 'catastrophic'], weights=[0.6, 0.4])[0]
        
        # Minutes se terminant par 1
        if minute % 10 == 1:
            if second < 30:
                return alternation_pattern['minute_1_quality']
            else:
                # Deuxième moitié de la minute : plus favorable
                if alternation_pattern['minute_1_quality'] == 'good':
                    return random.choices(['good', 'normal'], weights=[0.8, 0.2])[0]
                else:
                    return random.choices(['normal', 'bad'], weights=[0.7, 0.3])[0]
        
        # Autres règles inchangées
        if minute % 7 == 0: return 'catastrophic'
        if minute % 5 == 0: return random.choices(['bad', 'catastrophic'], weights=[0.6, 0.4])[0]
        if minute % 3 == 0: return random.choices(['normal', 'bad'], weights=[0.6, 0.4])[0]
        
        # Qualité par défaut selon le cycle
        if alternation_pattern['cycle_type'] == 'favorable':
            return random.choices(['good', 'normal'], weights=[0.6, 0.4])[0]
        elif alternation_pattern['cycle_type'] == 'defavorable':
            return random.choices(['normal', 'bad'], weights=[0.6, 0.4])[0]
        else:
            return random.choices(['good', 'normal'], weights=[0.5, 0.5])[0]

    def _show_cycle_alternation_info(self, time):
        """Affiche les informations sur l'alternance des cycles."""
        alternation_pattern = self._get_cycle_alternation_pattern(time)
        cycle_phase = time.minute % 5
        minutes_until_reset = 5 - cycle_phase
        
        print(f"{bcolors.CYAN}⏰ Cycle: Phase {cycle_phase}/4 ({minutes_until_reset} min avant reset){bcolors.ENDC}")
        
        if alternation_pattern['cycle_type'] == 'favorable':
            print(f"{bcolors.GREEN}🎯 Cycle favorable - Minutes 1: {alternation_pattern['minute_1_quality']}, Minutes 9: {alternation_pattern['minute_9_quality']}{bcolors.ENDC}")
        elif alternation_pattern['cycle_type'] == 'defavorable':
            print(f"{bcolors.YELLOW}⚠️ Cycle défavorable - Minutes 1: {alternation_pattern['minute_1_quality']}, Minutes 9: {alternation_pattern['minute_9_quality']}{bcolors.ENDC}")
        else:
            print(f"{bcolors.PURPLE}○ Cycle neutre - Minutes 1: {alternation_pattern['minute_1_quality']}, Minutes 9: {alternation_pattern['minute_9_quality']}{bcolors.ENDC}")

    def _generate_multiplier_with_cycle_awareness(self, time):
        """Génère un multiplicateur avec prise en compte de l'alternance des cycles."""
        # Affiche les informations d'alternance
        self._show_cycle_alternation_info(time)
        
        # Utilise la qualité avec alternance
        minute_quality = self._determine_interval_quality_with_alternation('minute', time)
        
        # Génère le multiplicateur avec la qualité adaptée
        base_multiplier = self._get_quality_multiplier(minute_quality, time)
        
        # Applique les ajustements du cycle
        alternation_pattern = self._get_cycle_alternation_pattern(time)
        if alternation_pattern['cycle_type'] == 'favorable':
            adjusted_multiplier = base_multiplier * random.uniform(1.0, 1.2)
        elif alternation_pattern['cycle_type'] == 'defavorable':
            adjusted_multiplier = base_multiplier * random.uniform(0.8, 1.0)
        else:
            adjusted_multiplier = base_multiplier
        
        return round(adjusted_multiplier, 2)

    def _get_complete_alternation_pattern(self, time):
        """Détermine le pattern d'alternance complet pour toutes les minutes."""
        hour = time.hour
        minute = time.minute
        cycle_phase = minute % 5
        
        # Pattern de base selon l'heure (paire/impaire)
        if hour % 2 == 0:  # Heures paires
            base_pattern = self._get_even_hour_base_pattern(cycle_phase)
        else:  # Heures impaires
            base_pattern = self._get_odd_hour_base_pattern(cycle_phase)
        
        # Applique l'alternance à toutes les minutes
        return self._apply_minute_alternation(base_pattern, minute)

    def _get_even_hour_base_pattern(self, cycle_phase):
        """Pattern de base pour les heures paires."""
        if cycle_phase == 0:  # Début de cycle
            return {
                'cycle_type': 'favorable',
                'minute_patterns': {
                    0: 'good',    # XX:00, XX:10, XX:20, etc.
                    1: 'good',    # XX:01, XX:11, XX:21, etc.
                    2: 'normal',  # XX:02, XX:12, XX:22, etc.
                    3: 'normal',  # XX:03, XX:13, XX:23, etc.
                    4: 'bad',     # XX:04, XX:14, XX:24, etc.
                    5: 'bad',     # XX:05, XX:15, XX:25, etc.
                    6: 'normal',  # XX:06, XX:16, XX:26, etc.
                    7: 'normal',  # XX:07, XX:17, XX:27, etc.
                    8: 'good',    # XX:08, XX:18, XX:28, etc.
                    9: 'bad'      # XX:09, XX:19, XX:29, etc.
                }
            }
        elif cycle_phase == 4:  # Fin de cycle
            return {
                'cycle_type': 'defavorable',
                'minute_patterns': {
                    0: 'bad',     # XX:04, XX:14, XX:24, etc.
                    1: 'bad',     # XX:05, XX:15, XX:25, etc.
                    2: 'normal',  # XX:06, XX:16, XX:26, etc.
                    3: 'normal',  # XX:07, XX:17, XX:27, etc.
                    4: 'good',    # XX:08, XX:18, XX:28, etc.
                    5: 'good',    # XX:09, XX:19, XX:29, etc.
                    6: 'normal',  # XX:10, XX:20, XX:30, etc.
                    7: 'normal',  # XX:11, XX:21, XX:31, etc.
                    8: 'bad',     # XX:12, XX:22, XX:32, etc.
                    9: 'good'     # XX:13, XX:23, XX:33, etc.
                }
            }
        else:  # Phases intermédiaires
            return {
                'cycle_type': 'neutral',
                'minute_patterns': {
                    0: 'normal',  # Toutes les minutes sont normales
                    1: 'normal',
                    2: 'normal',
                    3: 'normal',
                    4: 'normal',
                    5: 'normal',
                    6: 'normal',
                    7: 'normal',
                    8: 'normal',
                    9: 'normal'
                }
            }

    def _get_odd_hour_base_pattern(self, cycle_phase):
        """Pattern de base pour les heures impaires (INVERSE des heures paires)."""
        if cycle_phase == 0:  # Début de cycle
            return {
                'cycle_type': 'defavorable',
                'minute_patterns': {
                    0: 'bad',     # XX:00, XX:10, XX:20, etc.
                    1: 'bad',     # XX:01, XX:11, XX:21, etc.
                    2: 'normal',  # XX:02, XX:12, XX:22, etc.
                    3: 'normal',  # XX:03, XX:13, XX:23, etc.
                    4: 'good',    # XX:04, XX:14, XX:24, etc.
                    5: 'good',    # XX:05, XX:15, XX:25, etc.
                    6: 'normal',  # XX:06, XX:16, XX:26, etc.
                    7: 'normal',  # XX:07, XX:17, XX:27, etc.
                    8: 'bad',     # XX:08, XX:18, XX:28, etc.
                    9: 'good'     # XX:09, XX:19, XX:29, etc.
                }
            }
        elif cycle_phase == 4:  # Fin de cycle
            return {
                'cycle_type': 'favorable',
                'minute_patterns': {
                    0: 'good',    # XX:04, XX:14, XX:24, etc.
                    1: 'good',    # XX:05, XX:15, XX:25, etc.
                    2: 'normal',  # XX:06, XX:16, XX:26, etc.
                    3: 'normal',  # XX:07, XX:17, XX:27, etc.
                    4: 'bad',     # XX:08, XX:18, XX:28, etc.
                    5: 'bad',     # XX:09, XX:19, XX:29, etc.
                    6: 'normal',  # XX:10, XX:20, XX:30, etc.
                    7: 'normal',  # XX:11, XX:21, XX:31, etc.
                    8: 'good',    # XX:12, XX:22, XX:32, etc.
                    9: 'bad'      # XX:13, XX:23, XX:33, etc.
                }
            }
        else:  # Phases intermédiaires
            return {
                'cycle_type': 'neutral',
                'minute_patterns': {
                    0: 'normal',  # Toutes les minutes sont normales
                    1: 'normal',
                    2: 'normal',
                    3: 'normal',
                    4: 'normal',
                    5: 'normal',
                    6: 'normal',
                    7: 'normal',
                    8: 'normal',
                    9: 'normal'
                }
            }

    def _apply_minute_alternation(self, base_pattern, minute):
        """Applique l'alternance spécifique selon la minute."""
        minute_digit = minute % 10
        base_quality = base_pattern['minute_patterns'][minute_digit]
        
        # Ajustements spéciaux selon la minute
        if minute_digit == 7:  # Multiples de 7
            if base_quality == 'good':
                return 'good'  # Reste bon
            else:
                return 'catastrophic'  # Devient catastrophique
        
        elif minute_digit == 5:  # Multiples de 5
            if base_quality == 'good':
                return 'normal'  # Dégradation
            elif base_quality == 'bad':
                return 'catastrophic'  # Aggravation
            else:
                return 'bad'  # Dégradation
        
        elif minute_digit == 3:  # Multiples de 3
            if base_quality == 'good':
                return 'normal'  # Dégradation
            elif base_quality == 'bad':
                return 'bad'  # Reste mauvais
            else:
                return 'bad'  # Dégradation
        
        return base_quality

    def _determine_interval_quality_with_complete_alternation(self, interval_type, time):
        """Détermine la qualité avec alternance complète pour toutes les minutes."""
        if interval_type != 'minute':
            return self._determine_interval_quality(interval_type, time)
        
        minute, second = time.minute, time.second
        
        # Récupère le pattern d'alternance complet
        alternation_pattern = self._get_complete_alternation_pattern(time)
        minute_digit = minute % 10
        base_quality = alternation_pattern['minute_patterns'][minute_digit]
        
        # Ajustements selon la seconde (première vs deuxième moitié de la minute)
        if second < 30:  # Première moitié
            return base_quality
        else:  # Deuxième moitié
            return self._adjust_quality_for_second_half(base_quality, minute_digit)

    def _adjust_quality_for_second_half(self, base_quality, minute_digit):
        """Ajuste la qualité pour la deuxième moitié de la minute."""
        if minute_digit in [1, 9]:  # Minutes spéciales
            if base_quality == 'good':
                return random.choices(['good', 'normal'], weights=[0.7, 0.3])[0]
            elif base_quality == 'bad':
                return random.choices(['bad', 'catastrophic'], weights=[0.6, 0.4])[0]
            else:
                return random.choices(['normal', 'bad'], weights=[0.7, 0.3])[0]
        
        elif minute_digit in [5, 7]:  # Minutes critiques
            if base_quality == 'good':
                return 'normal'  # Dégradation systématique
            elif base_quality == 'normal':
                return 'bad'  # Dégradation systématique
            else:
                return 'catastrophic'  # Aggravation systématique
        
        else:  # Minutes normales
            if base_quality == 'good':
                return random.choices(['good', 'normal'], weights=[0.8, 0.2])[0]
            elif base_quality == 'bad':
                return random.choices(['bad', 'catastrophic'], weights=[0.7, 0.3])[0]
            else:
                return base_quality  # Reste inchangé

    def _show_complete_alternation_info(self, time):
        """Affiche les informations complètes sur l'alternance."""
        alternation_pattern = self._get_complete_alternation_pattern(time)
        cycle_phase = time.minute % 5
        minutes_until_reset = 5 - cycle_phase
        minute_digit = time.minute % 10
        
        print(f"{bcolors.CYAN}⏰ Cycle: Phase {cycle_phase}/4 ({minutes_until_reset} min avant reset){bcolors.ENDC}")
        
        # Affiche le type de cycle
        if alternation_pattern['cycle_type'] == 'favorable':
            print(f"{bcolors.GREEN}🎯 Cycle favorable{bcolors.ENDC}")
        elif alternation_pattern['cycle_type'] == 'defavorable':
            print(f"{bcolors.YELLOW}⚠️ Cycle défavorable{bcolors.ENDC}")
        else:
            print(f"{bcolors.PURPLE}○ Cycle neutre{bcolors.ENDC}")
        
        # Affiche la qualité de la minute actuelle
        current_quality = alternation_pattern['minute_patterns'][minute_digit]
        quality_color = {
            'good': bcolors.GREEN,
            'normal': bcolors.PURPLE,
            'bad': bcolors.YELLOW,
            'catastrophic': bcolors.WARNING
        }
        
        print(f"Minute {minute_digit}: {quality_color[current_quality]}{current_quality}{bcolors.ENDC}")
        
        # Affiche les minutes favorables/défavorables du cycle
        favorable_minutes = [m for m, q in alternation_pattern['minute_patterns'].items() if q == 'good']
        unfavorable_minutes = [m for m, q in alternation_pattern['minute_patterns'].items() if q in ['bad', 'catastrophic']]
        
        if favorable_minutes:
            print(f"{bcolors.GREEN}✅ Minutes favorables: {favorable_minutes}{bcolors.ENDC}")
        if unfavorable_minutes:
            print(f"{bcolors.YELLOW}❌ Minutes défavorables: {unfavorable_minutes}{bcolors.ENDC}")

    def _show_crash_time_guidance(self, real_multiplier):
        """Affiche des conseils sur l'heure de crash attendue."""
        expected_crash_time = self._calculate_expected_crash_time(real_multiplier)
        
        print(f"\n{bcolors.CYAN}=== GUIDANCE HEURE DE CRASH ==={bcolors.ENDC}")
        print(f"{real_multiplier:.2f}x")
        print(f"Heure de départ: {self.current_time.strftime('%H:%M:%S')}")
        print(f"Heure de crash attendue: {expected_crash_time.strftime('%H:%M:%S')}")
        
        # Catégorise le multiplicateur
        if real_multiplier < 2.00:
            category = "bas"
            max_seconds = CONFIG['crash_time_generation']['low_mult_max_seconds']
        elif real_multiplier < 10.00:
            category = "moyen"
            max_seconds = CONFIG['crash_time_generation']['med_mult_max_seconds']
        else:
            category = "élevé"
            max_seconds = CONFIG['crash_time_generation']['high_mult_max_seconds']
        
        print(f"Catégorie: {category} (max {max_seconds}s)")
        
        # Plage de temps possible
        min_time = self.current_time + timedelta(seconds=1)
        max_time = self.current_time + timedelta(seconds=max_seconds)
        
        print(f"Plage possible: {min_time.strftime('%H:%M:%S')} - {max_time.strftime('%H:%M:%S')}")
        
        # Conseils selon la catégorie
        if category == "bas":
            print(f"{bcolors.YELLOW}💡 Conseil: Crash rapide attendu (1-{max_seconds}s){bcolors.ENDC}")
        elif category == "moyen":
            print(f"{bcolors.PURPLE}💡 Conseil: Crash moyen attendu (1-{max_seconds}s){bcolors.ENDC}")
        else:
            print(f"{bcolors.GREEN}💡 Conseil: Crash lent attendu (1-{max_seconds}s){bcolors.ENDC}")

    def _calculate_expected_crash_time(self, multiplier):
        """Calcule l'heure de crash attendue basée sur le multiplicateur."""
        # Utilise la même logique que _generate_crash_time
        crash_rules = CONFIG['crash_time_generation']
        
        if multiplier < 2.00:
            max_seconds = crash_rules['low_mult_max_seconds']
        elif multiplier < 10.00:
            max_seconds = crash_rules['med_mult_max_seconds']
        else:
            max_seconds = crash_rules['high_mult_max_seconds']
        
        # Calcule une durée moyenne (pas aléatoire pour l'affichage)
        avg_duration = max_seconds / 2
        expected_crash_time = self.current_time + timedelta(seconds=avg_duration)
        
        return expected_crash_time

    def _restart_session(self):
        """Menu principal avec options."""
        print(f"\n{bcolors.BOLD}📋 MENU PRINCIPAL{bcolors.ENDC}")
        print("=" * 50)
        print(f"{bcolors.CYAN}Choisissez une option:{bcolors.ENDC}")
        print(f"  1. {bcolors.YELLOW}Redémarrage rapide{bcolors.ENDC} (même heure de début)")
        print(f"  2. {bcolors.YELLOW}Nouvelle heure de début{bcolors.ENDC}")
        print(f"  3. {bcolors.YELLOW}Charger données historiques{bcolors.ENDC}")
        print(f"  4. {bcolors.YELLOW}Afficher résumé de session{bcolors.ENDC}")
        print(f"  5. {bcolors.YELLOW}Guide des phases et cycles{bcolors.ENDC}")
        print(f"  6. {bcolors.YELLOW}Phase actuelle{bcolors.ENDC}")
        print(f"  7. {bcolors.YELLOW}Statistiques et analyse{bcolors.ENDC}")
        print(f"  8. {bcolors.YELLOW}Annuler{bcolors.ENDC}")
        print("=" * 50)
        
        while True:
            choice = input(f"{bcolors.YELLOW}Votre choix (1-8):{bcolors.ENDC} ").strip()
            
            if choice == '1':
                self._quick_restart()
                break
            elif choice == '2':
                self._restart_complete_session()
                break
            elif choice == '3':
                self._load_historical_data()
                break
            elif choice == '4':
                self._show_session_summary()
                break
            elif choice == '5':
                self._show_phase_descriptions()
                break
            elif choice == '6':
                self._show_current_phase_info()
                break
            elif choice == '7':
                self._show_analysis()
                break
            elif choice == '8':
                print(f"{bcolors.BLUE}Retour au mode prédiction{bcolors.ENDC}")
                break
            else:
                print(f"{bcolors.RED}❌ Choix invalide. Entrez 1, 2, 3, 4, 5, 6, 7 ou 8.{bcolors.ENDC}")

    def _restart_complete_session(self, new_start_time=None):
        """Redémarre complètement la session avec une nouvelle heure."""
        if new_start_time is None:
            print(f"\n{bcolors.CYAN}Entrez la nouvelle heure de début:{bcolors.ENDC}")
            while True:
                try:
                    time_input = input(f"{bcolors.YELLOW}Format HH:MM:SS (ex: 14:30:00) ou Enter pour maintenant:{bcolors.ENDC} ").strip()
                    
                    if not time_input:
                        new_start_time = datetime.now()
                        break
                    
                    # Parsing de l'heure
                    new_start_time = datetime.strptime(time_input, "%H:%M:%S")
                    # Utilise la date d'aujourd'hui
                    now = datetime.now()
                    new_start_time = new_start_time.replace(year=now.year, month=now.month, day=now.day)
                    
                    print(f"{bcolors.GREEN}✅ Nouvelle heure de début: {new_start_time.strftime('%H:%M:%S')}{bcolors.ENDC}")
                    break
                    
                except ValueError:
                    print(f"{bcolors.RED}❌ Format invalide. Utilisez HH:MM:SS (ex: 14:30:00){bcolors.ENDC}")
                except KeyboardInterrupt:
                    print(f"\n{bcolors.YELLOW}Annulé{bcolors.ENDC}")
                    return
        
        # Réinitialise complètement
        self.current_time = new_start_time
        self.hourly_trends = {}
        self.quarter_hour_trends = {}
        self.five_min_trends = {}
        self.minute_trends = {}
        
        # Réinitialise le CSV
        self._setup_csv()
        
        print(f"{bcolors.GREEN}Session redémarrée à {self.current_time.strftime('%H:%M:%S')}{bcolors.ENDC}")

    def _quick_restart(self):
        """Redémarrage rapide : prend l'heure actuelle du système comme nouvelle heure de début."""
        from datetime import datetime
        self.current_time = datetime.now().replace(microsecond=0)
        print(f"{bcolors.GREEN}Redémarrage rapide effectué à {self.current_time.strftime('%H:%M:%S')}{bcolors.ENDC}")
        # Réinitialise les tendances
        self.hourly_trends = {}
        self.quarter_hour_trends = {}
        self.five_min_trends = {}
        self.minute_trends = {}
        # Réinitialise le CSV
        self._setup_csv()

    def _show_session_summary(self):
        """Affiche un résumé de la session actuelle."""
        print(f"\n{bcolors.BOLD}📊 RÉSUMÉ DE LA SESSION{bcolors.ENDC}")
        print("=" * 60)
        print(f"{bcolors.CYAN}Heure de début: {self.current_time.strftime('%H:%M:%S')}{bcolors.ENDC}")
        
        # Compte total des données
        total_rounds = 0
        total_low = 0
        total_med = 0
        total_high = 0
        
        for trend_dict in [self.hourly_trends, self.quarter_hour_trends, self.five_min_trends, self.minute_trends]:
            for trend in trend_dict.values():
                total_low += trend['low_count']
                total_med += trend['med_count']
                total_high += trend['high_count']
        
        total_rounds = total_low + total_med + total_high
        
        if total_rounds > 0:
            print(f"{bcolors.CYAN}Nombre total de tours: {total_rounds}{bcolors.ENDC}")
            print(f"  {bcolors.RED}< 2.00x: {total_low} ({total_low/total_rounds*100:.1f}%){bcolors.ENDC}")
            print(f"  {bcolors.GREEN}2.00-9.99x: {total_med} ({total_med/total_rounds*100:.1f}%){bcolors.ENDC}")
            print(f"  {bcolors.BLUE}≥ 10.00x: {total_high} ({total_high/total_rounds*100:.1f}%){bcolors.ENDC}")
        else:
            print(f"{bcolors.YELLOW}Aucune donnée collectée{bcolors.ENDC}")
        
        print("=" * 60)

    def _get_crash_time_input_compact(self):
        """Version compacte avec saisie individuelle."""
        print(f"{bcolors.CYAN}Heure de crash attendue: {self.current_time.strftime('%H:%M:%S')}{bcolors.ENDC}")
        
        while True:
            try:
                print(f"{bcolors.YELLOW}Entrez l'heure de crash (HH MM SS) ou Enter pour auto:{bcolors.ENDC}")
                
                # Saisie en une ligne
                time_input = input("  Format: HH MM SS (ex: 14 30 45): ").strip()
                
                if not time_input:
                    return None  # Auto
                
                # Parsing
                parts = time_input.split()
                if len(parts) != 3:
                    print(f"{bcolors.RED}❌ Format: HH MM SS (3 nombres séparés par des espaces){bcolors.ENDC}")
                    continue
                
                hour, minute, second = map(int, parts)
                
                # Validation
                if not (0 <= hour <= 23):
                    print(f"{bcolors.RED}❌ Heure invalide (0-23){bcolors.ENDC}")
                    continue
                if not (0 <= minute <= 59):
                    print(f"{bcolors.RED}❌ Minute invalide (0-59){bcolors.ENDC}")
                    continue
                if not (0 <= second <= 59):
                    print(f"{bcolors.RED}❌ Seconde invalide (0-59){bcolors.ENDC}")
                    continue
                
                # Construction de l'heure
                crash_time = self.current_time.replace(hour=hour, minute=minute, second=second)
                
                # Validation temporelle
                if crash_time <= self.current_time:
                    print(f"{bcolors.RED}❌ L'heure de crash doit être après {self.current_time.strftime('%H:%M:%S')}{bcolors.ENDC}")
                    continue
                
                print(f"{bcolors.GREEN}✅ Heure de crash: {crash_time.strftime('%H:%M:%S')}{bcolors.ENDC}")
                return crash_time
                
            except ValueError:
                print(f"{bcolors.RED}❌ Valeur numérique invalide{bcolors.ENDC}")
            except KeyboardInterrupt:
                print(f"\n{bcolors.YELLOW}Annulé{bcolors.ENDC}")
                return None

    def _show_phase_descriptions(self):
        """Affiche les descriptions détaillées des phases et cycles."""
        print(f"\n{bcolors.BOLD}📚 GUIDE DES PHASES ET CYCLES{bcolors.ENDC}")
        print("=" * 80)
        
        # Description des phases de qualité
        print(f"{bcolors.BOLD}🎯 PHASES DE QUALITÉ:{bcolors.ENDC}")
        print(f"  {bcolors.GREEN}🟢 BONNE (Good):{bcolors.ENDC}")
        print(f"    • Probabilité élevée de multiplicateurs 2.00-9.99x")
        print(f"    • Crashs modérés à lents")
        print(f"    • Moments favorables pour les gains")
        
        print(f"  {bcolors.PURPLE} NORMALE (Normal):{bcolors.ENDC}")
        print(f"    • Distribution équilibrée des multiplicateurs")
        print(f"    • Mix de crashs rapides et modérés")
        print(f"    • Phase neutre, prudence recommandée")
        
        print(f"  {bcolors.YELLOW}🟡 MAUVAISE (Bad):{bcolors.ENDC}")
        print(f"    • Probabilité élevée de multiplicateurs < 2.00x")
        print(f"    • Crashs rapides fréquents")
        print(f"    • Moments défavorables, retrait rapide conseillé")
        
        print(f"  {bcolors.RED}🔴 CATASTROPHIQUE (Catastrophic):{bcolors.ENDC}")
        print(f"    • Très forte probabilité de multiplicateurs < 2.00x")
        print(f"    • Crashs très rapides")
        print(f"    • Éviter les paris ou retrait immédiat")
        
        print("\n" + "-" * 80)
        
        # Description des multiplicateurs par couleur
        print(f"{bcolors.BOLD}🎨 GUIDE DES MULTIPLICATEURS:{bcolors.ENDC}")
        print(f"  {bcolors.RED}🔴 < 1.51x:{bcolors.ENDC}")
        print(f"    • Crash très rapide (1-5 secondes)")
        print(f"    • Risque très élevé")
        print(f"    • Retrait immédiat conseillé")
        
        print(f"  {bcolors.ORANGE}🟠 1.51-1.99x:{bcolors.ENDC}")
        print(f"    • Crash rapide (1-10 secondes)")
        print(f"    • Risque élevé")
        print(f"    • Retrait rapide recommandé")
        
        print(f"  {bcolors.GREEN}🟢 2.00-2.99x:{bcolors.ENDC}")
        print(f"    • Crash modéré (5-20 secondes)")
        print(f"    • Risque modéré")
        print(f"    • Timing important")
        
        print(f"  {bcolors.YELLOW}🟡 3.00-3.99x:{bcolors.ENDC}")
        print(f"    • Crash moyen-élevé (10-30 secondes)")
        print(f"    • Risque modéré-élevé")
        print(f"    • Surveillance attentive")
        
        print(f"  {bcolors.PURPLE}🟣 4.00-9.99x:{bcolors.ENDC}")
        print(f"    • Crash élevé (20-60 secondes)")
        print(f"    • Risque faible-moderé")
        print(f"    • Opportunité de gains")
        
        print(f"  {bcolors.BLUE}🔵 ≥ 10.00x:{bcolors.ENDC}")
        print(f"    • Crash très élevé (60+ secondes)")
        print(f"    • Risque faible")
        print(f"    • Potentiel de gros gains")
        
        print("\n" + "-" * 80)
        
        # Description des cycles temporels
        print(f"{bcolors.BOLD}⏰ CYCLES TEMPORELS:{bcolors.ENDC}")
        print(f"  {bcolors.CYAN}🔄 Cycles de 5 minutes:{bcolors.ENDC}")
        print(f"    • Réinitialisation toutes les 5 minutes")
        print(f"    • Patterns qui s'alternent selon l'heure")
        print(f"    • Phases 0-4 dans chaque cycle")
        
        print(f"  {bcolors.BLUE} Cycles d'heures:{bcolors.ENDC}")
        print(f"    • Heures de pointe: 9, 10, 14, 15, 20, 21")
        print(f"    • Heures moyennes: 11, 12, 13, 16, 17, 18, 19")
        print(f"    • Heures creuses: Toutes les autres")
        
        print(f"  {bcolors.PURPLE}⏱️ Cycles de quarts d'heure:{bcolors.ENDC}")
        print(f"    • Premier quart (00-14 min): Plus favorable")
        print(f"    • Quarts intermédiaires: Neutres")
        print(f"    • Dernier quart (45-59 min): Plus défavorable")
        
        print("\n" + "-" * 80)
        
        # Description des minutes spéciales
        print(f"{bcolors.BOLD}🔢 MINUTES SPÉCIALES:{bcolors.ENDC}")
        print(f"  {bcolors.RED}⚠️ Minutes se terminant par 9:{bcolors.ENDC}")
        print(f"    • Première moitié (0-29s): Très défavorable")
        print(f"    • Deuxième moitié (30-59s): Défavorable")
        
        print(f"  {bcolors.YELLOW}⚠️ Minutes se terminant par 1:{bcolors.ENDC}")
        print(f"    • Première moitié (0-29s): Défavorable")
        print(f"    • Deuxième moitié (30-59s): Neutre à défavorable")
        
        print(f"  {bcolors.RED}🚨 Multiples de 7:{bcolors.ENDC}")
        print(f"    • Minutes 7, 17, 27, 37, 47, 57")
        print(f"    • Très défavorables, crashs rapides")
        
        print(f"  {bcolors.YELLOW}⚠️ Multiples de 5:{bcolors.ENDC}")
        print(f"    • Minutes 5, 15, 25, 35, 45, 55")
        print(f"    • Défavorables à catastrophiques")
        
        print(f"  {bcolors.PURPLE}⚡ Multiples de 3:{bcolors.ENDC}")
        print(f"    • Minutes 3, 6, 9, 12, 15, 18, 21, 24, 27, 30, 33, 36, 39, 42, 45, 48, 51, 54, 57")
        print(f"    • Neutres à défavorables")
        
        print("\n" + "-" * 80)
        
        # Conseils d'utilisation
        print(f"{bcolors.BOLD}💡 CONSEILS D'UTILISATION:{bcolors.ENDC}")
        print(f"  {bcolors.GREEN}✅ Moments favorables:{bcolors.ENDC}")
        print(f"    • Heures de pointe, premier quart d'heure")
        print(f"    • Minutes normales (pas de multiples spéciaux)")
        print(f"    • Phases 'good' ou 'normal'")
        
        print(f"  {bcolors.RED}❌ Moments défavorables:{bcolors.ENDC}")
        print(f"    • Heures creuses, dernier quart d'heure")
        print(f"    • Minutes se terminant par 9 ou 1")
        print(f"    • Multiples de 7, 5, 3")
        print(f"    • Phases 'bad' ou 'catastrophic'")
        
        print(f"  {bcolors.YELLOW}⚠️ Stratégie recommandée:{bcolors.ENDC}")
        print(f"    • Surveiller les phases et cycles")
        print(f"    • Ajuster les paris selon les moments")
        print(f"    • Retrait rapide en phase défavorable")
        print(f"    • Profiter des phases favorables")
        
        print("=" * 80)

    def _show_current_phase_info(self):
        """Affiche les informations sur la phase actuelle."""
        current_time = self.current_time
        intervals = self._get_time_intervals(current_time)
        
        print(f"\n{bcolors.BOLD}📊 PHASE ACTUELLE{bcolors.ENDC}")
        print("=" * 60)
        print(f"{bcolors.CYAN}Heure actuelle: {current_time.strftime('%H:%M:%S')}{bcolors.ENDC}")
        
        # Qualité par intervalle
        for interval_type, interval_key in [('hour', intervals['hour']), 
                                           ('quarter', intervals['quarter']), 
                                           ('five_min', intervals['five_min']), 
                                           ('minute', intervals['minute'])]:
            quality = self._determine_interval_quality(interval_type, current_time)
            
            # Couleur selon la qualité
            quality_color = {
                'good': bcolors.GREEN,
                'normal': bcolors.PURPLE,
                'bad': bcolors.YELLOW,
                'catastrophic': bcolors.RED
            }
            
            quality_emoji = {
                'good': '🟢',
                'normal': '',
                'bad': '',
                'catastrophic': '🔴'
            }
            
            print(f"{interval_type.capitalize()}: {quality_emoji[quality]} {quality_color[quality]}{quality}{bcolors.ENDC}")
        
        # Informations sur les cycles
        cycle_phase = current_time.minute % 5
        minutes_until_reset = 5 - cycle_phase
        print(f"\n{bcolors.CYAN}🔄 Cycle: Phase {cycle_phase}/4 ({minutes_until_reset} min avant reset){bcolors.ENDC}")
        
        # Minute spéciale ?
        minute_digit = current_time.minute % 10
        if minute_digit == 9:
            print(f"{bcolors.RED}⚠️ Minute spéciale: Se termine par 9{bcolors.ENDC}")
        elif minute_digit == 1:
            print(f"{bcolors.YELLOW}⚠️ Minute spéciale: Se termine par 1{bcolors.ENDC}")
        elif current_time.minute % 7 == 0:
            print(f"{bcolors.RED}🚨 Minute critique: Multiple de 7{bcolors.ENDC}")
        elif current_time.minute % 5 == 0:
            print(f"{bcolors.YELLOW}⚠️ Minute critique: Multiple de 5{bcolors.ENDC}")
        elif current_time.minute % 3 == 0:
            print(f"{bcolors.PURPLE}⚡ Minute spéciale: Multiple de 3{bcolors.ENDC}")
        
        print("=" * 60)

    def run_interactive_mode_with_restart(self):
        """Version avec possibilité de redémarrage à tout moment."""
        print("\n" + "=" * 80)
        print(bcolors.BOLD + " ASSISTANT PRÉDICTIF INTERACTIF - MODE FEEDBACK ".center(80, "=") + bcolors.ENDC)
        print("=" * 80)
        print(f"{bcolors.CYAN}💡 Tapez 'M' à tout moment pour accéder au menu{bcolors.ENDC}")
        print(f"{bcolors.CYAN}💡 Tapez 'analysis' pour voir les statistiques{bcolors.ENDC}")
        print(f"{bcolors.CYAN}💡 Tapez 'phases' pour voir le guide des phases{bcolors.ENDC}")
        print(f"{bcolors.CYAN}💡 Tapez 'current' pour voir la phase actuelle{bcolors.ENDC}")
        print(f"{bcolors.CYAN}💡 Tapez 'q' pour quitter{bcolors.ENDC}")
        print("=" * 80)

        while True:
            self.generate_forecast()
            user_input = input(f"{bcolors.YELLOW}Entrez le multiplicateur réel (ex: 1.23), 'M' pour menu, 'analysis' pour statistiques, 'phases' pour guide, 'current' pour phase actuelle, ou 'q' pour quitter:{bcolors.ENDC} ").strip().lower()
            if user_input == 'q':
                print(f"{bcolors.BLUE}Au revoir !{bcolors.ENDC}")
                break
            elif user_input == 'm':
                self._restart_session()
                continue
            elif user_input == 'analysis':
                self._show_analysis()
                continue
            elif user_input == 'phases':
                self._show_phase_descriptions()
                continue
            elif user_input == 'current':
                self._show_current_phase_info()
                continue
            try:
                real_multiplier = float(user_input)
                # Demande de l'heure de crash avec saisie individuelle
                real_crash_time = self._get_crash_time_input_compact()
                if real_crash_time:
                    self.apply_real_result_with_crash_time(real_multiplier, real_crash_time)
                else:
                    self.apply_real_result(real_multiplier)
            except ValueError:
                print(f"{bcolors.RED}❌ Multiplicateur invalide. Utilisez un nombre (ex: 1.23){bcolors.ENDC}")


def main():
    """Point d'entrée principal du script interactif."""
    parser = argparse.ArgumentParser(description="Assistant prédictif interactif pour jeu de type Crash.")
    parser.add_argument("--hour", type=int, default=datetime.now().hour, help="Heure de début de la session (0-23).")
    parser.add_argument("--minute", type=int, default=datetime.now().minute, help="Minute de début de la session (0-59).")
    parser.add_argument("--second", type=int, default=datetime.now().second, help="Seconde de début de la session (0-59).")
    args = parser.parse_args()

    start_time = datetime.now().replace(hour=args.hour, minute=args.minute, second=args.second, microsecond=0)

    predictor = InteractivePredictor(start_time)
    predictor.run_interactive_mode_with_restart()

if __name__ == "__main__":
    main()