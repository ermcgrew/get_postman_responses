#!/usr/bin/env bash

source /project/wolk/Prisma3T/relong/scripts/get_postman_responses/config.py

form_id=$1

curl --location "https://upenn.flywheel.io/api/forms/${form_id}/responses" \
--header "Authorization: scitran-user upenn.flywheel.io:${postman_api_key}"

