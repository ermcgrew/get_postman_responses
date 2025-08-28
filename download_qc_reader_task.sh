#!/usr/bin/env bash

source /Users/emilymcgrew/Library/CloudStorage/Box-Box/scripts/flywheel/get_qc_responses/config.py 

form_id=$1

curl --location "https://upenn.flywheel.io/api/forms/${form_id}/responses" \
--header "Authorization: scitran-user upenn.flywheel.io:${postman_api_key}"

