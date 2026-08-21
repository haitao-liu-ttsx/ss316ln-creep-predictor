"""STEP17 backend: Flask API wrapping the frozen production surrogate.

POST /api/predict  {T,P,t,Rm,Ro,w} -> field[2304] + metrics + validity
Only loads ml/production/step15_v1_2/model/ (frozen v1.2). No retraining,
no OOD override. CORS enabled for local dev.
"""
import json
import os
import sys

from flask import Flask, jsonify, request
from flask_cors import CORS

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'ml', 'production', 'step15_v1_2', 'runtime'))
from predict_field import predict_field, get_hotspot  # noqa: E402

app = Flask(__name__)
CORS(app)


def to_payload(r):
    if r['validity'] != 'VALID':
        return jsonify({'valid': False, 'status': 'OUT_OF_DOMAIN',
                        'violations': r['domain_issues'],
                        'reason': '; '.join(r['domain_issues'])})
    hs = int(r['hotspot_element'])
    c = r['centroids'][hs]
    return jsonify({
        'valid': True, 'status': 'VALID',
        'field': r['ceeq_field'],
        'max_ceeq': r['max_ceeq'], 'mean_ceeq': r['mean_ceeq'],
        'p95_ceeq': r['p95_ceeq'],
        'hotspot_element': hs, 'hotspot_xyz': c,
        'hotspot_value': r['hotspot_value'],
        'pod_coefficients': r['pod_coefficients'],
        'physics_status': 'PASS' if not r['physics_warning'] else 'WARNING',
        'stress_scale': r['stress_scale'],
    })


@app.route('/api/predict', methods=['POST'])
def api_predict():
    data = request.get_json(force=True)
    try:
        T = float(data['T']); P = float(data['P']); t = float(data['t'])
        Rm = float(data['Rm']); Ro = float(data['Ro']); w = float(data['w'])
    except (KeyError, TypeError, ValueError):
        return jsonify({'valid': False, 'status': 'INVALID_INPUT',
                        'violations': ['missing or non-numeric parameter']})
    r = predict_field(T, P, t, Rm, Ro, w)
    return to_payload(r)


@app.route('/api/predict_v13', methods=['POST'])
def api_predict_v13():
    """V1.3 7-field multiphysics prediction (frozen models, domain guarded).
    V1.2 route /api/predict unchanged."""
    try:
        from ml.v13.predictor import predict_serializable
    except ImportError:
        import sys
        sys.path.insert(0, os.path.join(ROOT, 'ml'))
        from v13.predictor import predict_serializable
    data = request.get_json(force=True)
    try:
        T = float(data['T']); P = float(data['P']); t = float(data['t'])
        Rm = float(data['Rm']); Ro = float(data['Ro']); w = float(data['w'])
    except (KeyError, TypeError, ValueError):
        return jsonify({'status': 'INPUT_INVALID', 'errors': ['missing or non-numeric parameter']})
    return jsonify(predict_serializable(T, P, t, Rm, Ro, w))


@app.route('/api/hotspot', methods=['POST'])
def api_hotspot():
    data = request.get_json(force=True)
    f = data.get('field')
    if not f or len(f) != 2304:
        return jsonify({'error': 'field must be 2304'})
    return jsonify(get_hotspot(f))


@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'model': 'STEP15-v1.2', 'status': 'FROZEN'})


# ---- production static serving (single-service deploy: Flask serves dist/ + API) ----
_DIST = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'frontend', 'dist')
if os.path.isdir(_DIST):
    from flask import send_from_directory

    @app.route('/')
    def index():
        return send_from_directory(_DIST, 'index.html')

    @app.route('/<path:path>')
    def static_files(path):
        fp = os.path.join(_DIST, path)
        if os.path.isfile(fp):
            return send_from_directory(_DIST, path)
        return send_from_directory(_DIST, 'index.html')  # SPA fallback


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
