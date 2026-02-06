import sqlite3
from flask import Flask, jsonify, request

app = Flask(__name__)

@app.route('/addrow')
def addrow():
    return "Row added!"

if __name__=='__main__':
    app.run(debug=True)