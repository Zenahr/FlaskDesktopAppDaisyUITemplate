from flask import Flask, request, render_template, redirect, url_for, jsonify, session
from flaskwebgui import FlaskUI

app = Flask(__name__)
ui = FlaskUI(app)

@app.route('/')
def hello():
    if request.method == 'POST':
        q = request.form['query']
        return render_template('index.html', query=q)
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
    # ui.run() # toggle this line and comment out the above line to turn the web app into a desktop app.
