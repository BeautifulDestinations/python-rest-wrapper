#!flask/bin/python
import six
import time
import threading
import Queue
import PIL
from   PIL                import Image
from   flask              import Flask, jsonify, abort, request, make_response, url_for, send_from_directory
from   flask.ext.httpauth import HTTPBasicAuth
from   werkzeug           import secure_filename
import os
import sys
import string
import imagehash

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])

app = Flask(__name__, static_url_path="")
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

auth = HTTPBasicAuth()
jobs = Queue.Queue()

wkDir = os.getcwd()
baseDir = wkDir.partition('/python-rest-wrapper')[0]
sys.path.append( baseDir+'/theano_playground' )

import deployed_model
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
    jobType    = None
    parameters = None
    promise    = None
    def __init__(self, jobType, fileName, parameters, promise):
        self.jobType    = jobType
        self.fileName   = fileName
        self.parameters = parameters
        self.promise    = promise

def job_handler():
    while (True):
        job = jobs.get()
        with open( 'logFiles/queue.log', 'a' ) as f:
            f.write( str( jobs.qsize() ) )
        if job.jobType == 'predict':
            # Do image processing stuff with job.fileName and job.parameters
            pred = model1.make_prediction( job.fileName, job.parameters )
            # Send result to promise
            job.promise.fullfill( {'name': job.fileName, 'predictions':pred} )
        if job.jobType == 'enhance':
            img = deployed_model.enhance_image_clahe_on_LAB( job.fileName, job.parameters )
            img_hash = imagehash.average_hash( img )
            fpath = 'enhancement_results/'+str( img_hash ) + '.jpg'
            img.save( fpath )
            # Send result to promise
            job.promise.fullfill( {'name': job.fileName, 'url':fpath} )

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

@app.route('/api/v1/enhance', methods=['POST'])
def enhanceImage():
    file = request.files['file']
    if file and allowed_file(file.filename):
        # Auto generate filename to avoid clashes
        fileName     = secure_filename(file.filename)
        longFileName = os.path.join(app.config['UPLOAD_FOLDER'], fileName)

        assure_dir_exists()

        file.save(longFileName)

        prom = Promise()
        jobs.put(Job('enhance', longFileName, {'myParameter' : None}, prom))
        result = prom.sync()

        return jsonify(result)

@app.route('/api/v1/predict', methods=['POST'])
def uploadImage():
    file = request.files['file']
    if file and allowed_file(file.filename):
        # Auto generate filename to avoid clashes
        fileName     = secure_filename(file.filename)
        longFileName = os.path.join(app.config['UPLOAD_FOLDER'], fileName)

        assure_dir_exists()

        file.save(longFileName)

        prom = Promise()
        jobs.put(Job('predict', longFileName, {'myParameter' : None}, prom))
        result = prom.sync()

        return jsonify(result)

@app.route('/enhancement_results/<path:path>')
def send_img(path):
    return send_from_directory('enhancement_results/', path)


def assure_dir_exists():
   if not os.path.exists('uploads'):
       os.makedirs('uploads')
   if not os.path.exists('enhancement_results'):
       os.makedirs('enhancement_results')
   if not os.path.exists('logFiles'):
       os.makedirs('logFiles')

if __name__ == '__main__':
    t = threading.Thread(target = job_handler)
    t.daemon = True
    t.start()
    app.run(host= '0.0.0.0', debug=True)
