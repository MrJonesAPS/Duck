from gevent import monkey
monkey.patch_all()

import json
import os
import sqlite3

from datetime import date, datetime, timedelta
from flask import Flask, redirect, url_for, render_template, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
from flask_socketio import send, emit

from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
    UserMixin
)
from oauthlib.oauth2 import WebApplicationClient
import requests

#configuration
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", None)
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", None)
ADMIN_USER1_NUM = os.environ.get("ADMIN_USER1_NUM", None).strip()
ADMIN_USER2_NUM = os.environ.get("ADMIN_USER2_NUM", None).strip()
GOOGLE_DISCOVERY_URL = (
    "https://accounts.google.com/.well-known/openid-configuration"
)

app = Flask(__name__)
app.config.from_pyfile('instance/config.py')

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "home"
login_manager.login_message = "You are not logged in"

# OAuth 2 client setup
client = WebApplicationClient(GOOGLE_CLIENT_ID)

# Flask-Login helper to retrieve a user from our db
@login_manager.user_loader
def load_user(user_id):
    return get_user(user_id)

def get_google_provider_cfg():
    return requests.get(GOOGLE_DISCOVERY_URL).json()

@app.route("/login")
def login():
    # Find out what URL to hit for Google login
    google_provider_cfg = get_google_provider_cfg()
    authorization_endpoint = google_provider_cfg["authorization_endpoint"]

    # Use library to construct the request for Google login and provide
    # scopes that let you retrieve user's profile from Google
    request_uri = client.prepare_request_uri(
        authorization_endpoint,
        redirect_uri="https://www.duck.whscs.net/login/callback",
        scope=["openid", "email", "profile"],
    )
    return redirect(request_uri)

@app.route("/login/callback")
def callback():
    # Get authorization code Google sent back to you
    code = request.args.get("code")

    # Find out what URL to hit to get tokens that allow you to ask for
    # things on behalf of a user
    google_provider_cfg = get_google_provider_cfg()
    token_endpoint = google_provider_cfg["token_endpoint"]
    # Prepare and send a request to get tokens! Yay tokens!
    #For some reason, these request parameters were coming as http instead of https,
    #which was causing OAuth to throw errors.
    #I never figured out why, but this simple replace fixes it.
    token_url, headers, body = client.prepare_token_request(
        token_endpoint,
        authorization_response=request.url.replace("http:", "https:"),
        redirect_url=request.base_url.replace("http:", "https:"),
        code=code
    )
    token_response = requests.post(
        token_url,
        headers=headers,
        data=body,
        auth=(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET),
    )
       
    # Parse the tokens!
    client.parse_request_body_response(json.dumps(token_response.json()))

    # Now that you have tokens (yay) let's find and hit the URL
    # from Google that gives you the user's profile information,
    # including their Google profile image and email
    userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
    uri, headers, body = client.add_token(userinfo_endpoint)
    userinfo_response = requests.get(uri, headers=headers, data=body)

    # You want to make sure their email is verified.
    # The user authenticated with Google, authorized your
    # app, and now you've verified their email through Google!
    if userinfo_response.json().get("email_verified"):
        unique_id = userinfo_response.json()["sub"]
        users_name = userinfo_response.json()["given_name"]
    else:
        return "User email not available or not verified by Google.", 400

    # Create a user in your db with the information provided
    # by Google
    user = get_user(unique_id)

    # Begin user session by logging the user in
    if user != None:
        login_user(user, remember=True)
    else:
        return ("You just tried to login with an unknown userid: " + unique_id), 400
    # Send user back to homepage
    return redirect(url_for('pass_admin'))

@app.route("/", methods=["GET"])
@app.route("/home")
def home():
    return render_template("home.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("pass_admin"))


@app.route("/helpQ", methods=["GET"])
def helpQ():
    if request.method == "GET":
        waiter_list = Waiter.query.all()
        return render_template("helpQ.html", waiter_list = waiter_list, current_user=current_user)   


@app.route("/pass_admin", methods=["GET"])
@login_required
def pass_admin():
    if request.method == "GET":
        new_pass_requests = db.session.execute(db.select(HallPass).\
                                               filter(HallPass.approved_datetime == None,
                                                      HallPass.rejected.is_(False))).scalars()
        approved_passes = db.session.execute(db.select(HallPass).\
                                             filter(HallPass.approved_datetime != None,
                                                    HallPass.back_datetime == None)).scalars()
        
        new_WP_requests = db.session.execute(db.select(WPPass).\
                                               filter(WPPass.approved_datetime == None,
                                                      WPPass.rejected.is_(False))).scalars()

        approved_WP = db.session.execute(db.select(WPPass).\
                                               filter(WPPass.approved_datetime != None,
                                                      WPPass.rejected.is_(False))).scalars()


        
        
        #####
        #When a student has an unapproved request, quack
        #####
        firstRecord_PassRequests = db.session.execute(db.select(HallPass).\
                                               filter(HallPass.approved_datetime == None,
                                                    HallPass.rejected.is_(False))).first()
        
        should_we_quack = (firstRecord_PassRequests != None)

        return render_template("pass_admin.html",
                               new_pass_requests = new_pass_requests,
                               approved_passes = approved_passes,
                               new_WP_requests = new_WP_requests,
                               approved_WP = approved_WP,
                               current_user=current_user,
                               should_we_quack=should_we_quack,
                               now = datetime.now,
                               int = int,
                               str = str
                               )

@app.route("/pass_history", methods=["GET"])
@login_required
def pass_history():
    if request.method == "GET":
        old_passes = db.paginate(db.select(HallPass).\
                                               filter(HallPass.approved_datetime != None,
                                                      HallPass.rejected.is_(False))
                                                      .order_by(HallPass.approved_datetime.desc()))

        return render_template("pass_history.html",
                               old_passes = old_passes,
                               current_user=current_user,
                               now = datetime.now,
                               int = int,
                               str = str
                               )

@app.route("/approve_pass/<id>", methods=["GET"])
@login_required
def approve_pass(id):
    print("approving pass",id)
    thisPass = db.session.execute(db.select(HallPass).filter_by(id=id)).scalar_one()
    thisPass.approved_datetime = datetime.now()
    db.session.commit()
    nowTime = datetime.now().strftime("%I:%M %p")
    nowDate = date.today().strftime("%B %d, %Y")
    socketio.emit('Pass'
        , {'name': thisPass.name
            , 'destination': thisPass.destination
            , 'passID': id
            }
        )
    return redirect(url_for("pass_admin"))  

@app.route("/reject_pass/<id>", methods=["GET"])
@login_required
def reject_pass(id):
    print("rejecting pass",id)
    thisPass = db.session.execute(db.select(HallPass).filter_by(id=id)).scalar_one()
    thisPass.rejected = True
    db.session.commit()
    return redirect(url_for("pass_admin"))  

@app.route("/approve_wp/<id>", methods=["GET"])
@login_required
def approve_wp(id):
    ###
    #I got some of this code from stackoverflow
    #https://stackoverflow.com/questions/5891555/display-the-date-like-may-5th-using-pythons-strftime
    ###
    def suffix(d):
        return 'th' if 11<=d<=13 else {1:'st',2:'nd',3:'rd'}.get(d%10, 'th')

    def custom_strftime(format, t):
        return t.strftime(format).replace('{S}', str(t.day) + suffix(t.day))

    print("approving WP",id)
    thisPass = db.session.execute(db.select(WPPass).filter_by(id=id)).scalar_one()
    print(thisPass)
    thisPass.approved_datetime = datetime.now()
    db.session.commit()

    socketio.emit('WP', {'name': thisPass.name, 'date': custom_strftime('%a, %B {S}',thisPass.date)})
    return redirect(url_for("pass_admin"))  

@app.route("/reject_wp/<id>", methods=["GET"])
@login_required
def reject_wp(id):
    print("rejecting WP",id)
    thisPass = db.session.execute(db.select(WPPass).filter_by(id=id)).scalar_one()
    print(thisPass)
    thisPass.rejected = True
    db.session.commit()
    return redirect(url_for("pass_admin"))  

@app.route("/return_pass/<id>", methods=["GET"])
@login_required
def return_pass(id):
    print("returning pass",id)
    thisPass = db.session.execute(db.select(HallPass).filter_by(id=id)).scalar_one()
    thisPass.back_datetime = datetime.now()
    db.session.commit()
    return redirect(url_for("pass_admin"))  

@app.route("/view_pass/<id>", methods=["GET"])
def view_pass(id):
    
    thisPass = db.session.execute(db.select(HallPass).filter_by(id=id)).scalar_one_or_none()
    
    if thisPass is None or thisPass.approved_datetime is None:
        passStatus = "notvalid"
        destination = None
        approved_date = None
        name = None

    elif(thisPass.approved_datetime is not None 
        and thisPass.back_datetime is None):
        passStatus = "valid"
        destination=thisPass.destination
        approved_date=thisPass.approved_datetime
        name=thisPass.name

    elif(thisPass.approved_datetime is not None 
        and thisPass.back_datetime is not None):
        passStatus = "returned"
        destination=thisPass.destination
        approved_date=thisPass.approved_datetime
        name=thisPass.name

    return render_template("view_pass.html", 
            name=name, 
            destination=destination, 
            approved_date=approved_date,
            passStatus = passStatus) 

@app.route("/request_pass", methods=["GET","POST"])
def request_pass():
    if request.method == "GET":
        #hide this menu during the first/last 10 mins of class
        current_time = datetime.now()
        if((current_time.hour < 8)
            or (current_time.hour == 8 and current_time.minute <= 30)
            or (current_time.hour == 9 and 45 <= current_time.minute)
            or (current_time.hour == 10 and current_time.minute <= 11)
            or (current_time.hour == 11 and (3 <= current_time.minute <= 28))
            or (current_time.hour == 12)
            or (current_time.hour == 13 and (21 <= current_time.minute <= 47))
            or (current_time.hour >=15)):
            return render_template("no_hall_pass.html")
        else:
            return render_template("request_pass.html")
    elif request.method == "POST":
        name = request.form.get("name")
        destination = request.form.get("destination")
        request_datetime = datetime.now()
        new_pass_request = HallPass(name=name, destination=destination,request_datetime=request_datetime,rejected=False)
        db.session.add(new_pass_request)
        db.session.commit()
        flash("Hi " + name + " your pass for " + destination + " has been created. You can now ask Mr Jones to approve it")
        return redirect(url_for("home"))  

@app.route("/admin_request_pass", methods=["GET","POST"])
@login_required
def admin_request_pass():
    #this page for the admin both creates and approves the request
    if request.method == "GET":
        return render_template("admin_request_pass.html")
    elif request.method == "POST":
        name = request.form.get("name")
        destination = request.form.get("destination")
        request_datetime = datetime.now()
        new_pass_request = HallPass(name=name, destination=destination,request_datetime=request_datetime,rejected=False)
        db.session.add(new_pass_request)
        db.session.commit()
        #after you commit, the id is set. I'll use my existing approval code from here
        return approve_pass(new_pass_request.id)  

@app.route("/admin_request_invite", methods=["GET","POST"])
@login_required
def admin_request_invite():
    #this page for the admin both creates and approves the request
    if request.method == "GET":
        return render_template("admin_request_invite.html")
    elif request.method == "POST":
        name = request.form.get("name")
        date = request.form.get("date")
        period = request.form.get("period")
        reason = request.form.get("reason")
        #I'm not saving these in the DB for now. Will I regret that?

        socketio.emit('Invitation'
        , {'name': name
            , 'date': date
            , 'period': period
            , 'reason':reason
            }
        )
        return redirect(url_for("pass_admin"))  

@app.route("/request_wp", methods=["GET","POST"])
def request_wp():
    if request.method == "GET":
        return render_template("request_wp.html")
    elif request.method == "POST":
        name = request.form.get("name")
        date = datetime.strptime(request.form.get("date"), '%Y-%m-%d').date()
        request_datetime = datetime.now()
        new_wp_pass_request = WPPass(name=name, date=date,request_datetime=request_datetime,rejected=False)
        db.session.add(new_wp_pass_request)
        db.session.commit()
        flashMessage = "Hi " + name + " your Warriors Period pass for "
        tomorrow = datetime.today() + timedelta(days=1)

        if date == datetime.today().date():
            flashMessage += "today"
        elif date == tomorrow.date():
            flashMessage += "tomorrow"
        else:
            flashMessage += str(date)
        flashMessage += " has been created. You can now ask Mr Jones to approve it"
        flash(flashMessage)
        return redirect(url_for("home")) 

@app.route("/admin_request_wp", methods=["GET","POST"])
@login_required
def admin_request_wp():
    #this page for the admin both creates and approves the request
    if request.method == "GET":
        return render_template("request_wp.html")
    elif request.method == "POST":
        name = request.form.get("name")
        date = datetime.strptime(request.form.get("date"), '%Y-%m-%d').date()
        request_datetime = datetime.now()
        new_wp_pass_request = WPPass(name=name, date=date,request_datetime=request_datetime,rejected=False)
        db.session.add(new_wp_pass_request)
        db.session.commit()
        return approve_wp(new_wp_pass_request.id)
        

@app.route("/resetdb")
@login_required
def resetdb():
    with app.app_context():
        db.drop_all()
        db.create_all()
        adminUser1 = User(id=ADMIN_USER1_NUM,name="Admin")
        db.session.add(adminUser1)
        adminUser1 = User(id=ADMIN_USER1_NUM,name="Admin")
        db.session.add(adminUser1)
        db.session.commit()
        flash("The DB was just reset","error")
        return redirect(url_for("home"))


###
#DATABASE STUFF
###

db = SQLAlchemy(app)

class Waiter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    completed_datetime = db.Column(db.DateTime)

class HallPass(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    destination = db.Column(db.String(100))
    request_datetime = db.Column(db.DateTime)
    approved_datetime = db.Column(db.DateTime)
    back_datetime = db.Column(db.DateTime)
    rejected = db.Column(db.Boolean)

class WPPass(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    date = db.Column(db.Date)
    request_datetime = db.Column(db.DateTime)
    approved_datetime = db.Column(db.DateTime)
    rejected = db.Column(db.Boolean)

def get_user(user_id):
    user = User.query.filter_by(id=user_id).first()
    return user

class User(db.Model, UserMixin):
    id = db.Column(db.String(100), primary_key=True)
    name = db.Column(db.String(100))

#########
#Socket Stuff
#########
socketio = SocketIO(app
    , async_mode='gevent'
    , engineio_logger=True
    , logger=True
    , cors_allowed_origins=['https://www.whscs.net','https://whscs.net','https://www.duck.whscs.net']
    #, cors_allowed_origins=['*']
    )

@socketio.on('connect')
def test_connect():
    send('after connect')

if __name__ == "__main__":
    socketio.run(app)