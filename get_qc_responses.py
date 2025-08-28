#!/usr/bin/env python3

from datetime import datetime
import flywheel
import json 
import pandas as pd
from pprint import pprint
import subprocess

current_datetime=datetime.now().strftime("%Y%m%d_%H%M%S")

t1_form_id = "6478f1f774fcd84f2224bf7e"


def download_postman_responses():
    result=subprocess.run(["./download_qc_reader_task.sh", t1_form_id], capture_output=True, text=True)
    # print(result.stdout)  ### dictionary: {'count':9,'results':[{},{}]}
    result_all = json.loads(result.stdout)
    # pprint(result_all)
    result_list = result_all['results']

    # list_for_df = []
    tmpdf = pd.DataFrame()
    try:
        print(f"{len(result_list)} responses retrieved")
    # #     # [pprint.pprint(result_list[i]) for i in range(0,len(result_list)) ]
        for i in range(0,len(result_list)):
            # pprint(result_list[i])
            df = pd.json_normalize(result_list[i], sep='_')
            # df.info()
            tmpdf = pd.concat([tmpdf,df])

            # dict_of_ratings = result_list[i]['response_data'] ### each result has a dict that is just form data, no other metadata
    # #         dict_of_ratings['RATER'] = result_list[i]['origin']['id']
    # #         dict_of_ratings['SESSION_ID'] = result_list[i]['parents']['session']
    # #         dict_of_ratings['ACQ_ID'] = result_list[i]['parents']['acquisition']
    # #         dict_of_ratings['FILE_ID'] = result_list[i]['parents']['file']
    # #         dict_of_ratings['task_created'] = result_list[i]['created']
    # #         dict_of_ratings['task_modified'] = result_list[i]['modified']
    # #         list_for_df.append(dict_of_ratings)
    except KeyError as e:
        print(f'Error {e}: {json.loads(result.stderr)}')

    tmpdf.info()
    ratings = tmpdf.copy()
    print(ratings.info())
    ratings.to_csv(f"ratings_responses_raw_{current_datetime}.csv", index=False, header=True)
    return ratings


def add_response_to_flywheel(ratings):
    fw = flywheel.Client()

    for index,row in ratings.iterrows():
        ## TODO: filter ratings df on modified date in last week? 
        session = fw.get(row['parents_session'])

        ratings.at[index,'INDD'] = session.subject.label
        ratings.at[index,'SCANDATE'] = str(session.timestamp)[:10].replace("-", "")

        ### get acquisition object
        acq = session.acquisitions.find(f"_id={row['parents_acquisition']}")  
            ## should always return one item, never more than that, might be 0 if acquisition has been removed
        # if len(acq) == 1:
        if len(acq) > 1:
            print('flywheel id error, multiple matches')
        else:
            try:
                this_acq = acq[0].reload()
                # print(this_acq['label'])
                ratings.at[index,'SEQUENCE_NAME'] = this_acq['label']

                # Get file for adding rating info to metadata
                file_rated = [f for f in this_acq.files if f.file_id == row['parents_file']][0]
                # print(file_rated.name)


                ### what is the key to check for? either qc_info or incidental_finding
                ### incidental finding checks on a different level

                fw_info_key = "qc_info"
                ## check if info exists in flywheel container already:
                # if file_rated.info[fw_info_key]:
                #     print('testing')
                try:
                    if file_rated.info[fw_info_key]:   
                        print('already have qc data for this one, skip and flag for manual review')
                except KeyError:
                    print('no existing qc')

                    ### collect QC data to add to flywheel container into a dictionary
                    info_toadd = {fw_info_key:{}}
                    for col in ratings.columns:
                        if "response_data" in col:
                            ### TODO: edit col names here
                            newname = "_".join(col.split("_")[2:]) 
                            print(newname)
                            info_toadd[fw_info_key][col] = row[col]
                    
                    info_toadd[fw_info_key]['qc_rater'] = row['origin_id'].split("@")[0]
                    info_toadd[fw_info_key]['qc_completion_date'] = row['modified'].split("T")[0]

                    # info_toadd = {"fw_info_key":
                    #                 {"qc_t1_wholebrain":row['t1_wholebrain'],
                    #                 "qc_t1_motion":row['t1_motion'],
                    #                 "qc_t1_other_artifact":row['t1_otherart'],
                    #                 "qc_t1_comments":row['notes'],
                    #                 "qc_rater":row['origin_id'], 
                    #                 "qc_completed":row['modified']
                    #                 }   
                    #                 }
                    print(info_toadd)
                    # file_rated.update_info(info_toadd)
            except IndexError:
                print("Acqusition not found")

    return ratings


def save_copy_of_ratings(ratings):
    ratings = ratings.drop(columns=["SESSION_ID", "ACQ_ID", "scan"]).rename(
        columns={'t1_wholebrain':"T1_WHOLEBRAIN","t1_motion":"T1_MOTION","t1_otherart":"T1_OTHER_ARTIFACT","notes":"T1_COMMENTS"})
    ratings = ratings[['INDD','SCANDATE','SEQUENCE_NAME','RATER',"T1_WHOLEBRAIN", "T1_MOTION", "T1_OTHER_ARTIFACT", "T1_COMMENTS", "FILE_ID"]]
    print(ratings.info())
    ratings.to_csv(f"T1_QC_ratings_{current_datetime}.csv",index=False,header=True)
    return


def main():
    # ratings = download_postman_responses()
    ratings = pd.read_csv("/Users/emilymcgrew/Library/CloudStorage/Box-Box/scripts/flywheel/get_qc_responses/ratings_responses_raw_20250828_102709.csv")
    formatted_ratings = add_response_to_flywheel(ratings)
    # save_copy_of_ratings(formatted_ratings)


if __name__ == "__main__":
    main()