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
    create_category_breakdown, create_configuration_panel
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

def simulation_callback(data):
    """Callback function for simulation updates"""
    # Convert to DataFrame row and append
    new_row = pd.DataFrame([data])
    if st.session_state.real_time_data.empty:
        st.session_state.real_time_data = new_row
    else:
        st.session_state.real_time_data = pd.concat([st.session_state.real_time_data, new_row], ignore_index=True)
    
    # Trigger rerun for real-time updates
    st.session_state.update_counter += 1

# Register callback
if not st.session_state.simulator.callbacks:
    st.session_state.simulator.add_callback(simulation_callback)

# Main title
st.title("🎯 Crash Simulation Dashboard")
st.markdown("Real-time crash multiplier simulation with advanced analytics")

# Sidebar controls
with st.sidebar:
    st.header("🎮 Simulation Controls")
    
    # Control buttons
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("▶️ Start", disabled=st.session_state.simulator.is_running):
            st.session_state.simulator.start_simulation()
            st.success("Simulation started!")
            st.rerun()
    
    with col2:
        if st.button("⏹️ Stop", disabled=not st.session_state.simulator.is_running):
            st.session_state.simulator.stop_simulation()
            st.success("Simulation stopped!")
            st.rerun()
    
    col3, col4 = st.columns(2)
    
    with col3:
        if st.button("⏸️ Pause", disabled=not st.session_state.simulator.is_running or st.session_state.simulator.is_paused):
            st.session_state.simulator.pause_simulation()
            st.info("Simulation paused!")
            st.rerun()
    
    with col4:
        if st.button("▶️ Resume", disabled=not st.session_state.simulator.is_paused):
            st.session_state.simulator.resume_simulation()
            st.success("Simulation resumed!")
            st.rerun()
    
    # Status indicators
    st.markdown("---")
    st.markdown("**Status:**")
    if st.session_state.simulator.is_running:
        if st.session_state.simulator.is_paused:
            st.warning("⏸️ Paused")
        else:
            st.success("▶️ Running")
    else:
        st.info("⏹️ Stopped")
    
    # Current round info
    if st.session_state.simulator.current_round > 0:
        st.metric("Current Round", st.session_state.simulator.current_round)
    
    # Configuration section
    st.markdown("---")
    if st.checkbox("⚙️ Configuration", key="config_checkbox"):
        new_config = create_configuration_panel(CONFIG)
        if st.button("Apply Configuration"):
            st.session_state.simulator.update_config(new_config)
            st.success("Configuration updated!")
            st.rerun()

# Main dashboard area
if st.session_state.simulator.is_running and not st.session_state.simulator.is_paused:
    # Auto-refresh for real-time updates
    time.sleep(0.5)
    st.rerun()

# Current multiplier display
if st.session_state.simulator.current_multiplier > 1.0:
    create_multiplier_display(
        st.session_state.simulator.current_multiplier,
        st.session_state.simulator.crash_time,
        st.session_state.simulator.round_start_time
    )

# Tabs for different views
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Real-time", "📈 Trends", "📋 Statistics", "📂 Historical", "⚙️ Analysis"])

with tab1:
    st.header("Real-time Simulation Data")
    
    # Real-time stats
    if not st.session_state.real_time_data.empty:
        current_stats = st.session_state.simulator.get_session_stats()
        create_stats_cards(current_stats)
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Real-time chart
            create_real_time_chart(st.session_state.real_time_data)
            
            # Recent rounds table
            st.subheader("Recent Rounds")
            if len(st.session_state.real_time_data) > 0:
                recent_data = st.session_state.real_time_data.tail(10).copy()
                recent_data['timestamp'] = pd.to_datetime(recent_data['timestamp']).dt.strftime('%H:%M:%S')
                recent_data['multiplier'] = recent_data['multiplier'].round(2)
                st.dataframe(recent_data[['timestamp', 'round', 'multiplier', 'phase']].sort_values('round', ascending=False), use_container_width=True)
        
        with col2:
            # Category breakdown
            create_category_breakdown(current_stats)
    else:
        st.info("Start the simulation to see real-time data")

with tab2:
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
