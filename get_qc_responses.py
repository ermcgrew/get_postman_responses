#!/usr/bin/env python3

import argparse
from datetime import datetime, timedelta
import flywheel
import json 
import logging
import os
import pandas as pd
import subprocess
import sys

current_datetime=datetime.now().strftime("%Y%m%d_%H%M%S")
weekago_dt = datetime.now() - timedelta(days=7)

qc_base_dir = "/project/wolk/Prisma3T/relong/QC/3TT1/flywheel_T1QC"
raw_qc_dir = f"{qc_base_dir}/raw_responses"
logdir = f"{qc_base_dir}/logs"
qc_data_report_dir = f"{qc_base_dir}/data" 


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

    ratings.to_csv(os.path.join(raw_qc_dir,f"ratings_responses_raw_{res_type}_{current_datetime}.csv"), index=False, header=True)

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


def add_tag(fw_object,session_label):
    if completed_tag not in fw_object.tags:
        try:
            fw_object.add_tag(completed_tag)
            logging.info(f"{session_label}: added tag sucessfully") 
        except:
            logging.error(f"{session_label}: An error occurred when tagging.")
    else:
        logging.debug(f"{session_label}: already tagged.")


def main():
    ratings = download_postman_responses()
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
                    if "details" in col:
                        newname = f"{res_type}_" + "_".join(col.split("_")[-2:]) 
                        if type(row[col]) == list:
                            ## only this field comes out as strings in a list
                            valuetoadd = ";".join(row[col])
                    else: 
                        newname = f"{res_type}_" + "_".join(col.split("_")[-1:]) 
                        valuetoadd = row[col]

                    info_toadd[fw_info_key][newname] = valuetoadd

            info_toadd[fw_info_key][f"{res_type}_rater"] = row['origin_id'].split("@")[0]
            info_toadd[fw_info_key][f"{res_type}_completion_date"] = row['modified'].split("T")[0]
            logging.info(f"info to add: {info_toadd}")
            ### get fw container to add the data to
            session = fw.get(row['parents_session'])
            session_name = session.label

            if  res_type == "t1_image_qc":
                try: 
                    acq = fw.get(row['parents_acquisition'])
                except:
                    logging.warning('acq not found')
                    continue
                this_acq = acq.reload()
                container_to_update = [f for f in this_acq.files if f.file_id == row['parents_file']][0]
            else:
                container_to_update = session
            
            if does_info_exist(container_to_update, fw_info_key, session_name) == False:
                    update_status = update_flywheel_container(container_to_update,info_toadd, session_name)
                    update_success += update_status
                    if update_status == 1:
                        ## Add 'completed' tag to container 
                        add_tag(container_to_update, session_name)
                        ### TODO: if whole brain value == no or motion value > 3, add "unusable/quarantine" tag?

    logging.info(f"{update_success} containers updated with new response data.")
    ### TODO: add dataview to pull new copy of response info as it is in flywheel
    # os.path.join(qc_data_report_dir,"")


logging.basicConfig(filename = os.path.join(logdir,f"get_qc_response_log_{current_datetime}.txt"), filemode = "w", format="%(levelname)s: %(message)s", level=logging.DEBUG)

parser = argparse.ArgumentParser()
parser.add_argument("-t","--response_type", choices = ["t1_image_qc","incidental_findings"], required=True, help="")
args = parser.parse_args()
res_type = args.response_type

if res_type == "t1_image_qc":
    form_id = "6478f1f774fcd84f2224bf7e"
    completed_tag = "T1ImageQCdone"
elif res_type == "incidental_findings":
    form_id = "64624766938e6547fa225ee6"
    completed_tag = "IF_done"

fw_info_key = res_type

logging.info(f"running with response type {res_type}.")
main()

