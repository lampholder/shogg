"""
Quick-and-dirty Flask app to pull per-month toggl project/task totals from toggl.
Designed to be deployed to AWS lambda and consumed from Google Sheets.
"""

import json
import datetime

import yaml
from flask import Flask
from flask import request
from flask import Response
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

config = yaml.load(open('config.yaml', 'r'))
AUTH = (config['toggl_api_token'], 'api_token')
WORKSPACE_ID = config['toggl_workspace_id']

def to_date_range(month_string):
    start = datetime.datetime.strptime('%s-01' % month_string[:7], '%Y-%m-%d')
    end = (start + datetime.timedelta(days=31)).replace(day=1)
    return (start, end)


def get_seconds(auth, workspace_id, search_criteria, month_string):
    URL = 'https://track.toggl.com/reports/api/v3/workspace/%s/search/time_entries/totals'

    start, end = to_date_range(month_string)

    base_query = {
        "start_date": start.strftime('%Y-%m-%d'),
        "end_date": end.strftime('%Y-%m-%d'),
        "grouping": "projects",
        "sub_grouping": "tasks",
        "with_graph": False
    }

    query = {**base_query, **search_criteria}
    response = requests.post(URL % workspace_id, json=query, auth=auth)
    return response.json().get('seconds')


def get_project_seconds(auth, workspace_id, project_id, month_string):
    search_criteria = {
        "project_ids": [project_id],
    }

    return get_seconds(auth, workspace_id, search_criteria, month_string)


def get_task_seconds(auth, workspace_id, task_id, month_string):
    search_criteria = {
        "task_ids": [task_id],
    }

    return get_seconds(auth, workspace_id, search_criteria, month_string)


def to_units(seconds, units):
    if units.lower() == 'seconds':
        return (seconds, 'seconds')
    elif units.lower() == 'minutes':
        return (seconds / 60.0, 'minutes')
    elif units.lower() == 'hours':
        return (seconds / 60.0 / 60.0, 'hours')
    elif units.lower() == 'days':
        return (seconds / 60.0 / 60.0 / 8.0, 'days')

@app.route('/effort')
def effort():
    month = request.args.get('month')
    units = request.args.get('units', 'days')
    task_id = request.args.get('task')
    if task_id:
        task_id = int(task_id)
    project_id = request.args.get('project')
    if project_id:
        project_id = int(project_id)

    if task_id and project_id:
        return Response('Bad request: task and project both specified', 400)

    elif task_id:
        seconds = get_task_seconds(AUTH, WORKSPACE_ID, task_id, month)
    elif project_id:
        seconds = get_project_seconds(AUTH, WORKSPACE_ID, project_id, month)
    else:
        return Response('Bad request: no task or project specified', 400)

    x, y = to_units(seconds, units)
    return '%s' % x


if __name__ == '__main__':
    app.run()

