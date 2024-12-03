import csv
from io import StringIO

from flask import Flask, render_template, redirect, url_for, request, session, flash, jsonify, make_response
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from paho.mqtt.client import Client
from threading import Thread
from datetime import datetime
import json
import os

# Initialize Flask App
app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    password = db.Column(db.String(150), nullable=False)


class SensorData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.String(100), nullable=False)
    temperature = db.Column(db.Float, nullable=False)
    humidity = db.Column(db.Float, nullable=False)


# MQTT Configuration
MQTT_BROKER = "alexpi"
MQTT_PORT = 1883
MQTT_TOPIC = "sensor/temperature_humidity"

mqtt_client = Client()

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT Broker")
        client.subscribe(MQTT_TOPIC)
    else:
        print(f"Failed to connect, return code {rc}")


def on_message(client, userdata, msg):
    with app.app_context():
        try:
            data = json.loads(msg.payload.decode())
            print(f"Received MQTT message: {data}")
            temperature = data.get("temperature")
            humidity = data.get("humidity")
            timestamp = data.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

            sensor_data = SensorData(
                timestamp=timestamp,
                temperature=temperature,
                humidity=humidity
            )
            db.session.add(sensor_data)
            db.session.commit()
        except Exception as e:
            print(f"Error processing message: {e}")


# Initialize MQTT in a separate thread
def mqtt_thread():
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
    mqtt_client.loop_forever()


thread = Thread(target=mqtt_thread)
thread.daemon = True
thread.start()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user'] = username
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        flash('Please log in to access the dashboard', 'warning')
        return redirect(url_for('login'))
    return render_template('dashboard.html')


@app.route('/sensor-data', methods=['GET'])
def sensor_data():
    """Fetch the latest sensor data for Chart.js."""
    latest_data = SensorData.query.order_by(SensorData.timestamp.desc()).first()
    if latest_data:
        return jsonify({
            'temperature': latest_data.temperature,
            'humidity': latest_data.humidity,
            'timestamp': latest_data.timestamp
        })
    else:
        return jsonify({'error': 'No data available'}), 404


@app.route('/historicaldata', methods=['GET', 'POST'])
def historicaldata():
    filters = {
        "start_time": None,
        "end_time": None,
        "min_temperature": None,
        "max_temperature": None,
        "min_humidity": None,
        "max_humidity": None,
    }

    if request.method == 'POST':
        # Get the filter values from the form
        filters["start_time"] = request.form.get('start_time') or None
        filters["end_time"] = request.form.get('end_time') or None
        filters["min_temperature"] = request.form.get('min_temperature') or None
        filters["max_temperature"] = request.form.get('max_temperature') or None
        filters["min_humidity"] = request.form.get('min_humidity') or None
        filters["max_humidity"] = request.form.get('max_humidity') or None

        # Convert numeric fields to float where applicable
        try:
            if filters["min_temperature"]:
                filters["min_temperature"] = float(filters["min_temperature"])
            if filters["max_temperature"]:
                filters["max_temperature"] = float(filters["max_temperature"])
            if filters["min_humidity"]:
                filters["min_humidity"] = float(filters["min_humidity"])
            if filters["max_humidity"]:
                filters["max_humidity"] = float(filters["max_humidity"])
        except ValueError:
            flash("Invalid numeric input for filters", "error")
            filters = {key: None for key in filters}  # Reset filters on error

    # Query the database with filters
    query = SensorData.query
    if filters["start_time"]:
        query = query.filter(SensorData.timestamp >= filters["start_time"])
    if filters["end_time"]:
        query = query.filter(SensorData.timestamp <= filters["end_time"])
    if filters["min_temperature"] is not None:
        query = query.filter(SensorData.temperature >= filters["min_temperature"])
    if filters["max_temperature"] is not None:
        query = query.filter(SensorData.temperature <= filters["max_temperature"])
    if filters["min_humidity"] is not None:
        query = query.filter(SensorData.humidity >= filters["min_humidity"])
    if filters["max_humidity"] is not None:
        query = query.filter(SensorData.humidity <= filters["max_humidity"])

    data = query.all()
    return render_template('historicaldata.html', data=data, filters=filters)

@app.route('/export', methods=['GET'])
def export_data():
    # Get filters from the session or from the GET request if available
    filters = {
        "start_time": request.args.get('start_time', None),
        "end_time": request.args.get('end_time', None),
        "min_temperature": request.args.get('min_temperature', None),
        "max_temperature": request.args.get('max_temperature', None),
        "min_humidity": request.args.get('min_humidity', None),
        "max_humidity": request.args.get('max_humidity', None),
    }

    # Query the filtered data
    query = SensorData.query
    if filters["start_time"]:
        query = query.filter(SensorData.timestamp >= filters["start_time"])
    if filters["end_time"]:
        query = query.filter(SensorData.timestamp <= filters["end_time"])
    if filters["min_temperature"] is not None:
        query = query.filter(SensorData.temperature >= float(filters["min_temperature"]))
    if filters["max_temperature"] is not None:
        query = query.filter(SensorData.temperature <= float(filters["max_temperature"]))
    if filters["min_humidity"] is not None:
        query = query.filter(SensorData.humidity >= float(filters["min_humidity"]))
    if filters["max_humidity"] is not None:
        query = query.filter(SensorData.humidity <= float(filters["max_humidity"]))

    data = query.all()

    # Create a CSV response
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Timestamp', 'Temperature (°C)', 'Humidity (%)'])  # Column headers

    # Write the data to CSV
    for record in data:
        writer.writerow([record.timestamp, record.temperature, record.humidity])

    # Generate response to download CSV file
    output.seek(0)
    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = 'attachment; filename=historical_data.csv'
    response.mimetype = 'text/csv'

    return response


def init_db():
    db_path = os.path.join(os.getcwd(), 'instance', 'database.db')

    if not os.path.exists(db_path):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        with app.app_context():
            db.create_all()
            print("Database created and tables initialized.")

            hashed_password = generate_password_hash("password")
            new_user = User(username="admin", password=hashed_password)
            db.session.add(new_user)
            db.session.commit()
            print("Admin user created.")
    else:
        print("Database already exists.")


init_db()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
