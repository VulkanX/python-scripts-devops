# Required Libraries azure-mgmt-compute azure-identity azure-mgmt-subscription

# Generate a list of Azure VM's and run commands against them to get licensing information

from azure.identity import DefaultAzureCredential
from azure.mgmt.compute import ComputeManagementClient
import csv
import json
import subprocess

# Class to manage Azure Subscriptions and VMs
class Azure:

    def __init__(self, subFilter, vmFilter, vmType, vmOS=None, vmOSVersion=None):
        self.credentials = DefaultAzureCredential()
        self.subFilter = subFilter
        self.vmFilter = vmFilter
        self.vmType = vmType
        self.vmOS = vmOS
        self.vmOSVersion = vmOSVersion
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
                # Assume the VM is good to add by default then rule out reasons to not add it
                addVm = True

                # Get running status of VM
                # .instance_view.statuses[1].display_status
                vmState = computeClient.virtual_machines.get(vm.id.split('/')[4], vm.name, expand='instanceView').instance_view.statuses[1].display_status

                # Get OS details
                # Not all storage profiles have image references
                if vm.storage_profile.image_reference is None:
                    vmos = None
                    vmosversion = None
                else:
                    vmos = vm.storage_profile.image_reference.offer
                    vmosversion = vm.storage_profile.image_reference.sku

                vmtype = vm.storage_profile.os_disk.os_type

                # Check OS type and add if it matches the list of OS types
                if vmtype not in self.vmType:
                    addVm = False

                # Check if tag filter requirments are met
                if "Tags" in self.vmFilter:
                    for key, value in self.vmFilter["Tags"].items():
                        if vm.tags is None or key not in vm.tags:
                            addVm = False
                        elif value is not None:
                            if vm.tags[key] != value:
                                addVm = False

                # Check Name Filter exists and is not empty array
                if "Name" in self.vmFilter and len(self.vmFilter["Name"]) > 0:
                    if vm.name not in self.vmFilter["Name"]:
                        addVm = False

                # Check OS Type
                if vmos is not None:
                    if vmos not in self.vmOS:
                        addVm = False

                # Check OS Version
                if self.vmOSVersion is not None:
                    if vmosversion not in self.vmOSVersion:
                        addVm = False

                if addVm:
                    totalVms += 1
                    print(".", end="", flush=True)
                    sub["vm"].append({
                        "id": vm.id,
                        "resourceGroup": vm.id.split('/')[4],
                        "location": vm.location, 
                        "name": vm.name,
                        "state": vm.provisioning_state,
                        "os": vmtype,
                        "ostype": vmos,
                        "osversion": vmosversion,
                        "tags": vm.tags,
                        "status": vmState,
                        "licensed": None,
                        "domain": None,
                        "kmsserver": None,
                        "kmsip": None,
                        "kmsreachable": None,
                        "output": None,
                        "error": None})
                else:
                    print("x", end="", flush=True)
        print("\r\n Total VMs Found: " + str(totalVms))

    def get_all_subscriptions(self):
        print("Getting all subscriptions")

        # Python SDK has issues retreiving tags consistently, using az cli Graph query instead to get all subscriptions
        azclioutput = json.loads(subprocess.check_output("az graph query -q \"resourcecontainers | where type == 'microsoft.resources/subscriptions' | project id, name, subscriptionId, properties.state, tags\"", shell=True).decode('utf-8'))
        subObjects = list(azclioutput["data"])
        subscriptions = []

        for sub in subObjects:
            addSub = True
            # Check if tag filter requirements are met
            if "Tags" in self.subFilter:
                for key, value in self.subFilter["Tags"].items():
                    if sub["tags"] is None or key not in sub["tags"]:
                        addSub = False
                    elif value is not None:
                        if sub["tags"][key] != value:
                            addSub = False
            # Check Name Filter
            if "Name" in self.subFilter:
                if sub["name"] not in self.subFilter["Name"]:
                    addSub = False

            if addSub:
                print(".", end="", flush=True)
                print("Adding Subscription: " + sub["name"])
                if sub["tags"] is None:
                    sub["tags"] = {}
                subscriptions.append({"id": sub["subscriptionId"], "name": sub["name"], "state": sub["properties_state"], "tags": list(sub["tags"]), "vm": []})
        print("\r\nSubscriptions found: " + str(len(subscriptions)))
        return subscriptions

    def run_cb(self, response):
        print("CB Called:")
        result = response.result()
        print(result)

    def run_command(self, os_type, command, vmid=None):
        #check if Command is a list or not and make it a list
        if not isinstance(command, list):
            command = [command]

        # Get credentials
        credential = DefaultAzureCredential()

        # Check if we are running against a specific VM ID or None
        if vmid is None:
            # Run against all VMs in each subscription
            for sub in self.subscriptions:
                print("\r\nRunning Commands on VMs in Subscription: " + sub["name"])
                for vm in sub["vm"]:
                    if vm["status"] == "VM running":
                        try:
                            compute_client = ComputeManagementClient(credential, sub["id"])
                            parameters = {
                                'command_id': 'RunPowerShellScript',
                                'script': command,
                            }
                            poller = compute_client.virtual_machines.begin_run_command(vm["resourceGroup"], vm["name"], parameters) 
                            print(".", end="", flush=True)
                            result = poller.result()
                            vm["output"] = result.value[0].message
                            for value in result.value[0].message.split("\n"):
                                if len(value) > 0:
                                    temp = value.split(":")
                                    if temp[0].strip() == "License Status":
                                        vm["licensed"] = temp[1].strip()
                                    elif temp[0].strip() == "Registered KMS machine name":
                                        vm["kmsserver"] = temp[1].strip()
                                    elif temp[0].strip() == "KMS machine IP address":
                                        vm["kmsip"] = temp[1].strip()
                                    elif temp[0].strip() == "KMS_Reachable":
                                        vm["kmsreachable"] = temp[1].strip()
                                    elif temp[0].strip() == "Domain":
                                        vm["domain"] = temp[1].strip()
                        except Exception as e:
                            print("X", end="", flush=True)
                            print(e)
                    else:
                        vm["licensed"] = "VM not running"
                        print("O", end="", flush=True)

    def export_csv(self, filename):
        # Export subscript,vm,output data to csv file
        # Write the header for the csv file
        csvfile = open(filename, 'w', newline='')
        fieldnames = ['Subscription', 'ResourceGroup', 'Location', 'VM', 'OS', 'OS Type', 'OS Version', 'CloudReachSupport', 'Status', 'Domain', 'Licensed', 'KMSServer', 'KMSIP', 'KMS Reachable']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        # Loop through all subs and VMs and export to CSV
        for sub in self.subscriptions:
            for vm in sub["vm"]:
                writer.writerow({
                    'Subscription': sub["name"],
                    'ResourceGroup': vm["resourceGroup"],
                    'Location': vm["location"],
                    'VM': vm["name"],
                    'OS': vm["os"],
                    'OS Type': vm["ostype"],
                    'OS Version': vm["osversion"],
                    'CloudReachSupport': vm["tags"]['CloudreachSupport'] if 'CloudreachSupport' in vm["tags"] else '',
                    'Status': vm["status"],
                    'Domain': vm["domain"],
                    'Licensed': vm["licensed"],
                    'KMSServer': vm["kmsserver"],
                    'KMSIP': vm["kmsip"],
                    'KMS Reachable': vm["kmsreachable"]})
        csvfile.close()
        print("\r\nExported to CSV file: " + filename)
