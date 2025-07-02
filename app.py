import streamlit as st
import pandas as pd
import time
from datetime import datetime, timedelta
import threading
import plotly.graph_objects as go

from simulation_engine import CrashSimulator, CONFIG
from dashboard_components import (
    create_multiplier_display, create_trend_chart, create_distribution_chart,
    create_phase_analysis_chart, create_real_time_chart, create_stats_cards,
    create_category_breakdown, create_configuration_panel,
    create_5min_forecast_display, create_real_result_input, create_phase_indicator
)
from data_manager import DataManager

# Language configurations
LANGUAGES = {
    'en': {
        'title': '🔮 Crash Prediction Dashboard',
        'subtitle': 'Generate crash multiplier predictions and provide real-time feedback to improve accuracy.',
        'tabs': {
            'dashboard': '📊 Dashboard',
            'predictions': '📅 Predictions', 
            'analytics': '📈 Analytics',
            'historical': '📂 Historical',
            'config': '⚙️ Config'
        },
        'dashboard': {
            'header': 'Dashboard Overview',
            'instructions_title': 'How to Use the Crash Predictor',
            'instructions': [
                '**Generate Predictions** - Use the "Predictions" tab to create 5-minute forecasts',
                '**Edit Results** - Adjust predicted values and submit real results directly in the predictions interface',
                '**Analyze Trends** - View analytics to understand prediction accuracy and patterns',
                '**Configure** - Adjust simulation parameters in the Config tab'
            ],
            'metrics': {
                'active_predictions': 'Active Predictions',
                'submitted_results': 'Submitted Results', 
                'avg_prediction': 'Avg Prediction'
            },
            'recent_activity': 'Recent Activity',
            'no_results': 'No results submitted yet. Use the Predictions tab to generate and submit results.',
            'get_started': 'Get started by generating your first predictions in the Predictions tab.'
        },
        'predictions': {
            'header': '5-Minute Predictions',
            'generate_btn': '🔮 Generate 5-Minute Forecast',
            'clear_btn': '🗑️ Clear Forecast',
            'success': 'Forecast generated successfully!',
            'info': 'Click "Generate 5-Minute Forecast" to see predictions based on your simulation algorithm.'
        },
        'analytics': {
            'header': 'Analytics & Trends',
            'data_source': 'Data Source',
            'current_session': 'Current Session',
            'historical_data': 'Historical Data',
            'time_range': 'Time Range',
            'trend_interval': 'Trend Interval',
            'last_hour': 'Last Hour',
            'last_6_hours': 'Last 6 Hours', 
            'last_24_hours': 'Last 24 Hours',
            'all_data': 'All Data',
            'no_data': 'No data available for analysis. Generate predictions and submit results to see trends.'
        },
        'historical': {
            'header': 'Historical Data Analysis',
            'data_summary': 'Data Summary',
            'total_records': 'Total Records',
            'date_range': 'Date Range',
            'multiplier_range': 'Multiplier Range',
            'date_filter': 'Date Range Filter',
            'start_date': 'Start Date',
            'end_date': 'End Date',
            'no_data_range': 'No data found for the selected date range.',
            'no_historical': 'No historical data available. Run some predictions to generate historical data.'
        },
        'config': {
            'header': 'Configuration',
            'simulation_params': 'Simulation Parameters',
            'save_btn': 'Save Configuration',
            'reset_btn': 'Reset to Defaults',
            'saved': 'Configuration saved successfully!',
            'reset': 'Configuration reset to defaults!'
        }
    },
    'fr': {
        'title': '🔮 Tableau de Bord de Prédiction de Crash',
        'subtitle': 'Générez des prédictions de multiplicateur de crash et fournissez des commentaires en temps réel pour améliorer la précision.',
        'tabs': {
            'dashboard': '📊 Tableau de Bord',
            'predictions': '📅 Prédictions',
            'analytics': '📈 Analytiques', 
            'historical': '📂 Historique',
            'config': '⚙️ Config'
        },
        'dashboard': {
            'header': 'Aperçu du Tableau de Bord',
            'instructions_title': 'Comment Utiliser le Prédicteur de Crash',
            'instructions': [
                '**Générer des Prédictions** - Utilisez l\'onglet "Prédictions" pour créer des prévisions de 5 minutes',
                '**Modifier les Résultats** - Ajustez les valeurs prédites et soumettez les résultats réels directement dans l\'interface de prédictions',
                '**Analyser les Tendances** - Consultez les analyses pour comprendre la précision des prédictions et les modèles',
                '**Configurer** - Ajustez les paramètres de simulation dans l\'onglet Config'
            ],
            'metrics': {
                'active_predictions': 'Prédictions Actives',
                'submitted_results': 'Résultats Soumis',
                'avg_prediction': 'Prédiction Moy.'
            },
            'recent_activity': 'Activité Récente',
            'no_results': 'Aucun résultat soumis pour le moment. Utilisez l\'onglet Prédictions pour générer et soumettre des résultats.',
            'get_started': 'Commencez en générant vos premières prédictions dans l\'onglet Prédictions.'
        },
        'predictions': {
            'header': 'Prédictions de 5 Minutes',
            'generate_btn': '🔮 Générer Prévision 5 Minutes',
            'clear_btn': '🗑️ Effacer Prévision',
            'success': 'Prévision générée avec succès!',
            'info': 'Cliquez sur "Générer Prévision 5 Minutes" pour voir les prédictions basées sur votre algorithme de simulation.'
        },
        'analytics': {
            'header': 'Analyses et Tendances',
            'data_source': 'Source de Données',
            'current_session': 'Session Actuelle',
            'historical_data': 'Données Historiques',
            'time_range': 'Plage de Temps',
            'trend_interval': 'Intervalle de Tendance',
            'last_hour': 'Dernière Heure',
            'last_6_hours': '6 Dernières Heures',
            'last_24_hours': '24 Dernières Heures', 
            'all_data': 'Toutes les Données',
            'no_data': 'Aucune donnée disponible pour l\'analyse. Générez des prédictions et soumettez des résultats pour voir les tendances.'
        },
        'historical': {
            'header': 'Analyse des Données Historiques',
            'data_summary': 'Résumé des Données',
            'total_records': 'Total des Enregistrements',
            'date_range': 'Plage de Dates',
            'multiplier_range': 'Plage de Multiplicateurs',
            'date_filter': 'Filtre de Plage de Dates',
            'start_date': 'Date de Début',
            'end_date': 'Date de Fin',
            'no_data_range': 'Aucune donnée trouvée pour la plage de dates sélectionnée.',
            'no_historical': 'Aucune donnée historique disponible. Exécutez quelques prédictions pour générer des données historiques.'
        },
        'config': {
            'header': 'Configuration',
            'simulation_params': 'Paramètres de Simulation',
            'save_btn': 'Sauvegarder Configuration',
            'reset_btn': 'Remettre aux Défauts',
            'saved': 'Configuration sauvegardée avec succès!',
            'reset': 'Configuration remise aux valeurs par défaut!'
        }
    }
}

# Page configuration
st.set_page_config(
    page_title="Crash Prediction Dashboard",
    page_icon="🔮",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Add responsive CSS
st.markdown("""
<style>
    .stApp {
        max-width: 100%;
    }
    .block-container {
        padding-top: 1rem;
        padding-bottom: 0rem;
        padding-left: 5%;
        padding-right: 5%;
    }
    @media (max-width: 768px) {
        .block-container {
            padding-left: 2%;
            padding-right: 2%;
        }
        .stColumns > div {
            min-width: 0 !important;
        }
    }
    /* Better time display */
    .time-display {
        font-family: 'Courier New', monospace;
        font-weight: bold;
        font-size: 1.1em;
    }
    .stNumberInput > div > div > input {
        font-family: 'Courier New', monospace;
    }
    .stTextInput > div > div > input {
        font-family: 'Courier New', monospace;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'simulator' not in st.session_state:
    st.session_state.simulator = CrashSimulator()
    st.session_state.data_manager = DataManager()
    st.session_state.real_time_data = pd.DataFrame()
    st.session_state.update_counter = 0
    st.session_state.forecast_predictions = []
    st.session_state.language = 'en'  # Default language
    st.session_state.config = CONFIG.copy()  # Store editable config

def simulation_callback(data):
    """Callback function for simulation updates"""
    # Convert to DataFrame and append to session data
    new_row = pd.DataFrame([data])
    if not st.session_state.real_time_data.empty:
        st.session_state.real_time_data = pd.concat([st.session_state.real_time_data, new_row], ignore_index=True)
    else:
        st.session_state.real_time_data = new_row
    
    st.session_state.update_counter += 1

# Register the callback
st.session_state.simulator.add_callback(simulation_callback)

# Language selector in sidebar
with st.sidebar:
    st.header("🌐 Language / Langue")
    language_choice = st.selectbox(
        "Select Language / Choisir la langue",
        options=['en', 'fr'],
        format_func=lambda x: 'English' if x == 'en' else 'Français',
        index=0 if st.session_state.language == 'en' else 1
    )
    
    if language_choice != st.session_state.language:
        st.session_state.language = language_choice
        st.rerun()

# Get current language text
text = LANGUAGES[st.session_state.language]

# Header
st.title(text['title'])
st.markdown(text['subtitle'])

# Phase indicator (always visible)
phase_info = create_phase_indicator()

# Tabs for different views - now with Config tab added
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    text['tabs']['dashboard'], 
    text['tabs']['predictions'], 
    text['tabs']['analytics'], 
    text['tabs']['historical'],
    text['tabs']['config']
])

with tab1:
    st.header(text['dashboard']['header'])
    
    # Instructions
    st.markdown(f"### {text['dashboard']['instructions_title']}")
    for instruction in text['dashboard']['instructions']:
        st.markdown(f"1. {instruction}")
    
    # Show current status
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.session_state.forecast_predictions:
            st.metric(text['dashboard']['metrics']['active_predictions'], len(st.session_state.forecast_predictions))
        else:
            st.metric(text['dashboard']['metrics']['active_predictions'], "0")
    
    with col2:
        feedback_count = len([key for key in st.session_state.keys() if key.startswith("submitted_")])
        st.metric(text['dashboard']['metrics']['submitted_results'], feedback_count)
    
    with col3:
        if st.session_state.forecast_predictions:
            avg_prediction = sum(p['predicted_multiplier'] for p in st.session_state.forecast_predictions) / len(st.session_state.forecast_predictions)
            st.metric(text['dashboard']['metrics']['avg_prediction'], f"{avg_prediction:.2f}x")
        else:
            st.metric(text['dashboard']['metrics']['avg_prediction'], "—")
    
    # Show recent activity if available
    if not st.session_state.real_time_data.empty:
        st.subheader(text['dashboard']['recent_activity'])
        
        feedback_data = st.session_state.real_time_data[
            st.session_state.real_time_data['phase'] == 'real_result'
        ].tail(5).copy()
        
        if not feedback_data.empty:
            feedback_data['timestamp'] = pd.to_datetime(feedback_data['timestamp']).dt.strftime('%H:%M:%S')
            feedback_data['multiplier'] = feedback_data['multiplier'].round(2)
            st.dataframe(
                feedback_data[['timestamp', 'multiplier']].sort_values('timestamp', ascending=False), 
                use_container_width=True
            )
        else:
            st.info(text['dashboard']['no_results'])
    else:
        st.info(text['dashboard']['get_started'])

with tab2:
    st.header(text['predictions']['header'])
    
    # Generate forecast button
    col1, col2 = st.columns([3, 1])
    
    with col1:
        if st.button(text['predictions']['generate_btn'], type="primary"):
            try:
                st.session_state.forecast_predictions = st.session_state.simulator.generate_5min_forecast()
                st.success(text['predictions']['success'])
                st.rerun()
            except Exception as e:
                st.error(f"Error generating forecast: {e}")
    
    with col2:
        if st.session_state.forecast_predictions:
            if st.button(text['predictions']['clear_btn']):
                st.session_state.forecast_predictions = []
                # Clear all submitted results
                keys_to_remove = [key for key in st.session_state.keys() if key.startswith("submitted_")]
                for key in keys_to_remove:
                    del st.session_state[key]
                st.rerun()
    
    # Display current forecast with enhanced features
    if st.session_state.forecast_predictions:
        # The enhanced display handles trend adjustment and editable results
        submitted_data = create_5min_forecast_display(st.session_state.forecast_predictions)
        
        # Process submitted results for learning
        if submitted_data:
            for result in submitted_data:
                try:
                    # Apply the real result to the simulator for learning
                    st.session_state.simulator.apply_real_result(
                        result['real_multiplier'], 
                        None  # No crash time provided in this interface
                    )
                except Exception as e:
                    st.error(f"Error processing result: {e}")
    else:
        st.info(text['predictions']['info'])

with tab3:
    st.header(text['analytics']['header'])
    
    # Data source selector
    data_source = st.radio(text['analytics']['data_source'], 
                          [text['analytics']['current_session'], text['analytics']['historical_data']], 
                          horizontal=True)
    
    if data_source == text['analytics']['current_session']:
        trend_data = st.session_state.real_time_data
    else:
        trend_data = st.session_state.data_manager.load_historical_data()
    
    if not trend_data.empty:
        # Time range selector
        col1, col2 = st.columns(2)
        with col1:
            time_range_options = [text['analytics']['last_hour'], text['analytics']['last_6_hours'], 
                                text['analytics']['last_24_hours'], text['analytics']['all_data']]
            time_range = st.selectbox(text['analytics']['time_range'], time_range_options)
        
        with col2:
            trend_interval = st.selectbox(text['analytics']['trend_interval'], ["minute", "five_min", "quarter", "hour"])
        
        # Filter data based on time range
        if time_range != text['analytics']['all_data']:
            hours_map = {
                text['analytics']['last_hour']: 1, 
                text['analytics']['last_6_hours']: 6, 
                text['analytics']['last_24_hours']: 24
            }
            trend_data = st.session_state.data_manager.filter_data_by_time_range(
                trend_data, hours_map[time_range]
            )
        
        # Create trend chart
        create_trend_chart(trend_data, trend_interval)
        
        # Distribution chart
        col1, col2 = st.columns(2)
        with col1:
            create_distribution_chart(trend_data)
        with col2:
            create_phase_analysis_chart(trend_data)
    else:
        st.info(text['analytics']['no_data'])

with tab4:
    st.header(text['historical']['header'])
    
    # Load historical data
    historical_data = st.session_state.data_manager.load_historical_data()
    
    if not historical_data.empty:
        # Data summary
        summary = st.session_state.data_manager.get_data_summary(historical_data)
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader(text['historical']['data_summary'])
            st.write(f"**{text['historical']['total_records']}:** {summary.get('total_records', 'N/A')}")
            st.write(f"**{text['historical']['date_range']}:** {summary.get('date_range', 'N/A')}")
            st.write(f"**{text['historical']['multiplier_range']}:** {summary.get('multiplier_range', 'N/A')}")
        
        with col2:
            st.subheader(text['historical']['date_filter'])
            min_date = historical_data['timestamp'].min().date()
            max_date = historical_data['timestamp'].max().date()
            
            start_date = st.date_input(text['historical']['start_date'], min_date, min_value=min_date, max_value=max_date)
            end_date = st.date_input(text['historical']['end_date'], max_date, min_value=min_date, max_value=max_date)
        
        # Filter data
        filtered_data = st.session_state.data_manager.filter_data_by_date_range(historical_data, start_date, end_date)
        
        if not filtered_data.empty:
            # Historical statistics
            historical_stats = st.session_state.data_manager.calculate_statistics(filtered_data)
            create_stats_cards(historical_stats)
            
            # Historical trends
            create_trend_chart(filtered_data, "hour")
        else:
            st.warning(text['historical']['no_data_range'])
    else:
        st.info(text['historical']['no_historical'])

with tab5:
    st.header(text['config']['header'])
    
    # Configuration panel
    st.subheader(text['config']['simulation_params'])
    
    # Create configuration form
    config_panel = create_configuration_panel(st.session_state.config)
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button(text['config']['save_btn'], type="primary"):
            try:
                # Update simulator configuration
                st.session_state.simulator.update_config(st.session_state.config)
                st.success(text['config']['saved'])
                st.rerun()
            except Exception as e:
                st.error(f"Error saving configuration: {e}")
    
    with col2:
        if st.button(text['config']['reset_btn']):
            try:
                # Reset to defaults
                st.session_state.config = CONFIG.copy()
                st.session_state.simulator.update_config(st.session_state.config)
                st.success(text['config']['reset'])
                st.rerun()
            except Exception as e:
                st.error(f"Error resetting configuration: {e}")

# Auto-refresh for real-time updates (optional)
if st.session_state.forecast_predictions and len(st.session_state.forecast_predictions) > 0:
    time.sleep(0.1)  # Small delay to prevent excessive refreshing