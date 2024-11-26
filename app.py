import os
from flask import Flask, render_template, redirect, url_for, request, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from paho.mqtt.client import Client
import json
import matplotlib.pyplot as plt
from io import BytesIO
import base64
from threading import Thread
from datetime import datetime

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
MQTT_BROKER = "10.0.0.167"
MQTT_PORT = 1883
MQTT_TOPIC = "sensor/temperature_humidity"

mqtt_client = Client()

# MQTT Callback Functions
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT Broker")
        client.subscribe(MQTT_TOPIC)
    else:
        print(f"Failed to connect, return code {rc}")


def on_message(client, userdata, msg):
    with app.app_context():  # Explicitly push Flask's application context
        try:
            data = json.loads(msg.payload.decode())
            print(f"Received MQTT message: {data}")
            temperature = data.get("temperature")
            humidity = data.get("humidity")
            timestamp = data.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

            # Save data to database
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


# Start the MQTT client in a separate thread
thread = Thread(target=mqtt_thread)
thread.daemon = True
thread.start()


# Flask Routes
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


@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        flash('Please log in to access the dashboard', 'warning')
        return redirect(url_for('login'))

    # Fetch data from the database
    data = SensorData.query.order_by(SensorData.timestamp).all()
    temperatures = [record.temperature for record in data]
    humidities = [record.humidity for record in data]
    timestamps = [record.timestamp for record in data]

    # Generate Plot
    img = BytesIO()
    plt.figure(figsize=(10, 6))
    plt.plot(timestamps, temperatures, label="Temperature (°C)", color="red")
    plt.plot(timestamps, humidities, label="Humidity (%)", color="blue")
    plt.xlabel("Timestamp")
    plt.ylabel("Values")
    plt.title("Temperature and Humidity Over Time")
    plt.legend()
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(img, format='png')
    img.seek(0)
    plot_url = base64.b64encode(img.getvalue()).decode()

    return render_template('dashboard.html', plot_url=plot_url)


@app.route('/logout')
def logout():
    session.pop('user', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))


def init_db():
    db_path = os.path.join(os.getcwd(), 'instance', 'database.db')

    if not os.path.exists(db_path):
        # Manually create the database file before running the app
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        # Use app context to create tables
        with app.app_context():
            db.create_all()  # Create tables
            print("Database created and tables initialized.")

            # Create the admin user
            hashed_password = generate_password_hash("password")
            new_user = User(username="admin", password=hashed_password)
            db.session.add(new_user)
            db.session.commit()
            print("Admin user created.")
    else:
        print("Database already exists.")


# Ensure the database is initialized before the app starts
init_db()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
