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

def get_multiplier_ball(multiplier):
    """Return colored ball emoji based on multiplier value"""
    if multiplier < 1.51:
        return "🔴"  # Red
    elif 1.51 <= multiplier < 2.00:
        return "🟠"  # Orange
    elif 2.00 <= multiplier < 3.00:
        return "🟢"  # Green
    elif 3.00 <= multiplier < 4.00:
        return "🟡"  # Yellow
    elif 4.00 <= multiplier < 10.00:
        return "🟣"  # Purple
    else:  # >= 10.00
        return "🔵"  # Blue

def get_multiplier_color(multiplier):
    """Return background color based on multiplier value"""
    if multiplier < 1.51:
        return "#FF6B6B"  # Red
    elif 1.51 <= multiplier < 2.00:
        return "#FF8E53"  # Orange
    elif 2.00 <= multiplier < 3.00:
        return "#51CF66"  # Green
    elif 3.00 <= multiplier < 4.00:
        return "#FFD43B"  # Yellow
    elif 4.00 <= multiplier < 10.00:
        return "#9775FA"  # Purple
    else:  # >= 10.00
        return "#74C0FC"  # Blue

def create_phase_indicator():
    """Create current phase indicator and editor"""
    import streamlit as st
    from datetime import datetime
    
    current_time = datetime.now()
    hour = current_time.hour
    minute = current_time.minute
    second = current_time.second
    
    # Determine current phase
    if hour in [9, 10, 14, 15, 20, 21]:
        phase = "Peak Hours"
        phase_color = "#ff4b4b"
    elif hour in [11, 12, 13, 16, 17, 18, 19]:
        phase = "Medium Hours"
        phase_color = "#ff8c00"
    else:
        phase = "Off-Peak Hours"
        phase_color = "#1f77b4"
    
    # Quarter hour phase
    quarter = minute // 15
    if quarter == 0:
        quarter_phase = "First Quarter (0-14 min)"
    elif quarter == 3:
        quarter_phase = "Last Quarter (45-59 min)"
    else:
        quarter_phase = "Middle Quarter (15-44 min)"
    
    # Minute special patterns
    minute_pattern = "Regular"
    if minute % 10 == 9:
        if second < 30:
            minute_pattern = "Special 9 Early (Catastrophic Risk)"
        else:
            minute_pattern = "Special 9 Late"
    elif minute % 10 == 1:
        if second < 30:
            minute_pattern = "Special 1 Early"
        else:
            minute_pattern = "Special 1 Late"
    elif minute % 7 == 0:
        minute_pattern = "Multiple of 7 (Catastrophic Risk)"
    elif minute % 5 == 0:
        minute_pattern = "Multiple of 5"
    elif minute % 3 == 0:
        minute_pattern = "Multiple of 3"
    
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, {phase_color}22, {phase_color}11); padding: 15px; border-radius: 10px; border-left: 4px solid {phase_color}; margin-bottom: 20px;">
        <h3 style="margin: 0 0 10px 0; color: {phase_color};">📍 Current Phase Analysis</h3>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px;">
            <div><strong>Time:</strong> {current_time.strftime('%H:%M:%S')}</div>
            <div><strong>Hour Phase:</strong> {phase}</div>
            <div><strong>Quarter Phase:</strong> {quarter_phase}</div>
            <div><strong>Minute Pattern:</strong> {minute_pattern}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    return {
        'current_time': current_time,
        'phase': phase,
        'quarter_phase': quarter_phase,
        'minute_pattern': minute_pattern
    }

def create_5min_forecast_display(predictions):
    """Create enhanced 5-minute forecast display with editable results"""
    import streamlit as st
    
    if not predictions:
        st.info("No predictions available. Generate a forecast to see predictions.")
        return
    
    st.subheader("📅 5-Minute Forecast")
    
    # Phase indicator
    phase_info = create_phase_indicator()
    
    # Trend adjustment controls
    st.markdown("**Trend Adjustment:**")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        trend_adjustment = st.selectbox(
            "Current Trend",
            ["Auto", "Force Higher", "Force Lower", "Force Mixed"],
            help="Adjust the prediction trend for upcoming rounds"
        )
    
    with col2:
        strength = st.slider("Adjustment Strength", 0.1, 2.0, 1.0, 0.1)
    
    with col3:
        # Manual phase override
        manual_phase = st.selectbox(
            "Override Phase",
            ["Auto", "Peak Hours", "Medium Hours", "Off-Peak Hours"],
            help="Manually override the current phase detection"
        )
    
    with col4:
        if st.button("Apply Adjustments", type="primary"):
            # Apply the trend adjustment to the simulator
            if 'simulator' in st.session_state:
                st.session_state.simulator.set_trend_adjustment(trend_adjustment, strength)
                st.success("Adjustments applied to future predictions!")
            else:
                st.error("Simulator not available")
    
    st.markdown("---")
    
    # Create a DataFrame for display
    forecast_df = pd.DataFrame(predictions)
    
    # Group by minute for background coloring
    forecast_df['start_time_dt'] = pd.to_datetime(forecast_df['timestamp'])
    forecast_df['minute'] = forecast_df['start_time_dt'].dt.minute
    forecast_df['start_time_display'] = forecast_df['start_time_dt'].dt.strftime('%H:%M:%S')
    forecast_df['predicted_crash_time_display'] = pd.to_datetime(
        forecast_df['predicted_crash_time']).dt.strftime('%H:%M:%S')
    
    # Display predictions grouped by minute with editable results
    unique_minutes = forecast_df['minute'].unique()
    
    for i, minute in enumerate(unique_minutes):
        minute_data = forecast_df[forecast_df['minute'] == minute].copy()
        
        # Alternate background colors for different minutes
        bg_color = "#F8F9FA" if i % 2 == 0 else "#E9ECEF"
        
        st.markdown(f"""
        <div style="background-color: {bg_color}; padding: 15px; border-radius: 10px; margin: 10px 0;">
            <h4 style="margin: 0 0 10px 0;">Minute: {minute:02d}</h4>
        </div>
        """, unsafe_allow_html=True)
        
        # Display each prediction in this minute
        for _, row in minute_data.iterrows():
            col1, col2, col3, col4, col5, col6 = st.columns([2, 2, 2, 2, 2, 1.5])
            
            with col1:
                # Editable start time with seconds
                start_time_display = row['start_time'].strftime("%H:%M:%S")
                start_time_input = st.text_input(
                    "Start Time (HH:MM:SS)",
                    value=start_time_display,
                    key=f"start_time_{row['round']}",
                    help="Edit the start time (format: HH:MM:SS)"
                )
            
            with col2:
                # Editable predicted crash time with seconds
                predicted_time_display = row['predicted_crash_time'].strftime("%H:%M:%S")
                predicted_time_input = st.text_input(
                    "Predicted Time (HH:MM:SS)", 
                    value=predicted_time_display,
                    key=f"pred_time_{row['round']}",
                    help="Edit the predicted crash time (format: HH:MM:SS)"
                )
            
            with col3:
                # Editable predicted multiplier
                predicted_multiplier = st.number_input(
                    "Predicted Mult",
                    min_value=1.0,
                    max_value=100.0,
                    value=float(row['predicted_multiplier']),
                    step=0.01,
                    key=f"pred_mult_{row['round']}",
                    help="Edit the predicted multiplier"
                )
            
            with col4:
                # Editable real result input
                real_multiplier = st.number_input(
                    "Real Result",
                    min_value=1.0,
                    max_value=100.0,
                    value=1.0,
                    step=0.01,
                    key=f"real_mult_{row['round']}",
                    help="Enter the actual multiplier result"
                )
            
            with col5:
                # Display colored multiplier ball for visual reference
                ball = get_multiplier_ball(predicted_multiplier)
                color = get_multiplier_color(predicted_multiplier)
                st.markdown(f"""
                <div style="background-color: {color}; padding: 4px; border-radius: 15px; text-align: center; color: white; font-weight: bold; font-size: 0.8em; margin-top: 25px;">
                    {ball} {predicted_multiplier:.2f}x
                </div>
                """, unsafe_allow_html=True)
            
            with col6:
                if st.button("✓ Submit", key=f"submit_{row['round']}", type="secondary"):
                    # Apply the real result with all editable fields
                    st.session_state[f"submitted_{row['round']}"] = {
                        'real_multiplier': real_multiplier,
                        'predicted_multiplier': predicted_multiplier,
                        'start_time': start_time_input,
                        'predicted_time': predicted_time_input,
                        'timestamp': row['timestamp']
                    }
                    st.success(f"Result submitted: {real_multiplier:.2f}x")
                    st.rerun()
        
        st.markdown("<br>", unsafe_allow_html=True)
    
    # Create forecast chart
    fig = go.Figure()
    
    # Add prediction line
    fig.add_trace(go.Scatter(
        x=forecast_df['round'],
        y=forecast_df['predicted_multiplier'],
        mode='lines+markers',
        name='Predicted Multipliers',
        line=dict(color='orange', width=3),
        marker=dict(size=10, color='orange')
    ))
    
    # Add submitted real results if any
    submitted_data = []
    for _, row in forecast_df.iterrows():
        if f"submitted_{row['round']}" in st.session_state:
            submitted = st.session_state[f"submitted_{row['round']}"]
            submitted_data.append({
                'round': row['round'],
                'real_multiplier': submitted['real_multiplier'],
                'predicted_multiplier': submitted['predicted_multiplier']
            })
    
    if submitted_data:
        submitted_df = pd.DataFrame(submitted_data)
        fig.add_trace(go.Scatter(
            x=submitted_df['round'],
            y=submitted_df['real_multiplier'],
            mode='markers',
            name='Real Results',
            marker=dict(size=12, color='red', symbol='x')
        ))
    
    # Add threshold lines
    fig.add_hline(y=2.0, line_dash="dash", line_color="green", annotation_text="2.0x")
    fig.add_hline(y=4.0, line_dash="dash", line_color="yellow", annotation_text="4.0x")
    fig.add_hline(y=10.0, line_dash="dash", line_color="cyan", annotation_text="10.0x")
    
    fig.update_layout(
        title="5-Minute Forecast vs Real Results",
        xaxis_title="Round",
        yaxis_title="Multiplier",
        height=400,
        showlegend=True
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Show accuracy summary if we have submitted results
    if submitted_data:
        st.subheader("Accuracy Summary")
        submitted_df = pd.DataFrame(submitted_data)
        submitted_df['error'] = abs(submitted_df['real_multiplier'] - submitted_df['predicted_multiplier'])
        submitted_df['accuracy'] = 100 - (submitted_df['error'] / submitted_df['real_multiplier'] * 100)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Average Error", f"{submitted_df['error'].mean():.2f}x")
        with col2:
            st.metric("Average Accuracy", f"{submitted_df['accuracy'].mean():.1f}%")
        with col3:
            st.metric("Results Submitted", len(submitted_data))
    
    return submitted_data

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
