# Crash Simulation Dashboard

## Overview

This is a crash multiplier prediction dashboard built with Streamlit. The application generates crash predictions based on complex time-based algorithms and learns from real crash data feedback to improve accuracy over time. The system focuses on prediction generation and feedback collection rather than real-time simulation.

The application consists of a prediction engine that generates crash forecasts based on time-based rules, a feedback system for collecting real crash data, and an interactive dashboard for prediction management and analysis.

## System Architecture

### Frontend Architecture
- **Framework**: Streamlit web application with wide layout configuration
- **Visualization**: Plotly for interactive charts and real-time graphing
- **Components**: Modular dashboard components for different chart types and displays
- **Real-time Updates**: Session state management with callback-based updates

### Backend Architecture
- **Simulation Engine**: Core logic for crash multiplier generation with configurable rules
- **Data Manager**: File-based data persistence using CSV storage
- **Threading**: Background simulation execution with callback mechanisms
- **Configuration**: Centralized configuration system for all simulation parameters

### Data Storage
- **Primary Storage**: CSV files for historical session data
- **In-Memory**: Pandas DataFrames for real-time data processing
- **Session State**: Streamlit session state for application persistence

## Key Components

### 1. Simulation Engine (`simulation_engine.py`)
- **Purpose**: Core simulation logic for crash multiplier generation
- **Key Features**:
  - Time-based quality rules (hourly, quarterly, minute-based patterns)
  - Configurable crash time generation
  - Multiple multiplier categories with color coding
  - Callback system for real-time updates

### 2. Data Manager (`data_manager.py`)
- **Purpose**: Handle data persistence and retrieval operations
- **Key Features**:
  - CSV-based historical data storage
  - Time-based data filtering capabilities
  - Trend data aggregation by intervals
  - Error handling for data operations

### 3. Dashboard Components (`dashboard_components.py`)
- **Purpose**: Reusable UI components for the dashboard
- **Key Features**:
  - Large multiplier display with color coding
  - Various chart types (trend, distribution, phase analysis)
  - Real-time chart updates
  - Statistics cards and configuration panels

### 4. Main Application (`app.py`)
- **Purpose**: Main Streamlit application orchestrating all components
- **Key Features**:
  - Session state initialization
  - Real-time callback registration
  - UI layout and component integration

## Data Flow

1. **Simulation Initialization**: CrashSimulator instance created with default configuration
2. **Real-time Updates**: Simulation engine triggers callbacks with new data points
3. **Data Processing**: New data converted to DataFrame rows and appended to session state
4. **Visualization**: Dashboard components consume real-time and historical data
5. **Persistence**: DataManager handles CSV storage for session logs
6. **Analytics**: Various chart components process data for different analytical views

## External Dependencies

### Core Libraries
- **Streamlit**: Web application framework and UI components
- **Pandas**: Data manipulation and analysis
- **Plotly**: Interactive visualization and charting
- **NumPy**: Numerical computing support

### Standard Libraries
- **threading**: Background simulation execution
- **datetime/time**: Time-based operations and scheduling
- **csv**: Data persistence operations
- **random**: Simulation randomization
- **os**: File system operations

## Deployment Strategy

### Local Development
- Streamlit development server for local testing
- File-based CSV storage for data persistence
- Session-based state management

### Production Considerations
- The application currently uses local file storage
- Real-time updates rely on Streamlit's session state
- Threading model supports background simulation execution

## User Preferences

Preferred communication style: Simple, everyday language.

## Recent Changes

- July 02, 2025: Added multilingual support (English/French) with comprehensive language switching
- July 02, 2025: Restored configuration options with Config tab for simulation parameters
- July 02, 2025: Enhanced responsive design with mobile-friendly CSS styling
- July 02, 2025: Integrated feedback system directly into Predictions tab (removed separate Feedback tab)
- July 02, 2025: Added precise time display with HH:MM:SS format for better readability
- July 02, 2025: Implemented live phase analysis with manual override controls

## Key Features

### Multilingual Support
- Full English/French language switching via sidebar selector
- All interface text, buttons, labels, and messages translate dynamically
- Language preference stored in session state for consistency

### Configuration System
- Dedicated Config tab for adjusting simulation parameters
- Save/Reset functionality for configuration management
- Real-time parameter updates to the simulation engine

### Responsive Design
- Mobile-friendly layout with adaptive padding and columns
- Monospace fonts for time displays ensuring precise readability
- CSS media queries for optimal viewing on all screen sizes

### Phase Analysis
- Live current phase detection (hour, quarter, minute patterns)
- Manual override controls for market condition adjustments
- Real-time time tracking with seconds precision

## Changelog

- July 02, 2025: Initial setup with multilingual and configuration features