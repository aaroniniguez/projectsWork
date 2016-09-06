import ast
import glob
import os
import optparse
import sys

def parse_csp_to_chassis(hw_details):
    chassis_dict = dict()
    port_pair_id = 0
    for hw in hw_details:
        #print 'hwwwwwwwwww:', hw
        hw_csp = hw_details[hw]
        for csp in hw_csp:
            indv_csp = csp.split(';')
            port_pair_id = port_pair_id + 1
            for chassis_splitted in indv_csp:
                chassis_splitted = chassis_splitted.split('/')
                cip = chassis_splitted[0]
                slot = chassis_splitted[1]
                port = chassis_splitted[2]
                if cip not in chassis_dict:
                    module_dict = dict()
                    module_dict[hw]=slot + "/" + port
                    chassis_dict[cip] = module_dict
                else:
                    chassis_dict[cip][hw] =chassis_dict[cip].get(hw,'') + ";"  + slot + "/" + port 
    return chassis_dict

def get_port_pairs(hw_details):
    totalportpairs = 0
    for chassis in hw_details:
        for module in chassis_dict[chassis]:
            portpair = chassis_dict[chassis][module].lstrip(';')
            totalportpairs = totalportpairs + len(portpair.split(";"))
            semi_colon_count = 0
            for i in range(len(portpair)):
                if portpair[i]==';':
                    semi_colon_count = semi_colon_count+1
                    if semi_colon_count %2==0:
                        portpair = portpair[:i] + '    ' + portpair[(i+1):]
    totalportpairs = totalportpairs/2
    return totalportpairs
    
def parse_resourcefile(file):
    print file    
    with open(file, 'r') as resource_file:
        for line in resource_file.readlines():
            if line.startswith('hw_details'):
                hw_details = line.split('=')[1].strip()   
                available_hw_info = ast.literal_eval(hw_details)
                chassis_dict = parse_csp_to_chassis(available_hw_info)
    return chassis_dict

def main():
    curFileName = os.path.realpath(__file__).split("/")[-1]
    parser = optparse.OptionParser("usage: %prog [options] arg1 arg2 arg3")
    parser.add_option("-r", "--resourcefile", action = "store", type = "string", dest = "resource_file", help="Resource file name"  )
    parser.add_option("-d", "--hardwareDetail", action = "store", type = "string", dest = "hw_detail", help="List of hardware details "  )
    (options, args) = parser.parse_args()
    print"******* Input variables ********\n"
    for key,value in vars(options).iteritems():
        print key, ":", value
    print"************************************\n"
    if not options.resource_file and not options.hw_detail:
        print "Please enter a resource file or a list of hardware detail"
        print "Example:\npython "+curFileName+" -r SYS-01-LG.txt "
        sys.exit(1)
    elif options.resource_file:
        return get_port_pairs(parse_resourcefile(options.resource_file))
    elif options.hw_detail:
        return get_port_pairs(options.hw_detail)
if __name__ == "__main__":
    main()

