import argparse
import os
from argparse import ArgumentParser

import mysql.connector
import yaml


def is_valid_file(parser, arg):
    if not os.path.exists(arg):
        parser.error("The file %s does not exist!" % arg)
    else:
        with open("./status-dashboard.yaml", "r") as yaml_file:
            return yaml.safe_load(yaml_file)

def get_config():
    argument_parser = argparse.ArgumentParser(
        description='Script to calculate service uptime and store it in MySQL database')
    argument_parser.add_argument("--config_path", dest="cfg", required=True,
                        help="Path to yaml configuration", metavar="FILE",
                        type=lambda x: is_valid_file(argument_parser, x))

    argument_parser = argument_parser.parse_args()
    return argument_parser.cfg


def main():
    cfg = get_config()

    src_db = mysql.connector.connect(
        host=cfg["source_database"]["host"],
        user=cfg["source_database"]["user"],
        password=cfg["source_database"]["password"],
        database=cfg["source_database"]["database"],
    )
    dest_db = mysql.connector.connect(
        host=cfg["destination_database"]["host"],
        user=cfg["destination_database"]["user"],
        password=cfg["destination_database"]["password"],
        database=cfg["destination_database"]["database"],
    )

if __name__ == "__main__":
    main()
