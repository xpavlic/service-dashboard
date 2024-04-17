from datetime import datetime, timedelta

from dateutil.relativedelta import relativedelta
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

OK = "OK"
WARNING = "WARNING"
CRITICAL = "CRITICAL"


def uptime_db_to_dict(db_data, display_name, converted_data=None):
    if not db_data:
        return {}
    if not converted_data:
        converted_data = {"service_name": display_name, OK: 0, WARNING: 0, CRITICAL: 0}
    for row in db_data:
        uptime = row[0]
        downtime = row[1]
        warntime = row[2]
        converted_data[OK] += uptime
        converted_data[WARNING] += warntime
        converted_data[CRITICAL] += downtime
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


def calculate_service_uptime(cursor, sql_condition, first_status_condition, first_status_from,
                             last_status_up_to):
    cursor.execute(f"SELECT status FROM {status_table} {first_status_condition} ORDER BY event_time DESC LIMIT 1 ;")
    status_list = []
    first_status = cursor.fetchall()
    cursor.execute(
        f"SELECT event_time, status FROM {status_table} {sql_condition} ORDER BY event_time ASC;;")
    data = cursor.fetchall()
    if first_status and data:
        status_list.append({"time": first_status_from, "status": first_status[0][0]})
    status_list = []
    for row in data:
        event_time = row[0]
        status = row[1]
        status_list.append({"time": event_time, "status": status})

    status_uptime = {OK: 0, WARNING: 0, CRITICAL: 0}

    prev_status = ""
    prev_time = 0
    for status in status_list:
        if not prev_status:
            prev_status = status["status"]
            prev_time = status["time"]
            continue
        status_uptime[prev_status] += int((status["time"] - prev_time).total_seconds())
        prev_status = status["status"]
        prev_time = status["time"]
    if prev_status:
        status_uptime[prev_status] += int(
            (last_status_up_to - prev_time).total_seconds())
    if (status_uptime[OK] == 0 and status_uptime[WARNING] == 0
            and status_uptime[CRITICAL] == 0):
        return {}
    return status_uptime


def get_charts_data(db_cursor, sql_condition, first_status_from, last_status_up_to):
    charts_data = []
    charts_dict = {}
    db_cursor.execute(f"SELECT DISTINCT service, host FROM {status_table};")
    for row in db_cursor.fetchall():
        service_db_name = row[0]
        host = row[1]
        display_name = service_db_name if cfg["services"].get(
            service_db_name) is None else cfg["services"][service_db_name]
        status_uptime = calculate_service_uptime(db_cursor,
                                                 f"{sql_condition} AND service = '{service_db_name}' AND host = '{host}'",
                                                 f"WHERE event_time < '{first_status_from}' AND service = '{service_db_name}' AND host = '{host}'",
                                                 first_status_from,
                                                 last_status_up_to)
        if not status_uptime:
            continue
        if not charts_dict.get(display_name):
            charts_dict[display_name] = status_uptime
        else:
            status_uptime[OK] += charts_dict[display_name][OK]
            status_uptime[WARNING] += charts_dict[display_name][WARNING]
            status_uptime[CRITICAL] += charts_dict[display_name][CRITICAL]
    for key, value in charts_dict.items():
        charts_data.append(
            {"service_name": key, OK: value[OK], WARNING: value[WARNING],
             CRITICAL: value[CRITICAL]})
    return charts_data


def get_status_data(db_cursor, sql_condition):
    status_data = []
    db_cursor.execute(f"SELECT DISTINCT service FROM {status_table};")
    for row in db_cursor.fetchall():
        service_db_name = row[0]
        display_name = service_db_name if cfg["services"].get(
            service_db_name) is None else cfg["services"][service_db_name]

        db_cursor.execute(
            f"SELECT event_time, status, host FROM {status_table} "
            f"{sql_condition} AND service = '{service_db_name}' ORDER BY event_time DESC;;")
        service_status_data = status_db_to_dict(db_cursor.fetchall(), display_name)
        if service_status_data:
            status_data.append(service_status_data)
    return status_data


def get_status_charts_data(period):
    db_cursor = database.cursor()
    sql_condition = f"WHERE event_time >= NOW() - INTERVAL 1 {period}"
    status_data = get_status_data(db_cursor, sql_condition)
    if period == "DAY":
        first_status_from = datetime.now() - timedelta(days=1)
    elif period == "MONTH":
        first_status_from = datetime.now() - relativedelta(months=1)
    else:
        first_status_from = datetime.now() - relativedelta(year=1)

    charts_data = get_charts_data(db_cursor, sql_condition, first_status_from,
                                  datetime.now())
    db_cursor.close()
    database.commit()
    return status_data, charts_data


def get_status_charts_data_for_date(date):
    db_cursor = database.cursor()
    start_date = date + ' 00:00:00'
    end_date = date + ' 23:59:59'
    date_format = "%Y-%m-%d %H:%M:%S"
    sql_condition = f"WHERE event_time BETWEEN '{start_date}' AND '{end_date}'"
    status_data = get_status_data(db_cursor, sql_condition)
    charts_data = get_charts_data(db_cursor, sql_condition,
                                  datetime.strptime(start_date, date_format),
                                  datetime.strptime(end_date, date_format))
    db_cursor.close()
    database.commit()
    return status_data, charts_data


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
        status_data, charts_data = get_status_charts_data_for_date(date)
        return render_template('dashboard.html', selected_range="select_date",
                               charts_data=charts_data, status_data=status_data, )

    range_to_sql = {"past_day": "DAY", "past_month": "MONTH", "past_year": "YEAR"}
    if selected_range not in range_to_sql.keys():
        return redirect(url_for('dashboard', selected_range="past_day"))

    status_data, charts_data = get_status_charts_data(range_to_sql[selected_range])
    return render_template('dashboard.html', charts_data=charts_data,
                           status_data=status_data, selected_range=selected_range)


if __name__ == '__main__':
    app.run(port=8080)
