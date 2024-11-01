import os
import sqlite3
import logging
from flask import Flask, request, jsonify, render_template, redirect, url_for
from datetime import datetime
import folium

# pip install flask
# pip install folium

domainUrl = "http://127.0.0.1:5000"

app = Flask(__name__)

# Setup logging
if not os.path.exists('LOGs'):
    os.makedirs('LOGs')

logging.basicConfig(filename=f'LOGs/log_{datetime.now().strftime("%d_%m_%Y")}.log',
                    level=logging.INFO,
                    format='%(levelname)s | %(message)s')

# Database connection
DATABASE = 'tree_plantation.db'

def get_db_connection():
    """Establish a database connection and create tables if they don't exist"""
    try:
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        # Create tables if they don't exist
        conn.execute('''CREATE TABLE IF NOT EXISTS NodeValues (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            nodename TEXT NOT NULL,
                            height REAL NOT NULL,
                            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                            ipaddress TEXT
                        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS NodeData (
                            nodename TEXT PRIMARY KEY,
                            latitude REAL,
                            longitude REAL
                        )''')
        return conn
    except sqlite3.Error as e:
        logging.error(f"Database connection error: {e}")
        return None


# Helper function to log actions
def log_action(level, message):
    """Log actions to the log file with appropriate logging level."""
    if level == logging.INFO:
        logging.info(message)
    elif level == logging.ERROR:
        logging.error(message)
    elif level == logging.DEBUG:
        logging.debug(message)


@app.route('/')
def index():
    """Home route displaying total records and current values of each unique node"""
    conn = get_db_connection()
    if conn is None:
        return "Database connection failed", 500
    try:
        node_values = conn.execute("SELECT nodename, height FROM NodeValues ORDER BY timestamp DESC").fetchall()
        conn.close()

        # Fetch unique nodes with their most recent heights
        unique_nodes = {}
        for row in node_values:
            if row['nodename'] not in unique_nodes:
                unique_nodes[row['nodename']] = row['height']

        total_records = len(node_values)
        # log_action(logging.INFO, f"Accessed home page, total records: {total_records}")

        return render_template('index.html', total_records=total_records, nodes=unique_nodes)
    except sqlite3.Error as e:
        # log_action(logging.ERROR, f"Database query failed: {e}")
        return "Error fetching node values", 500

@app.route('/uploaddata', methods=['GET'])
def upload_data():
    """GET method to insert node data with IP address and create empty lat/lon for new node"""
    nodename = request.args.get('nodename')
    height = request.args.get('height')
    ip_address = request.remote_addr

    if nodename and height:
        conn = get_db_connection()
        if conn is None:
            return "Database connection failed", 500

        try:
            # Insert into NodeValues table
            conn.execute(
                "INSERT INTO NodeValues (nodename, height, timestamp, ipaddress) VALUES (?, ?, ?, ?)",
                (nodename, height, datetime.now(), ip_address)
            )
            
            # Check if the nodename exists in NodeData, if not, create a new entry with lat/lon as 'empty'
            existing_node = conn.execute("SELECT nodename FROM NodeData WHERE nodename = ?", (nodename,)).fetchone()
            if existing_node is None:
                conn.execute(
                    "INSERT INTO NodeData (nodename, latitude, longitude) VALUES (?, ?, ?)",
                    (nodename, 'empty', 'empty')
                )
                # log_action(logging.INFO, f"New node {nodename} added to NodeData with empty lat/lon")
            
            conn.commit()
            conn.close()
            # log_action(logging.INFO, f"Node {nodename} with height {height} added from IP {ip_address}")
            return f"nodename={nodename} and height={height} got saved"
        except sqlite3.Error as e:
            # log_action(logging.ERROR, f"Failed to insert data: {e}")
            return "Failed to save data", 500
    else:
        # log_action(logging.ERROR, "Missing parameters in /uploaddata request")
        return "Missing nodename or height", 400

@app.route('/displaynode')
def display_node():
    """Display all nodes and their details with periodic refresh"""
    conn = get_db_connection()
    unique_nodes = conn.execute("SELECT DISTINCT nodename FROM NodeValues").fetchall()
    latest_record = conn.execute("SELECT * FROM NodeValues ORDER BY timestamp DESC LIMIT 1").fetchone()
    conn.close()

    # log_action(logging.INFO, "Accessed display node page")

    return render_template('display_nodes.html', nodes=unique_nodes, latest_record=latest_record)

@app.route('/displaynode/<nodename>')
def display_node_data(nodename):
    """Display all records for a specific nodename"""
    conn = get_db_connection()
    node_values = conn.execute("SELECT * FROM NodeValues WHERE nodename = ?", (nodename,)).fetchall()
    node_data = conn.execute("SELECT * FROM NodeData WHERE nodename = ?", (nodename,)).fetchone()
    conn.close()

    # log_action(logging.INFO, f"Displaying records for node {nodename}")
    
    return render_template('node_data.html', node_values=node_values, node_data=node_data)

@app.route('/getnodejson/<nodename>')
def get_node_json(nodename):
    """Return node data in JSON format"""
    conn = get_db_connection()
    node_values = conn.execute("SELECT * FROM NodeValues WHERE nodename = ?", (nodename,)).fetchall()
    node_data = conn.execute("SELECT * FROM NodeData WHERE nodename = ?", (nodename,)).fetchone()
    latest_record = conn.execute("SELECT * FROM NodeValues WHERE nodename = ? ORDER BY timestamp DESC LIMIT 1", (nodename,)).fetchone()
    conn.close()

    # log_action(logging.INFO, f"Returned JSON data for node {nodename}")

    return jsonify({
        'node_values': [dict(row) for row in node_values],
        'node_data': dict(node_data) if node_data else {},
        'latest_record': dict(latest_record) if latest_record else {}
    })

@app.route('/getnodelatestjson/<nodename>')
def get_latest_node_json(nodename):
    """Return the latest node record in JSON format"""
    conn = get_db_connection()
    latest_record = conn.execute("SELECT * FROM NodeValues WHERE nodename = ? ORDER BY timestamp DESC LIMIT 1", (nodename,)).fetchone()
    node_data = conn.execute("SELECT * FROM NodeData WHERE nodename = ?", (nodename,)).fetchone()
    conn.close()

    # log_action(logging.INFO, f"Returned latest JSON data for node {nodename}")

    return jsonify({
        'latest_record': dict(latest_record) if latest_record else {},
        'node_data': dict(node_data) if node_data else {}
    })

@app.route('/edit')
def edit():
    """Display unique nodes with edit links"""
    conn = get_db_connection()
    unique_nodes = conn.execute("SELECT DISTINCT nodename FROM NodeData").fetchall()
    conn.close()

    # log_action(logging.INFO, "Accessed edit page")

    return render_template('edit_List_nodes.html', nodes=unique_nodes)

@app.route('/edit/<nodename>', methods=['GET', 'POST'])
def edit_node_data(nodename):
    """Edit node data"""
    conn = get_db_connection()

    if request.method == 'POST':
        latitude = request.form.get('latitude')
        longitude = request.form.get('longitude')
        conn.execute("UPDATE NodeData SET latitude = ?, longitude = ? WHERE nodename = ?", (latitude, longitude, nodename))
        conn.commit()
        conn.close()
        # log_action(logging.INFO, f"Node {nodename} updated with new data")
        return redirect(url_for('edit'))

    node_data = conn.execute("SELECT * FROM NodeData WHERE nodename = ?", (nodename,)).fetchone()
    conn.close()

    # log_action(logging.INFO, f"Accessed edit page for node {nodename}")

    return render_template('edit_node.html', node_data=node_data)

@app.route('/mapit')
def map_it():
    """Map all nodes using folium"""
    conn = get_db_connection()
    node_data = conn.execute("SELECT * FROM NodeData").fetchall()
    conn.close()

    # Generate map
    tree_map = folium.Map(location=[19.0760, 72.8777], zoom_start=12)
    for node in node_data:
        try:
            # Ensure latitude and longitude are not None
            if node['latitude'] is not None and node['longitude'] is not None:
                folium.Marker([node['latitude'], node['longitude']], popup=node['nodename']).add_to(tree_map)
        except KeyError as e:
            # log_action(logging.ERROR, f"Missing coordinate in node data: {e}")
            print(e)

    # Render the map to an HTML string
    map_html = tree_map._repr_html_()  # Get the HTML representation of the map
    # log_action(logging.INFO, "Map generated and rendered as HTML")

    return render_template('map.html', map_html=map_html)

@app.route('/getmap')
def getmap():
    """Map all nodes using folium"""
    conn = get_db_connection()
    node_data = conn.execute("SELECT * FROM NodeData").fetchall()
    conn.close()

    # Generate map
    tree_map = folium.Map(location=[19.0760, 72.8777], zoom_start=12)
    for node in node_data:
        try:
            # Ensure latitude and longitude are not None
            if node['latitude'] is not None and node['longitude'] is not None:
                folium.Marker([node['latitude'], node['longitude']], popup=node['nodename']).add_to(tree_map)
        except KeyError as e:
            # log_action(logging.ERROR, f"Missing coordinate in node data: {e}")
            print(e)

    tree_map.save('templates/getmap.html')
    # log_action(logging.INFO, "Map generated and displayed")

    return render_template('getmap.html')

@app.route('/apis')
def apis():
    # log_action(logging.INFO, "Display Api Page")

    return render_template('apis.html', domainUrl=domainUrl)


if __name__ == '__main__':
    app.run(debug=False)
