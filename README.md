Python REST-server
=============

Forked from:

- [Designing a RESTful API with Python and Flask](http://blog.miguelgrinberg.com/post/designing-a-restful-api-with-python-and-flask)
- [Designing a RESTful API using Flask-RESTful](http://blog.miguelgrinberg.com/post/designing-a-restful-api-using-flask-restful)

Setup
-----

- Install Python 2.7 and git.
- Run `setup.sh`
- Run `./rest-server.py` to start the server

Deploy a change
---------------

- SSH to root@188.226.203.74 (you need a key, and also forward your SSH key in /etc/ssh/ssh_config)
- cd python-rest-server
- git pull
- service pypredict restart
