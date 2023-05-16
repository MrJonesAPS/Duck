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

app = Flask(__name__)
app.config.from_pyfile('instance/config.py')

def initializePrinter():
    ThermalPrinter = adafruit_thermal_printer.get_printer_class(2.68)
    uart = serial.Serial("/dev/serial0", baudrate=19200, timeout=3000)
    printer = ThermalPrinter(uart, auto_warm_up=False)
    printer.warm_up()
    return printer

def checkPaper():
    if printer.has_paper():
        #flash("Printer has paper")
        pass
    else:
        flash("The printer is out of paper. Tell Mr. Jones to fix it!","error")

@app.route("/", methods=["GET"])
def home():
    return render_template("home.html")

@app.route("/helpQ", methods=["GET"])
def helpQ():
    if request.method == "GET":
        waiter_list = Waiter.query.all()
        checkPaper()
        return render_template("helpQ.html", waiter_list = waiter_list)

@app.route("/add", methods=["POST"])
def add():
    #create a new Waiter and add it to the queue
    name = request.form.get("name")
    new_waiter = Waiter(name=name)
    db.session.add(new_waiter)
    db.session.commit()

    #redirect
    flash("Hi " + name + " you have been added to the help queue")
        
    return redirect(url_for("home"))

@app.route("/joinQ", methods=["GET"])
def joinQ():
    checkPaper()
    return render_template("joinQ.html")

@app.route("/request_pass", methods=["GET","POST"])
def request_pass():
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
        flash("Hi " + name + " your pass for " + destination + " has been created. You can now ask Mr Jones to approve it")
        return redirect(url_for("home"))    

@app.route("/view_pass/<id>", methods=["GET"])
def view_pass(id):
    thisPass = db.session.execute(db.select(HallPass).filter_by(id=id)).scalar_one()
    thisPass.back_datetime = datetime.now()
    db.session.commit()
    return render_template("view_pass.html", name=thisPass.name, destination=thisPass.destination) 

@app.route("/request_wp", methods=["GET","POST"])
def request_wp():
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

###
#Initialize Printer
###
printer = initializePrinter()

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

if __name__ == "__main__":
    #app.run(port=80, host='0.0.0.0', debug=True)
    app.run(port=80, host='0.0.0.0', debug=False)