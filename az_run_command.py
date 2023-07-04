# Required Libraries azure-mgmt-compute azure-identity azure-mgmt-subscription

from azure.identity import DefaultAzureCredential
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.resource import SubscriptionClient
import time

# Class to manage Azure Subscriptions and VMs
class AzureRunCommand:

    def __init__(self, subFilter, vmFilter, vmType):
        self.credentials = DefaultAzureCredential()
        self.subFilter = subFilter
        self.vmFilter = vmFilter
        self.vmType = vmType
        self.subscriptions = self.get_all_subscriptions()
        self.get_all_vms()

    def __repr__(self) -> str:
        return_string = ""
        return_string += "Subscriptions: " + str(len(self.subscriptions)) + "\r\n"
        for sub in self.subscriptions:
            return_string += sub["name"] + " (VM Count: " + str(len(list(sub["vm"]))) + ")\r\n"
        return return_string

    def get_all_vms(self):
        print("Getting VMs for all subscriptions")
        credentials = DefaultAzureCredential()
        totalVms = 0
        for sub in self.subscriptions:
            computeClient = ComputeManagementClient(credentials, sub["id"])
            vmObjects = computeClient.virtual_machines.list_all()
            for vm in vmObjects:
                addVm = True

                # Check OS type and add if it matches the list of OS types
                if vm.storage_profile.os_disk.os_type not in self.vmType:
                    addVm = False
            
                # Check if tag filter requirments are met
                if self.vmFilter is not None:
                    for filter in self.vmFilter:
                        for key, value in filter.items():
                            if key not in vm.tags:
                                addVm = False
                            elif value is not None:
                                if vm.tags[key] != value:
                                    addVm = False
                if addVm:
                    totalVms += 1
                    print(".", end="")
                    sub["vm"].append({
                        "id": vm.id,
                        "resourceGroup": vm.id.split('/')[4],
                        "location": vm.location, 
                        "name": vm.name, 
                        "tags": vm.tags})
                    
        print("\r\nVMs found: " + str(totalVms))

    def get_all_subscriptions(self):
        print("Getting all subscriptions")
        credentials = DefaultAzureCredential()
        subscription_client = SubscriptionClient(credentials)
        subObjects = subscription_client.subscriptions.list()
        subscriptions = []

        for sub in subObjects:
            addSub = True
            # Check if tag filter requirements are met
            if self.subFilter is not None:
                for filter in self.subFilter:
                    for key, value in filter.items():
                        if key not in sub.tags:
                            addSub = False
                        elif value is not None:
                            if sub.tags[key] != value:
                                addSub = False
            if addSub:
                print (".", end="")
                subscriptions.append({"id": sub.subscription_id, "name": sub.display_name, "state": sub.state, "tags": sub.tags, "vm": []})
        print("\r\nSubscriptions found: " + str(len(subscriptions)))
        return subscriptions


    def run_cb(self, response):
        print("CB Called:")
        result = response.result()
        print(result)

    def run_command(self, os_type, command, vmid = None):
        #check if Command is a list or not and make it a list
        if not isinstance(command, list):
            command = [command]

        pollers = []

        # Get credentials
        credential = DefaultAzureCredential()

        # Check if we are running against a specific VM ID or None
        if vmid is None:
            # Run against all VMs in each subscription
            for sub in self.subscriptions:
                for vm in sub["vm"]:
                    print(vm["resourceGroup"])
                    compute_client = ComputeManagementClient(credential, sub["id"])
                    parameters = {
                        'command_id': 'RunPowerShellScript',
                        'script': command,
                    }
                    print("Launching Command on " + vm["name"])
                    poller = compute_client.virtual_machines.begin_run_command(vm["resourceGroup"], vm["name"], parameters) 
                    pollers.append(poller)
        

# Create AzureSubscription object
# Parameters: subFilter, vmFilter (Tag names)
azacct = AzureRunCommand([{"Type":"Domain","Support": "Yes"}], [{"Supported":"Yes","Environment": "Prod"}], ["Windows"])
azacct.run_command("Windows", 'cscript C:\windows\system32\slmgr.vbs /dlv | select-string -pattern "License Status"')


# az vm run-command create --name "myRunCommand" --vm-name "My-vm-test-01" --resource-group "RG-DIV-PROD-DEPT-USE1" --script "Write-Host Hello World!"
# az vm run-command show --name "myRunCommand" --vm-name "My-vm-test-01" --resource-group "RG-DIV-PROD-DEPT-USE1" --expand instanceView