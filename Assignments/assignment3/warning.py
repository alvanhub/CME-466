import sys
import os
from PyQt5.QtWidgets import QApplication, QDialog
from PyQt5.QtCore import QThread, pyqtSignal, QTimer
from PyQt5 import uic
import time
import paho.mqtt.client as mqtt
from cryptography.fernet import Fernet

cypher_key = b'GbiLRJv9r26tQu7jmmoJn7meiLcCbYFis4EHFhVlrYU='
cipher = Fernet(cypher_key)

# mqtt_broker = "test.mosquitto.org"
mqtt_broker = "broker.hivemq.com"
topic_publish = "CME466/from_pa/assignment3"
topic_subscribe = "CME466/to_pa/assignment3"  

# Publisher client
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, "parking_lot")
client.connect(mqtt_broker)
client.loop_start()

# Subscriber client 
subscriber_client = None


class SmartParkingSystem(QDialog):
    # Signal for MQTT messages 
    mqtt_parking_update = pyqtSignal(int, bool)  # spot_index, is_occupied
    
    def __init__(self):
        super().__init__()
        
        # Load the UI file 
        ui_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'a3parkingui')
        uic.loadUi(ui_file, self)
        
        self.spot_states = [False] * 5
        
        self.spot_indicators = [
            self.label,      # Spot 1
            self.label_2,    # Spot 2
            self.label_3,    # Spot 3
            self.label_4,    # Spot 4
            self.label_5     # Spot 5
        ]
        self.spot_status_labels = [
            self.lineEdit_12,  # Spot 1 status
            self.lineEdit_13,  # Spot 2 status
            self.lineEdit_14,  # Spot 3 status
            self.lineEdit_15,  # Spot 4 status
            self.lineEdit_16   # Spot 5 status
        ]
        
        # Connect signals 
        self.pushButton.clicked.connect(self.turn_warning_on)      # ON button
        self.pushButton_2.clicked.connect(self.turn_warning_off)   # OFF button
        self.pushButton_3.clicked.connect(self.send_message)       # Send button
        self.lineEdit_17.returnPressed.connect(self.send_message)  # Message input
        
        self.textEdit_3.setPlainText("Waiting for MQTT data from RPI5...\n")
        
        self.mqtt_parking_update.connect(self.update_spot_indicator)
        
        self.setup_mqtt_subscriber()
        
    
    def update_spot_indicator(self, spot_index, is_occupied):
        """Update the visual indicator for a parking spot"""
        self.spot_states[spot_index] = is_occupied
        
        indicator = self.spot_indicators[spot_index]
        status_label = self.spot_status_labels[spot_index]
        
        if is_occupied:
            # Red circle for occupied
            indicator.setStyleSheet(
                "background-color: red; "
                "border-radius: 10px; "
                "border: 1px solid black;"
            )
            status_label.setText("Full")
            status_label.setStyleSheet(
                "background-color: #FFFFFF; "
                "color: red; "
                "border: 2px solid #333333; "
                "font-size: 14px;"
            )
        else:
            # Green circle for empty
            indicator.setStyleSheet(
                "background-color: green; "
                "border-radius: 10px; "
                "border: 1px solid black;"
            )
            status_label.setText("Empty")
            status_label.setStyleSheet(
                "background-color: #FFFFFF; "
                "color: green; "
                "border: 2px solid #333333; "
                "font-size: 14px;"
            )
    
    def setup_mqtt_subscriber(self):
        """Set up MQTT subscriber to receive parking spot updates from RPI5"""
        global subscriber_client
        subscriber_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, "ydt529_subscriber")
        
        # Set callbacks
        subscriber_client.on_connect = self.on_mqtt_connect
        subscriber_client.on_message = self.on_mqtt_message
        
        # Connect and start loop in background
        subscriber_client.connect(mqtt_broker)
        subscriber_client.loop_start()
        
        print("MQTT subscriber started and waiting for parking spot updates...")
    
    def on_mqtt_connect(self, client, userdata, flags, rc, properties=None):
        """Callback when MQTT subscriber connects"""
        if rc == 0:
            print("Connected to MQTT broker successfully!")
            # Subscribe to the parking spots topic
            client.subscribe(topic_subscribe)
            print(f"Subscribed to topic: {topic_subscribe}")
        else:
            print(f"Failed to connect to MQTT broker. Return code: {rc}")
    
    def on_mqtt_message(self, client, userdata, msg):
        """Callback when MQTT message is received"""
        try:
            # Decrypt the message
            encrypted_message = msg.payload
            # decrypted_message = cipher.decrypt(encrypted_message).decode('utf-8')
            
            print(f"Received message: {encrypted_message}")
            
            # "sensor_value:spot1:spot2:spot3:spot4:spot5"
            # Where sensor_value is the distance, and spots are 1 (occupied) or 0 (free)
            
            parts = encrypted_message.decode('utf-8').split(":")
            
            if len(parts) >= 6: 
                sensor_value = parts[0]
                self.update_sensor_display(f"Distance: {sensor_value} cm")
                
                # Next 5 values are parking spot statuses
                for i in range(5):
                    spot_status = parts[i + 1].strip()
                    is_occupied = (spot_status == "1")  # "1" means occupied, "0" means free
                    
                    # Emit signal to update UI 
                    self.mqtt_parking_update.emit(i, is_occupied)
                
                print(f"Processed: Sensor={sensor_value}, Spots=[{','.join(parts[1:6])}]")
            else:
                print(f"Invalid message format. Expected 6 colon-separated values, got {len(parts)}")
                self.update_sensor_display(f"Invalid message format: {encrypted_message}")
        
        except Exception as e:
            print(f"Error processing MQTT message: {e}")
            self.update_sensor_display(f"Error processing message: {e}")
    
    def turn_warning_on(self):
        """Send warning ON command to RPI5 via MQTT"""
        # Light up the Warning ON box in UI
        self.lineEdit.setText("Warning ON")
        self.lineEdit.setStyleSheet(
            "background-color: #27ae60; "
            "color: #ffffff; "
            "border: 2px solid #333333; "
            "font-size: 14px;"
        )
        
        # Publish WARNING_ON message to RPI5
        b_message = bytes("WARNING_ON", 'utf-8')
        e_message = cipher.encrypt(b_message)
        client.publish(topic_publish, b_message)
        print("Published WARNING_ON to topic:", topic_publish)
        
        # Reset the Warning OFF box to default state
        self.lineEdit_2.setText("Warn OFF")
        self.lineEdit_2.setStyleSheet(
            "background-color: #1e1e1e; "
            "color: #ffffff; "
            "border: 2px solid #333333; "
            "font-size: 14px;"
        )
    
    def turn_warning_off(self):
        """Send warning OFF command to RPI5 via MQTT"""
        # Light up the Warning OFF box in UI
        self.lineEdit_2.setText("Warning OFF")
        self.lineEdit_2.setStyleSheet(
            "background-color: #e74c3c; "
            "color: #ffffff; "
            "border: 2px solid #333333; "
            "font-size: 14px;"
        )
        
        # Publish WARNING_OFF message to RPI5
        b_message = bytes("WARNING_OFF", 'utf-8')
        e_message = cipher.encrypt(b_message)
        client.publish(topic_publish, b_message)
        print("Published WARNING_OFF to topic:", topic_publish)
        
        # Reset the Warning ON box to default state
        self.lineEdit.setText("Warn ON")
        self.lineEdit.setStyleSheet(
            "background-color: #1e1e1e; "
            "color: #ffffff; "
            "border: 2px solid #333333; "
            "font-size: 14px;"
        )
    
    def update_sensor_display(self, message):
        """Update the sensor data display"""
        timestamp = time.strftime("%H:%M:%S")
        self.textEdit_3.append(f"[{timestamp}] {message}")
        # Auto-scroll to bottom
        scrollbar = self.textEdit_3.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def send_message(self):
        """Send message to display board (print to terminal)"""
        message = self.lineEdit_17.text().strip()
        if message:
            print(f"\n{'='*60}")
            print(f"DISPLAY BOARD MESSAGE: {message}")
            print(f"{'='*60}\n")
            self.lineEdit_17.clear()

            b_message = bytes(message, 'utf-8')
            e_message = cipher.encrypt(b_message)
            client.publish(topic_publish, b_message)
            print("Published message to topic:", topic_publish)
            self.update_sensor_display(f"Message sent to display board: {message}")
    
    def closeEvent(self, event):
        # Clean up MQTT connections
        global subscriber_client
        if subscriber_client:
            subscriber_client.loop_stop()
            subscriber_client.disconnect()
            print("MQTT subscriber disconnected")
        
        client.disconnect()
        print("MQTT publisher disconnected")
        
        event.accept()

def main():
    app = QApplication(sys.argv)
    window = SmartParkingSystem()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()