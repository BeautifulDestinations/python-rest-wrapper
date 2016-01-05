#!flask/bin/python
import six
import time
import threading
import Queue
from   flask              import Flask, jsonify, abort, request, make_response, url_for
from   flask.ext.httpauth import HTTPBasicAuth
from   werkzeug           import secure_filename
import os

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])

app = Flask(__name__, static_url_path="")
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

auth = HTTPBasicAuth()
jobs = Queue.Queue()

import sys
wkDir = os.getcwd()
baseDir = wkDir.partition('/python-rest-wrapper')[0]
sys.path.append( baseDir+'/theano_playground' )

import deployed_model

###
### Import model here
###
from deployed_model import model1

print '\nModel imported!\n'

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
    fileName   = None
    parameters = None
    promise    = None
    def __init__(self, fileName, parameters, promise):
        self.fileName   = fileName
        self.parameters = parameters
        self.promise    = promise

def job_handler():
    while (True):
        job = jobs.get()
        print("Processing ", job.fileName, job.parameters)
        # Do image processing stuff with job.fileName and job.parameters
        pred = model1.make_prediction( job.fileName, job.parameters )
        # Send result to promise
        job.promise.fullfill( {'name': job.fileName, 'this':pred} )

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

def allowed_file(fileName):
    return '.' in fileName and \
           fileName.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

@app.route('/api/v1/predict', methods=['POST'])
def uploadImage():
    file = request.files['file']
    if file and allowed_file(file.filename):
        fileName     = secure_filename(file.filename)
        longFileName = os.path.join(app.config['UPLOAD_FOLDER'], fileName)

        if not os.path.exists('uploads'):
            os.makedirs('uploads')
        file.save(longFileName)

        prom = Promise()
        jobs.put(Job(longFileName, {'myParameter' : None}, prom))
        result = prom.sync()

        return jsonify(result)


if __name__ == '__main__':
    t = threading.Thread(target = job_handler)
    t.daemon = True
    t.start()
    app.run(debug=True)
