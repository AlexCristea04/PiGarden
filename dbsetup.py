import os
from werkzeug.security import generate_password_hash
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

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
    date = db.Column(db.String(100), nullable=False)
    temperature = db.Column(db.Float, nullable=False)
    humidity = db.Column(db.Float, nullable=False)

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
