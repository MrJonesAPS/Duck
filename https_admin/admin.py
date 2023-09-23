import json
import os
import sqlite3

from datetime import date, datetime, timedelta
from flask import Flask, redirect, url_for, render_template, request, flash
from flask_sqlalchemy import SQLAlchemy
import board
import busio
import adafruit_thermal_printer
import serial

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
from escpos.printer import Serial

#configuration
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", None)
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", None)
SERVER_IP_ADDRESS = os.environ.get("IP", None).strip()
ADMIN_USER_NUM = os.environ.get("ADMIN_USER_NUM", None).strip()
GOOGLE_DISCOVERY_URL = (
    "https://accounts.google.com/.well-known/openid-configuration"
)

app = Flask(__name__)
app.config.from_pyfile('instance/config.py')

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
#I don't need to flash a message if logged out because I always just redirect to login
login_manager.login_message = None


# OAuth 2 client setup
client = WebApplicationClient(GOOGLE_CLIENT_ID)

# Flask-Login helper to retrieve a user from our db
@login_manager.user_loader
def load_user(user_id):
    return get_user(user_id)

def initializePrinter():
    ThermalPrinter = adafruit_thermal_printer.get_printer_class(2.68)
    uart = serial.Serial("/dev/serial0", baudrate=19200, timeout=0)
    printer = ThermalPrinter(uart, 
                            auto_warm_up=False, 
                            dot_print_s = 0.01, 
                            byte_delay_s = 0)
    printer.warm_up()
    printer.print("DUCK is online. Here is the IP address:")
    printer.print(SERVER_IP_ADDRESS)
    printer.feed(2)
    return printer

def initializePrinter_escpos():
    p = Serial(devfile='/dev/serial0',
           baudrate=19200,
           bytesize=8,
           parity='N',
           stopbits=1,
           timeout=0.01,
           dsrdtr=True)
    return p

def checkPaper():
    try:
        if printer.has_paper():
            pass
        else:
            flash("The printer is out of paper. Tell Mr. Jones to fix it!","error")
    except:
        flash("Unable to check paper status","error")

def PrintHallPass(name, destination, date, time, id):
    printer.size = adafruit_thermal_printer.SIZE_MEDIUM
    printer.justify = adafruit_thermal_printer.JUSTIFY_CENTER
    printer.print("__(.)<   THIS IS A   <(.)__")
    printer.print("\___)    HALL PASS    (___/")
    printer.feed(1)
    printer.print(name)
    printer.print("is going to " + destination)
    printer.print("at " + time)
    printer.print("on " + date)
    printer.feed(1)
    printer.print("Questions? See Mr. Jones")
    printer.print("in room C116")
    printer.feed(1)
    printer.size = adafruit_thermal_printer.SIZE_SMALL
    printer.print("(scan to validate)")
    printer_escpos.qr("https://www.youtube.com/watch?v=dQw4w9WgXcQ" + str(id),native=False ,size=8)
    printer_escpos.text("\n\n\n")

def PrintWPPass(name, date):
    ###
    #I got some of this code from stackoverflow
    #https://stackoverflow.com/questions/5891555/display-the-date-like-may-5th-using-pythons-strftime
    ###
    def suffix(d):
        return 'th' if 11<=d<=13 else {1:'st',2:'nd',3:'rd'}.get(d%10, 'th')

    def custom_strftime(format, t):
        return t.strftime(format).replace('{S}', str(t.day) + suffix(t.day))

    printer.size = adafruit_thermal_printer.SIZE_LARGE
    printer.justify = adafruit_thermal_printer.JUSTIFY_LEFT
    printer.print("__(.)<   WARRIOR")
    printer.print("\___)    PASS")
    printer.justify = adafruit_thermal_printer.JUSTIFY_CENTER
    printer.feed(3)
    printer.print(name)
    printer.print("is invited")
    printer.print("to room C116")
    printer.print("on")
    printer.print(custom_strftime('%a, %B {S}', date))
    printer.feed(3)
    printer.print("Questions?") 
    printer.print("See Mr. Jones")
    printer.print("in room C116")
    printer.feed(2)


def PrintInvitation(name, date, period, reason):
    ###
    #I got some of this code from stackoverflow
    #https://stackoverflow.com/questions/5891555/display-the-date-like-may-5th-using-pythons-strftime
    ###
    def suffix(d):
        return 'th' if 11<=d<=13 else {1:'st',2:'nd',3:'rd'}.get(d%10, 'th')

    def custom_strftime(format, t):
        return t.strftime(format).replace('{S}', str(t.day) + suffix(t.day))

    printer.size = adafruit_thermal_printer.SIZE_LARGE
    printer.justify = adafruit_thermal_printer.JUSTIFY_LEFT
    printer.print("__(.)<INVITATION")
    printer.print("\___)")
    printer.justify = adafruit_thermal_printer.JUSTIFY_CENTER
    printer.feed(2)
    printer.print(name)
    printer.print("you are invited")
    printer.print("to room C116")
    printer.print("during " + period)
    printer.print("on")
    printer.print(custom_strftime('%a, %B {S}', date))
    printer.print("reason:")
    printer.size = adafruit_thermal_printer.SIZE_SMALL
    printer.print(reason)
    printer.size = adafruit_thermal_printer.SIZE_LARGE
    printer.feed(2)
    printer.print("Questions?") 
    printer.print("See Mr. Jones")
    printer.print("in room C116")
    printer.feed(2)
    printer.size = adafruit_thermal_printer.SIZE_SMALL
    printer.justify = adafruit_thermal_printer.JUSTIFY_LEFT
    printer.print("****")
    printer.print("This invitation only signifies")
    printer.print("that you are welcome to be in")
    printer.print("C116 during this period.")
    printer.print("Your teacher must give")
    printer.print("permission to leave their")
    printer.print("classroom.")
    printer.feed(2)


@app.context_processor
def inject_dict_for_all_templates():
    return dict(SERVER_IP_ADDRESS=SERVER_IP_ADDRESS)

def get_google_provider_cfg():
    return requests.get(GOOGLE_DISCOVERY_URL).json()

@app.before_request
def before_request():
    if not request.is_secure:
        url = request.url.replace('http://', 'https://', 1)
        code = 301
        return redirect(url, code=code)

@app.route("/login")
def login():
    # Find out what URL to hit for Google login
    google_provider_cfg = get_google_provider_cfg()
    authorization_endpoint = google_provider_cfg["authorization_endpoint"]

    # Use library to construct the request for Google login and provide
    # scopes that let you retrieve user's profile from Google
    request_uri = client.prepare_request_uri(
        authorization_endpoint,
        redirect_uri=request.base_url + "/callback",
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
    token_url, headers, body = client.prepare_token_request(
        token_endpoint,
        authorization_response=request.url,
        redirect_url=request.base_url,
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
        login_user(user)
    else:
        flash("You just tried to login with an unknown userid: " + user.id,"error")

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
        checkPaper()
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


        checkPaper()
        
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

@app.route("/approve_pass/<id>", methods=["GET"])
@login_required
def approve_pass(id):
    print("approving pass",id)
    thisPass = db.session.execute(db.select(HallPass).filter_by(id=id)).scalar_one()
    thisPass.approved_datetime = datetime.now()
    db.session.commit()
    nowTime = datetime.now().strftime("%I:%M %p")
    nowDate = date.today().strftime("%B %d, %Y")
    PrintHallPass(thisPass.name, thisPass.destination, nowDate, nowTime, id)
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
    print("approving WP",id)
    thisPass = db.session.execute(db.select(WPPass).filter_by(id=id)).scalar_one()
    print(thisPass)
    thisPass.approved_datetime = datetime.now()
    db.session.commit()
    PrintWPPass(thisPass.name, thisPass.date)
    return redirect(url_for("pass_admin"))  

@app.route("/reject_wp/<id>", methods=["GET"])
@login_required
def reject_wp(id):
    print("rejecting WP",id)
    thisPass = db.session.execute(db.select(WPPass).filter_by(id=id)).scalar_one()
    print(thisPass)
    thisPass.rejected = True #Why doesn't this work???
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
    #this page for the admin both creates and approves the request
    if request.method == "GET":
        checkPaper()
        return render_template("request_pass.html")
    elif request.method == "POST":
        name = request.form.get("name")
        destination = request.form.get("destination")
        request_datetime = datetime.now()
        new_pass_request = HallPass(name=name, destination=destination,request_datetime=request_datetime,rejected=False)
        db.session.add(new_pass_request)
        db.session.commit()
        #after you commit, the id is set. I'll use my existing approval code from here
        return approve_pass(new_pass_request.id)  

@app.route("/request_wp", methods=["GET","POST"])
def request_wp():
    #this page for the admin both creates and approves the request
    if request.method == "GET":
        checkPaper()
        return render_template("request_wp.html")
    elif request.method == "POST":
        name = request.form.get("name")
        date = datetime.strptime(request.form.get("date"), '%Y-%m-%d').date()
        request_datetime = datetime.now()
        new_wp_pass_request = WPPass(name=name, date=date,request_datetime=request_datetime,rejected=False)
        db.session.add(new_wp_pass_request)
        db.session.commit()
        return approve_wp(new_wp_pass_request.id)
        
@app.route("/request_invite", methods=["GET","POST"])
def request_invite():
    #this page for the admin both creates and approves the request
    if request.method == "GET":
        checkPaper()
        return render_template("request_invite.html")
    elif request.method == "POST":
        name = request.form.get("name")
        date = datetime.strptime(request.form.get("date"), '%Y-%m-%d').date()
        period = request.form.get("period")
        reason = request.form.get("reason")
        PrintInvitation(name, date, period, reason)
        return redirect(url_for("pass_admin"))  

@app.route("/resetdb")
@login_required
def resetdb():
    with app.app_context():
        db.drop_all()
        db.create_all()
        adminUser = User(id=ADMIN_USER_NUM,name="Admin")
        db.session.add(adminUser)
        db.session.commit()
        flash("The DB was just reset","error")
        return redirect(url_for("home"))

@app.route("/summary")
@login_required
def summary():
    approved_passes = db.session.execute(db.select(HallPass).\
                                            filter(HallPass.approved_datetime != None)).scalars()
        
    approved_WP = db.session.execute(db.select(WPPass).\
                                            filter(WPPass.approved_datetime != None)).scalars()
    
    printer.size = adafruit_thermal_printer.SIZE_LARGE
    printer.justify = adafruit_thermal_printer.JUSTIFY_CENTER
    printer.print("SUMMARY FOR")
    printer.print(date.today().strftime("%B %d, %Y"))
    printer.justify = adafruit_thermal_printer.JUSTIFY_LEFT
    printer.size = adafruit_thermal_printer.SIZE_MEDIUM
    printer.print("Hall Passes:")
    printer.size = adafruit_thermal_printer.SIZE_SMALL
    for p in approved_passes:
        printer.print(p.name + " | " + p.destination)
        goneTime = p.back_datetime - p.approved_datetime
        printer.underline = adafruit_thermal_printer.UNDERLINE_THICK
        printer.print(p.approved_datetime.strftime("%B %d, %y %I:%M %p") + "(" + str(int(goneTime.total_seconds() // 60)) + " mins)")
        printer.underline = None

    printer.feed(1)
    printer.size = adafruit_thermal_printer.SIZE_MEDIUM
    printer.print("Warrior's passes:")
    printer.size = adafruit_thermal_printer.SIZE_SMALL
    printer.feed(1)
    for p in approved_WP:
        printer.print(">" + p.name + "|" + p.date.strftime("%B %d, %Y"))

    printer.size = adafruit_thermal_printer.SIZE_LARGE
    printer.feed(1)
    printer.justify = adafruit_thermal_printer.JUSTIFY_CENTER
    printer.print("END SUMMARY")
    printer.feed(2)
    flash("Summary print successful")
    return redirect(url_for("home"))

###
#Initialize Printer
###
printer = initializePrinter()
printer_escpos = initializePrinter_escpos()

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

if __name__ == "__main__":
    #app.run(port=443, host='0.0.0.0', debug=True,ssl_context="adhoc")
    app.run(port=443, host='0.0.0.0', debug=False,ssl_context="adhoc")