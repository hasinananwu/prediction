import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime, timedelta
import numpy as np

def create_multiplier_display(current_multiplier, crash_time=None, round_start_time=None):
    """Create large multiplier display with color coding"""
    color_map = {
        "grey": "#808080",
        "green": "#00FF00", 
        "purple": "#800080",
        "yellow": "#FFD700",
        "cyan": "#00FFFF"
    }
    
    from simulation_engine import CrashSimulator
    color_category = CrashSimulator.get_multiplier_color_category(current_multiplier)
    color = color_map.get(color_category, "#808080")
    
    # Calculate time remaining if crash time is available
    time_remaining = ""
    if crash_time and round_start_time:
        now = datetime.now()
        if isinstance(crash_time, str):
            crash_time = datetime.fromisoformat(crash_time)
        if isinstance(round_start_time, str):
            round_start_time = datetime.fromisoformat(round_start_time)
        
        remaining = (crash_time - now).total_seconds()
        if remaining > 0:
            time_remaining = f"Crash in: {remaining:.1f}s"
        else:
            time_remaining = "CRASHED!"
    
    st.markdown(f"""
    <div style="text-align: center; padding: 20px;">
        <h1 style="color: {color}; font-size: 4em; margin: 0;">
            {current_multiplier:.2f}x
        </h1>
        <p style="font-size: 1.2em; color: #666;">
            {time_remaining}
        </p>
    </div>
    """, unsafe_allow_html=True)

def create_trend_chart(data, trend_type="minute"):
    """Create trend chart for different time intervals"""
    if data.empty:
        st.info(f"No data available for {trend_type} trends")
        return
    
    fig = go.Figure()
    
    # Convert timestamp to datetime if it's a string
    if 'timestamp' in data.columns:
        data['timestamp'] = pd.to_datetime(data['timestamp'])
    
    # Create line chart
    fig.add_trace(go.Scatter(
        x=data['timestamp'],
        y=data['multiplier'],
        mode='lines+markers',
        name='Multiplier',
        line=dict(color='blue', width=2),
        marker=dict(size=6)
    ))
    
    # Add horizontal lines for multiplier categories
    fig.add_hline(y=2.0, line_dash="dash", line_color="green", annotation_text="2.0x")
    fig.add_hline(y=4.0, line_dash="dash", line_color="yellow", annotation_text="4.0x")
    fig.add_hline(y=10.0, line_dash="dash", line_color="cyan", annotation_text="10.0x")
    
    fig.update_layout(
        title=f"{trend_type.title()} Multiplier Trends",
        xaxis_title="Time",
        yaxis_title="Multiplier",
        hovermode='x unified',
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)

def create_distribution_chart(data):
    """Create multiplier distribution chart"""
    if data.empty:
        st.info("No data available for distribution chart")
        return
    
    # Create histogram
    fig = go.Figure()
    
    fig.add_trace(go.Histogram(
        x=data['multiplier'],
        nbinsx=20,
        name='Multiplier Distribution',
        marker_color='lightblue',
        opacity=0.7
    ))
    
    fig.update_layout(
        title="Multiplier Distribution",
        xaxis_title="Multiplier",
        yaxis_title="Frequency",
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)

def create_phase_analysis_chart(data):
    """Create phase analysis chart"""
    if data.empty or 'phase' not in data.columns:
        st.info("No phase data available")
        return
    
    # Count phases
    phase_counts = data['phase'].value_counts()
    
    fig = go.Figure(data=[
        go.Bar(x=phase_counts.index, y=phase_counts.values, 
               marker_color=['green', 'yellow', 'orange', 'red'][:len(phase_counts)])
    ])
    
    fig.update_layout(
        title="Phase Distribution",
        xaxis_title="Phase",
        yaxis_title="Count",
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)

def create_real_time_chart(data, max_points=50):
    """Create real-time updating chart"""
    if data.empty:
        return
    
    # Limit to last N points for performance
    recent_data = data.tail(max_points)
    
    fig = go.Figure()
    
    # Add multiplier line
    fig.add_trace(go.Scatter(
        x=list(range(len(recent_data))),
        y=recent_data['multiplier'],
        mode='lines+markers',
        name='Multiplier',
        line=dict(color='blue', width=2),
        marker=dict(size=4)
    ))
    
    # Color code markers based on multiplier value
    colors = []
    for mult in recent_data['multiplier']:
        if mult < 2.0:
            colors.append('grey')
        elif mult < 3.0:
            colors.append('green')
        elif mult < 4.0:
            colors.append('purple')
        elif mult < 10.0:
            colors.append('gold')
        else:
            colors.append('cyan')
    
    fig.update_traces(marker=dict(color=colors))
    
    fig.update_layout(
        title="Real-time Multiplier Feed",
        xaxis_title="Round",
        yaxis_title="Multiplier",
        height=300,
        showlegend=False
    )
    
    st.plotly_chart(fig, use_container_width=True, key="realtime_chart")

def create_stats_cards(stats):
    """Create statistics cards"""
    if not stats:
        return
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Rounds", stats.get('total_rounds', 0))
    
    with col2:
        st.metric("Average Multiplier", f"{stats.get('avg_multiplier', 0):.2f}x")
    
    with col3:
        st.metric("Min Multiplier", f"{stats.get('min_multiplier', 0):.2f}x")
    
    with col4:
        st.metric("Max Multiplier", f"{stats.get('max_multiplier', 0):.2f}x")

def create_category_breakdown(stats):
    """Create multiplier category breakdown"""
    if not stats:
        return
    
    categories = ['Low (<2x)', 'Medium (2-10x)', 'High (>10x)']
    values = [
        stats.get('low_mult_count', 0),
        stats.get('med_mult_count', 0),
        stats.get('high_mult_count', 0)
    ]
    
    fig = go.Figure(data=[
        go.Pie(
            labels=categories,
            values=values,
            hole=0.3,
            marker_colors=['lightgrey', 'lightgreen', 'lightcoral']
        )
    ])
    
    fig.update_layout(
        title="Multiplier Categories",
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)

def create_configuration_panel(current_config):
    """Create configuration panel for simulation parameters"""
    st.subheader("Simulation Configuration")
    
    with st.expander("Basic Settings"):
        pause_between_rounds = st.slider(
            "Pause Between Rounds (seconds)", 
            min_value=1, 
            max_value=60, 
            value=current_config.get('simulation', {}).get('pause_between_rounds_seconds', 10)
        )
        
        forecast_duration = st.slider(
            "Forecast Duration (minutes)", 
            min_value=1, 
            max_value=30, 
            value=current_config.get('simulation', {}).get('forecast_duration_minutes', 5)
        )
    
    with st.expander("Crash Time Settings"):
        low_mult_max = st.slider(
            "Low Multiplier Max Seconds", 
            min_value=1, 
            max_value=20, 
            value=current_config.get('crash_time_generation', {}).get('low_mult_max_seconds', 5)
        )
        
        med_mult_max = st.slider(
            "Medium Multiplier Max Seconds", 
            min_value=5, 
            max_value=60, 
            value=current_config.get('crash_time_generation', {}).get('med_mult_max_seconds', 20)
        )
        
        high_mult_max = st.slider(
            "High Multiplier Max Seconds", 
            min_value=30, 
            max_value=300, 
            value=current_config.get('crash_time_generation', {}).get('high_mult_max_seconds', 120)
        )
    
    with st.expander("Quality Generation"):
        good_phase_chance = st.slider(
            "Good Phase High Multiplier Chance", 
            min_value=0.0, 
            max_value=1.0, 
            value=current_config.get('multiplier_generation', {}).get('good_phase_high_mult_chance', 0.7),
            step=0.1
        )
        
        bad_phase_chance = st.slider(
            "Bad Phase Low Multiplier Chance", 
            min_value=0.0, 
            max_value=1.0, 
            value=current_config.get('multiplier_generation', {}).get('bad_phase_low_mult_chance', 0.7),
            step=0.1
        )
    
    # Return updated configuration
    return {
        'simulation': {
            'pause_between_rounds_seconds': pause_between_rounds,
            'forecast_duration_minutes': forecast_duration,
        },
        'crash_time_generation': {
            'low_mult_max_seconds': low_mult_max,
            'med_mult_max_seconds': med_mult_max,
            'high_mult_max_seconds': high_mult_max,
        },
        'multiplier_generation': {
            'good_phase_high_mult_chance': good_phase_chance,
            'bad_phase_low_mult_chance': bad_phase_chance,
        }
    }

def create_5min_forecast_display(predictions):
    """Create 5-minute forecast display"""
    if not predictions:
        st.info("No predictions available. Generate a forecast to see predictions.")
        return
    
    st.subheader("📅 5-Minute Forecast")
    
    # Create a DataFrame for display
    forecast_df = pd.DataFrame(predictions)
    
    # Format times for display
    forecast_df['start_time_display'] = pd.to_datetime(forecast_df['timestamp']).dt.strftime('%H:%M:%S')
    forecast_df['predicted_crash_time_display'] = pd.to_datetime(
        forecast_df['predicted_crash_time']).dt.strftime('%H:%M:%S')
    
    # Color code multipliers
    def get_multiplier_style(mult):
        if mult < 2.0:
            return "background-color: #808080; color: white;"
        elif mult < 3.0:
            return "background-color: #00FF00; color: black;"
        elif mult < 4.0:
            return "background-color: #800080; color: white;"
        elif mult < 10.0:
            return "background-color: #FFD700; color: black;"
        else:
            return "background-color: #00FFFF; color: black;"
    
    # Display forecast table
    display_df = forecast_df[['round', 'start_time_display', 'predicted_multiplier', 'predicted_crash_time_display']].copy()
    display_df.columns = ['Round', 'Start Time', 'Predicted Multiplier', 'Predicted Crash Time']
    display_df['Predicted Multiplier'] = display_df['Predicted Multiplier'].round(2)
    
    st.dataframe(display_df, use_container_width=True)
    
    # Create forecast chart
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=forecast_df['round'],
        y=forecast_df['predicted_multiplier'],
        mode='lines+markers',
        name='Predicted Multipliers',
        line=dict(color='orange', width=3),
        marker=dict(size=8, color='orange')
    ))
    
    # Add threshold lines
    fig.add_hline(y=2.0, line_dash="dash", line_color="green", annotation_text="2.0x")
    fig.add_hline(y=4.0, line_dash="dash", line_color="yellow", annotation_text="4.0x")
    fig.add_hline(y=10.0, line_dash="dash", line_color="cyan", annotation_text="10.0x")
    
    fig.update_layout(
        title="5-Minute Forecast Predictions",
        xaxis_title="Round",
        yaxis_title="Predicted Multiplier",
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)

def create_real_result_input():
    """Create real result input form"""
    st.subheader("📝 Enter Real Result")
    
    with st.form("real_result_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            real_multiplier = st.number_input(
                "Real Multiplier", 
                min_value=1.0, 
                max_value=100.0, 
                value=1.0, 
                step=0.01,
                format="%.2f"
            )
        
        with col2:
            crash_time = st.time_input(
                "Crash Time (optional)", 
                value=datetime.now().time()
            )
        
        include_crash_time = st.checkbox("Include crash time in feedback")
        
        submitted = st.form_submit_button("Submit Real Result", type="primary")
        
        if submitted:
            return {
                'multiplier': real_multiplier,
                'crash_time': crash_time if include_crash_time else None,
                'include_crash_time': include_crash_time
            }
    
    return None
