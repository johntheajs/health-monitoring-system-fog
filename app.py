import serial
import time
import firebase_admin
from firebase_admin import credentials, firestore, storage
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.exceptions import NotFittedError
import pickle
import os

# Set up Firebase
cred = credentials.Certificate("firebase.json")
firebase_admin.initialize_app(cred, {'storageBucket': 'fog-project-99a13.appspot.com'})
db = firestore.client()
bucket = storage.bucket()

# Arduino Setup
arduino = serial.Serial('COM3', 9600, timeout=1)
time.sleep(2)

# Initial Data for training
data = {'Time': [], 'HeartRate': [], 'Label': []}

# Model Initialization
model = RandomForestClassifier()

# Check if a model exists in Firebase Storage and load it
def load_model_from_firebase():
    model_filename = "heart_model.pkl"
    blob = bucket.blob(model_filename)

    if blob.exists():
        print("Model found in Firebase Storage. Loading...")
        blob.download_to_filename(model_filename)

        try:
            with open(model_filename, 'rb') as model_file:
                loaded_model = pickle.load(model_file)
            
            # Check if the model has been trained (has estimators_)
            if hasattr(loaded_model, 'estimators_'):
                print("Loaded model is trained and ready to use.")
                return loaded_model
            else:
                print("Loaded model is untrained. Starting fresh model.")
                return None
        except Exception as e:
            print(f"Error loading model: {e}")
            return None
    else:
        print("No existing model found in Firebase Storage. Starting fresh.")
        return None

# Function to upload data to Firestore
def upload_data(heart_rate, timestamp, prediction):
    db.collection('heart_rate_data').add({
        'timestamp': timestamp,
        'heart_rate': heart_rate,
        'prediction': 'Abnormal' if prediction == 1 else 'Normal'
    })

# Function to upload the model to Firebase Storage
def upload_model_to_firebase():
    model_filename = "heart_model.pkl"
    with open(model_filename, 'wb') as model_file:
        pickle.dump(model, model_file)

    blob = bucket.blob(model_filename)
    blob.upload_from_filename(model_filename)
    print("Model uploaded to Firebase Storage.")

# Load model if present, otherwise continue with new model
loaded_model = load_model_from_firebase()
if loaded_model:
    model = loaded_model
else:
    model = RandomForestClassifier()

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

                # Upload data to Firestore
                upload_data(bpm, timestamp, label)

                # Update model with new data every N samples
                if len(data['Time']) % 10 == 0:  # Train after every 10 new readings
                    df = pd.DataFrame(data)
                    X = df[['HeartRate']]
                    y = df['Label']
                    model.fit(X, y)

                    # Replace model in Firebase Storage after every update
                    upload_model_to_firebase()

                # Predict using updated model
                try:
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

                # Print heart rate and prediction in the console
                print(f"Time: {timestamp}, HeartRate: {bpm}, Prediction: {prediction}")

            except ValueError:
                print(f"Invalid BPM data: {line}")

    time.sleep(1)
