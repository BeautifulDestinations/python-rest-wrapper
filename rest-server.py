#!flask/bin/python
import six
import time
import threading
import Queue
from flask import Flask, jsonify, abort, request, make_response, url_for
from flask.ext.httpauth import HTTPBasicAuth
from werkzeug import secure_filename
import os

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])

app = Flask(__name__, static_url_path="")
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

auth = HTTPBasicAuth()
jobs = Queue.Queue()

class Promise():
    value = None
    queue = Queue.Queue(1)
    def fullfill(self, x):
        try:
            self.value = x
            self.queue.put(None)
        except Queue.Full:
            return None
    def sync(self):
        while(True):
            try:
                self.queue.get(True, 1)
                return self.value
            except Queue.Empty:
                x = 1
                # Nothing
        return None
        # TODO

class Job:
    filename   = None
    parameters = None
    promise   = None
    def __init__(self, filename, parameters, promise):
        self.filename   = filename
        self.parameters = parameters
        self.promise    = promise

def job_handler():
    while (True):
        job = jobs.get()
        print("Processing ", job.filename, job.parameters)
        # Do image processing stuff with job.filename and job.parameters
        # Send result to promise
        job.promise.fullfill({'this':1, 'is':2, 'a':[1,2,3,4], 'result':True})

@auth.get_password
def get_password(username):
    if username == 'miguel':
        return 'python'
    return None


@auth.error_handler
def unauthorized():
    # return 403 instead of 401 to prevent browsers from displaying the default
    # auth dialog
    return make_response(jsonify({'error': 'Unauthorized access'}), 403)


@app.errorhandler(400)
def bad_request(error):
    return make_response(jsonify({'error': 'Bad request'}), 400)


@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

@app.route('/api/v1/predict', methods=['POST'])
def uploadImage():
    # return jsonify({'status': 'ok'})
    file = request.files['file']
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        # TODO assure uploads directory
        # Write to ./uploads
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        # TODO post to job queue with future

        prom = Promise()
        jobs.put(Job(os.path.join(app.config['UPLOAD_FOLDER'], filename), {'myParameter':None}, prom))

        r = prom.sync()
        return jsonify({'status': r})


if __name__ == '__main__':
    t = threading.Thread(target = job_handler)
    t.daemon = True
    t.start()
    app.run(debug=True)
