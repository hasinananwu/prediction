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
    create_5min_forecast_display, create_real_result_input
)
from data_manager import DataManager

# Page configuration
st.set_page_config(
    page_title="Crash Simulation Dashboard",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'simulator' not in st.session_state:
    st.session_state.simulator = CrashSimulator()
    st.session_state.data_manager = DataManager()
    st.session_state.real_time_data = pd.DataFrame()
    st.session_state.update_counter = 0
    st.session_state.forecast_predictions = []

def simulation_callback(data):
    """Callback function for simulation updates"""
    try:
        # Check if session state exists (for threading compatibility)
        if hasattr(st, 'session_state') and hasattr(st.session_state, 'real_time_data'):
            # Convert to DataFrame row and append
            new_row = pd.DataFrame([data])
            if st.session_state.real_time_data.empty:
                st.session_state.real_time_data = new_row
            else:
                st.session_state.real_time_data = pd.concat([st.session_state.real_time_data, new_row], ignore_index=True)
            
            # Trigger rerun for real-time updates
            st.session_state.update_counter += 1
    except Exception as e:
        # Ignore threading context errors - this is expected in Streamlit
        pass

# Register callback
if not st.session_state.simulator.callbacks:
    st.session_state.simulator.add_callback(simulation_callback)

# Main title
st.title("🎯 Crash Simulation Dashboard")
st.markdown("Real-time crash multiplier simulation with advanced analytics")

# Sidebar - Prediction Controls
with st.sidebar:
    st.header("🎯 Crash Predictor")
    st.info("Generate predictions from launch time and provide real crash data feedback to improve accuracy.")
    
    # Quick prediction generation
    st.markdown("---")
    st.markdown("**Quick Actions:**")
    
    if st.button("🔮 Generate Forecast", type="primary"):
        try:
            st.session_state.forecast_predictions = st.session_state.simulator.generate_5min_forecast()
            st.success("Forecast generated!")
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")
    
    if st.session_state.forecast_predictions:
        st.metric("Active Predictions", len(st.session_state.forecast_predictions))
        if st.button("🗑️ Clear Forecast"):
            st.session_state.forecast_predictions = []
            st.rerun()
    
    # Configuration section
    st.markdown("---")
    if st.checkbox("⚙️ Configuration", key="config_checkbox"):
        new_config = create_configuration_panel(CONFIG)
        if st.button("Apply Configuration"):
            st.session_state.simulator.update_config(new_config)
            st.success("Configuration updated!")
            st.rerun()



# Dashboard welcome message
st.markdown("### Welcome to the Crash Predictor")
st.markdown("Generate crash multiplier predictions and provide feedback to improve accuracy over time.")

# Tabs for different views
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📊 Real-time", "📅 Predictions", "📝 Feedback", "📈 Trends", "📋 Statistics", "📂 Historical"])

with tab1:
    st.header("Dashboard Overview")
    
    # Instructions
    st.markdown("""
    ### How to Use the Crash Predictor
    
    1. **Generate Predictions** - Use the "Predictions" tab or sidebar button to create 5-minute forecasts
    2. **Provide Feedback** - Enter real crash data in the "Feedback" tab to improve predictions
    3. **Analyze Results** - View trends and statistics to understand prediction accuracy
    """)
    
    # Show current status
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.session_state.forecast_predictions:
            st.metric("Active Predictions", len(st.session_state.forecast_predictions))
        else:
            st.metric("Active Predictions", "0")
    
    with col2:
        feedback_count = len(st.session_state.real_time_data[
            st.session_state.real_time_data['phase'] == 'real_result'
        ]) if not st.session_state.real_time_data.empty else 0
        st.metric("Feedback Entries", feedback_count)
    
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
            st.info("No feedback data yet. Start by generating predictions and providing feedback.")
    else:
        st.info("Get started by generating your first predictions in the Predictions tab.")

with tab2:
    st.header("5-Minute Predictions")
    
    # Generate forecast button
    if st.button("🔮 Generate 5-Minute Forecast", type="primary"):
        try:
            st.session_state.forecast_predictions = st.session_state.simulator.generate_5min_forecast()
            st.success("Forecast generated successfully!")
            st.rerun()
        except Exception as e:
            st.error(f"Error generating forecast: {e}")
    
    # Display current forecast
    if st.session_state.forecast_predictions:
        create_5min_forecast_display(st.session_state.forecast_predictions)
        
        # Clear forecast button
        if st.button("🗑️ Clear Forecast"):
            st.session_state.forecast_predictions = []
            st.rerun()
    else:
        st.info("Click 'Generate 5-Minute Forecast' to see predictions based on your simulation algorithm.")

with tab3:
    st.header("Real Result Feedback")
    
    # Real result input form
    result_input = create_real_result_input()
    
    if result_input:
        try:
            real_multiplier = result_input['multiplier']
            crash_time = None
            
            if result_input['include_crash_time'] and result_input['crash_time']:
                # Combine today's date with the crash time
                today = datetime.now().date()
                crash_time = datetime.combine(today, result_input['crash_time'])
            
            # Apply the real result to improve predictions
            feedback_result = st.session_state.simulator.apply_real_result(real_multiplier, crash_time)
            
            st.success(f"Real result recorded: {real_multiplier:.2f}x")
            
            # Display feedback analysis
            st.subheader("Feedback Analysis")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("Multiplier Recorded", f"{real_multiplier:.2f}x")
                if crash_time:
                    st.metric("Crash Time", crash_time.strftime('%H:%M:%S'))
            
            with col2:
                # Get multiplier category
                category = st.session_state.simulator.get_multiplier_color_category(real_multiplier)
                st.metric("Category", category.title())
                
                # Calculate if this improves learning
                st.info("This feedback will improve future predictions by updating the simulation's learning algorithms.")
            
            # Show how this compares to recent predictions
            if st.session_state.forecast_predictions:
                st.subheader("Comparison with Recent Predictions")
                
                recent_pred_df = pd.DataFrame(st.session_state.forecast_predictions)
                if not recent_pred_df.empty:
                    avg_prediction = recent_pred_df['predicted_multiplier'].mean()
                    
                    difference = real_multiplier - avg_prediction
                    if abs(difference) < 0.5:
                        st.success(f"Close prediction! Difference: {difference:+.2f}x")
                    elif difference > 0:
                        st.warning(f"Real result higher than predicted: {difference:+.2f}x")
                    else:
                        st.warning(f"Real result lower than predicted: {difference:+.2f}x")
            
        except Exception as e:
            st.error(f"Error processing real result: {e}")
    
    # Display recent feedback history
    st.subheader("Recent Feedback History")
    
    # Filter real results from session data
    if not st.session_state.real_time_data.empty:
        real_results = st.session_state.real_time_data[
            st.session_state.real_time_data['phase'] == 'real_result'
        ].copy()
        
        if not real_results.empty:
            # Format display
            real_results['timestamp_display'] = pd.to_datetime(real_results['timestamp']).dt.strftime('%H:%M:%S')
            display_cols = ['timestamp_display', 'multiplier', 'crash_time']
            available_cols = [col for col in display_cols if col in real_results.columns]
            
            st.dataframe(
                real_results[available_cols].tail(10).sort_values('timestamp_display', ascending=False),
                use_container_width=True
            )
        else:
            st.info("No real results entered yet. Use the form above to provide feedback.")
    else:
        st.info("No feedback data available yet.")

with tab4:
    st.header("Trend Analysis")
    
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
        st.info("No trend data available")

with tab3:
    st.header("Session Statistics")
    
    # Statistics for current session
    if not st.session_state.real_time_data.empty:
        stats = st.session_state.data_manager.calculate_statistics(st.session_state.real_time_data)
        
        # Display comprehensive stats
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.subheader("Basic Statistics")
            st.metric("Total Rounds", stats.get('total_rounds', 0))
            st.metric("Average Multiplier", f"{stats.get('avg_multiplier', 0):.2f}x")
            st.metric("Median Multiplier", f"{stats.get('median_multiplier', 0):.2f}x")
            st.metric("Standard Deviation", f"{stats.get('std_multiplier', 0):.2f}")
        
        with col2:
            st.subheader("Range Statistics")
            st.metric("Minimum Multiplier", f"{stats.get('min_multiplier', 0):.2f}x")
            st.metric("Maximum Multiplier", f"{stats.get('max_multiplier', 0):.2f}x")
            if 'avg_duration' in stats:
                st.metric("Average Duration", f"{stats.get('avg_duration', 0):.1f}s")
        
        with col3:
            st.subheader("Category Breakdown")
            st.metric("Low Multipliers (<2x)", f"{stats.get('low_mult_count', 0)} ({stats.get('low_mult_pct', 0):.1f}%)")
            st.metric("Medium Multipliers (2-10x)", f"{stats.get('med_mult_count', 0)} ({stats.get('med_mult_pct', 0):.1f}%)")
            st.metric("High Multipliers (>10x)", f"{stats.get('high_mult_count', 0)} ({stats.get('high_mult_pct', 0):.1f}%)")
        
        # Export current session data
        st.markdown("---")
        if st.button("📥 Export Current Session Data"):
            filename = st.session_state.simulator.export_session_data()
            if filename:
                st.success(f"Data exported to: {filename}")
                
                # Provide download link
                with open(filename, 'rb') as f:
                    st.download_button(
                        label="Download Exported File",
                        data=f.read(),
                        file_name=filename,
                        mime='text/csv'
                    )
    else:
        st.info("No session data available. Start a simulation to generate statistics.")

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
            st.write(f"**Total Records:** {summary['total_records']}")
            st.write(f"**Date Range:** {summary['date_range']}")
            st.write(f"**Multiplier Range:** {summary['multiplier_range']}")
        
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
            
            # Recent performance comparison
            st.subheader("Recent vs Historical Performance")
            recent_perf = st.session_state.data_manager.get_recent_performance(filtered_data)
            
            if recent_perf and historical_stats:
                comparison_data = {
                    'Metric': ['Average Multiplier', 'Low Mult %', 'High Mult %'],
                    'Recent (Last 100)': [
                        f"{recent_perf.get('avg_multiplier', 0):.2f}x",
                        f"{recent_perf.get('low_mult_pct', 0):.1f}%",
                        f"{recent_perf.get('high_mult_pct', 0):.1f}%"
                    ],
                    'Historical Average': [
                        f"{historical_stats.get('avg_multiplier', 0):.2f}x",
                        f"{historical_stats.get('low_mult_pct', 0):.1f}%",
                        f"{historical_stats.get('high_mult_pct', 0):.1f}%"
                    ]
                }
                st.dataframe(pd.DataFrame(comparison_data), use_container_width=True)
        
        # Data export
        st.markdown("---")
        if st.button("📥 Export Historical Data"):
            filename = st.session_state.data_manager.export_data(filtered_data)
            if filename:
                st.success(f"Historical data exported to: {filename}")
                
                with open(filename, 'rb') as f:
                    st.download_button(
                        label="Download Historical Data",
                        data=f.read(),
                        file_name=filename,
                        mime='text/csv'
                    )
    else:
        st.info("No historical data found. Run some simulations to generate historical data.")

with tab5:
    st.header("Advanced Analysis")
    
    # Choose data source
    analysis_source = st.radio("Analysis Data Source", ["Current Session", "Historical Data"], horizontal=True, key="analysis_source")
    
    if analysis_source == "Current Session":
        analysis_data = st.session_state.real_time_data
    else:
        analysis_data = st.session_state.data_manager.load_historical_data()
    
    if not analysis_data.empty:
        # Performance metrics over time
        st.subheader("Performance Metrics Over Time")
        
        # Create rolling averages
        if len(analysis_data) >= 10:
            analysis_data_copy = analysis_data.copy()
            analysis_data_copy['rolling_avg'] = analysis_data_copy['multiplier'].rolling(window=10).mean()
            analysis_data_copy['rolling_std'] = analysis_data_copy['multiplier'].rolling(window=10).std()
            
            fig = go.Figure()
            
            # Add original multipliers
            fig.add_trace(go.Scatter(
                x=analysis_data_copy.index,
                y=analysis_data_copy['multiplier'],
                mode='markers',
                name='Multipliers',
                marker=dict(size=4, opacity=0.6)
            ))
            
            # Add rolling average
            fig.add_trace(go.Scatter(
                x=analysis_data_copy.index,
                y=analysis_data_copy['rolling_avg'],
                mode='lines',
                name='Rolling Average (10)',
                line=dict(color='red', width=2)
            ))
            
            fig.update_layout(
                title="Multiplier Performance with Rolling Average",
                xaxis_title="Round",
                yaxis_title="Multiplier",
                height=400
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        # Phase transition analysis
        if 'phase' in analysis_data.columns:
            st.subheader("Phase Transition Analysis")
            
            # Calculate phase transitions
            phases = analysis_data['phase'].tolist()
            transitions = {}
            
            for i in range(len(phases) - 1):
                current_phase = phases[i]
                next_phase = phases[i + 1]
                transition = f"{current_phase} → {next_phase}"
                transitions[transition] = transitions.get(transition, 0) + 1
            
            if transitions:
                transition_df = pd.DataFrame(list(transitions.items()), columns=['Transition', 'Count'])
                transition_df = transition_df.sort_values('Count', ascending=False)
                
                st.dataframe(transition_df, use_container_width=True)
        
        # Outlier detection
        st.subheader("Outlier Detection")
        
        multipliers = analysis_data['multiplier']
        q1 = multipliers.quantile(0.25)
        q3 = multipliers.quantile(0.75)
        iqr = q3 - q1
        
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        
        outliers = analysis_data[(multipliers < lower_bound) | (multipliers > upper_bound)]
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Total Outliers", len(outliers))
            st.metric("Outlier Percentage", f"{(len(outliers) / len(analysis_data)) * 100:.2f}%")
        
        with col2:
            if not outliers.empty:
                st.write("**Outlier Summary:**")
                st.write(f"Min Outlier: {outliers['multiplier'].min():.2f}x")
                st.write(f"Max Outlier: {outliers['multiplier'].max():.2f}x")
                st.write(f"Avg Outlier: {outliers['multiplier'].mean():.2f}x")
        
        # Show outlier details
        if not outliers.empty and st.checkbox("Show Outlier Details"):
            outlier_display = outliers[['timestamp', 'round', 'multiplier', 'phase']].copy()
            if 'timestamp' in outlier_display.columns:
                outlier_display['timestamp'] = pd.to_datetime(outlier_display['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
            st.dataframe(outlier_display, use_container_width=True)
    else:
        st.info("No data available for analysis")

# Footer
st.markdown("---")
st.markdown("**Crash Simulation Dashboard** | Real-time multiplier simulation with advanced analytics")
