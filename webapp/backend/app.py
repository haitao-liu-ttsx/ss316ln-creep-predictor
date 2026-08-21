"""V1.3 316LN creep field predictor API (V1.2 removed).

POST /api/predict_v13  {T,P,t,Rm,Ro,w} -> 7 fields (2304 each) + von Mises
                       + centroids + summary + domain status
Serves the built frontend (dist/) in production (single-service deploy).
"""
import json
import os

from flask import Flask, jsonify, request
from flask_cors import CORS

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

app = Flask(__name__)
CORS(app)


@app.route('/api/predict_v13', methods=['POST'])
def api_predict_v13():
    try:
        import sys
        sys.path.insert(0, os.path.join(ROOT, 'ml'))
        from v13.predictor import predict_serializable
    except ImportError:
        import sys
        sys.path.insert(0, os.path.join(ROOT, 'ml', 'v13'))
        from predictor import predict_serializable
    data = request.get_json(force=True)
    try:
        T = float(data['T']); P = float(data['P']); t = float(data['t'])
        Rm = float(data['Rm']); Ro = float(data['Ro']); w = float(data['w'])
    except (KeyError, TypeError, ValueError):
        return jsonify({'status': 'INPUT_INVALID', 'errors': ['missing or non-numeric parameter']})
    return jsonify(predict_serializable(T, P, t, Rm, Ro, w))


@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'model': 'V1.3', 'schema': 'v13.1', 'status': 'READY'})


# ---- production static serving (single-service deploy) ----
_DIST = os.path.join(ROOT, 'webapp', 'frontend', 'dist')
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
