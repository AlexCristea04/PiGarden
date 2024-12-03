/// PIGARDEN ///

This project integrates IoT technologies with environmental monitoring and automation to create a smart plant care system. 
The system combines temperature, humidity, soil moisture, and light sensors to ensure optimal conditions for plant health.
A Raspberry Pi serves as the central hub, running a Flask-based web application for real-time monitoring, data visualization, and control.

The temperature and humidity are measured using a DHT sensor and transmitted to the system via MQTT. Soil moisture is monitored 
using a moisture sensor, which activates a water pump when the soil is too dry, ensuring the plant receives adequate hydration. 
A light sensor detects ambient light levels and automatically powers LEDs to provide supplemental lighting during dark conditions, 
supporting the plant's growth.

To ensure continuous functionality, the Raspberry Pi operates offline when network connectivity is unavailable. Sensor readings 
and events are saved locally, allowing the system to maintain its automation features. When the connection is restored, all stored 
data is synchronized with the central database, ensuring no information is lost.

Data from all sensors is visualized in an intuitive web dashboard, accessible remotely via the Flask app. The system includes 
MQTT integration for seamless data transfer and an easy-to-use control panel for configuring thresholds and monitoring sensor activity. 
This project provides an efficient, robust, and scalable solution for automating plant care, making it ideal for smart gardening 
enthusiasts and agricultural applications.

Full project documentation can be found here:
https://docs.google.com/document/d/1jRzlhsofpJJZEJpq2Fw3a0l3rPG2EbD4V2WyJ9xZcK4/edit?usp=sharing 
