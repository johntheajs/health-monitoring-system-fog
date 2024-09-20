import serial
import time
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.exceptions import NotFittedError

# Set up Firebase
cred = credentials.Certificate("firebase.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# Arduino Setup
arduino = serial.Serial('COM3', 9600, timeout=1)
time.sleep(2)

# Initial Data for training
data = {'Time': [], 'HeartRate': [], 'Label': []}

# Model Initialization
model = RandomForestClassifier()

# Function to upload data to Firebase
def upload_data(heart_rate, timestamp, prediction):
    db.collection('heart_rate_data').add({
        'timestamp': timestamp,
        'heart_rate': heart_rate,
        'prediction': 'Abnormal' if prediction == 1 else 'Normal'
    })

# Real-time data processing
while True:
    line = arduino.readline().decode().strip()

    if line:
        # Ensure the line starts with "BPM: " and extract the BPM value
        if line.startswith("BPM: "):
            try:
                bpm = int(line.split(": ")[1])  # Parse BPM from Arduino serial
                timestamp = time.time()

                # Labeling: define abnormality threshold
                label = 1 if bpm > 100 else 0  # Modify threshold as needed

                # Add new data to dataset for continuous training
                data['Time'].append(timestamp)
                data['HeartRate'].append(bpm)
                data['Label'].append(label)

                # Update model with new data every N samples
                if len(data['Time']) % 10 == 0:  # Train after every 10 new readings
                    df = pd.DataFrame(data)
                    X = df[['HeartRate']]
                    y = df['Label']
                    model.fit(X, y)

                try:
                    # Predict using updated model
                    prediction = model.predict([[bpm]])[0]
                except NotFittedError:
                    print("Model is not fitted yet. Waiting for more data...")
                    prediction = label  # Default to using the label for now

                # Control buzzer based on prediction
                if prediction == 1:  # If abnormal heart rate
                    print("Abnormal! Trigger Buzzer!")
                    # You can send a command to Arduino to trigger the buzzer
                else:
                    print("Heart rate normal.")

                # Upload data to Firebase
                upload_data(bpm, timestamp, prediction)

                # Print heart rate and prediction in the console
                print(f"Time: {timestamp}, HeartRate: {bpm}, Prediction: {prediction}")

            except ValueError:
                print(f"Invalid BPM data: {line}")
        
    time.sleep(1)
