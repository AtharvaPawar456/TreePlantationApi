from flask import Flask, request, jsonify, render_template, redirect, url_for
import sqlite3
import datetime
import folium
import logging

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)

# SQLite database initialization
def init_db():
    conn = sqlite3.connect('plantation.db')
    cursor = conn.cursor()
    
    # Create the required tables if they don't exist
    cursor.execute('''CREATE TABLE IF NOT EXISTS feildTable (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        node TEXT NOT NULL,
                        plantheight REAL NOT NULL,
                        timestamp TEXT DEFAULT CURRENT_TIMESTAMP
                    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS locationTable (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        lat TEXT NOT NULL,
                        long TEXT NOT NULL,
                        node TEXT NOT NULL UNIQUE
                    )''')
    
    conn.commit()
    conn.close()

# Route "/": Welcome page
@app.route('/')
def index():
    return "Welcome to the tree plantation API..."

# Route "/uploadvalue": Get node name and plant height, update database
@app.route('/uploadvalue', methods=['GET'])
def upload_value():
    node = request.args.get('node')
    plantheight = request.args.get('plantheight')
    
    if not node or not plantheight:
        return "Error: Missing node or plantheight", 400
    
    try:
        # Convert plantheight to float
        plantheight = float(plantheight)
        timestamp = datetime.datetime.utcnow().isoformat()

        # Log the request
        logging.info(f"Received upload request for node: {node}, plantheight: {plantheight}")

        # Insert into the feildTable
        conn = sqlite3.connect('plantation.db')
        cursor = conn.cursor()
        
        # Check if the record already exists
        cursor.execute('''SELECT COUNT(*) FROM feildTable WHERE node = ? AND plantheight = ? AND timestamp = ?''', 
                       (node, plantheight, timestamp))
        count = cursor.fetchone()[0]
        
        if count == 0:  # Only insert if no existing record matches
            cursor.execute('''INSERT INTO feildTable (node, plantheight, timestamp)
                              VALUES (?, ?, ?)''', (node, plantheight, timestamp))
        else:
            logging.info("Duplicate entry found, not inserting.")

        # Check if the node exists in locationTable, else insert a placeholder
        cursor.execute('''SELECT * FROM locationTable WHERE node = ?''', (node,))
        if cursor.fetchone() is None:
            cursor.execute('''INSERT INTO locationTable (node, lat, long)
                              VALUES (?, 'pls set the value', 'pls set the value')''', (node,))
        
        conn.commit()
        conn.close()

        return f"db updated for {node}: {plantheight}: {timestamp}"
    except Exception as e:
        return f"Error: {str(e)}", 500


# Route "/history": Display all records from the database
@app.route('/history', methods=['GET'])
def history():
    conn = sqlite3.connect('plantation.db')
    cursor = conn.cursor()
    cursor.execute("SELECT node, plantheight, timestamp FROM feildTable")
    records = cursor.fetchall()
    conn.close()
    
    history_data = [
        {"node": record[0], "plantheight": record[1], "timestamp": record[2]} 
        for record in records
    ]
    return jsonify(history_data)

# Route "/mapplant": Display plant locations on the map using Folium
@app.route('/mapplant', methods=['GET'])
def map_plant():
    conn = sqlite3.connect('plantation.db')
    cursor = conn.cursor()
    cursor.execute("SELECT lat, long, node FROM locationTable")
    locations = cursor.fetchall()
    conn.close()
    
    folium_map = folium.Map(location=[19.0760, 72.8777], zoom_start=12)
    
    for loc in locations:
        folium.Marker([float(loc[0]), float(loc[1])], popup=loc[2]).add_to(folium_map)
    
    return folium_map._repr_html_()

# Route "/latlogedit": Edit lat, long in locationTable
@app.route('/latlogedit', methods=['GET', 'POST'])
def lat_log_edit():
    conn = sqlite3.connect('plantation.db')
    cursor = conn.cursor()
    
    if request.method == 'POST':
        # Get values from form submission
        node_id = request.form.get('id')
        lat = request.form.get('lat')
        long = request.form.get('long')
        
        # Ensure the node_id, lat, and long are not None
        if node_id and lat and long:
            cursor.execute("UPDATE locationTable SET lat = ?, long = ? WHERE id = ?", (lat, long, node_id))
            conn.commit()
        conn.close()
        return redirect(url_for('lat_log_edit'))
    
    # Fetch all locations from the database to display in the form
    cursor.execute("SELECT id, node, lat, long FROM locationTable")
    locations = cursor.fetchall()
    conn.close()
    
    return render_template('latlogedit.html', locations=locations)

if __name__ == '__main__':
    init_db()  # Initialize the database on startup
    app.run(debug=True)
