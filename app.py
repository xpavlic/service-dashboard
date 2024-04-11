import json

from flask import Flask, render_template, redirect, url_for

import yaml

import mysql.connector

app = Flask(__name__)

with open("./status-dashboard.yaml", "r") as yaml_file:
    cfg = yaml.safe_load(yaml_file)

database = mysql.connector.connect(
    host=cfg["database"]["host"],
    user=cfg["database"]["user"],
    password=cfg["database"]["password"],
    database=cfg["database"]["database"],
)

dashboard_table = cfg["database"]["table"]


@app.route('/')
def home():
    return redirect(url_for('dashboard', selected_range="past_day"))


@app.route('/<selected_range>')
def dashboard(selected_range):  # put application's code here
    charts_data = [{"service_name": "Auth saml", "ok": 100, "warning": 50, "error": 10},
                   {"service_name": "Auth saml 2", "ok": 100, "warning": 50,
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

    status_data = []
    range_to_sql = {"past_day": "DAY", "past_month": "MONTH", "past_year": "YEAR"}
    if selected_range not in range_to_sql.keys():
        return redirect(url_for('dashboard', selected_range="past_day"))

    db_cursor = database.cursor()
    for service in cfg["services"]:
        service_db_name = service["db_name"]
        display_name = service["display_name"]

        db_cursor.execute(f"SELECT * FROM {dashboard_table} WHERE event_time >= NOW() - INTERVAL 1 {range_to_sql[selected_range]} AND service = '{service_db_name}' ORDER BY event_time DESC;;")
        service_status_data = db_to_dict(db_cursor.fetchall(), display_name)
        if service_status_data:
            status_data.append(service_status_data)
    db_cursor.close()
    database.commit()
    return render_template('dashboard.html', charts_data=charts_data,
                           status_data=status_data, selected_range=selected_range)


def db_to_dict(db_data, display_name):
    if not db_data:
        return {}
    converted_data = {"service_name": display_name, "data": []}
    for row in db_data:
        event_time = row[3]
        status = row[4]

        event = {"datetime": event_time,
                 "status": status}
        converted_data["data"].append(event)

    return converted_data


@app.route('/status_data/<service_name>/<index>', methods=["GET"])
def get_status_data(service_name, index):
    status_data = {"auth_saml": [{"datetime": 11234, "status": "OK"},
                                 {"datetime": 11235, "status": "WARNING"}],
                   "auth_saml2": [{"datetime": 11234, "status": "WARNING"}]}
    return json.dumps(status_data[service_name])


if __name__ == '__main__':
    app.run(port=8080)
