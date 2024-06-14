import requests
import urllib3

PVE_IP = "" # IP address of the Proxmox node that you want to back up
TrueNAS_IP = "" # IP address of the remote TrueNAS server
PiKVM_IP = "" # IP address of your PiKVM

PVE_Node_Name = "" # Name of the Proxmox node that you want to back up

PVE_Backup_Storage_ID = "" # ID that you assigned when adding the SMB share as a Proxmox backup storage target

TrueNAS_Replication_Task_ID = "" # Get the ID of the preconfigured replication task that you want to run by executing "midctl call replication.query" in the TrueNAS shell

PVE_API_Key_ID = "" # ID that you assigned when adding the API key
PVE_API_Key = "" # Generate an API key by navigating to Datacenter > Permissions > API Tokens > Add in the Proxmox web interface
TrueNAS_API_Key = "" # Generate an API key by navigating to Settings > API Keys > Add in the TrueNAS web interface
PiKVM_Username = "" # Username of your PiKVM, default is "admin"
PiKVM_Password = "" # Password of your PiKVM

# Disable warnings that are raised when SSL certificates are not verified
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Start the remote server via the PiKVM ATX power management API
requests.post("https://" + PiKVM_IP + "/api/atx/power?action=on", headers={"X-KVMD-User": PiKVM_Username, "X-KVMD-Passwd": PiKVM_Password}, verify=False)

# Wait for the specified Proxmox backup target storage to become active
while True:
    StatusResponse = requests.get("https://" + PVE_IP + ":8006/api2/json/nodes/" + PVE_Node_Name + "/storage/" + PVE_Backup_Storage_ID + "/status", headers={"Authorization": f"PVEAPIToken=root@pam!{PVE_API_Key_ID}={PVE_API_Key}"}, verify=False).json().get("data", [])
    if StatusResponse.get("active") == 1:
        break
    print(StatusResponse)

# Back up all Proxmox VMs to the specified backup storage target
requests.post("https://" + PVE_IP + ":8006/api2/json/nodes/" + PVE_Node_Name + "/vzdump", data={"all": "1", "compress": "zstd", "storage": PVE_Backup_Storage_ID}, headers={"Authorization": f"PVEAPIToken=root@pam!{PVE_API_Key_ID}={PVE_API_Key}"}, verify=False)

# Wait for all Proxmox backups to finish
while True:
    TasksResponse = (requests.get("https://" + PVE_IP + ":8006/api2/json/cluster/tasks", headers={"Authorization": f"PVEAPIToken=root@pam!{PVE_API_Key_ID}={PVE_API_Key}"}, verify=False).json()).get("data", [])
    StatusNotInTaskResponseObject = []
    for TaskResponseObject in TasksResponse:
        if TaskResponseObject.get("type") == "vzdump" and "status" not in TaskResponseObject: StatusNotInTaskResponseObject.append(TaskResponseObject)
    if len(StatusNotInTaskResponseObject) == 0:
        break

# Start the specified TrueNAS replication task
requests.post("https://" + TrueNAS_IP + "/api/v2.0/replication/id/" + TrueNAS_Replication_Task_ID + "/run", headers={"Authorization": f"Bearer {TrueNAS_API_Key}"}, verify=False)

# Wait for all TrueNAS replication tasks to finish
while True:
    JobsResponse = requests.get("https://" + TrueNAS_IP + "/api/v2.0/core/get_jobs", headers={"Authorization": f"Bearer {TrueNAS_API_Key}"}, verify=False).json()
    StateRunning = []
    for JobResponseObject in JobsResponse:
        if JobResponseObject.get("method") == "replication.run" and JobResponseObject.get("state") == "RUNNING":
            StateRunning.append(JobResponseObject)
    if len(StateRunning) == 0:
        break

# Shut down the remote rerver
requests.post("https://" + TrueNAS_IP + "/api/v2.0/system/shutdown", headers={"Authorization": f"Bearer {TrueNAS_API_Key}"}, verify=False)
