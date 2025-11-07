Get QC responses

Responses from Guided Reader Tasks in Flywheel are recorded in Postman API tool. This script retrieves all responses and add any new response data back to the applicable Flywheel container. 

Works for both T1 image QC and Incidental Findings Guided Reader Tasks. 
To run for T1 image QC, use command `python get_qc_responses -t t1_image_qc`.
To run for Incidental Findings, use command `python get_qc_responses -t incidental_findings`.

Requires postman API key stored in config file as variable "postman_api_key".
Variable "qc_base_dir" in get_qc_responses determines top-level local folder where raw responses and logs are stored. 