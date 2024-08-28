from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from flask_pymongo import PyMongo
from flask_mqtt import Mqtt
from datetime import datetime
import random
import json

from flask_cors import cross_origin, CORS
from dotenv import load_dotenv

import os

from celery import Celery, Task
from celery.signals import worker_ready
from celery.result import AsyncResult

from flask_session import Session
from redis import Redis

from flask_bcrypt import Bcrypt

load_dotenv()

def create_app():
    app = Flask(__name__)

    app.config['MONGO_URI'] = os.getenv('FLASK_MONGO_URI')
    app.config['UPSTASH_URI'] = os.getenv('FLASK_UPSTASH_URI')
    
    return app

def celery_init_app(app: Flask) -> Celery:
    class FlaskTask(Task):
        def __call__(self, *args: object, **kwargs: object) -> object:
            with app.app_context():
                return self.run(*args, **kwargs)

    celery_app = Celery(app.name, task_cls=FlaskTask)
    celery_app.config_from_object(app.config["CELERY"])
    celery_app.set_default()
    app.extensions["celery"] = celery_app
    return celery_app

app = create_app()

# init mongo
mongo = PyMongo(app)

# init celery with upstash as broker
app.config.from_mapping(
    CELERY=dict(
        broker_url=app.config['UPSTASH_URI'],
        result_backend=app.config['UPSTASH_URI'],
        task_ignore_result=True,
    ),
)

app.config['CELERY_TIMEZONE'] = 'UTC'
celery_app = celery_init_app(app)

# init session
app.config['SESSION_REDIS'] = Redis(host='redis', port=6379)
# app.config['SESSION_REDIS'] = Redis(host=os.getenv('FLASK_SESSION_HOST'), port=os.getenv('FLASK_SESSION_PORT'), password=os.getenv('FLASK_SESSION_PASSWORD'), ssl=False)

app.config['SESSION_TYPE'] = 'redis'
Session(app)

# init cors
CORS(app, supports_credentials=True, origins='http://localhost:3000', expose_headers='Access-Control-Allow-Credentials')

# init bcrypt
bcrypt = Bcrypt(app)

@celery_app.task(name='return_something')
def return_something():
    print('this is something')
    return 'this is something'

"""get current user"""
@app.route('/get-user')
# @cross_origin(supports_credentials=True)
def get_user():
    user_id = session.get('user_id', 'no user logged in')
    return {'msg': user_id, 'code': 200 if user_id != 'no user logged in' else 401}
    
"""function called by react to verify credential"""
@app.route('/verify', methods=['POST'])
# @cross_origin(supports_credentials=True)
def verify():    
    data = request.json
    if 'username' and 'password' not in data:
        return {'msg': 'incorrect json key, use username and password'}
    
    username = data.get('username')
    password = data.get('password')
    print(username)
    print(password)

    # verify
    res = mongo.db.user.find_one({'username': username})
    if not res:
        return {'msg': 'no user', 'code': 401}
        
    print(res)
    print(res.keys())
    valid = bcrypt.check_password_hash(res['password'], password)
    if not valid:
        return {'msg': 'incorrect username and password', 'code': 401}
    print('correct username and password')

    if session:
        print('there is a session')
        # regenerate session to mitigate session fixation
        app.session_interface.regenerate(session)
    else:
        print('there isn\'t a session')

    # add user id session
    session['user_id'] = username
    print('added session is ' + session.get('user_id'))

    # return res
    return {'data': [username, password], 'code': 200, 'session_id': session.get('user_id')}


"""function to register user"""
@app.route('/register', methods=['POST'])
def register():
    if request.method == 'POST':
        username = request.json.get('username')
        password = request.json.get('password')

        # find
        res = mongo.db.user.find_one({'username': username})
        # add
        if not res:
            mongo.db.user.insert_one({'username': username, 'password': bcrypt.generate_password_hash(password).decode('utf-8')})
            return {'msg': 'register successful', 'code': 201}

        return {'msg': 'already taken', 'code': 409}
        

"""function to logout and clear session"""
@app.route('/logout')
# @cross_origin(supports_credentials=True)
def logout():
    session.clear()
    return {'msg': 'logged out', 'code': 200}
    
"""
Generate random data, save, and push to database

Create collection in myDatabase 'humidity'
"""

app.config['MQTT_BROKER_URL'] = 'broker.hivemq.com'  # use the free broker from HIVEMQ
app.config['MQTT_BROKER_PORT'] = 1883  # default port for non-tls connection
app.config['MQTT_USERNAME'] = ''  # set the username here if you need authentication for the broker
app.config['MQTT_PASSWORD'] = ''  # set the password here if the broker demands authentication
app.config['MQTT_KEEPALIVE'] = 5  # set the time interval for sending a ping to the broker to 5 seconds
app.config['MQTT_TLS_ENABLED'] = False  # set TLS to disabled for testing purposes

# app.config['MQTT_CLIENT_ID'] = f'python-mqtt-14'

import ssl

# Parameters for SSL enabled
# app.config['MQTT_TLS_ENABLED'] = True
# app.config['MQTT_TLS_VERSION'] = ssl.PROTOCOL_TLSv1_2

# app.config['MQTT_TLS_CA_CERTS'] = 'pwa/broker.emqx.io-ca.crt'
# app.config['MQTT_TLS_CERTFILE'] = 'C:/Users/user/Desktop/Programming/freelance-pwa/env/Lib/site-packages/certifi/cacert.pem'

# app.config['MQTT_TRANSPORT'] = 'websockets'

topic = '/jarren/mqtt'

mqtt_client = Mqtt(app, connect_async=True)

@mqtt_client.on_connect()
def handle_connect(client, userdata, flags, rc):
   if rc == 0:
       print('Connected successfully')
       mqtt_client.subscribe('/jarren/mqtt') # subscribe topic
   else:
       print('Bad connection. Code:', rc)


@mqtt_client.on_message()
def handle_mqtt_message(client, userdata, message):
   data = dict(
       topic=message.topic,
       payload=message.payload.decode()
  )
#    print('Received message on topic: {topic} with payload: {payload}'.format(**data))
   print('Received message on topic: {topic} with payload')

from flask_mqtt import MQTT_LOG_ERR, MQTT_LOG_DEBUG, MQTT_LOG_INFO, MQTT_LOG_NOTICE, MQTT_LOG_WARNING

@mqtt_client.on_log()
def handle_logging(client, userdata, level, buf):
    if level == MQTT_LOG_ERR:
        print('Error: {}'.format(buf))
    if level == MQTT_LOG_DEBUG:
        print('Debug: {}'.format(buf))
    if level == MQTT_LOG_INFO:
        print('Info: {}'.format(buf))
    if level == MQTT_LOG_NOTICE:
        print('Notice: {}'.format(buf))
    if level == MQTT_LOG_WARNING:
        print('Warning: {}'.format(buf))
    
@mqtt_client.on_publish()
def handle_publish(client, userdata, mid):
    print('Published message with mid {}.'
            .format(mid))

"""publish test function"""
@app.route('/publish', methods=['GET'])
def publish_message():
    """
    Generate random number
    Insert to database
    Get data from database
    Send to front-end
    """
    
    mongo.db.humidity.insert_one({
        'timedate': datetime.now().strftime("%m/%d/%Y, %H:%M:%S"),
        'humidity': random.randint(60, 80)
    })

    res = mongo.db.humidity.find({}, {"_id": 0, "timedate": 1, "humidity": 1}).limit(10)


    """
    convert to list
    convert to json
    send
    """
    list_res = list(res)
    print('list res', list_res)
    td = {
        'data': list_res
    }
    final = json.dumps(td, indent=2)
    print('final', final)
    request_data = {
        'topic': '/jarren/mqtt',
        'msg': 'sdfsfdfs this is final bang kampret la'
    }
    publish_result = mqtt_client.publish('/jarren/mqtt', 'this is qos 1', qos=1)

    publish_result = mqtt_client.publish('/jarren/mqtt', 'this is qos 2', qos=2)

    return jsonify({'code': publish_result[0]})

import time

"""publish test function as a task in celery"""
@celery_app.task
@app.route('/celery-publish', methods=['GET'])
def celery_publish_message():
    time.sleep(5)
    publish_result = mqtt_client.publish('/jarren/mqtt', 'publish with celery task')

    return jsonify({'code': publish_result[0]})

import paho.mqtt.client as mqtt

def on_publish(client, userdata, mid):
    # reason_code and properties will only be present in MQTTv5. It's always unset in MQTTv3
    try:
        userdata.remove(mid)
    except KeyError:
        print("on_publish() is called with a mid not present in unacked_publish")
        print("This is due to an unavoidable race-condition:")
        print("* publish() return the mid of the message sent.")
        print("* mid from publish() is added to unacked_publish by the main thread")
        print("* on_publish() is called by the loop_start thread")
        print("While unlikely (because on_publish() will be called after a network round-trip),")
        print(" this is a race-condition that COULD happen")
        print("")
        print("The best solution to avoid race-condition is using the msg_info from publish()")
        print("We could also try using a list of acknowledged mid rather than removing from pending list,")
        print("but remember that mid could be re-used !")

mqttc = mqtt.Client()
mqttc.on_publish = on_publish
mqttc.on_log = handle_logging


@celery_app.task(task_ignore_result=False)
def add():
    # print(mqtt_client.broker_url)
    # publish_result = mqtt_client.publish('/jarren/mqtt', 'tt', qos=2)
    # print('res is ' + str(publish_result[0]))

    # unacked_publish = set()

    # unacked_publish.add(publish_result[1])

    # # Wait for all message to be published
    # while len(unacked_publish):
    #     time.sleep(0.1)

    # # Due to race-condition described above, the following way to wait for all publish is safer
    # publish_result.wait_for_publish()

    # return publish_result

    """Revision 0.1"""
    unacked_publish = set()

    mqttc.user_data_set(unacked_publish)
    mqttc.connect(app.config['MQTT_BROKER_URL'], app.config['MQTT_BROKER_PORT'])
    mqttc.loop_start()

    # Our application produce some messages
    msg_info = mqttc.publish("/jarren/mqtt", "my message", qos=1)
    unacked_publish.add(msg_info.mid)

    msg_info2 = mqttc.publish("/jarren/mqtt", "my message2", qos=1)
    unacked_publish.add(msg_info2.mid)

    # Wait for all message to be published
    while len(unacked_publish):
        time.sleep(0.1)

    # Due to race-condition described above, the following way to wait for all publish is safer
    msg_info.wait_for_publish()
    msg_info2.wait_for_publish()

    mqttc.disconnect()
    mqttc.loop_stop()

    return msg_info.mid


@app.route('/add')
def send_add():
    # res = add.apply_async(countdown=10)
    res = add.delay()
    # time.sleep(5)
    return {'code': res.id}

@app.route('/get-add')
def get_add():
    return 


@app.get("/result/<string:id>")
def task_result(id: str) -> dict[str, object]:
    result = AsyncResult(id)
    return {
        "ready": result.ready(),
        "successful": result.successful(),
        "value": result.result if result.ready() else None,
    }

"""publish test function as a task in celery with schedule"""
@celery_app.task(name='koko')
def celery_schedule_publish_message():
    publish_result = mqtt_client.publish('/jarren/mqtt', 'publish with celery task with schedule')

    return jsonify({'code': publish_result[0]})

"""function to create new data, insert to db, and send to frontend. Called at an interval to simulate realtime data"""
@celery_app.task(name='send_mqtt')
@app.route('/pb', methods=['GET'])
def pm():
    """
    Generate random number
    Insert to database
    Get data from database
    Send to front-end
    """
    
    mongo.db.humidity.insert_one({
        'timedate': datetime.now().strftime("%m/%d/%Y, %H:%M:%S"),
        'humidity': random.randint(60, 80)
    })

    res = mongo.db.humidity.find({}, {"_id": 0, "timedate": 1, "humidity": 1}).sort('_id', -1).limit(10)

    """
    convert to list
    convert to json
    send
    """
    list_res = list(res)[::-1]
    # print('list res', list_res)
    td = {
        'data': list_res
    }
    final = json.dumps(td, indent=2)
    # print('final', final)
    request_data = {
        'topic': '/jarren/mqtt',
        'msg': 'this is celery function'
    }

    # pr = mqtt_client.publish('/jarren/new/mqtt', 'idk what this is')
    # print('the code is', pr[0], pr[1])
    # publish_result = mqtt_client.publish('/jarren/mqtt', 'this is celery func')
    
    unacked_publish = set()

    mqttc.user_data_set(unacked_publish)
    mqttc.connect(app.config['MQTT_BROKER_URL'], app.config['MQTT_BROKER_PORT'])
    mqttc.loop_start()

    # Send data
    msg_info = mqttc.publish("/jarren/mqtt", final, qos=1)
    unacked_publish.add(msg_info.mid)

    # Due to race-condition described above, the following way to wait for all publish is safer
    msg_info.wait_for_publish()

    # Wait for all message to be published
    while len(unacked_publish):
        time.sleep(0.1)

    mqttc.disconnect()
    mqttc.loop_stop()

    return msg_info.mid

    # return {'code': publish_result[0]}
    
"""function to initialize starting data for linechart on front end"""
@app.route('/get-data')
# @cross_origin(supports_credentials=True)
def get_data():
    """
    find collection
    reverse
    convert to json string
    """
    res = mongo.db.humidity.find({}, {"_id": 0, "timedate": 1, "humidity": 1}).sort('_id', -1).limit(10)
    list_res = list(res)[::-1]
    # print('list res', list_res)
    final = json.dumps(list_res, indent=2)
    # print('final', final)
    return final


celery_app.conf.beat_schedule = {
    'sendfool': {
        'task': 'send_mqtt',
        'schedule': 10,
    }
}

# @celery_app.on_after_configure.connect
# def setup_periodic_tasks(sender, **kwargs):
    # sender.add_periodic_task(10, pm.s(), name='send_mqtt') # change to 5 second when production
    # sender.add_periodic_task(10, celery_schedule_publish_message.s()) # change to 5 second when production
    # pass

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8000, use_reloader=False)