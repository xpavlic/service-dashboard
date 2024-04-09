from flask import Flask, render_template

import yaml

app = Flask(__name__)

with open("./status-dashboard.yaml", "r") as yaml_file:
    cfg = yaml.safe_load(yaml_file)


@app.route('/')
def hello_world():  # put application's code here
    charts_data = [{"service_name": "auth_saml", "ok": 100, "warning": 50, "error": 10},
                   {"service_name": "auth_saml2", "ok": 100, "warning": 50,
                    "error": 15}]
    status_data = [{"service_name": "auth_saml",
                    "data": [{"datetime": 11234, "status": "OK"},
                             {"datetime": 11235, "status": "WARNING"}]},
                   {"service_name": "auth_saml2"}]
    return render_template('dashboard.html', charts_data=charts_data,
                           status_data=status_data)


if __name__ == '__main__':
    app.run(port=8080)
