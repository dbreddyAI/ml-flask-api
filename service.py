#!flask/bin/python
import os
from flask import Flask
from flask import request
from flask import Flask, Response
from model import Model, validate_features
from time import time

app = Flask(__name__)

try:
    from input_validator import validate_features
except ImportError:
    def validate_features(f):
        @wraps(f)
        def wrapper(*args, **kw):
            app.logger.info('Input validation was not performed. No validation function defined')
            return f(*args, **kw)
        return wrapper

# Load model
base_dir = '/usr/src/app/data/'
model_path = os.path.join(base_dir, os.environ.get('MODEL_NAME', 'model.joblib'))
if not os.path.exists(model_path):
    raise RuntimeError("Model {} not found".format(model_path))
else:
    model = Model(model_path)

@app.route('/predict', methods=['GET'])
@validate_features
def predict():
    # Parameters
    output_proba = request.args.get('output_proba', False)
    correlation_id = request.headers.get('X-Correlation-ID')
    # Predict
    before_time = time()
    input = list(request.args.values())
    prediction = model.predict_proba(input) if output_proba else model.predict(input)
    result = {'prediction': prediction}
    after_time = time()
    # log
    to_be_logged = {
        'input': request.args,
        'request_id': correlation_id,
        'prediction': prediction,
        'model': model.meta_data,
        'elapsed_time': after_time - before_time
    }
    app.logger.info(to_be_logged)
    return jsonify(result)


@app.route('/health')
def health_check():
    return Response("", status = 200)


@app.route('/ready')
def readiness_check():
    if model.is_ready():
        return Response("", status = 200)
    else:
        return Response("", status = 503)


if __name__ == '__main__':
    app.run(
        debug=os.environ.get('DEBUG', True),
        host=os.environ.get('HOST', '0.0.0.0'),
        port=os.environ.get('PORT', '5000'))