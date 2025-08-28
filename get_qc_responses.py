#!/usr/bin/env python3

import argparse
from datetime import datetime, timedelta
import flywheel
import json 
import logging
import pandas as pd
import subprocess
import sys

current_datetime=datetime.now().strftime("%Y%m%d_%H%M%S")
weekago_dt = datetime.now() - timedelta(days=7)

def download_postman_responses():
    result=subprocess.run(["./download_qc_reader_task.sh", form_id], capture_output=True, text=True) 

    try:
        result_all = json.loads(result.stdout)
    except KeyError as e:
        logging.error(f'Error {e}: {json.loads(result.stderr)}')
        sys.exit(1) 

    result_list = result_all['results']
    logging.info(f"{len(result_list)} responses retrieved")
    ratings = pd.DataFrame()

    for i in range(0,len(result_list)):
        df = pd.json_normalize(result_list[i], sep='_')
        ratings = pd.concat([ratings,df])

    ratings.to_csv(f"ratings_responses_raw_{res_type}_{current_datetime}.csv", index=False, header=True)

    return ratings


def does_info_exist(container,info_key, session_name):
    try:
        if container.info[info_key]:   
            logging.warning(f"Container {session_name} already contains data, flag for manual review.")
            return True
    except KeyError:
        return False


def update_flywheel_container(container, info, session_name):
    logging.info(f"updating container {session_name} with response info.")
    try:
        container.update_info(info)
        return 1
    except:
        logging.error(f"error updating container")
        return 0


def main():
    ratings = download_postman_responses()
    # ratings = pd.read_csv("/Users/emilymcgrew/Library/CloudStorage/Box-Box/scripts/flywheel/get_qc_responses/ratings_responses_raw_20250828_102709.csv")
    # ratings = pd.read_csv("/Users/emilymcgrew/Library/CloudStorage/Box-Box/scripts/flywheel/get_qc_responses/ratings_responses_raw_incidental_findings_20250828_135718.csv")
    fw = flywheel.Client()

    ### if running weekly with the rename and create tasks script, identify new responses
    ratings['modified_short'] = ratings['modified'].str.split(".").str[0]
    ratings['modified_dt'] = pd.to_datetime(ratings['modified_short'])
    ratings.loc[ratings['modified_dt'] >= weekago_dt, ['new_rating']] = 1

    logging.info(f"{len(ratings.loc[ratings['new_rating'] == 1])} new responses from last week.")
    update_success = 0
    for index,row in ratings.iterrows():
        if row['new_rating'] != 1:
            continue
        else:
            ### collect response data to add to flywheel container into a dictionary
            info_toadd = {fw_info_key:{}}
            for col in ratings.columns:
                if "response_data" in col:
                    newname = f"{res_type}_" + "_".join(col.split("_")[-1:]) 
                    info_toadd[fw_info_key][newname] = row[col]
            info_toadd[fw_info_key][f"{res_type}_rater"] = row['origin_id'].split("@")[0]
            info_toadd[fw_info_key][f"{res_type}_completion_date"] = row['modified'].split("T")[0]

            ### get fw container to add the data to
            session = fw.get(row['parents_session'])
            session_name = session.label

            if res_type == "incidental_findings":
                if does_info_exist(session,fw_info_key, session_name) == False:
                    update_status = update_flywheel_container(session,info_toadd, session_name)
                    update_success += update_status
            else: 
                ### get to fw file container via acqusition
                try: 
                    acq = fw.get(row['parents_acquisition'])
                except:
                    logging.warning('acq not found')
                    continue
                this_acq = acq.reload()
                file_rated = [f for f in this_acq.files if f.file_id == row['parents_file']][0]
                if does_info_exist(file_rated,fw_info_key, session_name) == False:
                    update_status = update_flywheel_container(file_rated,info_toadd, session_name)
                    update_success += update_status

                    ### TODO: if whole brain value == no or motion value > 3, add "unusable/quarantine" tag?

    logging.info(f"{update_success} containers updated with new response data.")
    ### TODO: add dataview to pull new copy of response info as it is in flywheel


logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.DEBUG)

parser = argparse.ArgumentParser()
parser.add_argument("-t","--response_type", choices = ["t1_image_qc","incidental_findings"], required=True, help="")
args = parser.parse_args()
res_type = args.response_type

if res_type == "t1_image_qc":
    form_id = "6478f1f774fcd84f2224bf7e"
elif res_type == "incidental_findings":
    form_id = "64624766938e6547fa225ee6"

fw_info_key = res_type

logging.info(f"running with response type {res_type}.")


if __name__ == "__main__":
    main()

