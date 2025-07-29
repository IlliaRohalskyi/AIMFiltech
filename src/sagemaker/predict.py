import pandas as pd
from flask import Flask, request, jsonify
from src.logger import logging
from src.components.mlflow_utils import setup_mlflow, load_production_model
import io

app = Flask(__name__)

@app.route('/ping', methods=['GET'])
def ping():
    """Health check endpoint"""
    return jsonify({"status": "ok"}), 200

@app.route('/invocations', methods=['POST'])
def invocations():
    """Handle prediction requests"""
    try:
        if request.content_type != 'text/csv':
            return jsonify({"error": "Invalid content type. Expected 'text/csv'"}), 415
        
        input_data = request.data.decode('utf-8')
        df = pd.read_csv(io.StringIO(input_data))
        logging.info(f"Received input data with shape: {df.shape}")
        
        setup_mlflow()

        model, prod_model = load_production_model()
        
        predictions = model.predict(df)
        prediction_probs = model.predict_proba(df)
        
        df['Predicted_Class'] = predictions
        df['Confidence'] = prediction_probs.max(axis=1) 
        
        for i, class_name in enumerate(model.classes_):
            df[f'Prob_Class_{class_name}'] = prediction_probs[:, i]
        
        response_csv = df.to_csv(index=False)
        
        logging.info("Predictions completed successfully")
        return response_csv, 200, {'Content-Type': 'text/csv'}
    
    except Exception as e:
        logging.error(f"Prediction failed: {e}")
        raise e