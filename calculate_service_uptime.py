import argparse
import os

import mysql.connector
import yaml

OK = "OK"
WARNING = "WARNING"
CRITICAL = "CRITICAL"


def is_valid_file(parser, arg):
    if not os.path.exists(arg):
        parser.error("The file %s does not exist!" % arg)
    else:
        with open(arg) as yaml_file:
            return yaml.safe_load(yaml_file)


def get_config():
    argument_parser = argparse.ArgumentParser(
        description='Script to calculate service uptime and store it in MySQL database')
    argument_parser.add_argument("--config-path", dest="cfg", required=True,
                                 help="Path to yaml configuration", metavar="FILE",
                                 type=lambda x: is_valid_file(argument_parser, x))

    argument_parser = argument_parser.parse_args()
    return argument_parser.cfg


def calculate_service_uptime_for_period(cursor, src_table, sql_condition):
    cursor.execute(
        f"SELECT event_time, status FROM {src_table} {sql_condition} ORDER BY event_time ASC;;")
    data = cursor.fetchall()
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

    if status_uptime[OK] == 0 and status_uptime[WARNING] == 0 and status_uptime[CRITICAL] == 0:
        return {}
    return status_uptime


def store_service_uptime(service_name, host, period, cursor, dest_table, uptime, downtime, warntime):
    cursor.execute(
        f"SELECT id FROM {dest_table} WHERE service = '{service_name}' AND host = '{host}' AND period = '{period}'")
    service_record = cursor.fetchall()
    if not service_record:
        cursor.execute(
            f"INSERT INTO {dest_table} (service, host, period, uptime, downtime, warntime) VALUES ('{service_name}', '{host}', '{period}', {uptime}, {downtime}, {warntime})")
    else:
        cursor.execute(
            f"UPDATE {dest_table} SET uptime = {uptime}, downtime = {downtime}, warntime = {warntime} WHERE id = {service_record[0][0]}")


def calculate_and_store_uptime(cursor, src_table, dest_table):
    cursor.execute("SHOW TABLES LIKE %s", (dest_table,))
    if not cursor.fetchall():
        cursor.execute(f"""
            CREATE TABLE {dest_table} (
                id INT AUTO_INCREMENT PRIMARY KEY,
                service VARCHAR(255),
                host VARCHAR(255),
                period ENUM ('DAY', 'MONTH', 'YEAR'),
                uptime INT,
                downtime INT,
                warntime INT
            );
        """)

    cursor.execute(f"SELECT DISTINCT service, host FROM {src_table};")
    for row in cursor.fetchall():
        service_name = row[0]
        host = row[1]
        for period in ["DAY", "MONTH", "YEAR"]:
            status_uptime = calculate_service_uptime_for_period(cursor, src_table,
                                                                f"WHERE service = '{service_name}' AND host = '{host}' AND event_time >= NOW() - INTERVAL 1 {period}")
            if status_uptime:
                store_service_uptime(service_name, host, period, cursor, dest_table, status_uptime[OK],
                                     status_uptime[CRITICAL], status_uptime[WARNING])


def main():
    cfg = get_config()

    database = mysql.connector.connect(
        host=cfg["database"]["host"],
        user=cfg["database"]["user"],
        password=cfg["database"].get("password"),
        database=cfg["database"]["database"],
    )

    src_table = cfg["database"]["source_table"]
    dest_table = cfg["database"]["destination_table"]

    calculate_and_store_uptime(database.cursor(), src_table, dest_table)
    database.commit()


if __name__ == "__main__":
    main()
