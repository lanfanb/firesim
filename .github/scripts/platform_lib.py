import abc

import sys
import boto3
import os
from enum import Enum
from fabric.api import *
from ci_variables import local_fsim_dir, ci_azure_sub_id
import datetime
import pytz

from azure.mgmt.resource import ResourceManagementClient
from azure.identity import DefaultAzureCredential
from azure.mgmt.compute import ComputeManagementClient
import azure.mgmt.resourcegraph as arg

from typing import Any, Callable, Dict, List

# Reuse manager utilities
# Note: ci_firesim_dir must not be used here because the persistent clone my not be initialized yet.
sys.path.append(local_fsim_dir + "/deploy")
from awstools.awstools import get_instances_with_filter

# This tag is common to all instances launched as part of a given workflow
unique_tag_key = 'ci_workflow_id'
# Managers additionally have this empty tag defined
manager_filter = {'Name': 'tag:ci_manager', 'Values' : ['']}

# The following is an enum used to represent the different platforms
class Platform(Enum):
    ALL = 'all'
    AWS = 'aws'
    AZURE = 'azure'
    def __str__(self) -> str:
        return self.value

def get_platform_enum(platform_string: str) -> Platform:
    if platform_string == 'aws':
        return Platform.AWS
    elif platform_string == 'azure':
        return Platform.AZURE
    elif platform_string == 'all':
        return Platform.ALL
    else:
        raise Exception(f"Invalid platform string: '{platform_string}'")

class PlatformLib(metaclass=abc.ABCMeta):
    """
    This is a class hierarchy to support multiple platforms in FireSim CI
    Note that there are 2 terms used to refer to machines running CI: Managers and Instances

    Managers - refer to a manager instance, this only really matters for AWS, but it's the main machine
    running CI

    Instances - a more general term, but can refer to runfarm / buildfarm instances run by CI as well
    """

    @abc.abstractmethod
    def get_filter(self, tag_value: str) -> Dict:
        """ Returns a filter that returns all instances associated with workflow """        
        raise NotImplementedError
    
    @abc.abstractmethod
    def get_manager_tag_dict(self, sha: str, tag_value: str) -> Dict[str, str]:
        """ Returns the tag dictionary for launching the manager """
        raise NotImplementedError

    @abc.abstractmethod
    def check_manager_exists(self, tag_value: str) -> bool:
        """ Returns whether workflow manager already exists """
        raise NotImplementedError

    @abc.abstractmethod
    def find_all_workflow_instances(self, tag_value: str) -> List:
        """ Returns all instances in this workflow (including manager) """
        raise NotImplementedError

    @abc.abstractmethod
    def find_all_ci_instances(self) -> List:
        """ Returns all instances across CI workflows """
        raise NotImplementedError

    @abc.abstractmethod
    def get_manager_ip(self, tag_value: str) -> str:
        """ Returns ip of the manager specified by the tag """
        raise NotImplementedError

    @abc.abstractmethod
    def get_manager_workflow_id(self, tag_value: str) -> str:
        """ Returns the workflow id of the manager specified by the tag """
        raise NotImplementedError

    @abc.abstractmethod
    def change_workflow_instance_states(self, gh_token: str, tag_value: str, state_change: str, dryrun: bool=False) -> None:
        """ Changes the state of the instances specified by 'tag_value' to 'state_change' """
        raise NotImplementedError
    
    @abc.abstractmethod
    def get_platform_enum(self) -> Platform:
        """ Returns the enum associated with the platform implemented by the PlatformLib """
        raise NotImplementedError

    @abc.abstractmethod
    def get_manager_metadata_string(self, tag_value: str) -> str:
        """ Get metadata string for the manager of the workflow """
        raise NotImplementedError

    def stop_instances(self, gh_token: str, tag_value: str) -> None:
        """ Stops the instances specified by 'tag_value' """
        self.change_workflow_instance_states(gh_token, tag_value, 'stop')
    
    def terminate_instances(self, gh_token: str, tag_value: str) -> None:
        """ Stops the instances specified by 'tag_value' """
        self.change_workflow_instance_states(gh_token, tag_value, 'terminate')
    
    def get_manager_hostname(self, tag_value: str) -> str:
        """ Returns the hostname of the ci manager specified """
        return f"centos@{self.get_manager_ip(tag_value)}"

class AWSPlatformLib(PlatformLib):

    def __init__(self, deregister_runners: Callable[[str, str], None]):
        if os.path.exists(os.path.expanduser('~/.aws/config')): # only set client if this exists
            self.client = boto3.client('ec2')
        self.manager_filter = {'Name': 'tag:ci_manager', 'Values' : ['']}
        self.deregister_runners = deregister_runners
    
    def get_filter(self, tag_value: str) -> Dict[str, Any]:
        return {'Name': 'tag:' + unique_tag_key, 'Values' : [tag_value]}

    def get_manager_tag_dict(self, sha, tag_value):
        """ Populates a set of tags for the manager of our CI run """
        # Note: At one point these tags had hyphens instead of underscores.
        # Since hyphens are interpreted as a subtraction operation in 
        # Kusto Query Langauge (KQL) used by Azure Resource Graphs,
        # these have been chnaged to underscores as a result.
        return {
            'ci_commit_sha1': sha,
            'ci_manager': '',
            unique_tag_key: tag_value}

    def check_manager_exists(self, tag_value: str) -> bool:
        inst = self.find_manager(tag_value)
        return not (inst is None)
    
    def find_manager(self, tag_value: str):
        instances = get_instances_with_filter([self.get_filter(tag_value), manager_filter])
        if instances:
            assert len(instances) == 1 # this must be called before any new instances are launched by workflow
            return instances[0]
        else:
            return None

    def find_all_workflow_instances(self, tag_value: str) -> List:
        """ Grabs a list of all instance dicts sharing the CI workflow run's unique tag """
        return get_instances_with_filter([self.get_filter(tag_value)])

    def find_all_ci_instances(self) -> List:
        """ Grabs a list of all instances across all CI using the CI unique tag key"""
        all_ci_instances_filter = {'Name': 'tag:' + unique_tag_key, 'Values' : ['*']}
        all_ci_instances = get_instances_with_filter([all_ci_instances_filter], allowed_states=['*'])
        return all_ci_instances

    def get_manager_ip(self, tag_value: str) -> str:
        """
        Looks up the AWS manager IP using the CI workflow run's unique tag
        """
        aws_manager = self.find_manager(tag_value)
        if aws_manager is None:
            raise Exception("No AWS manager instance running with tag matching the assigned workflow id\n")
    
        return aws_manager['PublicIpAddress']
    
    def get_manager_workflow_id(self, tag_value: str) -> str:
        return f"aws-{tag_value}"

    def change_workflow_instance_states(self, gh_token: str, tag_value: str, state_change: str, dryrun: bool = False) -> None:
        """ Change the state of all instances sharing the same CI workflow run's tag. """
        
        all_instances = self.find_all_workflow_instances(tag_value)
        manager_instance = self.find_manager(tag_value)

        # Ensure we do the manager last, as this function may be invoked there
        sorted_instances = [inst for inst in all_instances if inst != manager_instance]
        if manager_instance is not None:
            sorted_instances.append(manager_instance)

        instance_ids = [inst['InstanceId'] for inst in sorted_instances]

        if state_change == 'stop':
            print("Stopping instances: {}".format(", ".join(instance_ids)))
            self.deregister_runners(gh_token, f"aws-{tag_value}")
            self.client.stop_instances(InstanceIds=instance_ids, DryRun=dryrun)
        elif state_change == 'start':
            print("Starting instances: {}".format(", ".join(instance_ids)))
            self.client.start_instances(InstanceIds=instance_ids, DryRun=dryrun)

            # If we have a manager (typical), wait for it to come up and report its IP address
            if manager_instance is not None:
                print("Waiting on manager instance.")
                manager_id = manager_instance['InstanceId']
                #wait_on_instance(manager_id) # TODO: this is not defined anywhere, even in the OG common.py
                print("Manager ready.")
                # Re-query the instance to get an updated IP address
                print(self.instance_metadata_str(self.find_manager(tag_value)))

        elif state_change == 'terminate':
            print("Terminating instances: {}".format(", ".join(instance_ids)))
            self.deregister_runners(gh_token, f"aws-{tag_value}")
            self.client.terminate_instances(InstanceIds=instance_ids, DryRun=dryrun)
        else:
            raise ValueError("Unrecognized transition type: {}".format(state_change))

    def get_platform_enum(self) -> None:
        return Platform.AWS

    def get_manager_metadata_string(self, tag_value: str) -> str:
        return self.instance_metadata_str(self.find_manager(tag_value))

    def instance_metadata_str(self, instance) -> str:
        """ Pretty prints instance info, including ID, state, and public IP """
        static_md = """    Instance ID: {}
        Instance State: {}""".format(instance['InstanceId'], instance['State']['Name'])

        dynamic_md = ""

        if instance.get('PublicIpAddress') is not None:
            dynamic_md = """
        Instance IP: {}""".format(instance['PublicIpAddress'])

        return static_md + dynamic_md


class AzurePlatformLib(PlatformLib):
    def __init__(self, deregister_runners: Callable[[str, str], None]):
        self.credential = DefaultAzureCredential()
        self.resource_client = ResourceManagementClient(self.credential, ci_azure_sub_id)
        self.arg_client = arg.ResourceGraphClient(self.credential)
        self.compute_client = ComputeManagementClient(self.credential, ci_azure_sub_id)

        self.deregister_runners = deregister_runners
        # This is a dictionary that's used to translate between simpler terms and
        # those useful to search for Azure resources
        self.azure_translation_dict = {
            'vm' : 'virtualMachines',
            'ip' : 'publicIPAddresses',
            'nsg' : 'networkSecurityGroups',
            'nic' : 'networkInterfaces',
            'disk' : 'disks',
            'vnet' : 'virtualNetworks'
        }

    def get_filter(self, tag_value: str) -> Dict[str, str]:
        """ this is the azure equivalent of 'get_ci_filter' since azure queries are different"""
        return {unique_tag_key: tag_value}
    
    def get_manager_tag_dict(self, sha, tag_value):
        """ Populates a set of tags for the manager of our CI run """
        # Note: At one point these tags had hyphens instead of underscores.
        # Since hyphens are interpreted as a subtraction operation in 
        # Kusto Query Langauge (KQL) used by Azure Resource Graphs,
        # these have been chnaged to underscores as a result.
        return {
            'ci_commit_sha1': sha,
            'ci_manager': '',
            unique_tag_key: tag_value,
            'FireSimCI': 'True',
            'LaunchTime': datetime.datetime.utcnow().replace(tzinfo=pytz.UTC)}

    def check_manager_exists(self, tag_value: str):
        # Note: Right now, Azure workflow does not spawn new instances
        return len(self.find_all_workflow_instances(tag_value)) == 1
    
    def find_all_workflow_instances(self, tag_value : str) -> List:
        tag_filter = self.get_filter(tag_value)
        all_ci_resources = self.get_azure_resources_with_tags(tag_filter)
        return self.get_type_from_resource_list(all_ci_resources, 'vm')

    def find_all_ci_instances(self) -> List:
        tag_filter = {'FireSimCI' : "True"}
        all_ci_resources = self.get_azure_resources_with_tags(tag_filter)
        return self.get_type_from_resource_list(all_ci_resources, 'vm')

    def get_manager_ip(self, tag_value : str) -> str:
        """
        Looks up the Azure manager IP using the CI workflow run's unique tag
        """
        azure_manager_resources = self.get_azure_resources_with_tags(self.get_filter(tag_value))
        azure_ip = self.get_type_from_resource_list(azure_manager_resources, 'ip')

        if not azure_ip: #if an empty list is returned
            raise Exception("No Azure IP found associated with tag matching the assigned workflow id\n")
        
        azure_ip = azure_ip[0] #assume only 1 ip in list
        return azure_ip['properties']['ipAddress']

    def get_manager_workflow_id(self, tag_value: str) -> str:
        return f"azure-{tag_value}"

    def change_workflow_instance_states(self, gh_token: str, tag_value: str, state_change: str, dryrun: bool=False) -> None:
        """
            Now that terminate / stop look a bit more similar, we can condense them into a single function
            Dryrun is just a dummy variable to match abstract class signature
        """
        instances = self.find_all_workflow_instances(tag_value)

        if not instances: #if an empty list is returned
            raise Exception(f"Couldn't find an active vm associated with tags {self.get_filter(tag_value)}")
        
        if state_change == 'stop':
            self.deregister_runners(gh_token, self.get_manager_workflow_id(tag_value))
            for inst in instances:
                print(f"Flagged VM {inst['name']} for shutdown")
                poller = self.compute_client.virtual_machines.begin_power_off(inst['resourceGroup'], inst['name']) 
                print(f"Successfully stopped VM {inst['name']}")
        elif state_change == 'terminate':
            self.deregister_runners(gh_token, self.get_manager_workflow_id(tag_value))
            self.terminate_azure_vms(instances)
        elif state_change == 'start':
            raise  NotImplementedError
        else:
            raise ValueError("Unrecognized transition type: {}".format(state_change))
    
    def get_platform_enum(self) -> Platform:
        return Platform.AZURE
    
    def get_manager_metadata_string(self, tag_value: str) -> str:
        inst_list = self.find_all_workflow_instances(tag_value) 
        assert len(inst_list) == 1
        manager = inst_list[0]
        return str(manager)

    def get_azure_type_key(self, type_name: str) -> str:
        return self.azure_translation_dict[type_name]

    def get_type_from_resource_list(self, resource_list: List, type_name: str):
        """ 
            Gets specific type of resource from a resource list obtained from one of the query
        """
        type_key = self.get_azure_type_key(type_name)
        return_list = []
        for resource in resource_list:
            if type_key.casefold() in resource['type'].casefold():
                return_list.append(resource)
        
        return return_list

    def get_azure_resources_with_tags(self, tag_dict: Dict[str, str]) -> List:
        arg_query_options = arg.models.QueryRequestOptions(result_format="objectArray") 

        query = "Resources | where "
        for key in tag_dict.keys():
            query += f"tags.{key}=~'{tag_dict[key]}' and "
        query = query[:-4]

        arg_query = arg.models.QueryRequest(subscriptions=[ci_azure_sub_id], query=query, options=arg_query_options)

        return self.arg_client.resources(arg_query).data
    
    def terminate_azure_vms(self, resource_list: List) -> None:
        vms_to_delete = []
        for resource in resource_list:
            if 'virtualMachines'.casefold() in resource['type'].casefold():
                vms_to_delete.append(resource)

        vm_pollers = []
        for vm in vms_to_delete:
            poller = self.resource_client.resources.begin_delete_by_id(vm['id'], self.resource_client.DEFAULT_API_VERSION)
            print(f"VM {vm['name']} flagged for deletion")
            vm_pollers.append((vm, poller))
        
        for vm, poller in vm_pollers:
            deletion_result = poller.result()
            if deletion_result:
                print(f"Failed to delete VM {vm['name']}, expected 'None' and got result {deletion_result}")
            else:
                print(f"Succeeded in deleting VM {vm['name']}")
