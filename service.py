#!flask/bin/python
"""
Flask application to serve Machine Learning models
"""
import os
import flask
import json
import argparse
import logging
import numpy as np

from time import time
from model import Model
from functools import wraps


# Version of this APP template
__version__ = '1.1.1'
# Read env variables
DEBUG = os.environ.get('DEBUG', True)
MODEL_NAME = os.environ.get('MODEL_NAME', 'model.joblib')
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'local')
SERVICE_START_TIMESTAMP = time()


class NumpyEncoder(flask.json.JSONEncoder):
    """Encoder of numpy primitives into JSON strings"""
    primitives = (np.ndarray, np.integer, np.inexact)

    def default(self, obj):
        if isinstance(obj, np.flexible):
            return None if isinstance(obj, np.void) else obj.tolist()
        elif isinstance(obj, self.primitives):
            return obj.tolist()
        return json.JSONEncoder.default(self, obj)


def returns_json(f):
    """Wraps a function to transform the output into a JSON string with a
    specific encoder"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        r = f(*args, **kwargs)
        if isinstance(r, flask.Response):
            return r
        else:
            return flask.Response(json.dumps(r, cls=NumpyEncoder), status=200,
                                  mimetype='application/json; charset=utf-8')
    return decorated_function


def create_model_instance():
    global MODEL_NAME
    # Get current directory
    base_dir = os.getcwd()
    # Fix for documentation compilation
    if os.path.basename(base_dir) == 'docsrc':
        base_dir = os.path.dirname(base_dir)
    # Check if there is a model in the directory with the expected name
    model_path = os.path.join(base_dir, MODEL_NAME)
    if not os.path.exists(model_path):
        raise RuntimeError("Model {} not found".format(model_path))
    else:
        # Model found! now create an instance
        return Model(model_path)


# Create Flask Application
app = flask.Flask(__name__)
# Customize Flask Application
app.logger.setLevel(logging.DEBUG)
app.json_encoder = NumpyEncoder
# Create Model instance
model = create_model_instance()
# laod saved model
app.logger.info('ENVIRONMENT: {}'.format(ENVIRONMENT))
app.logger.info('Using template version: {}'.format(__version__))
app.logger.info('Loading model...')
model.load()


@app.route('/predict', methods=['POST'])
@returns_json
def predict():
    # Parameters
    do_proba = int(flask.request.args.get('proba', 0))
    do_explain = int(flask.request.args.get('explain', 0))
    input = json.loads(flask.request.data or '{}')
    # Predict
    before_time = time()
    try:
        predict_function = 'predict_proba' if do_proba else 'predict'
        prediction = getattr(model, predict_function)(input)
    except Exception as err:
        return flask.Response(str(err), status=500)
    result = {'prediction': prediction}
    # Explain
    if do_explain:
        try:
            explanation = model.explain(input)
        except Exception as err:
            return flask.Response(str(err), status=500)
        else:
            result['explanation'] = explanation
    after_time = time()
    # log
    to_be_logged = {
        'input': flask.request.data,
        'params': flask.request.args,
        'request_id': flask.request.headers.get('X-Correlation-ID'),
        'result': result,
        'model': model.metadata,
        'elapsed_time': after_time - before_time
    }
    app.logger.info(to_be_logged)
    return result


@app.route('/predict_proba', methods=['POST'])
def predict_proba():
    return flask.redirect(flask.url_for('predict', proba=1))


@app.route('/explain', methods=['POST'])
def explain():
    return flask.redirect(flask.url_for('predict', proba=1, explain=1))


@app.route('/info',  methods=['GET'])
@returns_json
def info():
    try:
        info = model.info
    except Exception as err:
        return flask.Response(str(err), status=500)
    else:
        return info


@app.route('/features',  methods=['GET'])
@returns_json
def features():
    try:
        features = model.features()
    except Exception as err:
        return flask.Response(str(err), status=500)
    else:
        return features


@app.route('/preprocess',  methods=['POST'])
@returns_json
def preprocess():
    input = json.loads(flask.request.data or '{}')
    try:
        data = model.preprocess(input)
    except Exception as err:
        return flask.Response(str(err), status=500)
    else:
        return data


@app.route('/health')
def health_check():
    return flask.Response("up", status=200)


@app.route('/ready')
def readiness_check():
    if model.is_ready():
        return flask.Response("ready", status=200)
    else:
        return flask.Response("not ready", status=503)


@app.route('/service-info')
@returns_json
def service_info():
    info =  {
        'version-template': __version__,
        'running-since': SERVICE_START_TIMESTAMP,
        'serving-model': MODEL_NAME,
        'debug': DEBUG}
    return info


if __name__ == '__main__':
    app.run(
        debug=DEBUG,
        host=os.environ.get('HOST', 'localhost'),
        port=os.environ.get('PORT', '5000'))
