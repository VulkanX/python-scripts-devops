from AzureLib import Azure
import json
import sys

# ConfigFile

# Get Config from CLI Args
if len(sys.argv) > 1 and sys.argv[1].strip().lower() != "none":
    config_file = sys.argv[1]
else:
    print("No config file specified")

# Get Subscriptions from CLI Args
if len(sys.argv) > 2 and sys.argv[2].strip().lower() != "none":
    subscription_file = sys.argv[2]
else:
    subscription_file = None

# Get Server List from CLI Args
if len(sys.argv) > 3 and sys.argv[3].strip().lower() != "none":
    server_list_file = sys.argv[3]
else:
    server_list_file = None

# Get KMS Command from CLI Args
if len(sys.argv) > 4 and sys.argv[4].strip().lower() != "none":
    kms_command = sys.argv[4]
else:
    kms_command = None

# Get CSV Filename from CLI Args
if len(sys.argv) > 5 and sys.argv[5].strip().lower() != "none":
    csv_filename = sys.argv[5]
else:
    csv_filename = None


# Parse JSON file
with open(config_file, 'r') as stream:
    config = json.load(stream)

# If subscriptions text file was specified, load it
if subscription_file is not None:
    with open(subscription_file, 'r') as stream:
        data = stream.read().splitlines()
        config["subscriptionFilter"]["Name"] = data

# If server list text file was specified, load it
if server_list_file is not None:
    with open(server_list_file, 'r') as stream:
        data = stream.read().splitlines()
        config["vmFilter"]["Name"] = data


kms_check = [
    'cscript C:\\windows\\system32\\slmgr.vbs /dlv | select-string -pattern "License Status"',
    ('cscript C:\\windows\\system32\\slmgr.vbs /dlv'
        ' | select-string -pattern "Registered KMS machine name"'),
    ('cscript C:\\windows\\system32\\slmgr.vbs /dlv'
        ' | select-string -pattern "KMS machine IP address"'),
    ('$kms = cscript C:\\windows\\system32\\slmgr.vbs /dlv'
        ' | select-string -pattern "KMS Machine name:" | out-string -stream'),
    ('write-host "KMS_Reachable:" '
        '(tnc -ComputerName $kms.split(":")[2].trim() '
        '-Port $kms.split(":")[3].trim() -InformationLevel detailed).TcpTestSucceeded'),
    'systeminfo | findstr -i "domain"'
]

kms_fix = [
    'cscript C:\\windows\\system32\\slmgr.vbs /ckms',
    ('cscript C:\\windows\\system32\\slmgr.vbs /ato'
        ' | select-string -pattern "Registered KMS machine name"'),
    ('cscript C:\\windows\\system32\\slmgr.vbs /dlv'
        ' | select-string -pattern "License Status"'),
    ('cscript C:\\windows\\system32\\slmgr.vbs /dlv'
        ' | select-string -pattern "Registered KMS machine name"'),
    ('cscript C:\\windows\\system32\\slmgr.vbs /dlv'
        ' | select-string -pattern "KMS machine IP address"')
]

az = Azure(config["subscriptionFilter"], config["vmFilter"], config["osFilter"], config["osType"])

if kms_command == "check":
    print("Running KMS Check")
    az.run_command("Windows", kms_check)
elif kms_command == "fix":
    print("Running KMS Fix")
    az.run_command("Windows", kms_fix)

print(str(az), "\n")

if csv_filename is not None:
    az.export_csv(csv_filename)
