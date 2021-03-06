from flask import Flask, render_template, request, redirect, session, url_for, jsonify
from twilio.rest import TwilioRestClient
import boto
import json
import os

app = Flask(__name__)

sdb = boto.connect_sdb(os.environ['AWS_ACCESS_KEY_ID'], os.environ['AWS_SECRET_ACCESS_KEY'])
client = TwilioRestClient(os.environ['TWILIO_KEY'], os.environ['TWILIO_SECRET'])
members = sdb.get_domain('members')
notifications = sdb.get_domain('notifications')
members_list = {}
notifications_list = []

for item in members:
  members_list[item.name] = {'name': item['name'], 'gender': item['gender'], 'height' : item['height'], 'weight' : item['weight'], 'eye_color' : item['eye_color'], 'hair_color' : item['hair_color'], 'picture' : item['picture'], 'user_number' : item['user_number'], 'emergency_number' : item['emergency_number']}

for item in notifications:
  message = ''
  if item['type'] == 'timer':
    message = 'A timer has gone off!'
  else:
    message = 'An escort has been requested.'

  notification = [item['latitude'], item['longitude'], members_list[item.name], message, item.name, item['type']]
  notifications_list.append(notification)

#check if logged in, redirect to homepage
@app.route('/')
def home():
  if 'user' in session:
    return render_template('home.html', coordinates=notifications_list, coordinates_json=json.dumps(notifications_list))
  return redirect(url_for('login'))

#when a user registers he is added to the db
@app.route('/addmember', methods=['POST'])
def add_member():
  new_member = members.new_item(request.form['email'])
  new_member['name'] = request.form['name']
  new_member['gender'] = request.form['gender']
  new_member['height'] = request.form['height']
  new_member['weight'] = request.form['weight']
  new_member['eye_color'] = request.form['eye_color']
  new_member['hair_color'] = request.form['hair_color']
  new_member['picture'] = "http://" + request.form['picture']
  new_member['user_number'] = request.form['user_number']
  new_member['emergency_number'] = request.form['emergency_number']
  new_member.save()
  members_list[request.form['email']] = {'name': request.form['name'], 'gender': request.form['gender'], 'height' : request.form['height'], 'weight' : request.form['weight'], 'eye_color' : request.form['eye_color'], 'hair_color' : request.form['hair_color'], 'picture' : "http://" + request.form['picture'], 'user_number': request.form['user_number'], 'emergency_number': request.form['emergency_number']}
  return jsonify([])

#when a timer goes off a notification is added to the database
@app.route('/addnotification', methods=['POST'])
def add_notification():
  print request.form
  new_notification = notifications.new_item(request.form['email'])
  new_notification['latitude'] = request.form['latitude']
  new_notification['longitude'] = request.form['longitude']
  new_notification['type'] = request.form['type']
  if request.form['type'] == 'timer':
    new_notification['message'] = "A timer has gone off!"
    lat = new_notification['latitude']
    longitude = new_notification['longitude']
    location = "http://maps.google.com/?ie=UTF8&q=e@" + lat + "," + longitude
    bod = "SafetyPenn Alert!" + members_list[request.form['email']]['name'] + " is in trouble! You can find " + members_list[request.form['email']]['name'] + " here: " + location
    client.messages.create(to=members_list[request.form['email']]['emergency_number'], from_="+12674158806", body=bod)
  else:
    new_notification['message'] = "An escort has been requested"
  new_notification.save()

  notification = [new_notification['latitude'], new_notification['longitude'], members_list[request.form['email']], new_notification['message'], request.form['email'], request.form['type']]
  inList = False
  for notif in notifications_list:
    if notif[4] == request.form['email']:
      notif = notification
      inList = True
  if inList is False:
    notifications_list.append(notification)
  return jsonify([])

@app.route('/edit', methods=['POST'])
def edit():
  print 'here'
  print request.form
  email = request.form['email']
  user = members.get_item(email)
  print email
  print user
  try:
    picture = "http://" + request.form['picture']
    user['picture'] = picture
    members_list[email]['picture'] = picture
    user.save()
  except KeyError:
    print "do nothing"
  try:
    emergency = request.form['emergency_number']
    user['emergency_number'] = emergency
    members_list[email]['emergency_number'] = emergency
    user.save()
  except KeyError:
    print "do nothing"
  return jsonify([])


@app.route('/remove')
def remove_notification():
  print 'remove'
  id = request.args.get('id', '')
  print "id = " + id
  for notification in notifications_list:
    if notification[4] == id:
      print "found notification"
      if notification[5] == 'escort':
        print "print notification is escort"
        client.messages.create(to=members_list[notification[4]]['user_number'], from_="+12674158806", body="An escort has been sent to your location")
        print "message sent"
      notifications_list.remove(notification)
  notifications.delete_item(notifications.get_item(id))
  return redirect(url_for('home'))

@app.route('/login', methods=['GET', 'POST'])
def login():
  if request.method == 'POST':
    username = request.form['username']
    password = request.form['password']
    if username == 'admin' and password == 'password':
      session['user'] = username
      return redirect(url_for('home'))
    else:
      return render_template('login.html', loginError=True)
  else:
    return render_template('login.html')

@app.route('/logout')
def logout():
  # remove the username from the session if it's there
  session.pop('username', None)
  session.clear()
  return redirect('/login')

# set the secret key.  keep this really secret:
app.secret_key = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT'

if __name__ == '__main__':
  app.run(debug=True)
