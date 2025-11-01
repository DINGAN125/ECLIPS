import random
import threading

# --- GLOBAL STATE VARIABLES ---
# Tracks the current anomaly type. Initialized to "CO2" to start the game.
CURRENT_ANOMALY = "CO2" 

# NEW GLOBAL VARIABLE: Stores the locked metric data once an anomaly is triggered.
# This prevents the value and status from changing until the anomaly is resolved.
LOCKED_ANOMALY_DATA = {}

# --- CONFIGURATION: METRIC RANGES ---
NOMINAL_RANGES = {
    "Cabin Pressure (kPa)": (98.6, 103.4, "kPa"),
    "O₂ Partial Pressure (kPa)": (19.5, 23.8, "kPa"),
    "CO₂ Concentration (%)": (0.00, 0.40, "%"),
    "Cabin Temperature (°C)": (21.0, 24.0, "°C"), # The nominal range used for base generation
    "Relative Humidity (%)": (40, 60, "%"),
    "Water Reserves (L)": (500, 1200, "L") 
}

# --- CONFIGURATION: ANOMALY DATASET ---
ANOMALY_DATASET = {
    "CO2": {
        "metric": "CO₂ Concentration (%)",
        "title": "CO₂ SCRUBBER INEFFICIENCY",
        "message": "Elevated CO₂ readings indicate the Carbon Dioxide Removal Assembly (CDRA) is not fully scrubbing the cabin atmosphere. Immediate crew action is required to prevent hypoxia.",
        "priority": "HIGH",
        # NOTE: For simple anomalies, constraints remain (min_anomaly_val, max_anomaly_val, status)
        "constraints": (0.45, 0.65, "CAUTION"), 
        "solutions": [
            {"id": 1, "text": "Activate Secondary CO₂ Scrubber (Corrective Action)", "is_correct": True},
            {"id": 2, "text": "Reroute Airflow to Water Processor (Deferral/Wrong)", "is_correct": False},
            {"id": 3, "text": "Disable Cabin Ventilation (Wrong Action)", "is_correct": False}
        ]
    },
    
    "PRESSURE": {
        "metric": "Cabin Pressure (kPa)",
        "title": "LOW CABIN PRESSURE WARNING",
        "message": "Cabin pressure is dropping below the minimum nominal threshold. This suggests a micro-meteoroid strike or seal failure. Pressurization must be restored immediately.",
        "priority": "CRITICAL",
        "constraints": (96.0, 98.0, "CRITICAL"), 
        "solutions": [
            {"id": 1, "text": "Initiate Cabin Pressurization Sequence (Corrective Action)", "is_correct": True},
            {"id": 2, "text": "Open External Vent Valves (Wrong Action)", "is_correct": False},
            {"id": 3, "text": "Airlock Cycling Check (Deferral)", "is_correct": False}
        ]
    },

    # --- COMPLEX TEMPERATURE ANOMALY ---
    "TEMP": {
        "metric": "Cabin Temperature (°C)",
        "title": "THERMAL ANOMALY DETECTED",
        "message": (
            "Cabin temperature is outside the nominal safe range. "
            "If temperature rises too high, electronics and crew health are at risk. "
            "If temperature drops too low, life support systems and crew safety may be compromised."
        ),
        "constraints": {
            "nominal_range": (18.0, 26.0),  # Safe operating range
            "caution_ranges": [(10.0, 18.0), (26.0, 40.0)],  # Caution windows
            "critical_range": {"low": (3.0, 10.0), "high": (40.0, 175.0)}  # Critical conditions
        },
        "priority_logic": {
            "caution": "MEDIUM",
            "critical": "HIGH"
        },
        "solutions": [
            {
                "id": 1,
                "text": "Activate Secondary ATCS Pump and Heat Exchanger (Corrective Action for High Temp)",
                "is_correct": False  
            },
            {
                "id": 2,
                "text": "Reduce Cabin Heat Loss by Activating Emergency Insulation Panels (Corrective Action for Low Temp)",
                "is_correct": False  
            },
            {
                "id": 3,
                "text": "Take No Immediate Action (Incorrect – Situation Requires Intervention)",
                "is_correct": False
            }
        ]
    }
}


# --- UTILITY FUNCTION: ANOMALY RESET ---
def reset_anomaly_state():
    """Selects a new random anomaly and sets the global state."""
    global CURRENT_ANOMALY
    global LOCKED_ANOMALY_DATA # CLEAR locked data on reset
    
    # List of all possible anomalies (keys from the dataset)
    anomaly_keys = list(ANOMALY_DATASET.keys())
    
    # Select a new anomaly randomly
    new_anomaly = random.choice(anomaly_keys)
    
    CURRENT_ANOMALY = new_anomaly
    LOCKED_ANOMALY_DATA = {} # Reset lock
    print(f"\n--- [SIMULATION] New Anomaly Triggered: {new_anomaly}! Dashboard will update soon. ---\n")

# --- DATA GENERATION ---

def generate_random_data():
    """Generates a random data point for all metrics within the nominal range."""
    data = {}
    for key, (min_val, max_val, unit) in NOMINAL_RANGES.items():
        value = round(random.uniform(min_val, max_val), 2)
        data[key] = {"value": value, "unit": unit, "status": "NOMINAL"}
    return data

def get_anomaly_data():
    """
    Generates the data, applying the current anomaly's constraints.
    Crucially, it uses LOCKED_ANOMALY_DATA to fix the value/status once an anomaly starts.
    """
    global LOCKED_ANOMALY_DATA
    
    data = generate_random_data()
    
    if CURRENT_ANOMALY != "NONE":
        anomaly_profile = ANOMALY_DATASET.get(CURRENT_ANOMALY)
        
        if anomaly_profile:
            metric_key = anomaly_profile["metric"]
            
            # CHECK 1: If data is already locked, use the locked data and bypass generation
            if LOCKED_ANOMALY_DATA.get(metric_key):
                locked_val = LOCKED_ANOMALY_DATA[metric_key]["value"]
                locked_status = LOCKED_ANOMALY_DATA[metric_key]["status"]
                
                # Restore the locked values to the current data output
                data[metric_key]["value"] = locked_val
                data[metric_key]["status"] = locked_status
                
                # Re-apply dynamic TEMP profile updates (solutions, priority) from the locked state
                if CURRENT_ANOMALY == "TEMP":
                    # We need to re-run the logic that set the priority/solutions for TEMP
                    is_high = LOCKED_ANOMALY_DATA[metric_key]["is_high"]
                    status = locked_status
                    
                    anomaly_profile["priority"] = anomaly_profile["priority_logic"][status.lower()]
                    
                    # Determine the correct solution ID (1 for High, 2 for Low)
                    correct_solution_id = 1 if is_high else 2
                    
                    # Update the solutions list: set the correct one to True
                    for sol in anomaly_profile["solutions"]:
                        sol["is_correct"] = (sol["id"] == correct_solution_id)
                
                return data
            
            # CHECK 2: If data is NOT locked, proceed with anomaly generation and then LOCK it
            
            if CURRENT_ANOMALY == "TEMP":
                # --- Handle Complex TEMP Anomaly Logic ---
                temp_constraints = anomaly_profile["constraints"]
                
                all_anomaly_ranges = []
                crit_low_min, crit_low_max = temp_constraints["critical_range"]["low"]
                crit_high_min, crit_high_max = temp_constraints["critical_range"]["high"]
                all_anomaly_ranges.append({"min": crit_low_min, "max": crit_low_max, "status": "CRITICAL", "is_high": False})
                all_anomaly_ranges.append({"min": crit_high_min, "max": crit_high_max, "status": "CRITICAL", "is_high": True})
                
                caution_low_min, caution_low_max = temp_constraints["caution_ranges"][0]
                caution_high_min, caution_high_max = temp_constraints["caution_ranges"][1]
                all_anomaly_ranges.append({"min": caution_low_min, "max": caution_low_max, "status": "CAUTION", "is_high": False})
                all_anomaly_ranges.append({"min": caution_high_min, "max": caution_high_max, "status": "CAUTION", "is_high": True})
                
                chosen_range = random.choice(all_anomaly_ranges)
                
                anomaly_val = round(random.uniform(chosen_range["min"], chosen_range["max"]), 2)
                
                status = chosen_range["status"]
                is_high = chosen_range["is_high"]
                
                anomaly_profile["priority"] = anomaly_profile["priority_logic"][status.lower()]
                
                correct_solution_id = 1 if is_high else 2
                
                for sol in anomaly_profile["solutions"]:
                    sol["is_correct"] = (sol["id"] == correct_solution_id)
                
                # Update the data dictionary
                data[metric_key]["value"] = anomaly_val
                data[metric_key]["status"] = status
                
                # --- LOCK THE DATA ---
                LOCKED_ANOMALY_DATA[metric_key] = {
                    "value": anomaly_val, 
                    "status": status, 
                    "is_high": is_high # Store the high/low state for re-application
                }
                
            else:
                # --- Handle Standard Anomalies (CO2, PRESSURE) ---
                min_val, max_val, status = anomaly_profile["constraints"]
                
                anomaly_val = round(random.uniform(min_val, max_val), 2)
                
                # Update the data dictionary
                data[metric_key]["value"] = anomaly_val
                data[metric_key]["status"] = status
                
                # --- LOCK THE DATA ---
                LOCKED_ANOMALY_DATA[metric_key] = {
                    "value": anomaly_val, 
                    "status": status
                }
            
    return data

# --- ALERT / RECOMMENDATION LOGIC ---

def get_predictions():
    """Returns the prediction message if an anomaly is active."""
    if CURRENT_ANOMALY != "NONE":
        # The profile is dynamically updated/restored in get_anomaly_data before this is called
        return ANOMALY_DATASET.get(CURRENT_ANOMALY)
    return {}

def get_recommendations():
    """Returns the list of actions for the active anomaly."""
    if CURRENT_ANOMALY != "NONE":
        anomaly_profile = ANOMALY_DATASET.get(CURRENT_ANOMALY)
        # Note: Correct solution is marked as True in get_anomaly_data
        return anomaly_profile.get("solutions", [])
    return []

# --- ACTION EXECUTION ---

def execute_action(action_id):
    """Processes the crew's action and updates the game state."""
    global CURRENT_ANOMALY
    global LOCKED_ANOMALY_DATA # Use global keyword to modify the lock
    
    current_anomaly_profile = ANOMALY_DATASET.get(CURRENT_ANOMALY)
    
    if not current_anomaly_profile:
         return {"status": "error", "message": "No active anomaly to execute an action against."}

    recommendations = current_anomaly_profile["solutions"]
    action = next((r for r in recommendations if r['id'] == action_id), None)
    
    if action and action['is_correct']:
        solved_anomaly = CURRENT_ANOMALY
        CURRENT_ANOMALY = "NONE"        
        LOCKED_ANOMALY_DATA = {} # UNLOCK/CLEAR the anomaly data on successful fix!
        
        # --- Schedule the anomaly to return in 20 seconds ---
        threading.Timer(20.0, reset_anomaly_state).start()
        
        return {
            "status": "success",
            "message": f"✅ CORRECTIVE ACTION EXECUTED. The '{solved_anomaly}' anomaly is resolved. Systems returning to nominal.",
            "nasa_fact": random.choice([
                "Every kilogram of CO₂ removed saves 1 kg of lithium hydroxide on resupply missions.",
                "Cabin pressure is maintained using nitrogen (N₂) and oxygen (O₂).",
                "The ATCS uses water-based loops to cool cabin air and electronics."
            ])
        }
    
    elif action: # Incorrect action (ID 2 or 3)
        # The anomaly remains active, and the data remains locked
        return {
            "status": "failure",
            "message": f"🚨 ACTION FAILED: {action['text'].split('(')[0].strip()} resulted in a system spike. The {CURRENT_ANOMALY} anomaly remains active."
        }
        
    return {"status": "error", "message": "Unknown action ID."}