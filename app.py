from flask import Flask, request, render_template, redirect, url_for, jsonify, session
from flaskwebgui import FlaskUI
from lib.lib import simple_do_all, get_current_status_msg, get_estimated_video_duration

# We got to import all modules manually for PyInstaller to work. Use AUTOPYTOEXE in case the imports have changed since the date of writing this.
# See: https://github.com/Zulko/moviepy/issues/591#issuecomment-965203931

from importhelper import *

# Windows app icon fix (taskbar and taskbar manager)
import ctypes
myappid = u'mycompany.myproduct.subproduct.version' # arbitrary string
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

app = Flask(__name__)
gui = FlaskUI(app)

@app.route('/')
def home():
    if request.method == 'POST':
        q = request.form['query']
        return render_template('index.html', query=q)
    return render_template('index.html')

@app.route('/api/status', methods=['GET'])
def api_get_current_status_msg():
    return jsonify({'status': get_current_status_msg()})

@app.route('/api/compilationLength', methods=['GET'])
def api_get_estimated_video_duration():
    duration = get_estimated_video_duration()
    if duration == (0, 0, 0):
        # return jsonify({'compilationLength': 'cannot estimate resulting video duration yet.'})
        return jsonify({'compilationLength': 'n/a'})
    displayMsg = f'{duration[0]} hours, {duration[1]} minutes, {duration[2]} seconds'
    return jsonify({'compilationLength': displayMsg})

@app.route('/api/do', methods=['POST'])
def api_do_all():
    r = request.json
    channel = r['channel'].strip()
    period = r['period']
    simple_do_all(channel, period)
    return jsonify({'msg': get_current_status_msg()})


if __name__ == '__main__':
    app.run(debug=True)
    # gui.run()