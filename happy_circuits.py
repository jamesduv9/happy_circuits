import logging
import yaml
import sys
import argparse

from typing import Dict, List
from pyats import topology, easypy
from getpass import getpass


parser = argparse.ArgumentParser(description = "happy circuits CLI tool")
parser.add_argument("--username", help="Required if auth_type == token. Username to use for all devices")
parser.add_argument("--auth_type", help="Specify 'token' to login to each device individually and reprompt for passcode", default="testbed")
parser.add_argument("--intent_file", help="path to intent yaml file describing test parameters", required=True)

def load_yaml(file_: str) -> Dict:
    """
    Returns json format of provided yaml file
    """
    with open(file_, "r") as f:
        yaml_data = yaml.safe_load(f)
        return yaml_data

def get_token_passcode(device_name: str) -> str:
    """
    Specifically for tokens that must use a unique pin per device
    Expects the user to wait the timeout and input the next usable 2FA credentials
    """
    logging.critical(f"\nPlease enter the next unique token passcode to connect to device {device_name}\n")
    return getpass("Enter your passcode > ")

def handle_device_connection(device: object, username: str, auth_type: str) -> None:
    """
    Connects to each device, prompting for credentials when needed
    """
    if auth_type.lower() == "token":
        logging.info(f"Token authentication specified in intent_file, requesting user credentials")
        device.credentials.default.username = username
        device.credentials.default.password = get_token_passcode(device.name)
    else:
        logging.info(f"auth_type other than token, assuming credentials are in the testbed file")
    
    logging.info(f"Now connecting to device {device.name}")
    device.connect(log_stdout=False)

def get_device_values(device_name: str, intent_file: Dict) -> Dict:
    """
    Gets device specific details from the input script config file
    """
    device_values = intent_file.get("config").get("devices").get(device_name)
    if not device_values:
        logging.critical(f"No device values found for {device_name}")
        logging.critical("please validate the testbed and script config files have the same hostname set")
        logging.critical("exiting")
        sys.exit()
    else:
        return device_values


def main(runtime) -> None:
    """
    pyATS required main function
    Starts the test execution
    """
    args, sys.argv[1:] = parser.parse_known_args(sys.argv[1:])
    args = vars(args)
    username = None
    if args['auth_type'].lower() == "token":
        if not args.get('username'):
            logging.critical("auth_type == token, but no username is provided, exiting")
            sys.exit()
        else:
            username = args['username']
    intent_file = load_yaml(file_=args['intent_file'])
    logging.info("User input required")

    for device in runtime.testbed.devices.values():
        device_values = get_device_values(device_name=device.name, intent_file=intent_file)
        handle_device_connection(device=device, username=username, auth_type=args['auth_type'])
        easypy.run(testscript="./testscripts/interface_tests.py", taskid= f"Interface Tests on device - {device.name}", device=device, device_values=device_values, runtime = runtime)
        easypy.run(testscript="./testscripts/icmp_tests.py", taskid= f"ICMP Tests on device - {device.name}", device=device, device_values=device_values, runtime = runtime)
        easypy.run(testscript="./testscripts/bgp_tests.py", taskid= f"BGP Tests on device - {device.name}", device=device, device_values=device_values, runtime = runtime)

