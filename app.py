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

# Header
st.title("🔮 Crash Prediction Dashboard")
st.markdown("Generate crash multiplier predictions and provide real-time feedback to improve accuracy.")

# Phase indicator (always visible)
phase_info = create_phase_indicator()

# Tabs for different views (Feedback tab removed)
tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "📅 Predictions", "📈 Analytics", "📂 Historical"])

with tab1:
    st.header("Dashboard Overview")
    
    # Instructions
    st.markdown("""
    ### How to Use the Crash Predictor
    
    1. **Generate Predictions** - Use the "Predictions" tab to create 5-minute forecasts
    2. **Edit Results** - Adjust predicted values and submit real results directly in the predictions interface
    3. **Analyze Trends** - View analytics to understand prediction accuracy and patterns
    """)
    
    # Show current status
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.session_state.forecast_predictions:
            st.metric("Active Predictions", len(st.session_state.forecast_predictions))
        else:
            st.metric("Active Predictions", "0")
    
    with col2:
        feedback_count = len([key for key in st.session_state.keys() if key.startswith("submitted_")])
        st.metric("Submitted Results", feedback_count)
    
    with col3:
        if st.session_state.forecast_predictions:
            avg_prediction = sum(p['predicted_multiplier'] for p in st.session_state.forecast_predictions) / len(st.session_state.forecast_predictions)
            st.metric("Avg Prediction", f"{avg_prediction:.2f}x")
        else:
            st.metric("Avg Prediction", "—")
    
    # Show recent activity if available
    if not st.session_state.real_time_data.empty:
        st.subheader("Recent Activity")
        
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
            st.info("No results submitted yet. Use the Predictions tab to generate and submit results.")
    else:
        st.info("Get started by generating your first predictions in the Predictions tab.")

with tab2:
    st.header("5-Minute Predictions")
    
    # Generate forecast button
    col1, col2 = st.columns([3, 1])
    
    with col1:
        if st.button("🔮 Generate 5-Minute Forecast", type="primary"):
            try:
                st.session_state.forecast_predictions = st.session_state.simulator.generate_5min_forecast()
                st.success("Forecast generated successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Error generating forecast: {e}")
    
    with col2:
        if st.session_state.forecast_predictions:
            if st.button("🗑️ Clear Forecast"):
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
        st.info("Click 'Generate 5-Minute Forecast' to see predictions based on your simulation algorithm.")

with tab3:
    st.header("Analytics & Trends")
    
    # Data source selector
    data_source = st.radio("Data Source", ["Current Session", "Historical Data"], horizontal=True)
    
    if data_source == "Current Session":
        trend_data = st.session_state.real_time_data
    else:
        trend_data = st.session_state.data_manager.load_historical_data()
    
    if not trend_data.empty:
        # Time range selector
        col1, col2 = st.columns(2)
        with col1:
            time_range = st.selectbox("Time Range", ["Last Hour", "Last 6 Hours", "Last 24 Hours", "All Data"])
        
        with col2:
            trend_interval = st.selectbox("Trend Interval", ["minute", "five_min", "quarter", "hour"])
        
        # Filter data based on time range
        if time_range != "All Data":
            hours_map = {"Last Hour": 1, "Last 6 Hours": 6, "Last 24 Hours": 24}
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
        st.info("No data available for analysis. Generate predictions and submit results to see trends.")

with tab4:
    st.header("Historical Data Analysis")
    
    # Load historical data
    historical_data = st.session_state.data_manager.load_historical_data()
    
    if not historical_data.empty:
        # Data summary
        summary = st.session_state.data_manager.get_data_summary(historical_data)
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Data Summary")
            st.write(f"**Total Records:** {summary.get('total_records', 'N/A')}")
            st.write(f"**Date Range:** {summary.get('date_range', 'N/A')}")
            st.write(f"**Multiplier Range:** {summary.get('multiplier_range', 'N/A')}")
        
        with col2:
            st.subheader("Date Range Filter")
            min_date = historical_data['timestamp'].min().date()
            max_date = historical_data['timestamp'].max().date()
            
            start_date = st.date_input("Start Date", min_date, min_value=min_date, max_value=max_date)
            end_date = st.date_input("End Date", max_date, min_value=min_date, max_value=max_date)
        
        # Filter data
        filtered_data = st.session_state.data_manager.filter_data_by_date_range(historical_data, start_date, end_date)
        
        if not filtered_data.empty:
            # Historical statistics
            historical_stats = st.session_state.data_manager.calculate_statistics(filtered_data)
            create_stats_cards(historical_stats)
            
            # Historical trends
            create_trend_chart(filtered_data, "hour")
        else:
            st.warning("No data found for the selected date range.")
    else:
        st.info("No historical data available. Run some predictions to generate historical data.")

# Auto-refresh for real-time updates (optional)
if st.session_state.forecast_predictions and len(st.session_state.forecast_predictions) > 0:
    time.sleep(0.1)  # Small delay to prevent excessive refreshing