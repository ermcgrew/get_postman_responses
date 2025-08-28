#!/usr/bin/env python3

from datetime import datetime
import flywheel
import json 
import pandas as pd
from pprint import pprint
import subprocess

current_datetime=datetime.now().strftime("%Y%m%d_%H%M%S")

t1_form_id = "6478f1f774fcd84f2224bf7e"

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


# ratings = pd.DataFrame(list_for_df)
# print(ratings.info())

# ratings.to_csv(f"ratings_responses_raw_{current_datetime}.csv",index=False,header=True)
# ratings = pd.read_csv("/Users/emilymcgrew/Library/CloudStorage/Box-Box/scripts/flywheel/get_qc_responses/ratings_responses_raw_20250811_144812.csv")
# ratings = pd.read_csv("/Users/emilymcgrew/Library/CloudStorage/Box-Box/scripts/flywheel/get_qc_responses/ratings_responses_raw_20250819_122120.csv")

# fw = flywheel.Client()
# try:
#     project = fw.get_project('5c508d5fc2a4ad002d7628d8') #NACC-SC
# except flywheel.ApiException as e:
#     print(f'Error: {e}')

# for index,row in ratings.iterrows():
#     ## TODO: filter ratings df on modified date in last week? 

#     session = fw.get(row['SESSION_ID'])
#     ratings.at[index,'INDD'] = session.subject.label
#     ratings.at[index,'SCANDATE'] = str(session.timestamp)[:10].replace("-", "")

#     acq = session.acquisitions.find(f"_id={row['ACQ_ID']}")
#     if len(acq) == 1:
#         acq[0]=acq[0].reload()
#         ratings.at[index,'SEQUENCE_NAME'] = acq[0]['label']

#         ## Get file for adding rating info to metadata
#         file_rated = [f for f in acq[0].files if f.file_id == row['FILE_ID']][0]
#         print(file_rated.name)

#         ## check if qc info exists:
#         try:
#             if file_rated.info['qc_info']:   
#                 print('already have qc data for this one, skip and flag for manual review')
#         except:
#             print('no existing qc')
#             qcinfo_toadd = {"qc_info":
#                             {"qc_t1_wholebrain":row['t1_wholebrain'],
#                             "qc_t1_motion":row['t1_motion'],
#                             "qc_t1_other_artifact":row['t1_otherart'],
#                             "qc_t1_comments":row['notes'],
#                             "qc_rater":row['RATER'], 
#                             "qc_completed":row['task_modified']
#                             }   
#                             }
#             print(qcinfo_toadd)
#             # file_rated.update_info(qcinfo_toadd)        


# ratings = ratings.drop(columns=["SESSION_ID", "ACQ_ID", "scan"]).rename(
#     columns={'t1_wholebrain':"T1_WHOLEBRAIN","t1_motion":"T1_MOTION","t1_otherart":"T1_OTHER_ARTIFACT","notes":"T1_COMMENTS"})
# ratings = ratings[['INDD','SCANDATE','SEQUENCE_NAME','RATER',"T1_WHOLEBRAIN", "T1_MOTION", "T1_OTHER_ARTIFACT", "T1_COMMENTS", "FILE_ID"]]
# print(ratings.info())
# ratings.to_csv(f"T1_QC_ratings_{current_datetime}.csv",index=False,header=True)