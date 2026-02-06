import sqlite3
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app) # enable CORS for all routes and origins

# TypeError: Failed to fetch
# To deal with CORS
# On server: pip install Flask-CORS
# In code: import CORS, enable all routes and origins

@app.route('/addrow')
def addrow():
    return "Row added!"

# To access this api remotely on the nextwork
# you must include the host as 0.0.0.0. This
# allows flask to listen on more than just localhost.
if __name__=='__main__':
    app.run(debug=True, host='0.0.0.0', port=8001)