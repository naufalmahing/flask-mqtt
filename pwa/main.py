from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_pymongo import PyMongo
from flask_mqtt import Mqtt
from datetime import datetime
import random
import json

from apscheduler.schedulers.background import BackgroundScheduler
import atexit

from flask_cors import cross_origin

app = Flask(__name__)
app.config['MONGO_URI'] = 'changethistoyoursplease hahaha'

mongo = PyMongo(app)

# testing
@app.route("/")
def index():
    mongo.db.humidity.insert_one({
        'timedate': datetime.now(),
        'humidity': random.randint(60, 80)
    })

    """
    Generate random number
    Insert to database
    Get data from database
    Send to front-end
    """

    res = mongo.db.humidity.find({}, {"_id": 0, "timedate": 1, "humidity": 1})

    for x in res:
        print(x)

    return {
        'data': 'this is home'
    }

@app.route('/login', methods=['GET', 'POST'])
@cross_origin()
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # verify
        res = mongo.db.user.find_one({'username': username, 'password': password})
        print(res)

        # return res
        if res:
            return redirect(url_for('index'))
        else:
            return 'wrong'
    else:
        return render_template('login.html')
    
# this is the function called by react
@app.route('/verify', methods=['POST'])
@cross_origin()
def verify():    
    data = request.json
    username = data.get('username')
    password = data.get('password')
    print(username)
    print(password)

    # verify
    res = mongo.db.user.find_one({'username': username, 'password': password})
    print(res)

    # return res
    if res:
        return {'data': [username, password], 'code': 200}
    else:
        return {'code': 404}

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # find
        res = mongo.db.user.find_one({'username': username})
        # add
        if not res:
            mongo.db.user.insert_one({'username': username, 'password': password})
        else:
            return 'already taken'
        
        return redirect(url_for('login'))
    else:
        return render_template('register.html')
    
"""
Generate random data, save, and push to database

Create collection in myDatabase 'humidity'
"""

app.config['MQTT_BROKER_URL'] = 'broker.emqx.io'
app.config['MQTT_BROKER_PORT'] = 1883
app.config['MQTT_USERNAME'] = ''  # Set this item when you need to verify username and password
app.config['MQTT_PASSWORD'] = ''  # Set this item when you need to verify username and password
app.config['MQTT_KEEPALIVE'] = 5  # Set KeepAlive time in seconds
app.config['MQTT_TLS_ENABLED'] = False  # If your broker supports TLS, set it True
topic = '/jarren/mqtt'

mqtt_client = Mqtt(app)

@mqtt_client.on_connect()
def handle_connect(client, userdata, flags, rc):
   if rc == 0:
       print('Connected successfully')
       mqtt_client.subscribe(topic) # subscribe topic
   else:
       print('Bad connection. Code:', rc)


@mqtt_client.on_message()
def handle_mqtt_message(client, userdata, message):
   data = dict(
       topic=message.topic,
       payload=message.payload.decode()
  )
   print('Received message on topic: {topic} with payload: {payload}'.format(**data))

# testing
@app.route('/publish', methods=['POST'])
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

    res = mongo.db.humidity.find({}, {"_id": 0, "timedate": 1, "humidity": 1})


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
        'topic': '/flask/mqtt',
        'msg': final
    }
    publish_result = mqtt_client.publish(request_data['topic'], request_data['msg'])
    return jsonify({'code': publish_result[0]})

# this is the function that's called by react to get realtime data
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
    print('list res', list_res)
    td = {
        'data': list_res
    }
    final = json.dumps(td, indent=2)
    print('final', final)
    request_data = {
        'topic': topic,
        'msg': final
    }
    publish_result = mqtt_client.publish(request_data['topic'], request_data['msg'])
    return jsonify({'code': publish_result[0]})

# start scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(func=pm, trigger="interval", seconds=5)
scheduler.start()

# Shut down the scheduler when exiting the app
atexit.register(lambda: scheduler.shutdown())
    
# this is the function that's called to initialize starting data for linechart in react
@app.route('/get-data')
@cross_origin()
def get_data():
    res = mongo.db.humidity.find({}, {"_id": 0, "timedate": 1, "humidity": 1}).sort('_id', -1).limit(10)
    list_res = list(res)[::-1]
    print('list res', list_res)
    final = json.dumps(list_res, indent=2)
    print('final', final)
    return final

if __name__ == '__main__':
    app.run(debug=True)
