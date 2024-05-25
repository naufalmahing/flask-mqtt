# Overview
Run flask app in local and deploy react in netlify

# Running the flask app 
install packages needed for flask application
`pip install -r requirements.txt`
if you want to, you can create virtual environment

start the app using this command
`python main.py`
or this command
`flask --app main run`
use the command in flask project directory, where main.py is located.
It's ready to be used as an api. It will run on port 5000, if you want to change the port also change the code in react to call the same port.

## Mongodb
I config the app to run on my mongodb cloud database you can use it for a while, you can create your own database as it's free.

# Deploy react app to netlify
Create netlify account. Upload build output to netlify and you can see your dashboard

As I don't create session for this react, you need to go to login page by url by appending
`/login`
use this credential to login, as I've created this in my database and haven't created register function
```
username: user
password: pass
```
and you will be directed to previous page

select wss protocol to be able to use on netlify
# Implementation
Implementing MQTT I create a form to connect and subscribe, so there won't be too much input message from the broker. I use MQTT Public so there's a chance you're using the same topic to send message as other people, to handle that you can change the topic in react and flask. There's an input for topic in react so you can change it from there, for flask you have to change from the code in main.py there will be a variable called topic.

Just explaining, you need to use the same topic to connect.

Also to simulate realtime data, I use random int and insert to database every 5 second. To change the interval go to main.py in flask project and find .add_job there you can change 'seconds' parameter to minutes, hours, etc. Check apscheduler package documentation.
