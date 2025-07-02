import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import time
from simulation_engine import CrashSimulator, CONFIG
from data_manager import DataManager
from original_style_components import (
    create_console_header, create_console_style_predictions, 
    create_menu_interface, create_feedback_input_form,
    create_analysis_display, create_session_summary
)

# Page configuration
st.set_page_config(
    page_title="Assistant Prédictif Interactif",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Initialize session state
if 'simulator' not in st.session_state:
    st.session_state.simulator = CrashSimulator()
    st.session_state.data_manager = DataManager()
    st.session_state.real_time_data = pd.DataFrame()
    st.session_state.forecast_predictions = []
    st.session_state.current_start_time = datetime.now().strftime('%H:%M:%S')

# Console header
create_console_header()

# Main navigation
st.markdown("### 🎮 Navigation")
nav_option = st.radio(
    "Choisissez une action:",
    [
        "🔮 Générer prédictions",
        "📝 Entrer résultat réel", 
        "📊 Voir analyse",
        "📋 Menu principal",
        "🔄 Redémarrer session"
    ],
    horizontal=True
)

# Display content based on navigation
if nav_option == "🔮 Générer prédictions":
    st.markdown("---")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        if st.button("🚀 Générer Prédictions 5min", type="primary", use_container_width=True):
            try:
                st.session_state.forecast_predictions = st.session_state.simulator.generate_5min_forecast()
                st.session_state.current_start_time = datetime.now().strftime('%H:%M:%S')
                st.success("Prédictions générées avec succès!")
                st.rerun()
            except Exception as e:
                st.error(f"Erreur lors de la génération: {e}")
        
        if st.session_state.forecast_predictions:
            st.info(f"✅ {len(st.session_state.forecast_predictions)} prédictions actives")
            if st.button("🗑️ Effacer prédictions"):
                st.session_state.forecast_predictions = []
                st.rerun()
    
    with col2:
        # Display predictions in console style
        create_console_style_predictions(
            st.session_state.forecast_predictions,
            st.session_state.current_start_time
        )

elif nav_option == "📝 Entrer résultat réel":
    st.markdown("---")
    
    # Feedback input form
    feedback_result = create_feedback_input_form()
    
    if feedback_result:
        try:
            real_multiplier = feedback_result['multiplier']
            crash_time = None
            
            if feedback_result['include_time'] and feedback_result['crash_time']:
                today = datetime.now().date()
                crash_time = datetime.combine(today, feedback_result['crash_time'])
            
            # Apply feedback to simulator
            result_data = st.session_state.simulator.apply_real_result(real_multiplier, crash_time)
            
            # Add to real-time data
            new_row = pd.DataFrame([result_data])
            if st.session_state.real_time_data.empty:
                st.session_state.real_time_data = new_row
            else:
                st.session_state.real_time_data = pd.concat([st.session_state.real_time_data, new_row], ignore_index=True)
            
            # Show confirmation in console style
            color = "#00FF00" if real_multiplier >= 2.0 else "#FF0000"
            st.markdown(f"""
            <div style="background-color: #000000; color: {color}; padding: 10px; font-family: 'Courier New', monospace; border: 1px solid {color};">
                >>> Résultat réel enregistré: ● {real_multiplier:.2f}x
                {f">>> Heure de crash: {crash_time.strftime('%H:%M:%S')}" if crash_time else ""}
                >>> Prochaine prédiction mise à jour avec ce feedback
            </div>
            """, unsafe_allow_html=True)
            
            # Comparison with predictions
            if st.session_state.forecast_predictions:
                st.markdown("#### 🔄 COMPARAISON AVEC PRÉDICTIONS")
                avg_pred = sum(p['predicted_multiplier'] for p in st.session_state.forecast_predictions) / len(st.session_state.forecast_predictions)
                difference = real_multiplier - avg_pred
                
                if abs(difference) < 0.5:
                    st.success(f"✅ Prédiction proche! Écart: {difference:+.2f}x")
                elif difference > 0:
                    st.warning(f"⬆️ Résultat plus élevé que prédit: {difference:+.2f}x")
                else:
                    st.warning(f"⬇️ Résultat plus bas que prédit: {difference:+.2f}x")
                    
        except Exception as e:
            st.error(f"Erreur lors de l'enregistrement: {e}")

elif nav_option == "📊 Voir analyse":
    st.markdown("---")
    
    # Filter feedback data
    if not st.session_state.real_time_data.empty:
        feedback_data = st.session_state.real_time_data[
            st.session_state.real_time_data['phase'] == 'real_result'
        ].copy()
        create_analysis_display(feedback_data)
    else:
        st.info("Aucune donnée d'analyse disponible. Entrez d'abord des résultats réels.")

elif nav_option == "📋 Menu principal":
    st.markdown("---")
    
    # Session summary
    feedback_data = st.session_state.real_time_data[
        st.session_state.real_time_data['phase'] == 'real_result'
    ] if not st.session_state.real_time_data.empty else pd.DataFrame()
    
    create_session_summary(feedback_data, st.session_state.forecast_predictions)
    
    st.markdown("---")
    
    # Menu options
    menu_choice = create_menu_interface()
    
    if "Redémarrage rapide" in menu_choice:
        if st.button("🔄 Redémarrage rapide"):
            st.session_state.current_start_time = datetime.now().strftime('%H:%M:%S')
            st.success("Session redémarrée avec l'heure actuelle!")
            st.rerun()
    
    elif "Nouvelle heure" in menu_choice:
        new_time = st.time_input("Nouvelle heure de début:", value=datetime.now().time())
        if st.button("✅ Appliquer nouvelle heure"):
            st.session_state.current_start_time = new_time.strftime('%H:%M:%S')
            st.success(f"Nouvelle heure de début: {st.session_state.current_start_time}")
            st.rerun()
    
    elif "données historiques" in menu_choice:
        st.markdown("#### 📂 DONNÉES HISTORIQUES")
        if not st.session_state.real_time_data.empty:
            st.dataframe(st.session_state.real_time_data, use_container_width=True)
        else:
            st.info("Aucune donnée historique disponible.")

elif nav_option == "🔄 Redémarrer session":
    st.markdown("---")
    st.warning("⚠️ Êtes-vous sûr de vouloir redémarrer complètement la session?")
    st.markdown("Cela effacera toutes les prédictions et données de feedback actuelles.")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Oui, redémarrer", type="primary"):
            # Clear all session data
            st.session_state.forecast_predictions = []
            st.session_state.real_time_data = pd.DataFrame()
            st.session_state.current_start_time = datetime.now().strftime('%H:%M:%S')
            st.success("Session complètement redémarrée!")
            st.rerun()
    
    with col2:
        if st.button("❌ Annuler"):
            st.info("Redémarrage annulé.")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; font-size: 12px;">
Assistant Prédictif Interactif | Mode: Prédictions + Feedback
</div>
""", unsafe_allow_html=True)