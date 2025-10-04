import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import time
import random

def calculate_carbon_grades(rougher_air, jameson_air, luproset, feed_carbon):
    """Calculate concentrate and tailings carbon grades based on rougher air, jameson air and luproset"""
    
    # Base concentrate carbon grade
    base_conc_grade = 40.0  # Base concentrate grade
    
    # Rougher air rate effect: higher air rate DECREASES grade (linear relationship)
    rougher_air_grade_effect = -rougher_air * 0.012  # Decreases grade as air rate increases
    
    # Jameson air rate effect: same relationship as rougher air but half the effect
    jameson_air_grade_effect = -jameson_air * 0.006  # Half the effect of rougher air
    
    # Luproset effect: higher luproset INCREASES grade by depressing gangue
    luproset_grade_effect = luproset * 0.08
    
    # Calculate concentrate grade
    concentrate_carbon = base_conc_grade + rougher_air_grade_effect + jameson_air_grade_effect + luproset_grade_effect
    concentrate_carbon = max(20.0, min(60.0, concentrate_carbon))  # Max 60% as specified
    
    # Tailings carbon calculation
    # Higher luproset = higher tailings carbon (carbon depressed, stays in tailings)
    # Higher air rate = lower tailings carbon (more carbon floated)
    base_tail_grade = feed_carbon * 0.5  # Base case
    
    # Luproset INCREASES tailings carbon (depresses carbon)
    luproset_tail_effect = luproset * 0.07
    
    # Higher rougher air rate DECREASES tailings carbon (more recovery)
    rougher_air_tail_effect = -rougher_air * 0.005
    
    # Higher jameson air rate DECREASES tailings carbon (more recovery) - half effect
    jameson_air_tail_effect = -jameson_air * 0.0025
    
    tailings_carbon = base_tail_grade + luproset_tail_effect + rougher_air_tail_effect + jameson_air_tail_effect
    tailings_carbon = max(0.2, min(feed_carbon * 1, tailings_carbon))
    
    return concentrate_carbon, tailings_carbon

def calculate_mass_balance(feed_carbon, concentrate_carbon, tailings_carbon, feed_tonnage=260):
    """Calculate mass balance for reverse flotation"""
    try:
        # Mass balance: Feed = Concentrate + Tailings
        concentrate_mass = feed_tonnage * (feed_carbon - tailings_carbon) / (concentrate_carbon - tailings_carbon)
        tailings_mass = feed_tonnage - concentrate_mass
        
        # Calculate carbon recovery to concentrate
        carbon_recovery = (concentrate_mass * concentrate_carbon) / (feed_tonnage * feed_carbon) * 100
        
        # Ensure physical constraints
        concentrate_mass = max(0, min(feed_tonnage * 0.5, concentrate_mass))  # Max 50% to concentrate
        tailings_mass = feed_tonnage - concentrate_mass
        carbon_recovery = max(0, min(100, carbon_recovery))
        
        return concentrate_mass, tailings_mass, carbon_recovery
    except:
        return 10, 90, 50  # Default values if calculation fails

def calculate_zn_loss(carbon_recovery):
    """Calculate Zn loss based on carbon recovery (0.5% to 4% range)"""
    # Linear relationship: as carbon recovery increases, Zn loss increases
    # Recovery range: 10-55%, Zn loss range: 0.5-4%
    min_recovery, max_recovery = 10, 55
    min_zn_loss, max_zn_loss = 0.1, 4.0
    
    # Normalize recovery to 0-1 range
    normalized_recovery = (carbon_recovery - min_recovery) / (max_recovery - min_recovery)
    normalized_recovery = max(0, min(1, normalized_recovery))  # Clamp to 0-1
    
    # Calculate Zn loss
    zn_loss = min_zn_loss + (normalized_recovery * (max_zn_loss - min_zn_loss))
    
    return zn_loss

def calculate_performance(rougher_air, jameson_air, luproset, feed_carbon):
    """Calculate flotation performance from rougher air, jameson air and luproset"""
    
    # Calculate concentrate and tailings carbon grades
    concentrate_carbon, tailings_carbon = calculate_carbon_grades(rougher_air, jameson_air, luproset, feed_carbon)
    
    # Calculate mass balance
    conc_mass, tail_mass, carbon_recovery = calculate_mass_balance(
        feed_carbon, concentrate_carbon, tailings_carbon
    )
    
    # Calculate overall recovery based on air rates and luproset
    # Higher rougher air rate = HIGHER recovery (linear relationship)
    rougher_air_recovery_effect = rougher_air * 0.045  # Linear increase with air rate
    
    # Higher jameson air rate = HIGHER recovery (linear relationship) - half effect
    jameson_air_recovery_effect = jameson_air * 0.0225  # Half the effect of rougher air
    
    # Higher luproset REDUCES recovery (carbon depressed to tailings)
    luproset_recovery_effect = -luproset * 0.015  # Reduces recovery
    
    base_recovery = 0.0  # Base recovery
    total_recovery = base_recovery + rougher_air_recovery_effect + jameson_air_recovery_effect + luproset_recovery_effect
    total_recovery = max(10, min(55, total_recovery))
    
    # Calculate Zn loss
    zn_loss = calculate_zn_loss(total_recovery)
    
    return total_recovery, concentrate_carbon, tailings_carbon, conc_mass, tail_mass, carbon_recovery, zn_loss

def generate_random_feed_carbon(current_value):
    """Generate a realistic random feed carbon value with gradual changes"""
    # Generate change within ±0.5% of current value
    variation = random.uniform(-1,1)
    new_value = current_value + variation
    # Keep within realistic bounds
    return max(3.0, min(6.0, new_value))

# Initialize session state
if 'dynamic_mode' not in st.session_state:
    st.session_state.dynamic_mode = False
if 'last_update_time' not in st.session_state:
    st.session_state.last_update_time = time.time()
if 'dynamic_feed_carbon' not in st.session_state:
    st.session_state.dynamic_feed_carbon = 4.5
if 'update_counter' not in st.session_state:
    st.session_state.update_counter = 0

# Streamlit App
st.set_page_config(
    page_title="Carbon Reverse Flotation Simulator",
    page_icon="⚫",
    layout="wide"
)

st.title("⚫ Pre Flotation Simulator - Dynamic Training Mode")
st.markdown("Parameters - Rougher Air, Jameson Air & Luproset")

# Dynamic mode controls
col1, col2, col3 = st.columns([2, 2, 3])

with col1:
    if st.button("🚀 Start Dynamic Mode", type="primary"):
        st.session_state.dynamic_mode = True
        st.session_state.last_update_time = time.time()
        st.session_state.update_counter = 0
        st.rerun()

with col2:
    if st.button("⏹️ Stop Dynamic Mode", type="secondary"):
        st.session_state.dynamic_mode = False
        st.rerun()

with col3:
    if st.session_state.dynamic_mode:
        current_time = time.time()
        time_since_last_update = current_time - st.session_state.last_update_time
        
        # Update every 60 seconds (1 minute)
        if time_since_last_update >= 30:
            st.session_state.dynamic_feed_carbon = generate_random_feed_carbon(st.session_state.dynamic_feed_carbon)
            st.session_state.last_update_time = current_time
            st.session_state.update_counter += 1
            st.rerun()
        
        # Show countdown
        time_remaining = 30 - time_since_last_update
        st.markdown(f"**🔄 Dynamic Mode Active** | Next update in: {time_remaining:.0f}s | Update #{st.session_state.update_counter}")
    else:
        st.markdown("**⏸️ Dynamic Mode Inactive**")

# Sidebar controls
st.sidebar.header("Process Parameters")

# Dynamic mode notification
if st.session_state.dynamic_mode:
    st.sidebar.warning("🔄 Dynamic Mode: Feed carbon changes automatically every minute!")

# Initialize parameter session state if not exists
if 'rougher_air_setpoint' not in st.session_state:
    st.session_state.rougher_air_setpoint = 0
if 'jameson_air_setpoint' not in st.session_state:
    st.session_state.jameson_air_setpoint = 0
if 'luproset_setpoint' not in st.session_state:
    st.session_state.luproset_setpoint = 80

st.sidebar.markdown("**Enter New Setpoints:**")

# Input boxes for setpoints
new_rougher_air = st.sidebar.number_input(
    "Rougher Air (m3/hr)",
    min_value=0, max_value=1000, 
    value=st.session_state.rougher_air_setpoint,
    step=10,
    key="rougher_air_input",
    help="Rougher air rate - HIGHER increases recovery but decreases grade"
)

new_jameson_air = st.sidebar.number_input(
    "Jameson Air (m3/hr)",
    min_value=0, max_value=600, 
    value=st.session_state.jameson_air_setpoint,
    step=5,
    key="jameson_air_input",
    help="Jameson air rate - Same effect as rougher air but half the magnitude"
)

new_luproset = st.sidebar.number_input(
    "Luproset Dosage (g/t)",
    min_value=0, max_value=100, 
    value=st.session_state.luproset_setpoint,
    step=1,
    key="luproset_input",
    help="Carbon depressant - HIGHER reduces recovery but increases grade"
)

# Auto-apply changes when values change (on Enter key press)
if (new_rougher_air != st.session_state.rougher_air_setpoint or 
    new_jameson_air != st.session_state.jameson_air_setpoint or 
    new_luproset != st.session_state.luproset_setpoint):
    st.session_state.rougher_air_setpoint = new_rougher_air
    st.session_state.jameson_air_setpoint = new_jameson_air
    st.session_state.luproset_setpoint = new_luproset

# Use the stored setpoints for calculations
rougher_air = st.session_state.rougher_air_setpoint
jameson_air = st.session_state.jameson_air_setpoint
luproset = st.session_state.luproset_setpoint

# Show current setpoints
st.sidebar.markdown("---")
st.sidebar.markdown("**Current Setpoints:**")
st.sidebar.markdown(f"• Rougher Air: **{rougher_air} m³/hr**")
st.sidebar.markdown(f"• Jameson Air: **{jameson_air} m³/hr**")
st.sidebar.markdown(f"• Luproset: **{luproset} g/t**")

# Feed carbon - either manual or dynamic
if st.session_state.dynamic_mode:
    feed_carbon = st.session_state.dynamic_feed_carbon
    st.sidebar.markdown(f"**Feed Carbon (Dynamic): {feed_carbon:.2f}%**")
    st.sidebar.markdown("*Auto-updating every minute*")
else:
    feed_carbon = st.sidebar.slider(
        "Feed Carbon (%)",
        min_value=3.0, max_value=6.0, value=4.5, step=0.1,
        help="Carbon content in feed stream"
    )

# Calculate performance
recovery, concentrate_carbon, tailings_carbon, conc_mass, tail_mass, mass_balance_recovery, zn_loss = calculate_performance(
    rougher_air, jameson_air, luproset, feed_carbon
)

# Main dashboard
st.subheader("Process Performance")
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric(
        "Carbon Recovery", 
        f"{recovery:.1f}%"
    )

with col2:
    st.metric(
        "Concentrate Carbon", 
        f"{concentrate_carbon:.1f}%"
    )

with col3:
    # Custom delta logic for tailings carbon - red if outside 2.8-3.0% range
    if 2.8 <= tailings_carbon <= 3.0:
        tail_delta = None  # No arrow if in target range
        tail_delta_color = "normal"
    else:
        # Always show positive delta value but make it red
        tail_delta = f"{abs(tailings_carbon - 2.9):.2f}%"
        tail_delta_color = "inverse"  # Red for any deviation from target range
    
    st.metric(
        "Tailings Carbon", 
        f"{tailings_carbon:.2f}%",
        delta=tail_delta,
        delta_color=tail_delta_color
    )

with col4:
    st.metric(
        "Zn Loss", 
        f"{zn_loss:.2f}%",
        
    )

# Dynamic mode guidance
if st.session_state.dynamic_mode:
    st.info("")

# Operating guidance
st.subheader("Operating Guidance")

col1, col2 = st.columns(2)

with col1:
    st.markdown("**Parameter Effects:**")
    st.markdown("- **Higher Rougher Air** = Higher recovery, Lower grade, Higher Zn loss")
    st.markdown("- **Higher Jameson Air** = Higher recovery, Lower grade, Higher Zn loss")
    st.markdown("- **Higher Luproset** = Lower recovery, Higher grade, Lower Zn loss")   

with col2:
    st.markdown("")
    if recovery < 30:
        st.markdown("")
        st.markdown("")
        st.markdown("")
        st.markdown("")
    
    
    if tailings_carbon > 3.5:
        st.markdown("")
        st.markdown("")
        st.markdown("")
    

# Reset button
if st.button("Reset All", type="secondary"):
    st.session_state.dynamic_mode = False
    st.session_state.dynamic_feed_carbon = 4.5
    st.session_state.update_counter = 0
    st.rerun()

# Auto-refresh for dynamic mode
if st.session_state.dynamic_mode:
    time.sleep(1)  # Small delay to prevent excessive refreshing
    st.rerun()