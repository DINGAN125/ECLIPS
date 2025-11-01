from flask import Flask, jsonify, render_template, request
from nasa_data import get_anomaly_data, get_predictions, get_recommendations, execute_action

app = Flask(__name__)

# Route 1: Serves the main HTML page
@app.route('/')
def index():
    return render_template('home.html')

# Route 2: GET metric data (Dashboard)
@app.route('/get_data')
def get_data():
    """Returns all current ECLSS metric data, including the anomaly."""
    return jsonify(get_anomaly_data())
    
# Route 3: GET active predictions/alerts
@app.route('/get_predictions')
def get_predictions_api():
    """Returns the current anomaly prediction/message."""
    return jsonify(get_predictions())

# Route 4: GET recommendation button details
@app.route('/get_recommendations')
def get_recommendations_api():
    """Returns the action buttons associated with the current anomaly."""
    return jsonify(get_recommendations())

# Route 5: POST action execution
@app.route('/execute_action', methods=['POST'])
def execute_action_api():
    """Receives an action ID and processes the game state update."""
    data = request.get_json()
    action_id = data.get('action_id')
    
    if action_id is not None:
        result = execute_action(action_id)
        return jsonify(result)
    
    return jsonify({"status": "error", "message": "No action_id provided."}), 400

if __name__ == '__main__':
    # Ensure your HTML file is named 'index.html' and is in a folder named 'templates' 
    # OR in the same directory as app.py (if no 'templates' folder is used).
    app.run(debug=True)
