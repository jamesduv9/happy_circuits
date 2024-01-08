# happy_circuits
For DevNet Expert Studies. Intent-based network circuit testing. Validate circuits are meeting your intent with pyATS tests. Describe your intent in a YAML file and let pyATS validate.

## Why?
Sometimes you want more than just simple red/green lights provided by a network monitoring tool, and some things simply don't show up in logs. External circuits are often a weak point in the network due to not having full visibility of both sides. I wanted to create a tool that could validate that these circuits are meeting some level of intent in an ondemand or scheduled test.

## Workflow
1. **Define Your Intent**: Craft your intent in an `intent.yml` file. For a practical example with extensive comments, check out `intent_file.yml`.
2. **Set Up Your Testbed**: Create your testbed file following standard conventions for a pyATS test. For detailed examples, refer to the [official documentation](https://pubhub.devnetcloud.com/media/pyats/docs/topology/example.html).
3. **Execute**: Run the pyATS Job file with the command line arguments detailed in the **Usage** section below. The tool will then perform Interface, ICMP, and BGP tests to ensure your circuits are adhering to the defined intent.
tent

## Usage
1. First, install the necessary Python libraries:
```
pip install -r requirements.txt
```

2. Execute the tool with:
```
pyats run job happy_circuits.py --testbed-file [your_tb.yaml] [optional_arguments]
```

Note: pyATS overrides the input arguments in an unexpected manner, which can affect the help documentation for script-specific arguments. The available optional arguments for `happy_circuits.py` are listed below:


```
Options:
  --intent_file TEXT      MANDATORY: path to your intent yaml file

  --auth_type TEXT        OPTIONAL: To have the script prompt you for new a
                                    new password per device, specify "token"

  --username TEXT         OPTIONAL: If auth_type == "token" you must provide 
                                    your username here
```
## Crafting Your Intent File
Your intent file should be structured as illustrated in the `intent_file.yml` in this repository. It demonstrates how to define tests for a single circuit on a single device. Please customize as needed for your specific setup. Default values in the example serve as basic suggestions; you can adjust them as per your requirements.

For clarity, every parameter that concludes with `_conform` must be associated with an operator (e.g., lt, le, gt, ge, eq). Always specify your intent, not the failure condition. For instance, if you desire "less than or equal to 20" crc errors, denote it as "le 20". If you wish to skip a particular test, simply assign its value to `null`.
```
################################################################################################
# Example Intent File                                                                          #
# all values ending with _conform must be configured with operators, (lt, le, gt, ge, eq)      #
# Specify your intent, not the fail condition, example: I WANT "le 20" crc errors              #
# Set any test value to null to skip the specific test                                         #
################################################################################################
---
config:
  devices:                              
    router1:                                        #Device hostname - must match testbed key
      circuits:
        - circuit: AAA1                             #Circuit identifier
          interface: GigabitEthernet3               #Interface tied to circuit
          is_subinterface: False                    #If subinterface set to True
          tests:    

            #######################################################
            # BGP test parameters                                 #
            #######################################################                
            bgp:
              test_bgp: True
              vrf: null                               #Specify as null for global, or an actual VRF name
              neighbors:                             
                - neighbor_ip: 169.254.100.2          #List of neighbors you expect to see over this circuit
                  uptime_conform: gt 1                #How many DAYS we expect the bgp peer to be up at minimum. 
                  address_families:                         
                    - address_family: ipv4 unicast    #Valid types - ipv4 unicast, vpnv4 unicast 
                      received_routes:                #Each route will be verified to exist in show ip bgp neighbor X received-routes
                        - 10.1.1.0/24
                      advertised_routes:              #Each route will be verified to exist in show ip bgp neighbor X advertised-routes
                        - 172.16.0.1/32
            #######################################################
            # ICMP test parameters                                #
            #######################################################
            icmp:
              test_icmp: True                         #To icmp test or not to icmp test. Disable if icmp blocked on interface
              pingable_address: 169.254.100.2         #Address that SHOULD be pingable across this circuit
              ping_count: 100                         #How many pings to send
              success_rate_percent_conform: ge 90     #What percentage of pings should go through successfully
              max_ms_conform: le 20                   #Highest latency ping should be within what range (in ms)
              jitter_conform: le 50                   #Jitter in ms, max_ms - min_ms ping
              vrf: null                               #Specify as null for global, or an actual VRF name
            #######################################################
            # Interface level tests - After correcting a failure, #
            #  suggested to clear counters on the device          #
            #######################################################
            interface:                                #Define the interface test
              test_interface: True                    #To test or not to test the interface
              ipv4: 169.254.100.1/30                  #Validate the interface has the required IP
              in_errors_conform: le 200               #How many in errors are acceptable
              in_crc_errors_conform: le 200           #How many crc errors are acceptable
              out_errors_conform: le 200              #How many out errors are acceptable
              out_collision_conform: le 200           #How many out collisions are acceptable
              txload_conform: le 128                  #What is the max acceptable txload? (out of 255)
              rxload_conform: le 128                  #What is the max acceptable rxload? (out of 255)
              duplex: Full                            #What duplex should the interface be operating at? (Full or Half)
              line_protocol: up                       #Should this interface be up or down?
              enabled: True                           #Should this interface be enabled?
...
```
## Known Issues
- The Genie parser for "show ip bgp neighbor x.x.x.x routes" provides the routes received without CIDR notation. Because of this the script only verifies that the received route is matched without prefix length. For example if you want to test that you receive 10.1.1.0/24, and you instead only receive 10.1.1.0/30, the test will still return as passed.

