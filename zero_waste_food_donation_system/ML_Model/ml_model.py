import joblib
import os

# Path to your saved model
MODEL_PATH = os.path.join(os.path.dirname(__file__), "gradient_boosting_priority_model.pkl")

# Load the model
priority_model = joblib.load(MODEL_PATH)

# LabelEncoder and Scaler (must match the ones used during training)
import pickle
with open(os.path.join(os.path.dirname(__file__), "food_type_encoder.pkl"), "rb") as f:
    food_type_encoder = pickle.load(f)
with open(os.path.join(os.path.dirname(__file__), "scaler.pkl"), "rb") as f:
    scaler = pickle.load(f)
