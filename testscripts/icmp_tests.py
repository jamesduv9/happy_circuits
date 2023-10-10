import logging
from pyats import aetest
from helpers.helpers import *

parameters = {}

class ICMPTest(aetest.Testcase):
    """
    Our ICMP tests are defined here. 
    """
    icmp_test = dict()
    ping_results = dict()

    @aetest.setup
    def icmp_setup(self, steps):
        """
        Attempts to conduct the specified ping and stores the results in the ping_results dict
        """
        for circuit in self.parameters['device_values']['circuits']:
            with steps.start(f"{circuit['circuit']} - Gathering required icmp details"):
                #Get the icmp test parameters from the input yaml
                self.icmp_test[circuit['interface']] = circuit.get('tests').get('icmp')

            with steps.start(f"{circuit['circuit']} - INITIATE PING {self.icmp_test.get(circuit['interface'], {}).get('pingable_address')} (no fail possible)") as substep:
                if not self.icmp_test[circuit['interface']].get('test_icmp'):
                    substep.skipped("No ICMP Test Requested")
                pingable_address = self.icmp_test.get(circuit['interface'], {}).get('pingable_address')
                source_vrf = self.icmp_test.get(circuit['interface'], {}).get('vrf')
                count = self.icmp_test.get(circuit['interface'], {}).get('ping_count')
                source_address = circuit['interface']
                
                #Any VRF input provided when the global vrf should be used results in "Invalid command has been executed"
                if source_vrf:
                    #Wake on LAN behavior, ensure arp entry exists
                    self.parameters['device'].api.ping(address=pingable_address, vrf=source_vrf, source=source_address, count=1, validate=True)
                    #Actual test
                    self.ping_results = self.parameters['device'].api.ping(address=pingable_address, source=source_address, vrf=source_vrf, count=count, validate=True)
                else:
                    #Wake on LAN behavior, ensure arp entry exists
                    self.parameters['device'].api.ping(address=pingable_address, source=source_address, count=1, validate=True)
                    #Actual test
                    self.ping_results[circuit['interface']] = self.parameters['device'].api.ping(address=pingable_address, source=source_address, count=count, validate=True)
                #logging.warning(self.ping_results)

        
    @aetest.test
    def icmp_response_exists(self, steps):
        """
        Simple check to see if the pings even sent successfully
        """
        for circuit in self.parameters['device_values']['circuits']:
            with steps.start(f"{circuit['circuit']}-{circuit['interface']} - VALIDATE RESPONSE", continue_=True) as substep:
                if not self.icmp_test[circuit['interface']].get('test_icmp'):
                    substep.skipped("No ICMP Test Requested")
                logging.info(f" expected - Non empty dictionary")
                logging.info(f" found - {self.ping_results.get(circuit['interface'])}")
                assert self.ping_results.get(circuit['interface'])
    
    @aetest.test
    def test_response_percentage(self, steps):
        """
        Validate that we recieved our desired amount of ICMP responses
        """
        for circuit in self.parameters['device_values']['circuits']:
            with steps.start(f"{circuit['circuit']}-{circuit['interface']} - REPLY COUNT CHECK", continue_=True) as substep:
                if not self.icmp_test[circuit['interface']].get('test_icmp'):
                    substep.skipped("No ICMP Test Requested")
                ping_statistics = self.ping_results[circuit['interface']].get('ping', {}).get('statistics')
                interface_test = self.icmp_test.get(circuit['interface'])
                if not interface_test.get('success_rate_percent_conform'):
                    substep.skipped("No success_rate_percent_conform defined")
                if not ping_statistics:
                    substep.failed("Failed to find icmp statistics")
                logging.info(f" expected - {interface_test.get('success_rate_percent_conform')}")
                logging.info(f" found - {ping_statistics.get('success_rate_percent')}")
                assert compare_values(ping_statistics.get('success_rate_percent'), interface_test.get('success_rate_percent_conform'))

    @aetest.test
    def test_max_ms(self, steps):
        """
        Validate that no pings exceeded our max expected latency
        """
        for circuit in self.parameters['device_values']['circuits']:
            with steps.start(f"{circuit['circuit']}-{circuit['interface']} - SINGLE PING LATENCY CHECK", continue_=True) as substep:
                if not self.icmp_test[circuit['interface']].get('test_icmp'):
                    substep.skipped("No ICMP Test Requested")
                round_trip = self.ping_results[circuit['interface']].get('ping', {}).get('statistics', {}).get('round_trip')
                interface_test = self.icmp_test.get(circuit['interface'])
                if not interface_test.get('max_ms_conform'):
                    substep.skipped("No max ms conform defined")
                if not round_trip:
                    substep.failed("Failed to find icmp statistics")
                logging.info(f" expected - {interface_test.get('max_ms_conform')}")
                logging.info(f" found - {round_trip.get('max_ms')}")
                assert compare_values(round_trip.get('max_ms'), interface_test.get('max_ms_conform'))

    @aetest.test
    def test_jitter(self, steps):
        """
        Very simple jitter check (max_ms - min_ms). Certainly better tools to check jitter
        If DSCP is not EF, you may get varying results under congestion
        """
        for circuit in self.parameters['device_values']['circuits']:
            with steps.start(f"{circuit['circuit']}-{circuit['interface']} - BASIC JITTER TEST EXPECTED = ", continue_=True) as substep:
                if not self.icmp_test[circuit['interface']].get('test_icmp'):
                    substep.skipped("No ICMP Test Requested")
                round_trip = self.ping_results[circuit['interface']].get('ping', {}).get('statistics', {}).get('round_trip')
                interface_test = self.icmp_test.get(circuit['interface'])
                if not interface_test.get('jitter_conform'):
                    substep.skipped("No jitter conform defined")
                if not round_trip:
                    substep.failed("Failed to find icmp statistics")
                try:
                    basic_jitter = int(round_trip.get('max_ms')) - int(round_trip.get('min_ms'))
                except ValueError:
                    substep.fail("unable to convert max_ms or min_ms")
                logging.info(f" expected - {interface_test.get('jitter_conform')}")
                logging.info(f" found - {basic_jitter}")
                assert compare_values(basic_jitter, interface_test.get('jitter_conform'))
