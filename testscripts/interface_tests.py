import logging
from pyats import aetest
from helpers.helpers import *

parameters = {}

class InterfaceTests(aetest.Testcase):
    """
    Test for common interface issues 
    down line protocol, output errors, crc errors, half duplex
    """
    interface_test = dict()
    interface_details = dict()

    @aetest.setup
    def gather_interface_details(self, steps):
        """
        Get all the values we care about out of show interface for future tests along with the test params
        """

        #Get the data show interface
        logging.info(self.parent.parameters['device_values'])
        for circuit in self.parameters['device_values']['circuits']:
            with steps.start(f"{circuit['circuit']} - Gathering required interface details"):
                #Get the interface test parameters from the input yaml
                self.interface_test[circuit['interface']] = circuit.get('tests').get('interface')
                #Specific logic to handle subinterfaces, we want to get physical and logical interface counters
                if circuit.get('is_subinterface'):
                    #Parent interface will be the interface that the parent is built on
                    parent_interface = split_subintf(circuit['interface'])
                    logging.info(f"This is a subinterface on {split_subintf(circuit['interface'])}")
                    interface_log_counters = self.parameters['device'].parse(f"show interface {circuit['interface']}")
                    interface_phy_counters = self.parameters['device'].parse(f"show interface {parent_interface}")
                    
                else:
                    interface_phy_counters = self.parameters['device'].parse(f"show interface {circuit['interface']}")
                    interface_log_counters = interface_phy_counters
                    parent_interface = circuit['interface']

                #Get the physical counters from parent interface
                self.interface_details[circuit['interface']] = dict()
                self.interface_details[circuit['interface']]['circuit'] = circuit['circuit']
                self.interface_details[circuit['interface']]['duplex_mode'] = interface_phy_counters.get(parent_interface, {}).get('duplex_mode')
                self.interface_details[circuit['interface']]['enabled'] = interface_phy_counters.get(parent_interface, {}).get('enabled')
                self.interface_details[circuit['interface']]['line_protocol'] = interface_phy_counters.get(parent_interface, {}).get('line_protocol')
                self.interface_details[circuit['interface']]['out_errors'] = interface_phy_counters.get(parent_interface, {}).get('counters', {}).get('out_errors')
                self.interface_details[circuit['interface']]['out_collision'] = interface_phy_counters.get(parent_interface, {}).get('counters', {}).get('out_collision')
                self.interface_details[circuit['interface']]['in_errors'] = interface_phy_counters.get(parent_interface, {}).get('counters', {}).get('in_errors')
                self.interface_details[circuit['interface']]['in_crc_errors'] = interface_phy_counters.get(parent_interface, {}).get('counters', {}).get('in_crc_errors')
                #Now we get the logical counters on the parent interface, or subinterface if specified
                self.interface_details[circuit['interface']]['txload'] = interface_log_counters.get(circuit['interface'], {}).get('txload')
                self.interface_details[circuit['interface']]['rxload'] = interface_log_counters.get(circuit['interface'], {}).get('rxload')
                self.interface_details[circuit['interface']]['ipv4'] = interface_log_counters.get(circuit['interface'], {}).get('ipv4', {})

    @aetest.test
    def test_interface_status(self, steps):
        """
        Test the line protocol of the interface
        Failures point to physical issues or interface shutdown
        """
        for interface, interface_values in self.interface_details.items():
            with steps.start(f"{interface_values['circuit']}-{interface} - STATUS CHECK") as substep:
                if not self.interface_test[interface].get('test_interface'):
                    substep.skipped(f"interface tests disabled for interface - {interface}")
                #Ensure we have the right values in the dictionary
                if 'line_protocol' in interface_values and 'enabled' in interface_values:
                    
                    #Now create a step to test Line protocol of the interface, continue if AssertionError
                    with substep.start(f"{interface_values['circuit']}-{interface} - Line protocol test EXPECTED =  {self.interface_test[interface].get('line_protocol')}", continue_=True) as subsubstep:
                        if not self.interface_test[interface].get('line_protocol'):
                            subsubstep.skipped("No line protocol test required")
                        logging.info(f" expected - {self.interface_test[interface].get('line_protocol').lower()}")
                        logging.info(f" found - {interface_values.get('line_protocol').lower()}")
                        assert interface_values.get('line_protocol').lower() == self.interface_test[interface].get('line_protocol').lower()
                    #Now create a step to test enablement of the interface, continue if AssertionError
                    with substep.start(f"{interface_values['circuit']}-{interface} - Interface enabled check EXPECTED =  {self.interface_test[interface].get('enabled')}", continue_=True):   
                        if not self.interface_test[interface].get('enabled'):
                            subsubstep.skipped("No enabled test required")
                        logging.info(f" expected - {self.interface_test[interface].get('enabled')}")
                        logging.info(f" found - {interface_values.get('enabled')}")
                        assert interface_values.get('enabled') == self.interface_test[interface].get('enabled')

                else:
                    self.failed("Test did not find the required line protocol and enabled keys")

    @aetest.test
    def test_interface_input_errors(self, steps):
        """
        Test for crc/in errors
        Failures point to physical issues
        """
        for interface, interface_values in self.interface_details.items():
            with steps.start(f"{interface_values['circuit']}-{interface} - INPUT ERROR CHECK") as substep:
                if not self.interface_test[interface].get('test_interface'):
                    substep.skipped(f"interface tests disabled for interface - {interface}")
                with substep.start(f"{interface_values['circuit']}-{interface} - Test for interface input errors EXPECTED {self.interface_test[interface].get('in_errors_conform')}", continue_=True) as subsubstep:
                    if not self.interface_test[interface].get('in_errors_conform'):
                        subsubstep.skipped("No in errors test required")
                    #Ensure we have the right values in the dictionary
                    if 'in_errors' in interface_values:
                        logging.info(f" expected - {self.interface_test[interface].get('in_errors_conform')}")
                        logging.info(f" found - {interface_values.get('in_errors')}")
                        assert compare_values(interface_values.get('in_errors'), self.interface_test[interface].get('in_errors_conform'))
                with substep.start(f"{interface_values['circuit']}-{interface} - Test for interface input crc errors EXPECTED =  {self.interface_test[interface].get('in_crc_errors_conform')}", continue_=True) as subsubstep:
                    if not self.interface_test[interface].get('in_crc_errors_conform'):
                        subsubstep.skipped("No in crc errors test required")
                    #Ensure we have the right values in the dictionary
                    if 'in_crc_errors' in interface_values:
                        logging.info(f" expected - {self.interface_test[interface].get('in_crc_errors_conform')}")
                        logging.info(f" found - {interface_values.get('in_crc_errors')}")
                        assert compare_values(interface_values.get('in_crc_errors'), self.interface_test[interface].get('in_crc_errors_conform'))
                
    @aetest.test
    def test_interface_output_errors(self, steps):
        """
        Test for output errors + collisions
        Failures point to physical issues
        """
        for interface, interface_values in self.interface_details.items():
            with steps.start(f"{interface_values['circuit']}-{interface} - OUTBOUND ERROR CHECK") as substep:
                if not self.interface_test[interface].get('test_interface'):
                    substep.skipped(f"interface tests disabled for interface - {interface}")
                with substep.start(f"{interface_values['circuit']}-{interface} - Test for interface output errors EXPECTED = {self.interface_test[interface].get('out_errors_conform')}", continue_=True) as subsubstep:
                    if not self.interface_test[interface].get('out_errors_conform'):
                        subsubstep.skipped("no test for out_errors conform requested")
                    #Ensure we have the right values in the dictionary
                    if 'out_errors' in interface_values:
                        logging.info(f" expected - {self.interface_test[interface].get('out_errors_conform')}")
                        logging.info(f" found - {interface_values.get('out_errors')}")
                        assert compare_values(interface_values.get('out_errors'), self.interface_test[interface].get('out_errors_conform'))
                with substep.start(f"{interface_values['circuit']}-{interface} - Test for interface output collisions EXPECTED = {self.interface_test[interface].get('out_collision_conform')}", continue_=True) as subsubstep:
                    if not self.interface_test[interface].get('out_collision_conform'):
                        subsubstep.skipped("no test for out_collision conform requested")
                    #Ensure we have the right values in the dictionary
                    if 'out_collision' in interface_values:
                        logging.info(f" expected - {self.interface_test[interface].get('out_collision_conform')}")
                        logging.info(f" found - {interface_values.get('out_collision')}")
                        assert compare_values(interface_values.get('out_collision'), self.interface_test[interface].get('out_collision_conform'))

    @aetest.test
    def test_interface_load(self, steps):
        """
        Test for interface load, inbound and outbound 
        Failures point to loops, DOS, greedy host
        """
        for interface, interface_values in self.interface_details.items():
            with steps.start(f"{interface_values['circuit']}-{interface} - LOAD TEST") as substep:
                if not self.interface_test[interface].get('test_interface'):
                    substep.skipped(f"interface tests disabled for interface - {interface}")
                with substep.start(f"{interface_values['circuit']}-{interface} - Test for interface excessive tx load EXPECTED = {self.interface_test[interface].get('txload_conform')}", continue_=True) as subsubstep:
                    if not self.interface_test[interface].get('txload_conform'):
                        subsubstep.skipped("No test required for txload")
                    #Ensure we have the right values in the dictionary
                    if 'txload' in interface_values:
                        logging.info(f" expected - {self.interface_test[interface].get('txload_conform')}")
                        logging.info(f" found - {split_load(interface_values.get('txload'))}")
                        assert compare_values(split_load(interface_values.get('txload')), self.interface_test[interface].get('txload_conform'))
                with substep.start(f"{interface_values['circuit']}-{interface} - Test for interface excessive rx load EXPECTED = {self.interface_test[interface].get('rxload_conform')}", continue_=True) as subsubstep:
                    if not self.interface_test[interface].get('rxload_conform'):
                        subsubstep.skipped("No test required for rxload")
                    #Ensure we have the right values in the dictionary
                    if 'rxload' in interface_values:
                        logging.info(f" expected - {self.interface_test[interface].get('rxload_conform')}")
                        logging.info(f" found - {split_load(interface_values.get('rxload'))}")
                        assert compare_values(split_load(interface_values.get('rxload')), self.interface_test[interface].get('rxload_conform'))

    @aetest.test
    def test_interface_duplex(self, steps):
        """
        Test for interface load, inbound and outbound 
        Failures point to bad negotiation, physical issues
        """
        for interface, interface_values in self.interface_details.items():
            with steps.start(f"{interface_values['circuit']}-{interface} - DUPLEX TEST") as substep:
                if not self.interface_test[interface].get('test_interface'):
                    substep.skipped(f"interface tests disabled for interface - {interface}")
                with substep.start(f"{interface_values['circuit']}-{interface} - Test for interface correct duplex = {self.interface_test[interface].get('duplex')}", continue_=True) as subsubstep:
                    if not self.interface_test[interface].get('duplex'):
                        subsubstep.skipped("No test required for duplex")
                    #Ensure we have the right values in the dictionary
                    if 'duplex' in interface_values:
                        logging.info(f" expected - {self.interface_test[interface].get('duplex').lower()}")
                        logging.info(f" found - {interface_values.get('duplex').lower()}")
                        assert interface_values.get('duplex').lower() == self.interface_test[interface].get('duplex').lower()


    @aetest.test
    def test_interface_ip(self, steps):
        """
        Ensure the interface is configured with our desired IP
        """
        for interface, interface_values in self.interface_details.items():
            with steps.start(f"{interface_values['circuit']}-{interface} - IP ADDRESS CHECK EXPECTED = {self.interface_test[interface].get('ipv4')}", continue_=True) as substep:
                if not self.interface_test[interface].get('ipv4'):
                    substep.skipped("No test required for ipv4")
                if not self.interface_test[interface].get('test_interface'):
                    substep.skipped(f"interface tests disabled for interface - {interface}")
                logging.info(f" expected - {self.interface_test[interface].get('ipv4')}")
                logging.info(f" found - {interface_values.get('ipv4').keys()}")
                assert self.interface_test[interface].get('ipv4') in interface_values.get('ipv4').keys()