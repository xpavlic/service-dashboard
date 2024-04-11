import json

from flask import Flask, render_template, redirect, url_for

import yaml

import mysql.connector

app = Flask(__name__)

with open("./status-dashboard.yaml", "r") as yaml_file:
    cfg = yaml.safe_load(yaml_file)

mydb = mysql.connector.connect(
    host=cfg["database"]["host"],
    user=cfg["database"]["user"],
    password=cfg["database"]["password"],
    database=cfg["database"]["database"],
)

dashboard_table = cfg["database"]["dashboard_table"]

mycursor = mydb.cursor()

mycursor.execute(f"SELECT * FROM {dashboard_table}")

myresult = mycursor.fetchall()

for x in myresult:
  print(x)


@app.route('/')
def home():
    return redirect(url_for('dashboard', selected_range="past_day"))


@app.route('/<selected_range>')
def dashboard(selected_range):  # put application's code here
    charts_data = [{"service_name": "auth_saml", "ok": 100, "warning": 50, "error": 10},
                   {"service_name": "auth_saml2", "ok": 100, "warning": 50,
                    "error": 15}]
    status_data = [{"service_name": "auth_saml",
                    "data": [{"datetime": 11234, "status": "OK"},
                             {"datetime": 11235, "status": "WARNING"},
                             {"datetime": 11234, "status": "OK"},
                             {"datetime": 11234, "status": "OK"},
                             {"datetime": 11234, "status": "OK"},
                             {"datetime": 11234, "status": "OK"},
                             {"datetime": 11234, "status": "OK"},
                             {"datetime": 11234, "status": "OK"},
                             {"datetime": 11234, "status": "OK"},
                             {"datetime": 11234, "status": "OK"},
                             {"datetime": 11234, "status": "OK"},
                             {"datetime": 11234, "status": "OK"},
                             {"datetime": 11234, "status": "OK"},
                             {"datetime": 11234, "status": "OK"},
                             {"datetime": 11234, "status": "OK"},
                             {"datetime": 11234, "status": "OK"},
                             {"datetime": 112366, "status": "OK"},
                             {"datetime": 112366, "status": "OK"}, ]},
                   {"service_name": "auth_saml2"}]
    return render_template('dashboard.html', charts_data=charts_data,
                           status_data=status_data, selected_range=selected_range)


@app.route('/status_data/<service_name>/<index>', methods=["GET"])
def get_status_data(service_name, index):
    status_data = {"auth_saml": [{"datetime": 11234, "status": "OK"},
                                 {"datetime": 11235, "status": "WARNING"}],
                   "auth_saml2": [{"datetime": 11234, "status": "WARNING"}]}
    return json.dumps(status_data[service_name])


if __name__ == '__main__':
    app.run(port=8080)
