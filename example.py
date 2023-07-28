from AzureLib import Azure

# Create AzureSubscription object
# Parameters: subFilter, vmFilter, OS, OS Type, OS Version
# subFilter: Filter the subscription based on tags and name
# vmFilter: Filter the VMs based on tags and name
# OS: Filter the VMs based on OS
# OS Type: Filter the VMs based on OS Type
# OS Version: Filter the VMs based on OS Version


azacct = Azure({
            # Subscription Filter
            "Name": [],
            "Tags": {
                "mytag": "tags-value"
            }
        }, {
            # VM Tag Filter
            "Name": [""],
            "Tags": {
                "supported": "Yes"
            }
        }, ["Windows"], ["WindowsServer"])

# Get KMS and Reachability Status
azacct.run_command(
    "Windows",
    [
        'cscript C:\\windows\\system32\\slmgr.vbs /dlv | select-string -pattern "License Status"',
        'cscript C:\\windows\\system32\\slmgr.vbs /dlv | select-string -pattern "Registered KMS machine name"',
        'cscript C:\\windows\\system32\\slmgr.vbs /dlv | select-string -pattern "KMS machine IP address"',
        '$kms = cscript C:\\windows\\system32\\slmgr.vbs /dlv | select-string -pattern "KMS Machine name:" | out-string -stream',
        'write-host "KMS_Reachable:" (tnc -ComputerName $kms.split(":")[2].trim() -Port $kms.split(":")[3].trim() -InformationLevel detailed).TcpTestSucceeded',
        'systeminfo | findstr -i "domain"'
    ])


# Clear KMS and Configure it to use DNS
# azacct.run_command(
#     "Windows",
#     [
#         'cscript C:\\windows\\system32\\slmgr.vbs /ckms',
#         'cscript C:\\windows\\system32\\slmgr.vbs /ato | select-string -pattern "Registered KMS machine name"',
#         'cscript C:\\windows\\system32\\slmgr.vbs /dlv | select-string -pattern "License Status"',
#         'cscript C:\\windows\\system32\\slmgr.vbs /dlv | select-string -pattern "Registered KMS machine name"',
#         'cscript C:\\windows\\system32\\slmgr.vbs /dlv | select-string -pattern "KMS machine IP address"',
#     ])


azacct.export_csv("vmlist.csv")
print(str(azacct))