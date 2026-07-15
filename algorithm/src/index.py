"""
index.py
 
Entry point for the algorithm microservice. Run standalone with
`python src/index.py` (see algorithm/requirements.txt) -- it's a separate
process/deployment from the main Flask backend, which calls it over HTTP
(see ALGORITHM_SERVICE_URL in the root app.py).
"""
import os
import sys
 
# Make `algorithm/` (this file's grandparent folder) importable as a
# package root, regardless of the working directory this is launched
# from -- this is what lets routes/ and src/ import from each other with
# plain `from src.services...` / `from routes...` statements below.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
 
from dotenv import load_dotenv
load_dotenv()
 
from flask import Flask
from flask_cors import CORS
 
from routes.recommednation_routes import recommend_bp
 
app = Flask(__name__)
CORS(app)
app.register_blueprint(recommend_bp)
 
 
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 4000))
    app.run(host='0.0.0.0', port=port, debug=True)
    