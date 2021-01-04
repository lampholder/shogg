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

config = yaml.load(open('config.yaml', 'r'), Loader=yaml.SafeLoader)
AUTH = (config['toggl_api_token'], 'api_token')
WORKSPACE_ID = config['toggl_workspace_id']


def last_day_of_month(any_day):
    # this will never fail
    # get close to the end of the month for any day, and add 4 days 'over'
    next_month = any_day.replace(day=28) + datetime.timedelta(days=4)
    # subtract the number of remaining 'overage' days to get last day of current month, or said programattically said, the previous day of the first of next month
    return next_month - datetime.timedelta(days=next_month.day)


def month_to_date_range(month_string):
    start = datetime.datetime.strptime('%s-01' % month_string[:7], '%Y-%m-%d')
    end = last_day_of_month(start)
    return (start, end)


def sprint_to_date_range(sprint_string):
    (year, month, half) = [int(x) for x in sprint_string.split('.')]
    if half == 1:
        start = datetime.datetime(year, month, 1)
        end = datetime.datetime(year, month, 16)
    elif half == 2:
        start = datetime.datetime(year, month, 17)
        end = last_day_of_month(start)
    return (start, end)


def get_seconds(auth, workspace_id, search_criteria, start, end):
    URL = 'https://track.toggl.com/reports/api/v3/workspace/%s/search/time_entries/totals'

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


def get_project_seconds(auth, workspace_id, project_id, start, end):
    search_criteria = {
        "project_ids": [project_id],
    }

    return get_seconds(auth, workspace_id, search_criteria, start, end)


def get_task_seconds(auth, workspace_id, task_id, start, end):
    search_criteria = {
        "task_ids": [task_id],
    }

    return get_seconds(auth, workspace_id, search_criteria, start, end)


def to_units(seconds, units):
    if units.lower() == 'seconds':
        return (seconds, 'seconds')
    elif units.lower() == 'minutes':
        return (seconds / 60.0, 'minutes')
    elif units.lower() == 'hours':
        return (seconds / 60.0 / 60.0, 'hours')
    elif units.lower() == 'days':
        return (seconds / 60.0 / 60.0 / 8.0, 'days')


def is_google_sheets(user_agent):
    """User-Agent: Mozilla/5.0 (compatible; GoogleDocs; apps-spreadsheets; +http://docs.google.com)"""
    return 'apps-spreadsheets' in user_agent


def make_toggl_link(start, end, project_id=None, task_id=None):
    """https://track.toggl.com/reports/detailed/2668357/from/2020-12-01/projects/165549143/to/2020-12-16/without/"""
    url = 'https://track.toggl.com/reports/detailed/%s/from/%s/%s/%s/to/%s/without/'
    if project_id:
        return url % (
                WORKSPACE_ID,
                start.strftime('%Y-%m-%d'),
                'projects',
                project_id,
                end.strftime('%Y-%m-%d')
                )
    else:
        return url % (
                WORKSPACE_ID,
                start.strftime('%Y-%m-%d'),
                'tasks',
                task_id,
                end.strftime('%Y-%m-%d')
                )

@app.route('/effort')
def effort():
    month = request.args.get('month')
    sprint = request.args.get('sprint')

    if month and not sprint:
        start, end = month_to_date_range(month)
    elif sprint:
        start, end = sprint_to_date_range(sprint) 
    else:
        return Response('Bad request: month and sprint both specified', 400)

    units = request.args.get('units', 'days')
    task_id = request.args.get('task')
    if task_id:
        task_id = int(task_id)
        toggl_link = make_toggl_link(start, end, task_id=task_id)

    project_id = request.args.get('project')
    if project_id:
        project_id = int(project_id)
        toggl_link = make_toggl_link(start, end, project_id=project_id)

    if task_id and project_id:
        return Response('Bad request: task and project both specified', 400)

    elif task_id:
        seconds = get_task_seconds(AUTH, WORKSPACE_ID, task_id, start, end)
    elif project_id:
        seconds = get_project_seconds(AUTH, WORKSPACE_ID, project_id, start, end)
    else:
        return Response('Bad request: no task or project specified', 400)

    x, y = to_units(seconds, units)

    if is_google_sheets(request.headers.get('User-Agent')):
        return '%s' % x

    else:
        return '<a href="%s" target="_blank">%s %s</a>' % (toggl_link, x, units)


if __name__ == '__main__':
    app.run()

