import logging
from pyats import aetest
from pprint import pprint
from genie.metaparser.util.exceptions import SchemaEmptyParserError
from ntc_templates.parse import parse_output
from helpers.helpers import *


parameters = {}

class BGPTests(aetest.Testcase):
    """
    Our BGP Tests are defined here
    """
    ip_bgp_neighbors = dict()
    neighbor_received_routes = dict()
    neighbor_advertised_routes = dict()
    bgp_test_params = dict()

    @aetest.setup
    def get_bgp_info(self, steps):
        """
        Get relevant info from our device to test against
        """
        
        for circuit in self.parameters['device_values']['circuits']:
            circuit_id = circuit['circuit']
            with steps.start(f"{circuit_id} - Gathering required bgp details - No fail possible", continue_=True) as substep:
                interface = circuit.get('interface')
                self.bgp_test_params[interface] = circuit.get('tests', {}).get('bgp')
                vrf = self.bgp_test_params[interface].get('vrf')
                if not vrf:
                    logging.info("VRF not defined or is null, setting to default")
                    vrf = "default"
                if not self.bgp_test_params.get(interface, {}).get('test_bgp'):
                    substep.skipped("No bgp test requested")
                for neighbor in self.bgp_test_params[interface].get('neighbors'):
                    neighbor_ip = neighbor.get('neighbor_ip')

                    #Get details for ip_bgp_neighbors
                    with substep.start(f"{circuit_id}-{interface} - Getting Neighbor Details") as subsubstep:
                        try:
                            neighbor_details = self.parent.parameters['device'].parse(f"show ip bgp neighbor {neighbor_ip}")
                        except SchemaEmptyParserError:
                            subsubstep.skipped("No output from parser, invalid command or incorrect neighbor")
                            neighbor_details = {}
                        
                        neighbor_details = neighbor_details.get('vrf', {}).get(vrf, {}).get('neighbor', {}).get(neighbor_ip, {})
                        if neighbor_details:
                            self.ip_bgp_neighbors.setdefault(interface, {})[neighbor_ip] = neighbor_details
                        else:
                            subsubstep.skipped("No neighbor details found for the given vrf and neighbor id combination")
                
                    #Get details for neighbor_advertised_routes
                    with substep.start(f"{circuit_id}-{interface} - Getting Neighbor Advertised Routes") as subsubstep:
                        try:
                            neighbor_advert = self.parent.parameters['device'].parse(f"show ip bgp neighbor {neighbor_ip} advertised-routes")
                        except SchemaEmptyParserError:
                            subsubstep.skipped("No output from parser, invalid command or incorrect neighbor")
                            neighbor_advert = {}
                        neighbor_advert = neighbor_advert.get("vrf", {}).get(vrf, {}).get('neighbor', {}).get(neighbor_ip, {})
                        self.neighbor_advertised_routes.setdefault(interface, {})[neighbor_ip] = neighbor_advert

                    #Get details for neighbor_received_routes
                    with substep.start(f"{circuit_id}-{interface} - Getting Neighbor Received Routes") as subsubstep:
                        try:
                            neighbor_received = self.parent.parameters['device'].parse(f"show ip bgp neighbor {neighbor_ip} routes")
                        except SchemaEmptyParserError:
                            subsubstep.skipped("No output from parser, invalid command or incorrect neighbor")
                            neighbor_received = {}
                        neighbor_received = neighbor_received.get("vrf", {}).get(vrf, {}).get('neighbor', {}).get(neighbor_ip, {})
                        self.neighbor_received_routes.setdefault(interface, {})[neighbor_ip] = neighbor_received


    @aetest.test
    def test_bgp_neighbor_uptime(self, steps):
        """
        Tests if the required neighbor even exists. Will not be present for 
        """
        for circuit in self.parameters['device_values']['circuits']:
            circuit_id = circuit['circuit']
            interface = circuit['interface']
            with steps.start(f"{circuit_id} - Validating neighbor uptime", continue_=True) as substep:
                #Check to see if this test is really needed or not
                if not self.bgp_test_params.get(interface, {}).get('test_bgp'):
                    substep.skipped("No bgp test requested")
                #Check to see if we even have bgp neighbor details for this peer
                if not self.ip_bgp_neighbors.get(interface, {}):
                    substep.failed("Could not find neighbor values for this circuit")
                for neighbor_ip, neighbor_values in self.ip_bgp_neighbors.get(interface, {}).items():
                    with substep.start(f"{circuit_id}-{interface}-{neighbor_ip} - Validating neighbor uptime", continue_=True) as subsubstep:
                        ms_uptime = neighbor_values.get('bgp_session_transport', {}).get('uptime')
                        if not ms_uptime:
                            subsubstep.failed("There doesn't appear to be an uptime, assuming neighbor is down")
                        days_uptime = milliseconds_to_days(ms_uptime)
                        current_neighbor = [neighbor for neighbor in self.bgp_test_params[interface]['neighbors'] if neighbor['neighbor_ip'] == neighbor_ip][0]
                        logging.info(f" expected - {current_neighbor['uptime_conform']}")
                        logging.info(f" found - {days_uptime}")
                        assert compare_values(days_uptime, current_neighbor['uptime_conform'])


    @aetest.test
    def test_bgp_neighbor_advertised(self, steps):
        """
        Tests if bgp neighbor is being advertised our intended routes
        """
        for circuit in self.parameters['device_values']['circuits']:
            circuit_id = circuit['circuit']
            interface = circuit['interface']
            with steps.start(f"{circuit_id} - Validating we are advertising specified routes", continue_=True) as substep:
                if not self.bgp_test_params.get(interface, {}).get('test_bgp'):
                    substep.skipped("No bgp test requested")
                if not self.neighbor_advertised_routes.get(interface, {}):
                    substep.failed("Could not find neighbor values for this circuit")
                for neighbor_ip, neighbor_values in self.neighbor_advertised_routes.get(interface, {}).items():
                    with substep.start(f"{circuit_id}-{interface}-{neighbor_ip} - Validating neighbor is advertised routes", continue_=True) as subsubstep:
                        current_neighbor = [neighbor for neighbor in self.bgp_test_params[interface]['neighbors'] if neighbor['neighbor_ip'] == neighbor_ip][0]
                        for af in current_neighbor.get('address_families', {}):
                            af_name = af.get('address_family')
                            if af_name == "ipv4 unicast" or not af_name:
                                af_name = ""
                            if af_name != "" or af_name != "vpnv4 unicast":
                                logging.info("No known af found, reverting to default")
                                af_name = ""
                            if not af.get('advertised_routes'):
                                subsubstep.skip("No advertised routes specified, skipping this test")
                            for tested_route in af.get('advertised_routes'):
                                advertised_routes = neighbor_values.get('address_family', {}).get(af_name, {}).get("advertised").keys()
                                logging.info(f"Expecting to find {tested_route} in {advertised_routes}")
                                assert tested_route in advertised_routes

    @aetest.test
    def test_bgp_neighbor_received(self, steps):
        """
        Tests if we are receiving the intended routes from the peer
        """
        for circuit in self.parameters['device_values']['circuits']:
            circuit_id = circuit['circuit']
            interface = circuit['interface']
            with steps.start(f"{circuit_id} - Validating we are receiving specified routes", continue_=True) as substep:
                if not self.bgp_test_params.get(interface, {}).get('test_bgp'):
                    substep.skipped("No bgp test requested")
                if not self.neighbor_received_routes.get(interface, {}):
                    substep.failed("Could not find neighbor values for this circuit")
                for neighbor_ip, neighbor_values in self.neighbor_received_routes.get(interface, {}).items():
                    with substep.start(f"{circuit_id}-{interface}-{neighbor_ip} - Validating neighbor is received routes", continue_=True) as subsubstep:
                        current_neighbor = [neighbor for neighbor in self.bgp_test_params[interface]['neighbors'] if neighbor['neighbor_ip'] == neighbor_ip][0]
                        pprint(current_neighbor)
                        for af in current_neighbor.get('address_families', {}):
                            af_name = af.get('address_family')
                            if af_name == "ipv4 unicast" or not af_name:
                                af_name = ""
                            if af_name != "" or af_name != "vpnv4 unicast":
                                logging.info("No known af found, reverting to default")
                                af_name = ""
                            if not af.get('advertised_routes'):
                                subsubstep.skip("No advertised routes specified, skipping this test")
                            for tested_route in af.get('received_routes'):
                                logging.critical("Take this test with a grain of salt, Cannot validate prefix length of the route due to Genie parser")
                                tested_route = tested_route.split('/')[0]
                                received_routes = neighbor_values.get('address_family', {}).get(af_name, {}).get("routes").keys()
                                
                                logging.info(f"Expecting to find {tested_route} in {received_routes}")
                                assert tested_route in received_routes
                        