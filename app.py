from flask import Flask, render_template, redirect, url_for, request

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

status_table = cfg["database"]["status_table"]
uptime_table = cfg["database"]["uptime_table"]


def uptime_db_to_dict(db_data, display_name):
    if not db_data:
        return {}
    converted_data = {"service_name": display_name, "OK": 0, "WARNING": 0, "ERROR": 0}
    for row in db_data:
        uptime = row[0]
        downtime = row[1]
        warntime = row[2]
        converted_data["OK"] += uptime
        converted_data["WARNING"] += warntime
        converted_data["ERROR"] += downtime
    return converted_data


def status_db_to_dict(db_data, display_name):
    if not db_data:
        return {}
    converted_data = {"service_name": display_name, "data": []}
    for row in db_data:
        event_time = row[0]
        status = row[1]
        host = row[2]

        event = {"datetime": event_time.strftime("%m/%d/%Y %H:%M:%S"),
                 "status": status,
                 "host": host}
        converted_data["data"].append(event)
    return converted_data


def calculate_status_data_for_date(date, cursor):
    pass


@app.route('/')
def home():
    return redirect(url_for('dashboard', selected_range="past_day"))


@app.route('/dashboard/<selected_range>')
def dashboard(selected_range):
    status_data = []
    charts_data = []

    if selected_range == "select_date":
        date = request.args.get("date")
        if date is None:
            return render_template("dashboard.html", selected_range="select_date",
                                   charts_data=charts_data, status_data=status_data)

        return render_template('dashboard.html', selected_range="select_date",
                               charts_data=charts_data, status_data=status_data, )

    range_to_sql = {"past_day": "DAY", "past_month": "MONTH", "past_year": "YEAR"}
    if selected_range not in range_to_sql.keys():
        return redirect(url_for('dashboard', selected_range="past_day"))

    db_cursor = database.cursor()
    db_cursor.execute(f"SELECT DISTINCT service FROM {status_table};")
    for row in db_cursor.fetchall():
        service_db_name = row[0]
        display_name = service_db_name if cfg["services"].get(
            service_db_name) is None else cfg["services"][service_db_name]

        db_cursor.execute(
            f"SELECT event_time, status, host FROM {status_table} WHERE event_time >= NOW() - INTERVAL 1 "
            f"{range_to_sql[selected_range]} AND service = '{service_db_name}' ORDER BY event_time DESC;;")
        service_status_data = status_db_to_dict(db_cursor.fetchall(), display_name)
        if service_status_data:
            status_data.append(service_status_data)

        db_cursor.execute(
            f"SELECT uptime, downtime, warntime FROM {uptime_table} "
            f"WHERE service = '{service_db_name}' AND period = '{range_to_sql[selected_range]}'")
        service_uptime_data = uptime_db_to_dict(db_cursor.fetchall(), display_name)
        if service_uptime_data:
            charts_data.append(service_uptime_data)

    db_cursor.close()
    database.commit()
    return render_template('dashboard.html', charts_data=charts_data,
                           status_data=status_data, selected_range=selected_range)


if __name__ == '__main__':
    app.run(port=8080)
