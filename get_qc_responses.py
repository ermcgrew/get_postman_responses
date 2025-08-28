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

    logging.info(ratings.info())
    ratings.to_csv(f"ratings_responses_raw_{res_type}_{current_datetime}.csv", index=False, header=True)

    return ratings


def does_info_exist(container,info_key):
    try:
        if container.info[info_key]:   
            logging.warning('Already have data for this one, skip and flag for manual review.')
            return True
    except KeyError:
        # logging.info('no existing data')
        return False


def update_flywheel_container(container, info):
    logging.info(f"updating container with response info.")
    # container.update_info(info)
    return


def add_response_to_flywheel(ratings):
    fw = flywheel.Client()
    for index,row in ratings.iterrows():
        ### if running weekly with the rename and create tasks script 
        date_test = datetime.strptime(row['modified'].split(".")[0], "%Y-%m-%dT%H:%M:%S")
        if date_test <= weekago_dt:
            ## data from before last run, skip
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

            ### Grab some extra data for the hard copy csv
            ### TODO: don't add this to the df, capture in another way to send back to main function
            # ratings.at[index,'INDD'] = session.subject.label
            # ratings.at[index,'SCANDATE'] = str(session.timestamp)[:10].replace("-", "")

            if res_type == "incidental_findings":
                if does_info_exist(session,fw_info_key) == False:
                    update_flywheel_container(session,info_toadd)
            else: 
                try: 
                    acq = fw.get(row['parents_acquisition'])
                except:
                    logging.warning('acq not found')
                    continue
                this_acq = acq.reload()
                file_rated = [f for f in this_acq.files if f.file_id == row['parents_file']][0]
                if does_info_exist(file_rated,fw_info_key) == False:
                    update_flywheel_container(file_rated,info_toadd)
                
                ### TODO: dont' add this to df, capture another way?
                # ratings.at[index,'SEQUENCE_NAME'] = this_acq['label']

    return ratings


def save_copy_of_ratings(ratings_plus):
    ratings_plus.info()
    [print(col) for col in ratings_plus.columns]

    ## pull this as a data view after? already setting up appropriate column names above

    ## cols to keep: response_data_*, INDD, SCANDATE, origin_id, modified, parents_session
        ### if t1_image_qc: SEQUENCE_NAME, parents_file

    # ratings = ratings.drop(columns=["SESSION_ID", "ACQ_ID", "scan"]).rename(
    #     columns={'t1_wholebrain':"T1_WHOLEBRAIN","t1_motion":"T1_MOTION","t1_otherart":"T1_OTHER_ARTIFACT","notes":"T1_COMMENTS"})

    # ratings = ratings[['INDD','SCANDATE','SEQUENCE_NAME','RATER',"T1_WHOLEBRAIN", "T1_MOTION", "T1_OTHER_ARTIFACT", "T1_COMMENTS", "FILE_ID"]]
    # print(ratings.info())
    # ratings.to_csv(f"T1_QC_ratings_{current_datetime}.csv",index=False,header=True)
    return


def main():
    # ratings = download_postman_responses()
    ratings = pd.read_csv("/Users/emilymcgrew/Library/CloudStorage/Box-Box/scripts/flywheel/get_qc_responses/ratings_responses_raw_20250828_102709.csv")
    ratings_plus = add_response_to_flywheel(ratings)
    # ratings_plus.to_csv(f"{res_type}_plus_{current_datetime}.csv",index=False,header=True)
    # ratings_plus = pd.read_csv("/Users/emilymcgrew/Library/CloudStorage/Box-Box/scripts/flywheel/get_qc_responses/t1_image_qc_plus_20250828_140033.csv")
    # save_copy_of_ratings(ratings_plus)


logging.basicConfig(format="%(levelname)s:%(message)s", level=logging.DEBUG)

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

