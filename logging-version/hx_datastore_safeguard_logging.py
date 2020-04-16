"""
Cisco HyperFlex Datastore Safeguard v1
Author: Ugo Emekauwa
Contact: uemekauw@cisco.com, uemekauwa@gmail.com
Summary: Cisco HyperFlex Datastore Safeguard for Cisco HyperFlex
         utilizes the HyperFlex API to automatically restore a targeted
         datastore's configuration if it is modified or deleted.
"""

# Import needed modules
import sys
import logging
import requests
import json
import urllib3
from datetime import datetime


######################
# Required Variables #
######################
log_file = ""
hx_admin = "admin"
hx_password = "C1sco12345!"
hx_connect_ip = "192.168.1.100"
hx_datastore_safeguard_list = ()


# Setup Logging
logging.basicConfig(filename=log_file, filemode='w', level=logging.DEBUG, format="%(asctime)s %(message)s")
logging.info("Starting the HyperFlex Datastore Safeguard Script.\n")

# Suppress InsecureRequestWarning
urllib3.disable_warnings()

# Obtain HyperFlex API access token
hx_token_request_headers = {"Content-Type": "application/json"}
hx_token_request_url = "https://{}/aaa/v1/auth?grant_type=password".format(hx_connect_ip)
hx_token_post_body = {
    "username": hx_admin,
    "password": hx_password,
    "client_id": "HxGuiClient",
    "client_secret": "Sunnyvale",
    "redirect_uri": "http://localhost:8080/aaa/redirect"
    }

try:
    logging.info("Attempting to obtain the HyperFlex API access token...")
    obtain_hx_api_token = requests.post(hx_token_request_url, headers=hx_token_request_headers, data=json.dumps(hx_token_post_body), verify=False)
    if obtain_hx_api_token.status_code == 201:
        hx_api_token_type = obtain_hx_api_token.json()["token_type"]
        hx_api_access_token = obtain_hx_api_token.json()["access_token"]
        logging.info("The HyperFlex API access token was sucessfully obtained.\n")
    else:
        logging.info("There was an error obtaining the HyperFlex API access token: ")
        logging.info("Status Code: {}".format(str(obtain_hx_api_token.status_code)))
        logging.info("{}\n".format(str(obtain_hx_api_token.json())))
        sys.exit(0)
except Exception as exception_message:
    logging.info("There was an error obtaining the HyperFlex API access token: ")
    logging.info("{}\n".format(str(exception_message)))
    sys.exit(0)
    
# Retrieve configured HyperFlex cluster information
hx_cluster_request_headers = {
    "Accept-Language": "application/json",
    "Authorization": "{}{}".format(str(hx_api_token_type), str(hx_api_access_token))
    }
hx_cluster_request_url = "https://{}/coreapi/v1/clusters".format(hx_connect_ip)

try:
    logging.info("Attempting to obtain the HyperFlex cluster configuration information...")
    get_hx_cluster = requests.get(hx_cluster_request_url, headers=hx_cluster_request_headers, verify=False) 
    if get_hx_cluster.status_code == 200:
        hx_cluster = get_hx_cluster.json()
        hx_cluster_name = hx_cluster[0]["name"]
        hx_cluster_uuid = hx_cluster[0]["uuid"]
        logging.info("The HyperFlex cluster named {} with the UUID {} has been found.\n".format(hx_cluster_name, hx_cluster_uuid))
    else:
        logging.info("There was an error obtaining the HyperFlex cluster configuration information: ")
        logging.info("Status Code: {}".format(str(get_hx_cluster.status_code)))
        logging.info("{}\n".format(str(get_hx_cluster.json())))
except Exception as exception_message:
    logging.info("There was an error obtaining the HyperFlex cluster configuration information: ")
    logging.info("{}\n".format(str(exception_message)))

# Retrieve current HyperFlex datastores list
get_hx_datastores_request_headers = {
    "Accept-Language": "application/json",
    "Authorization": "{}{}".format(str(hx_api_token_type), str(hx_api_access_token))
    }
get_hx_datastores_request_url = "https://{}/coreapi/v1/clusters/{}/datastores".format(hx_connect_ip, hx_cluster_uuid)

try:
    logging.info("Attempting to obtain the list of configured HyperFlex datastores...")
    get_hx_datastores = requests.get(get_hx_datastores_request_url, headers=get_hx_datastores_request_headers, verify=False) 
    if get_hx_datastores.status_code == 200:
        hx_datastores = get_hx_datastores.json()
        if not hx_datastores:
            logging.info("No HyperFlex datastores were found.")
        else:
            logging.info("The following HyperFlex datastores have been found:")
            for index, hx_datastore in enumerate(hx_datastores, start=1):
                if hx_datastore["dsconfig"]["provisionedCapacity"] >= 1099511627776:
                    hx_datastore_size = hx_datastore["dsconfig"]["provisionedCapacity"] / 1099511627776
                    hx_datastore_size_unit = "TB"
                else:
                    hx_datastore_size = hx_datastore["dsconfig"]["provisionedCapacity"] / 1073741824
                    hx_datastore_size_unit = "GB"
                hx_datastore_creation_time = datetime.fromtimestamp(int(hx_datastore["creationTime"])).strftime("%I:%M:%S %p on %A, %B %d, %Y")
                logging.info("    {}. {} with a provisioned size of {} {} and a creation time of {}. The block size is {}.".format(index, hx_datastore["dsconfig"]["name"], hx_datastore_size, hx_datastore_size_unit, hx_datastore_creation_time, hx_datastore["dsconfig"]["dataBlockSize"]))
    else:
        logging.info("There was an error obtaining the list of configured HyperFlex datastores: ")
        logging.info("Status Code: {}".format(str(get_hx_datastores.status_code)))
        logging.info("{}\n".format(str(get_hx_datastores.json())))
        sys.exit(0)
except Exception as exception_message:
    logging.info("There was an error obtaining the list of configured HyperFlex datastores: ")
    logging.info("{}\n".format(str(exception_message)))
    sys.exit(0)

# Check state of safeguarded HyperFlex datastores and remediate if necessary
update_hx_datastores_request_headers = {
    "Accept-Language": "application/json",
    "Authorization": "{}{}".format(str(hx_api_token_type), str(hx_api_access_token)),
    "Content-Type": "application/json"
    }

delete_hx_datastores_request_headers = {
    "Accept-Language": "application/json",
    "Authorization": "{}{}".format(str(hx_api_token_type), str(hx_api_access_token)),
    }

try:
    logging.info("Verifying that the HyperFlex Datastore Safeguard list requirements are met...")
    if hx_datastore_safeguard_list:
        for index, hx_safeguarded_datastore in enumerate(hx_datastore_safeguard_list):
            if len(hx_safeguarded_datastore["Name"].strip()) == 0:
                logging.info("There is an issue with the dictionary entry for the datastore at index {} in the HyperFlex Safeguard Datastore list!".format(index))
                logging.info("The provided name is empty and not an accepted value for the 'Name' dictionary key.".format(index))
                logging.info("The following dictionary entry needs to be repaired: {}.".format(hx_safeguarded_datastore))
                logging.info("Please provide a valid string value for the 'Name' key in the dictionary entry and restart the script:")
                sys.exit(0)
            if hx_safeguarded_datastore["SizeUnit"].upper() not in ("TB","GB","B"):
                logging.info("There is an issue with the dictionary entry for the datastore named {} at index {} in the HyperFlex Safeguard Datastore list!".format(hx_safeguarded_datastore["Name"].strip(), index))
                logging.info("The provided size unit value '{}' is not an accepted value for the 'SizeUnit' dictionary key.".format(hx_safeguarded_datastore["SizeUnit"]))
                logging.info("The following dictionary entry needs to be repaired: {}.".format(hx_safeguarded_datastore))
                logging.info("Please provide one of the following accepted string values for the 'SizeUnit' dictionary key and restart the script:")
                logging.info("1. 'TB' for terabytes.")
                logging.info("2. 'GB' for gigabytes.")
                logging.info("3. 'B' for bytes.")
                sys.exit(0)
            else:
                if hx_safeguarded_datastore["SizeUnit"].upper() == "TB":
                    hx_safeguarded_datastore_size_in_bytes = int(hx_safeguarded_datastore["Size"]) * 1099511627776
                elif hx_safeguarded_datastore["SizeUnit"].upper() == "GB":
                    hx_safeguarded_datastore_size_in_bytes = int(hx_safeguarded_datastore["Size"]) * 1073741824
                else:
                    hx_safeguarded_datastore_size_in_bytes = int(hx_safeguarded_datastore["Size"])            
            if int(hx_safeguarded_datastore["BlockSize"]) not in (4096, 8192):
                logging.info("There is an issue with the dictionary entry for the datastore named {} at index {} in the HyperFlex Safeguard Datastore list!".format(hx_safeguarded_datastore["Name"].strip(), index))
                logging.info("The provided block size value '{}' is not an accepted value for the 'BlockSize' dictionary key.".format(int(hx_safeguarded_datastore["BlockSize"])))
                logging.info("The following dictionary entry needs to be repaired: {}.".format(hx_safeguarded_datastore))
                logging.info("Please provide one of the following accepted integer values for the 'BlockSize' dictionary key and restart the script:")
                logging.info("1. 8192")
                logging.info("2. 4096")
                logging.info("Note: The recommended value is 8192.")
                sys.exit(0)
            for hx_datastore in hx_datastores:
                if hx_safeguarded_datastore["Name"].strip() == hx_datastore["dsconfig"]["name"]:
                    logging.info("The safeguarded datastore named {} has been found on the HyperFlex cluster.".format(hx_safeguarded_datastore["Name"].strip()))
                    if hx_safeguarded_datastore_size_in_bytes != hx_datastore["dsconfig"]["provisionedCapacity"]:
                        if hx_safeguarded_datastore["SizeUnit"].upper() == "TB":
                            hx_datastore_size_returned = hx_datastore["dsconfig"]["provisionedCapacity"] / 1099511627776
                        elif hx_safeguarded_datastore["SizeUnit"].upper() == "GB":
                            hx_datastore_size_returned = hx_datastore["dsconfig"]["provisionedCapacity"] / 1073741824
                        else:
                            hx_datastore_size_returned = hx_datastore["dsconfig"]["provisionedCapacity"]
                        logging.info("The current provisioned capacity for {} is {} {}. This does not match the safeguarded requirement of {} {}.".format(hx_safeguarded_datastore["Name"].strip(), hx_datastore_size_returned, hx_safeguarded_datastore["SizeUnit"].upper(), int(hx_safeguarded_datastore["Size"]), hx_safeguarded_datastore["SizeUnit"].upper()))
                        logging.info("Attempting to repair...")
                        put_hx_datastores_request_url = "https://{}/coreapi/v1/clusters/{}/datastores/{}".format(hx_connect_ip, hx_cluster_uuid, hx_datastore["uuid"])
                        updated_datastore_body = {
                            "name": hx_safeguarded_datastore["Name"].strip(),
                            "sizeInBytes": hx_safeguarded_datastore_size_in_bytes
                            }
                        logging.info("Updating the provisioned capacity...")
                        update_hx_datastore = requests.put(put_hx_datastores_request_url, headers=update_hx_datastores_request_headers, data=json.dumps(updated_datastore_body), verify=False)
                        if update_hx_datastore.status_code == 200:
                            logging.info("The provisioned capacity for {} has been restored to the safeguarded provisioned capacity of {} {}.".format(hx_safeguarded_datastore["Name"].strip(), int(hx_safeguarded_datastore["Size"]), hx_safeguarded_datastore["SizeUnit"].upper()))
                        else:
                            logging.info("There was an error restoring the provisioned capacity for {}.".format(hx_safeguarded_datastore["Name"].strip()))
                            logging.info("Status Code: {}".format(str(update_hx_datastore.status_code)))
                            logging.info("{}\n".format(str(update_hx_datastore.json())))
                    else:
                        logging.info("The current provisoned capacity for {} matches the safeguarded requirements.".format(hx_safeguarded_datastore["Name"].strip()))
                    if int(hx_safeguarded_datastore["BlockSize"]) != hx_datastore["dsconfig"]["dataBlockSize"]:
                        logging.info("The current data block size for {} is {}. This does not match the safeguarded requirement of {}.".format(hx_safeguarded_datastore["Name"].strip(), hx_datastore["dsconfig"]["dataBlockSize"], int(hx_safeguarded_datastore["BlockSize"])))
                        logging.info("Attempting to repair...")
                        delete_hx_datastores_request_url = "https://{}/coreapi/v1/clusters/{}/datastores/{}".format(hx_connect_ip, hx_cluster_uuid, hx_datastore["uuid"])
                        logging.info("Deleting the invalid datastore...")
                        delete_hx_datastore = requests.delete(delete_hx_datastores_request_url, headers=delete_hx_datastores_request_headers, verify=False)
                        if delete_hx_datastore.status_code == 200:
                            logging.info("The invalid datastore has been deleted.")
                            logging.info("Attempting to re-create {}...".format(hx_safeguarded_datastore["Name"].strip()))
                            post_hx_datastores_request_url = "https://{}/coreapi/v1/clusters/{}/datastores".format(hx_connect_ip, hx_cluster_uuid)
                            new_datastore_body = {
                                        "name": hx_safeguarded_datastore["Name"].strip(),
                                        "sizeInBytes": hx_safeguarded_datastore_size_in_bytes,
                                        "dataBlockSizeInBytes": int(hx_safeguarded_datastore["BlockSize"]),
                                        "siteName": hx_safeguarded_datastore["Name"].strip()
                                        }
                            new_hx_datastore = requests.post(post_hx_datastores_request_url, headers=update_hx_datastores_request_headers, data=json.dumps(new_datastore_body), verify=False)
                            if new_hx_datastore.status_code == 200:
                                logging.info("The safeguarded datastore named {} has been re-created on the HyperFlex cluster with the data block size of {}.".format(hx_safeguarded_datastore["Name"].strip(), int(hx_safeguarded_datastore["BlockSize"])))
                            else:
                                logging.info("There was an error creating {}.".format(hx_safeguarded_datastore["Name"].strip()))
                                logging.info("Status Code: {}".format(str(new_hx_datastore.status_code)))
                                logging.info("{}\n".format(str(new_hx_datastore.json())))
                        else:
                            logging.info("There was an error deleting {}.".format(hx_safeguarded_datastore["Name"].strip()))
                            logging.info("Status Code: {}".format(str(delete_hx_datastore.status_code)))
                            logging.info("{}\n".format(str(delete_hx_datastore.json())))
                    else:
                        logging.info("The current data block size for {} matches the safeguarded requirements.".format(hx_safeguarded_datastore["Name"].strip()))
                    break
            else:
                logging.info("The safeguarded datastore named {} was not found on the HyperFlex cluster.".format(hx_safeguarded_datastore["Name"].strip()))
                logging.info("Attempting to create {}...".format(hx_safeguarded_datastore["Name"].strip()))
                post_hx_datastores_request_url = "https://{}/coreapi/v1/clusters/{}/datastores".format(hx_connect_ip, hx_cluster_uuid)
                new_datastore_body = {
                            "name": hx_safeguarded_datastore["Name"].strip(),
                            "sizeInBytes": hx_safeguarded_datastore_size_in_bytes,
                            "dataBlockSizeInBytes": int(hx_safeguarded_datastore["BlockSize"]),
                            "siteName": hx_safeguarded_datastore["Name"].strip()
                            }
                new_hx_datastore = requests.post(post_hx_datastores_request_url, headers=update_hx_datastores_request_headers, data=json.dumps(new_datastore_body), verify=False)
                if new_hx_datastore.status_code == 200:
                    logging.info("The safeguarded datastore named {} has been created on the HyperFlex cluster.".format(hx_safeguarded_datastore["Name"].strip()))
                else:
                    logging.info("There was an error creating {}.".format(hx_safeguarded_datastore["Name"].strip()))
                    logging.info("Status Code: {}".format(str(new_hx_datastore.status_code)))
                    logging.info("{}\n".format(str(new_hx_datastore.json())))
    else:
        logging.info("No safeguarded datastores have been added to the script.")
        logging.info("Please add the datastore(s) to be safeguarded and re-run the script.")
        sys.exit(0)
except Exception as exception_message:
    logging.info("There was an error verifying the safeguarded HyperFlex datastores: ")
    logging.info("{}\n".format(str(exception_message)))

# Exiting the HyperFlex Datastore Safeguard Script
logging.info("The HyperFlex Datastore Safeguard Script is complete.\n\n")
sys.exit(0)
