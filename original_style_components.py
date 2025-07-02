import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.graph_objects as go

def create_console_style_predictions(predictions, start_time_str="17:27:19"):
    """Create console-style prediction display matching the original app"""
    if not predictions:
        st.info("No predictions available. Generate a forecast to see predictions.")
        return
    
    st.markdown("### 🔮 PRÉDICTIONS POUR LES 5 PROCHAINES MINUTES")
    st.markdown(f"**Heure de début: {start_time_str}**")
    st.markdown("---")
    
    # Create styled prediction rows
    prediction_html = ""
    for i, pred in enumerate(predictions, 1):
        start_time = pd.to_datetime(pred['start_time']).strftime('%H:%M:%S')
        crash_time = pd.to_datetime(pred['predicted_crash_time']).strftime('%H:%M:%S')
        multiplier = pred['predicted_multiplier']
        
        # Get color based on multiplier value
        color = get_multiplier_color_hex(multiplier)
        
        prediction_html += f"""
        <div style="font-family: 'Courier New', monospace; color: {color}; margin: 2px 0;">
            Tour {i:2d} | {start_time} → {crash_time} | ● {multiplier:.2f}x
        </div>
        """
    
    st.markdown(prediction_html, unsafe_allow_html=True)
    st.markdown("---")

def get_multiplier_color_hex(multiplier):
    """Get hex color for multiplier based on original app color scheme"""
    if multiplier < 1.51:
        return "#FF0000"  # Red
    elif multiplier < 2.00:
        return "#FF8C00"  # Orange
    elif multiplier < 3.00:
        return "#00FF00"  # Green
    elif multiplier < 4.00:
        return "#FFFF00"  # Yellow
    elif multiplier < 10.00:
        return "#800080"  # Purple
    else:
        return "#00FFFF"  # Cyan

def create_menu_interface():
    """Create the main menu interface matching the original app"""
    st.markdown("### 📋 MENU PRINCIPAL")
    st.markdown("**Choisissez une option:**")
    
    options = [
        "1. Redémarrage rapide (même heure de début)",
        "2. Nouvelle heure de début", 
        "3. Afficher données historiques",
        "4. Afficher résumé de session",
        "5. Guide des phases et cycles",
        "6. Phase actuelle",
        "7. Statistiques et analyse",
        "8. Annuler"
    ]
    
    selected_option = st.radio("Votre choix (1-8):", options, key="menu_option")
    
    return selected_option

def create_feedback_input_form():
    """Create feedback input form matching original app style"""
    st.markdown("### 📝 ENTRER LE RÉSULTAT RÉEL")
    
    with st.form("feedback_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            multiplier = st.number_input(
                "Multiplicateur réel (ex: 1.23):",
                min_value=1.0,
                max_value=100.0,
                value=1.0,
                step=0.01,
                format="%.2f"
            )
        
        with col2:
            # Crash time input
            crash_time = st.time_input(
                "Heure de crash (optionnel):",
                value=datetime.now().time()
            )
        
        include_time = st.checkbox("Inclure l'heure de crash dans l'analyse")
        
        submitted = st.form_submit_button("✅ Valider le résultat", type="primary")
        
        if submitted:
            return {
                'multiplier': multiplier,
                'crash_time': crash_time if include_time else None,
                'include_time': include_time
            }
    
    return None

def create_analysis_display(feedback_data):
    """Display analysis matching original app style"""
    if feedback_data.empty:
        st.info("Aucune donnée d'analyse disponible.")
        return
    
    st.markdown("### 📈 ANALYSE DES TENDANCES")
    st.markdown("=" * 60)
    
    # Color legend
    st.markdown("#### 🎨 LÉGENDE DES COULEURS:")
    legend_html = """
    <div style="font-family: 'Courier New', monospace;">
        <div style="color: #FF0000;">🔴 < 1.51x (Rouge) - Crash très rapide</div>
        <div style="color: #FF8C00;">  1.51-1.99x (Orange) - Crash rapide</div>
        <div style="color: #00FF00;">🟢 2.00-2.99x (Vert) - Crash modéré</div>
        <div style="color: #FFFF00;">  3.00-3.99x (Jaune) - Crash moyen-élevé</div>
        <div style="color: #800080;">  4.00-9.99x (Violet) - Crash élevé</div>
        <div style="color: #00FFFF;">🔵 ≥ 10.00x (Bleu) - Crash très élevé</div>
    </div>
    """
    st.markdown(legend_html, unsafe_allow_html=True)
    st.markdown("---")
    
    # Statistics
    total_entries = len(feedback_data)
    if total_entries > 0:
        low_count = len(feedback_data[feedback_data['multiplier'] < 2.0])
        med_count = len(feedback_data[(feedback_data['multiplier'] >= 2.0) & (feedback_data['multiplier'] < 10.0)])
        high_count = len(feedback_data[feedback_data['multiplier'] >= 10.0])
        
        low_pct = (low_count / total_entries) * 100
        med_pct = (med_count / total_entries) * 100
        high_pct = (high_count / total_entries) * 100
        
        stats_html = f"""
        <div style="font-family: 'Courier New', monospace;">
            <div style="color: #FF0000;">< 2.00x: {low_count} ({low_pct:.1f}%)</div>
            <div style="color: #00FF00;">2.00-9.99x: {med_count} ({med_pct:.1f}%)</div>
            <div style="color: #00FFFF;">≥ 10.00x: {high_count} ({high_pct:.1f}%)</div>
        </div>
        """
        st.markdown(stats_html, unsafe_allow_html=True)
        
        # Recent multipliers
        recent_data = feedback_data.tail(5)
        if not recent_data.empty:
            st.markdown("**Derniers résultats:**")
            recent_html = ""
            for _, row in recent_data.iterrows():
                color = get_multiplier_color_hex(row['multiplier'])
                recent_html += f'<span style="color: {color}; font-family: monospace;">● {row["multiplier"]:.2f}x </span>'
            st.markdown(recent_html, unsafe_allow_html=True)

def create_session_summary(feedback_data, predictions):
    """Create session summary matching original app"""
    st.markdown("### 📊 RÉSUMÉ DE SESSION")
    st.markdown("=" * 60)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Prédictions générées", len(predictions) if predictions else 0)
    
    with col2:
        st.metric("Résultats fournis", len(feedback_data) if not feedback_data.empty else 0)
    
    with col3:
        if not feedback_data.empty:
            avg_multiplier = feedback_data['multiplier'].mean()
            st.metric("Multiplicateur moyen", f"{avg_multiplier:.2f}x")
        else:
            st.metric("Multiplicateur moyen", "—")
    
    # Prediction accuracy if we have both predictions and feedback
    if predictions and not feedback_data.empty:
        st.markdown("#### 🎯 PRÉCISION DES PRÉDICTIONS")
        
        # Simple accuracy calculation
        recent_predictions = [p['predicted_multiplier'] for p in predictions[-len(feedback_data):]]
        recent_feedback = feedback_data['multiplier'].tolist()
        
        if recent_predictions and recent_feedback:
            accuracy_data = []
            for i, (pred, real) in enumerate(zip(recent_predictions, recent_feedback)):
                difference = abs(pred - real)
                accuracy = max(0, 100 - (difference / real * 100))
                accuracy_data.append({
                    'Round': i + 1,
                    'Predicted': pred,
                    'Actual': real,
                    'Accuracy': accuracy
                })
            
            accuracy_df = pd.DataFrame(accuracy_data)
            st.dataframe(accuracy_df, use_container_width=True)
            
            avg_accuracy = accuracy_df['Accuracy'].mean()
            st.metric("Précision moyenne", f"{avg_accuracy:.1f}%")

def create_console_header():
    """Create the console-style header"""
    header_html = """
    <div style="background-color: #000000; color: #00FF00; padding: 10px; font-family: 'Courier New', monospace; border: 2px solid #00FF00;">
        <div style="text-align: center; font-weight: bold;">
            ================ ASSISTANT PREDICTIF INTERACTIF ================
        </div>
        <div style="text-align: center;">
            MODE: PRÉDICTIONS + FEEDBACK
        </div>
        <div style="text-align: center;">
            ===============================================================
        </div>
    </div>
    """
    st.markdown(header_html, unsafe_allow_html=True)
    st.markdown("")