#Author: Aaron Iniguez and Sabrna Matsunaga
import ast
import glob
import os
import optparse
import sys

def parse_csp_to_chassis(hw_details):
    chassis_dict = dict()
    port_pair_id = 0
    for hw in hw_details:
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

def get_num_of_agents(hw_details,filename="HWDetails.log"):
    with open(os.path.basename(filename), 'w') as f:
        hw_details = ast.literal_eval(hw_details)
        hw_details = parse_csp_to_chassis(hw_details)
        totalportpairs = 0
        for chassis in hw_details:
            f.write( 'chassis host:' + chassis + '\n\n')
            for module in hw_details[chassis]:
                portpair = hw_details[chassis][module].lstrip(';')
                totalportpairs = totalportpairs + len(portpair.split(";"))
                semi_colon_count = 0
                for i in range(len(portpair)):
                    if portpair[i]==';':
                        semi_colon_count = semi_colon_count+1
                        if semi_colon_count %2==0:
                            portpair = portpair[:i] + '    ' + portpair[(i+1):]
                f.write( '{:13s}: {:s}'.format(module, portpair)   + '\n\n')
            f.write('-'*60 + '\n\n')
        totalportpairs = totalportpairs/2
        f.write("Total Port Pairs "+ str(totalportpairs) + '\n\n')
        numofagents = convert_num_agents_req(totalportpairs)
        f.write("Total Agents Required: " + str(numofagents) + '\n\n')
    return numofagents
    
def getHw_Modules(file):
    with open(file,'r') as resource_file:
        for line in resource_file.readlines():
            if line.startswith('hw_modules'):
                hw_modules = line.split('=')[1].strip()   
    print hw_modules
    quit()
    return hw_modules
def containsQemu(resource_file):
    hw_modules = getHw_Modules(resource_file)
    if "stcv-qemu" in hw_modules:
        return True
    return False
def parse_resourcefile(file):    
    with open(file, 'r') as resource_file:
        for line in resource_file.readlines():
            if line.startswith('hw_details'):
                hw_details = line.split('=')[1].strip()   
    return hw_details

def convert_num_agents_req(totalportpairs):
    agents = divmod(totalportpairs, 5)
    if (agents[1] > 0):
        return agents[0] + 1
    else:
        return agents[0]
    
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
        filename=os.path.basename(options.resource_file).replace(".txt",".log")
        numberAgents = get_num_of_agents(parse_resourcefile(options.resource_file),filename)
        if containsQemu(options.resource_file):
            pass
            #get jenkins params
            #then add to numberAgents
        return numberAgents
    elif options.hw_detail:
        return get_num_of_agents(options.hw_detail)
        
if __name__ == "__main__":
    print main()
