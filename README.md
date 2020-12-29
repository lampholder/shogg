# shoggl

A quick-and-dirty stateless API wrapper to expose toggl report sum data in a way that is easily ingested to Google sheets via an `IMPORTDATA` GET request.

## How to deploy

This is designed to work with Zappa to deploy to AWS lambda, so:

1. Create and source a python3 virtualenv
1. Make sure your relevant AWS credentials and config are set up correctly (in `~/.aws/` usually)
1. `cp config.example.yaml config.yaml`
1. Tweak `config.yaml` to your setup
1. `pip install -r requirements.txt`
1. `zappa init`
1. `zappa deploy production`

## How to use

You can make an unauthenticated GET request to `/effort` with the following params:

- `project` the ID of the toggl project on which to report. You must specify either a `project` or a `task`
- `task` the ID of the toggl task on which to report. You must specify either a `project` or a `task`
- `month` the month to report for, specified as YYYY-mm. You must specify either a `month` or a `sprint`
- `sprint` the sprint to report for, specified as YYYY.mm.<sprint ID (1 or 2)>. You must specify either a `month` or a `sprint`
- `units` the units in which to report. Options include seconds, minutes, hours or days 

If the user agent of the request includes the string "apps-spreadsheets" (signifying a request from Google Sheets) then just the value is returned. Otherwise, the value and units are returned, as a link linking to the relevant toggl report.
