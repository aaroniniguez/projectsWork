import csv
import os.path
import datetime
import pprint
import ast
import time
import math
import re
import xmlrpclib
import json
from xml.etree import ElementTree
from xml.dom import minidom
from xml.etree.ElementTree import Element, SubElement, Comment, tostring
from pw_testcase_fetcher import *
from random import choice
from random import shuffle
from ConfigParser import *
import string

DEFAULT_OUT_XML = "SmartTest.xml"
DEFAULT_EMAILS = 'DevOps=DevOpsTeam@spirent.com'
DEFAULT_EMAIL_SERVER = "smtprelay.spirent.com"
CHASSIS_SLOT_PORT = '10.100.21.5/1/1;10.100.21.5/1/3'
AGENT_TYPE = 'TCL'
AGENT_TSD = '//PV_Scripts/mainline/SmartTest/...'

tag_str = list()

DEFAULT_MISC_SCRIPT_DIR = str({})
DEFAULT_TEST_SCRIPT_DIR = str({'//PV_Scripts/mainline/SmartTest/...': {'source': 'perforce'},
                '//TestCenter/4.0_rel/scm/test_scripts/regression/reserve_provision/Script/...': {'source' : 'perforce'}})


DEFAULT_AGENTS_PER_HOST = 5
DEFAULT_HW_CHASSIS = ""
DEFAULT_HW_MODULES = ""
DEFAULT_HW_MODULES_MAPPINGS = str({ 'mx-10g' : ['mx-10g-s', 'mx-10g-c']})
DEFAULT_TESTSET = "BASE"

DEFAULT_agenthost_details = str({'localhost1' : {'host': 'localhost1', 'platform':"windows", 'OSVersion':"XPSP2"},
                     'localhost2' : {'host': 'localhost2', 'platform':"windows", 'OSVersion':"XPSP2"},
                     'localhost3' : {'host': 'localhost3', 'platform':"windows", 'OSVersion':"XPSP2"},
                     'localhost4': {'host': 'localhost4', 'platform':"windows", 'OSVersion':"XPSP2"}})

DEFAULT_available_hw_info = str({'cv-10g': ['csp1', 'csp2', 'csp3', 'csp4'],
                     'mx-100g': ['csp11', 'csp12', 'csp13']})

DEFAULT_TEST_RESULTS_DIR = str({'alias': '/thot-nas/DD_Regression/BLL0930_IL0990',
                                 'path': '\\\\10.8.50.181\\scm\\SCM_Regression\\3.90\\BLL2480_IL1910',
                                })

DEFAULT_DATABASE_SERVER_CONFIG = ''

DEFAULT_GRAPH_SERVER_CONFIG = ''

DEFAULT_AGENT_EXIT = str({'exitCount': '15',
                           'enabled': 'true',
                          })

DEFAULT_COMMAND_ANALYSIS = str({'enabled': 'false'})

DEFAULT_SMARTTEST_DB_UPDATE = str({'enabled': 'true'})

DEFAULT_DB_UPDATE = str({'type': 'database' , 'enabled': 'false'})

DEFAULT_SUITE_USER = str({ 'mode': 'SCM', 'scriptOrder' : 'alphabetical', 'extraSummaryColumn' : 'Total,CR'})

DEFAULT_ENV_ANALYSIS = str({ 'enabled': 'true', 'branch' : 'release', 'owner' : 'SmartTest'})

DEFAULT_QTP_WORKING_DIR = {'name' : 'C:\\Program Files\\Mercury Interactive\\QuickTest Professional\\bin'}

STAPP_TESTCASE_ACTIVE = 0;

STAPP_TESTCASE_INACTIVE = 1;

STAPP_TESTCASE_DEP = 2;

DEFAULT_TESTSUITE_NAME = "SmartTest"

VIRTUAL_TAG = 'stcv-qemu'

VIRTUAL_SERVER = 'http://calqmanager.spirentcom.com:8080'

VIRTUAL_SERVER_OPTS = str({'max_port_pairs' : 0 , 'id' : 'smarttest', 'vm_ttl' : None})

OPT_FOR_DISKSPACE = False

DEFAULT_THOT_THGROUP = "TAG"

sys.setrecursionlimit(2000)


class SMTConfigParser(ConfigParser):

    def as_dict(self):
        d = dict(self._sections)
        for k in d:
            d[k] = dict(self._defaults, **d[k])
            d[k].pop('__name__', None)
        return d

class FakeSecHead(object):
    def __init__(self, fp):
        self.fp = fp
        self.sechead = '[asection]\n'
    def readline(self):
        if self.sechead:
            try: return self.sechead
            finally: self.sechead = None
        else: return self.fp.readline()
#cp.readfp(FakeSecHead(open('my.props')))

def prettify(elem, fName=DEFAULT_OUT_XML):
    """Return a pretty-printed XML string for the Element.
    """
    rough_string = ElementTree.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)

    if not fName is None:
        f = open(fName, 'w')
        reparsed.writexml(f, indent="    ", addindent="    ", newl="\n")
        f.close()

    return reparsed.toprettyxml(indent="  ")

def chunks(tclist, agent_cnt):
    if agent_cnt <= 1:
        yield tclist
        return

    quick_sort(tclist)
    duration_list = []
    testcases_bucket_list = []
    for i in xrange(agent_cnt):
        duration_list.append(0)
        testcases_bucket_list.append(list())

    for tc in tclist:
        #find out which bucket has the least execution time
        min_idx = 0
        for i in xrange(1, agent_cnt):
            if duration_list[min_idx] > duration_list[i]:
                min_idx = i

        duration_list[min_idx] += tc.testcase.duration_seconds
        testcases_bucket_list[min_idx].append(tc)

    for testcases_bucket in testcases_bucket_list:
        shuffle(testcases_bucket)
        yield testcases_bucket

# quick sort
def quick_sort(l):
    quick_sort_r(l, 0, len(l) - 1)
    #sort by desc
    l.reverse()
    
# quick_sort_r, recursive (used by quick_sort)
def quick_sort_r(l , first, last):
    if last > first:
        pivot = partition(l, first, last)
        quick_sort_r(l, first, pivot - 1)
        quick_sort_r(l, pivot + 1, last)
        
# partition (used by quick_sort_r)
def partition(l, first, last):
    sred = (first + last)/2
    if l[first].testcase.duration_seconds > l[sred].testcase.duration_seconds:
        l[first], l[sred] = l[sred], l[first]  # swap
    if l[first].testcase.duration_seconds > l[last].testcase.duration_seconds:
        l[first], l[last] = l[last], l[first]  # swap
    if l[sred].testcase.duration_seconds > l[last].testcase.duration_seconds:
        l[sred], l[last] = l[last], l[sred]    # swap
    l[sred], l[first] = l[first], l[sred]    # swap
    pivot = first
    i = first + 1
    j = last
  
    while True:
        while i <= last and l[i].testcase.duration_seconds <= l[pivot].testcase.duration_seconds:
            i += 1
        while j >= first and l[j].testcase.duration_seconds > l[pivot].testcase.duration_seconds:
            j -= 1
        if i >= j:
            break
        else:
            l[i], l[j] = l[j], l[i]  # swap
    l[j], l[pivot] = l[pivot], l[j]  # swap
    return j


def parse_tags_file(fileName):
    reader = csv.reader(open(fileName, "rb"))
    discovered_tags = []
    for row in reader:
        discovered_tags += row
    
    discovered_tags = filter(bool, discovered_tags)
    return discovered_tags

def parse_bll_il_l4l7_versions(fileName='properties.txt'):
    bll = ""
    ill = ""
    l4l7 = ""
    try:
        fileO = open(fileName,'r')
        for line in fileO.readlines():
            match = re.search( 'BLL' , line )
            if match : 
                cols = line.split('=')
                cols1 = cols[1].split('\n') 
                bll = cols1[0]
            match = re.search( 'IL' , line )
            if match : 
                cols = line.split('=')
                cols1 = cols[1].split('\n') 
                ill = cols1[0] 
            match = re.search( 'L4L7' , line )
            if match : 
                cols = line.split('=')
                cols1 = cols[1].split('\n') 
                l4l7 = cols1[0]                                                        
        file.close
    except:
        print "Version Properties File Read Error"
    print "SmartTest Properties BLL ->" ,bll
    print "SmartTest Properties IL ->" ,ill
    print "SmartTest Properties L4L7 ->" ,l4l7
    
    return {'bll' : bll, 'il': ill, 'l4l7': l4l7}

    
###############################################################################
class VmManager(object):

    def __init__(self,
                 id='smartTest',
                 url='http://calqmanager.spirentcom.com:8080',
                 desc='smartTest',
                 host=None):
        self._qm = xmlrpclib.ServerProxy(url, allow_none=True)
        self._vm_ids = []
        self._vm_ips = {}
        self._ip_check = {}
        self._id = id
        self._fake = 0
        self._desc = desc
        self._host = host

    def get_vm_capacity_count(self):
        capacity = 0
        summary = self._qm.get_all_host_summary()
        for host_id, host_info in summary.viewitems():
            if not host_info.has_key('locked_by'):
                capacity += int(host_info.get('free cores'))
        return capacity

    def get_vm_count(self):
        return len(self._vm_ids)

    def start_vm_group(self, count, vm_mem, cores, use_sockets=False, vm_ttl=None, version=None):
        start_time = time.time()
        print('starting vm group with count {0}'.format(count))
        if use_sockets: 
            print 'VM manager is using socket based option', use_sockets
        else:
            print 'VM manager is not using socket based option', use_sockets
            
        if vm_mem == None:
            print " memory needed is 512"
        else:
            print " memory needed is", vm_mem
    
            
        if cores == None:
            print 'VM manager is using number of cores: 1' 
            cores = None
        else:
            print 'VM manager is using number of cores: ', cores
            
        if self._fake:
            ids = [x + self._fake for x in range(count)]
            self._fake += count
        else:
            print "number of cores needed ", cores
            ids = self._qm.start_stc_vm(self._id, version, vm_ttl, use_sockets, self._desc, count, self._host,None,None,vm_mem,cores)

        # since qm is not stable, add extra checks and print
        if ids is None or len(ids) != count:
            raise RuntimeError('qm.start_vm failed')
        print(ids)
        print('start_vm_group took {0:.2f} sec'.format(time.time() - start_time))
        self._vm_ids.extend(ids)
        return ids

    def get_vm_ips(self, ids):
        start_time = time.time()
        self._wait_for_ips()
        print('get_vm_ips took {0:.2f} sec'.format(time.time() - start_time))
        return (self._vm_ips.get(i, 'unknown') for i in ids)

    def stop_vm(self, vids):
        if self._fake:
            return

        for vid in vids:
            print('stopping vm: ' + vid)
            try:
                self._qm.stop_vm(self._id, vid)
            except Exception, ex:
                print 'ERROR: ' + str(ex)
    
    def stop_all_vm(self):
        if self._fake:
            return

        print('stopping vms')
        for vid in self._vm_ids:
            print('stopping vm: ' + vid)
            try:
                self._qm.stop_vm(self._id, vid)
            except Exception, ex:
                print 'ERROR: ' + str(ex)
        self._vm_ids = []
        self._vm_ips = {}

    def _wait_for_ips(self):
        print('waiting for vm ips')
        if self._fake:
            return

        for vid in self._vm_ids:
            ip = self._vm_ips.get(vid, 'unknown')

            if ip != 'unknown':
                continue

            while ip == 'unknown':
                #print('getting ip for {0}'.format(vid))
                ip = self._qm.get_vm_ip(vid)
                if ip == 'unknown':
                    time.sleep(1)
                #print('got ip {0} for {1}'.format(ip, vid))
                
            print 'got ip {0} for {1}'.format(ip, vid)
            if not (ip and ip[0].isdigit() and ip.count('.') == 3):
                # If not an IP address, then its a failure message.
                raise RuntimeError('vm {0} failed to start'.format(vid))

            if ip in self._ip_check:
                raise RuntimeError(
                    'vm {0} returned duplicate IP {1}'.format(vid, ip))
            self._ip_check[ip] = True
            self._vm_ips[vid] = ip
            


###############################################################################

def provision_equip(vms, vm_required, max_ports=0, group_size=2,vm_mem=None,cores=None):

    capacity = vms.get_vm_capacity_count()
    capacity = int(math.floor(capacity * 0.5))

    vm_pairs = []

    print 'Maximum virtual port pairs possible: %s' % capacity
    print 'Required virtual port pairs : %s' % vm_required

    if capacity == 0:
        print '--- No Virtual Ports Available ---'
        return {VIRTUAL_TAG : []}

    if vm_required > capacity:
        vm_to_create = capacity #leave room for someone else
    else:
        vm_to_create = vm_required

    if not max_ports == 0:
        if vm_to_create > max_ports:
            vm_to_create = max_ports

    use_buildnum=v_svr_opt.get('use_buildnum', 'True')

    buildnum=None

    if use_buildnum == 'True' :
        buildnum='#%s' % build_info['bll']

    print "QEMU build -> use buildnum:", use_buildnum 

    
    for i in range(vm_to_create):
        print "creating vm, memory needed is ", vm_mem
        vids = tuple(vms.start_vm_group(group_size, vm_mem, cores, vm_ttl=v_svr_opt.get('vm_ttl', None), use_sockets=v_svr_opt.get('use_sockets', False), version=buildnum))
        vm_pairs.append(vids)

    print(vm_pairs)

    equip_provs = []
    for vs in vm_pairs:
        csps = tuple(ip + '/1/1' for ip in vms.get_vm_ips(vs))
        equip_provs.append(';'.join(csps))

    qemuvmstr = ','.join(equip_provs) 
    paramfile = open(os.environ['WORKSPACE'] + "\qemuVM_IP.txt", "w")
    paramfile.write("QEMUVM_IP=" + qemuvmstr + "\n")   
    paramfile.close()
    
    print(equip_provs)
    return {VIRTUAL_TAG : equip_provs}

########################################################################


class ThotAgentManager:

    def __init__(self):
        self.max_agents_per_machine = 10
        self.agents_created = {}

    def set_test_suite(self, tc_suite):
        self.tc_suite = tc_suite
        
    def add_new_agent(self, agent_info={}):
        #Add TestCaseAgent
        new_agent = self.get_next_agent_details()
        defa_attrs = {'enabled' : 'true' , 'execMode' : 'Parallel', 'consoleOutput': 'false', 'type': 'TCL'}
        
        agent_attrs = dict(defa_attrs.items() + new_agent.items())
        if len(agent_info) > 0:
            agent_attrs = dict(agent_attrs.items() + agent_info.items())
        
        tc_agt = SubElement(self.tc_suite, 'TestCaseAgent', agent_attrs)

                
        if (agent_attrs.get('type') == 'QTP'):
            qtp_dir = SubElement(tc_agt, 'QTPWorkingDirectory', DEFAULT_QTP_WORKING_DIR)

        '''
        tc_agt = SubElement(self.tc_suite, 'TestCaseAgent' , {
                                                      'name': 'Windows_Agent', #provide
                                                      'enabled': 'true',
                                                      'execMode':"Parallel",
                                                      'type':"TCL",
                                                      'hostname':"localhost",
                                                      'chassisType':"11U", #provide
                                                      'moduleType':"Blink", #provide
                                                      'consoleOutput':"false",
                                                      'platform':"windows",
                                                      'OSVersion':"XPSP2"
                                                      })
        '''
        
        return tc_agt

    def get_next_agent_details(self):
        if len(self.agents_created) > 0:
            used_hosts = list(set(self.agents_details.keys()).intersection(self.agents_created.keys()))
            unused_hosts = list(set(self.agents_details.keys()).difference(self.agents_created.keys()))
            host_found = False
            for agnt in used_hosts:
                agnt_cnt = self.agents_created[agnt]
                if agnt_cnt < self.max_agents_per_machine:
                    #We can use this to create a new agent
                    if agnt not in self.agents_details.keys():
                        print "Internal Error"
                    agnt_cnt += 1
                    self.agents_created[agnt] = agnt_cnt
                    new_agent_host = agnt
                    host_found = True
                    break
            if not host_found:
                #used_host are full. create a new one
                if len(unused_hosts) > 0:
                    agnt = unused_hosts[0]
                    self.agents_created[agnt] = 1
                    new_agent_host = agnt
                else:
                    print "No host for agent available. Resource limitation"
        else:
            new_agent_host = self.agents_details.iterkeys().next()
            agnt_cnt = 1
            self.agents_created[new_agent_host] = agnt_cnt

        #Will generate error in case of unavailable resource.
        return self.agents_details[new_agent_host]


    def set_available_agents(self, agent_details):
        self.agents_details = agent_details



    def set_max_agents_per_agent_host(self, agent_cnt):
        self.max_agents_per_machine = agent_cnt
        


class ThotElementBase(object):
    def __getattr__(self, name):
        if name in self.__dict__.keys():
            return self.__dict__[name]    
    
    def __setattr__(self, name, value):
        self.__dict__[name] = value

class ThotSuite(ThotElementBase):
    name = ""
    purpose = ""
    agent_list = set()
    
class ThotAgent(ThotElementBase):
    name = ""
    hw_info = ""
    hostname = ""
    platform = ""
    execMode = ""
    scriptType = ""
    consoleOutput = ""
    OSVersion = ""
    test_scripts = list()

class ThotTestScript(ThotElementBase):    
    def __init__(self, attrs=dict()):
        for attr in attrs.keys():
            print "Key found: " + attr

class ThotConf(object):
    test_agents = set()

def create_testsuite():

    return

def add_testagent(test_suite):

    #Add TestCaseAgent
    tc_agt = SubElement(test_suite, 'TestCaseAgent' , {
                                                      'name': 'Windows_Agent',
                                                      'hostname': 'localhost',
                                                      'enabled': 'true',
                                                      'execMode':"Parallel",
                                                      'type':"TCL",
                                                      'platform':"windows",
                                                      'hostname':"localhost",
                                                      'enabled':"true",
                                                      'chassisType':"11U",
                                                      'moduleType':"Blink",
                                                      'consoleOutput':"false",
                                                      'OSVersion':"XPSP2"
                                                      })
    return tc_agt


def add_misc_files_directory1(tc_agent, mfd_list):
    for mfd in mfd_list:
        mfd1 = SubElement(tc_agent, 'MiscFilesDirectory')
        mfd1.set('source', 'perforce')
        mfd_attrs = mfd_list[mfd]
        for attr in mfd_attrs.keys():
            mfd1.set(attr, mfd_attrs[attr])
        mfd1.set('name' , mfd)


def add_test_files_directory(tc_agent, tsd_list):
    for tsd in tsd_list:
        tsd1 = SubElement(tc_agent, 'TestScriptDirectory')
        tsd1.set('source', 'perforce')
        tsd_attrs = tsd_list[tsd]
        for attr in tsd_attrs.keys():
            tsd1.set(attr, tsd_attrs[attr])
        tsd1.set('name' , tsd)


def add_email_server_to_notification(noti, email_server):
    tsd1 = SubElement(noti, 'EmailServer')
    tsd1.set('name' , email_server)


def add_format_to_notification(noti):
    frmt = SubElement(noti, 'Format', {
                                'level': 'SUITE'
                                })

    SubElement(frmt, 'Item', {
                              'name': 'SCM Summary'
                             })

    SubElement(frmt, 'Item', {
                              'name': 'Suite Configuration'
                             })

def add_notification_emails(tc_suite, emails):
    noti = SubElement(tc_suite, 'Notification')
    
    for k , v in emails.iteritems():
        SubElement(noti, 'Email',
                                { 'name': k,
                                  'email': v
                                })
    
    return noti

def add_test_agent_setup(tc_agent, opt_ds):

    tc_agt_setup = SubElement(tc_agent, 'Setup')

    if (AGENT_TYPE == 'itest'):
        SubElement(tc_agt_setup, 'iTest', {
                                   'command': 'itestcli',
                                   'version': '4.2'
                                    })

    elif (AGENT_TYPE == 'python'):
        SubElement(tc_agt_setup, 'Python', {
                                   'command': 'python',
                                   'version': '2.6'
                                    })
    elif (AGENT_TYPE == 'itestrt'):
        SubElement(tc_agt_setup, 'Python', {
                                   'command': 'python',
                                   'version': '2.6'
                                    })
    elif (AGENT_TYPE == 'perl'):
        SubElement(tc_agt_setup, 'Perl', {
                                   'command': 'perl',
                                   'version': '5.14'
                                    })
    elif (AGENT_TYPE == 'ruby'):
        SubElement(tc_agt_setup, 'Ruby', {
                                   'command': 'ruby',
                                   'version': '5.8'
                                    })
    else:
        SubElement(tc_agt_setup, 'Tcl', {
                                   'command': 'tclsh',
                                   'version': '8.4'
                                    })
        
    if opt_ds:
        SubElement(tc_agt_setup, 'ExternalScriptWS', {
                                           'enabled': 'true',
                                           'pathTranslate': 'true'
                                            })        
        '''
        SubElement(tc_agt_setup, 'MiscSetup ', {
                                           'mode': 'sequential',
                                           'pathTranslate': 'false'
                                            })        
        '''
    
    
def get_thot_thgroup(tc):
    if thgroup_to_use == "TAG":
        return tc.tag.name
    elif thgroup_to_use == "DB":
        return tc.testcase.mst.name

def format_seconds_to_hhmmss(seconds):
    hours = seconds // (60*60)
    seconds %= (60*60)
    minutes = seconds // 60
    seconds %= 60
    return "%02i:%02i:%02i" % (hours, minutes, seconds)


def add_test_scripts(tc_agent, unique_testcases_to_run, csp, bll_par, l4l7_par, bll, l4l7, lab, miscfiles_option,avnext,Roma_MacAddr,APInfo):
    global tags_list_q, gbl_script_timer
    total_exec_time = 0

    for tc in unique_testcases_to_run:
        total_exec_time += tc.testcase.duration_seconds
        
        tc_script = SubElement(tc_agent, 'TestScript')

    if (AGENT_TYPE == 'itestrt'):    
             tc_script.set('name' , 'thot_adapter.py')
             tc_script.set('scriptfile' , tc.testcase.script_name) 
             tc_script.set('chassisSlotPort' , csp)    
             extraParams_map = dict();
             for var in tc.testcase.tc_vars:
                  extraParams_map[var.variable.name] = str (var.variable.value)                
          if len(avnext) > 0:         
            match = re.search( 'controllerIP' , var.variable.name ) 
                        if match:
                           extraParams_map[var.variable.name] = avnext 
             output = json.dumps(extraParams_map)
             tc_script.set('extraParams' , output)    
    else:
             tc_script.set('name' , tc.testcase.script_name)
             tc_script.set('chassisSlotPort' , csp)
             for var in tc.testcase.tc_vars:
                 tc_script.set(var.variable.name , var.variable.value)

        if bll_par == True:       
         tc_script.set('BLL' , bll)
        if l4l7_par == True:       
         tc_script.set('L4L7' , l4l7)
        if len(lab) > 0:
             tc_script.set('LabServerList', lab)

        if len(Roma_MacAddr) > 0:
             tc_script.set('RomaMacAddrList', Roma_MacAddr)

        if len(APInfo) > 0:
             tc_script.set('APInfo', APInfo)

        SubElement(tc_script, 'THGroups' ,
                            { 'name': get_thot_thgroup(tc),
                             })

        SubElement(tc_script, 'TestCase' ,
                            { 'name': tc.testcase.name
                            })
        

        #Add Misc files information
        if miscfiles_option:
              misc_opt = ast.literal_eval(miscfiles_option)   
              path = misc_opt.get('path','/home/thot/thot_repo/')
              source = misc_opt.get('source','local')
              miscfiles = fetch_miscfiles_from_testcase(tc.testcase.id)
              for miscfile in miscfiles:        
                  miscfilepath = path + miscfile.path
                  SubElement(tc_script, 'MiscFile' ,
                                   { 'name': miscfilepath,
                                   'source': source
                                   })

        #Add Dead Script Timer
        timeout_seconds = 0
        if not gbl_script_timer is None and gbl_script_timer > 0:
            timeout_seconds = gbl_script_timer
        else:
            timeout_seconds = tc.testcase.timeout_seconds

        cal_time = format_seconds_to_hhmmss(timeout_seconds)
        (hr, mn, sc) = cal_time.split(':')        

        SubElement(tc_script, 'DeadScriptTimer', {'hour': hr,
                                                  'min': mn,
                                                  'sec': sc,
                                                 })        
        #print "Added -> %r, %r" % (tc.testcase.name, tc.tag.name)
    
    print "Count of test cases to run on Agent(%s - %s) : %s (Duration: %s seconds)" % (tc_agent.get("hostname"), tc_agent.get("name") , str(len(unique_testcases_to_run)), str(total_exec_time))



def filter_modules(orig_hw_list, stc_version):
    print "filter the hw_modules based on min supported stc version"
    query_by_version_list = list()
    query_hw_list = list()
    for minver in stc_version :
        query_by_version_list.append([StappTestModule.min_stc_version <= unicode(minver)])

    res = fetch_modules(query_by_version_list)
    for r in res:
        query_hw_list.append(r.name)
    
    return query_hw_list
 


def fetch_test_scripts_list(tags_list, testmodule_list, testset_list, testcases = [], testtypes = [], scripttypes = [], mstlist = [], minverlist = [], maxexeclist = [], prioritylist = []):
    
    #and_cnd_list = list([StappTestcase.state == STAPP_TESTCASE_ACTIVE])
    and_cnd_list = list()
    indv_or_list = list()
    for tc_state in tc_state_list:
        indv_or_list.append([StappTestcase.state == int(tc_state)])
    
    and_cnd_list.append(indv_or_list)
    
    if len(testcases) > 0:
        tc_or_list = list()
        for testcase in testcases:
            tc_or_list.append([StappTestcase.name == unicode(testcase)])
        and_cnd_list.append(tc_or_list)

    if len(testtypes) > 0:
        tt_or_list = list()
        for testtype in testtypes:
            tt_or_list.append([StappTestcase.testtype == int(testtype)])
        and_cnd_list.append(tt_or_list)

    if len(scripttypes) > 0:
        st_or_list = list()
        for scripttype in scripttypes:
            st_or_list.append([StappScriptType.interpreter == unicode(scripttype)])
        and_cnd_list.append(st_or_list)

    if len(minverlist) > 0:
        minver_or_list = list()   
        for minver in minverlist:
            minver_or_list.append([StappTestcase.min_stc_version <= unicode(minver)])    
        and_cnd_list.append(minver_or_list)

    if len(maxexeclist) > 0:
        exectime_or_list = list()   
        for exectime in maxexeclist:
            exectime_or_list.append([StappTestcase.duration_seconds <= int(exectime)])    
        and_cnd_list.append(exectime_or_list)

    if len(mstlist) > 0:
        ms_or_list = list()   
        for mst in mstlist:
            ms_or_list.append([StappMarketSegment.name == unicode(mst)])    
        and_cnd_list.append(ms_or_list)

    if len(prioritylist) > 0:
        priority_or_list = list()   
        for priority in prioritylist:
            priority_or_list.append([StappTestcase.priority == int(priority)])    
        and_cnd_list.append(priority_or_list)

    testcases_to_run = fetch_testcases_for_tag(tags_list, testmodule_list, testset_list, and_cnd_list)
    #print "Before Eliminating duplicate test cases, if any.: %s" % testcases_to_run.count()
    unique_testcases_to_run = dict()
    print "Eliminating duplicate test cases, if any."
    for sttc in testcases_to_run:
        #print sttc.testcase_id
        if not sttc.testcase.name in unique_testcases_to_run.keys():
            unique_testcases_to_run[sttc.testcase.name] = sttc
       
    print "Total Test Cases to run test cases: %s" % len(unique_testcases_to_run)
    return unique_testcases_to_run


def prepare_test_agent(tc_agent, opt_ds, csp, scpillog, monitorportgroup,chassislog ):
    emailR = {}
    add_notification_emails(tc_agent, emailR)

    #ADD Test AGent Setup
    add_test_agent_setup(tc_agent, opt_ds)

    #ADD SCPILLog
    if scpillog == 'true':
             scpillog = SubElement(tc_agent, 'SCPILLog', {'enabled': 'true',
                                                              'SCPILAddr': csp,
                                                              'username': 'thot',
                                                              'password': 'thot123',
                                                             })
    
    #ADD ChassisLog
    if chassislog == 'true':                
             cols = string.split(csp,';')  
             cols1 = string.split(cols[0],'/') 
             #cols2 = string.split(cols[1],'/') 
             chassis_list = cols1[0]
             chasssislog = SubElement(tc_agent, 'GetEquipmentLogs', {'chassis': chassis_list,                                                           
                                                             }) 

    #ADD MonitorPortGroup
    if monitorportgroup == 'true':
             monitorportgroup = SubElement(tc_agent, 'MonitorPortGroup', {'CSP': csp,
                                                              'reboot': 'true',                                                             
                                                             })


    #Add Dead Script Timer
    d_script_timer = SubElement(tc_agent, 'DeadScriptTimer', {'hour': '0',
                                                              'min': '15',
                                                              'sec': '0',
                                                             })
 
    s_script_timer = SubElement(tc_agent, 'SleepScriptTimer',
                                {'hour': '0',
                                  'min': '0',
                                  'sec': '5',
                                })

    #Add MiscFilesDirectory
    add_misc_files_directory1(tc_agent, mfd_dict)

    #Add TestScript Directory
    add_test_files_directory(tc_agent, tsd_dict)

def add_setup_application(tc_suite_setup,ap_upgrade):
    tc_suite_setup_ap = SubElement(tc_suite_setup, 'ApplicationInstall',
                                {'enabled': ap_upgrade,
                                 'name': 'STC',
                                 'version': '3.90.0000'
                                })
    
    return tc_suite_setup_ap

def add_setup_application_hosts(tc_suite_setup_ap, agent_hosts):
    for agent in agent_hosts:
        agt = agent_hosts[agent]
        ele = SubElement(tc_suite_setup_ap, 'Host',
                {'enabled': 'true',
                 'name': agt["hostname"],
                 'platform' : agt["platform"],
                 'buildLocation': 'none',
                 'destinationDir': 'default'
                })
        plat = agt["platform"]
        platCmp = "linux"
        if plat.lower() == platCmp.lower():
            ele.set("destinationDir", '/home/thot/Spirent_Communications/Spirent_TestCenter/bin')

def add_setup_application_sm(tc_suite_setup_ap): 
     ele = SubElement(tc_suite_setup_ap, 'Host',
             {'enabled': 'true',
              'name': 'localhost',
              'platform' : 'windows',
              'buildLocation': 'none',
              'destinationDir': 'default'
             })
        
def add_setup_hardwarelistupdate(tc_suite_setup):
    SubElement(tc_suite_setup, 'HardwareListUpdate', {
                                                    'enabled': 'true',
                                                    })

def add_setup_il(tc_suite_setup):
    tc_suite_setup_ap = SubElement(tc_suite_setup_fw, 'IL',
                                {'buildLocation': 'false',
                                 'version': '3.90.0000',
                                })

    return tc_suite_setup_ap

def add_setup_il_chassis(tc_suite_setup_ap, chassis_list):
    for chassisip in chassis_list:
        SubElement(tc_suite_setup_fw, 'Chassis',
                        {'ip': chassisip,
                         'slot': 'a',
                         'chassisInstall': 'true'
                        })

def parse_csp_to_chassis(hw_details):
    chassis_list = []
    for hw in hw_details:
        hw_csp = hw_details[hw]
        for csp in hw_csp:
            indv_csp = csp.split(';')
            for chassis_splitted in indv_csp:
                chassis_splitted = chassis_splitted.split('/')
                cip = chassis_splitted[0]
                if cip not in chassis_list:
                    chassis_list.append(cip)
    return chassis_list 

def reverse_chassis_type_map(type_chassis_map):
    chassis_type_map = dict();
    for type in type_chassis_map:
        for chassisIP in type_chassis_map[type]:
            chassis_type_map[chassisIP] = type

    return chassis_type_map
    
def sort_test_scripts_by_module(testcases_to_run, modules_queried=[]):
    sorted_by_module = dict();
    if len(modules_queried) == 0:
        res = fetch_all_modules()
        for r in res:
            modules_queried.append(r.name)
    for tc_name in testcases_to_run:
        sttc = testcases_to_run[tc_name]
        if options.optimize_with_virtual:
            virtual_enable = False
            for ts_mod in sttc.testcase.tc_modules:
                if ts_mod.testmodule_id == VIRTUAL_TAG:
                    virtual_enable = True
                    rand_mod = ts_mod.testmodule_id
        else:
            virtual_enable = False

        if not virtual_enable:
            for ts_mod in sttc.testcase.tc_modules:
                if tm_mappings.has_key(ts_mod.testmodule_id):
                    #print "found mapping ----------------------------------- %s" % sttc.testcase.name
                    rand_mod = choice(tm_mappings[ts_mod.testmodule_id])
                    #while rand_mod not in modules_queried:
                    #    rand_mod = choice(tm_mappings[ts_mod.testmodule_id])
                else:
                    rand_mod = ts_mod.testmodule_id
    
                if rand_mod in modules_queried:
                    if not sorted_by_module.has_key(rand_mod):
                        sorted_by_module[rand_mod] = dict()
                    sorted_by_module[rand_mod][sttc.testcase.name] = sttc
        else:
            if rand_mod in modules_queried:
                if not sorted_by_module.has_key(rand_mod):
                    sorted_by_module[rand_mod] = dict()
                sorted_by_module[rand_mod][sttc.testcase.name] = sttc
            
    for k, v in sorted_by_module.items():
        print k, "---> Total TC: ", len(v)
        for tc in v:
            print "\t%s - id: %s" % (v[tc].testcase.name, v[tc].testcase.id)

    return sorted_by_module

def find_chassis_type(hw_csp_val, chassis_type_map):
    for chassisIP in chassis_type_map:
        if hw_csp_val.find(chassisIP) > -1:
            return chassis_type_map[chassisIP]
    
    return "Modules"

def add_vm_port_into_chassis_type_map(vm_port_map, chassis_type_map):
    for chassis_type in vm_port_map:
        for port_pair in vm_port_map[chassis_type]:
            port_list = port_pair.split(';')
            for port in port_list:
                portIP = port.replace("/1/1","")
                chassis_type_map[portIP] = chassis_type

    return chassis_type_map

def compare_module_list(orig_hw_list, query_hw_list,stc_version):
    output_list = []
    min_version = ''
    count = 0
    for minver in stc_version :
        min_version = minver
        
    for item in orig_hw_list:
        if item in query_hw_list:
            output_list.append(item)
        else:
            print "module -- ", item , " is not supported for stc version --> ", min_version
            count = count +1
    if count == 0:
        print"All the input hw modules are supported for given stc version -->", min_version
        
    return output_list            

##    print
##    print "orig hw length is ", len(orig_hw_list)
##    print orig_hw_list
##    print
##    print "output length is ", len(output_list)
##    print output_list 
##    print
    
def get_all_tags():
    all_tags = []
    result = fetch_all_tags()
    for sttc in result:
        all_tags.append(sttc.name)

    return all_tags

if __name__ == '__main__':

    #print 'sys.argv[0] =', sys.argv[0]             
    #pathname = os.path.dirname(sys.argv[0])        
    #print 'path =', pathname

    usage = 'usage: %prog [options]  '
    
    parser = optparse.OptionParser(usage=usage)
    
    parser.add_option('--tagsfile', dest='tagsFile',
              type='string',
              help='tags, File containing the CSV separated Tags')
    
    parser.add_option('--tags', dest='tagsStr',
              type='string', default='',
              help='directory, CSV separated Tags String')

    parser.add_option('--hw_chassis', dest='hw_chassis',
              type='string', default=DEFAULT_HW_CHASSIS,
              help='HW chassis to run test cases for.')

    parser.add_option('--hw_modules', dest='hw_modules',
              type='string', default=DEFAULT_HW_MODULES,
              help='HW modules to run test cases for.')

    parser.add_option('--hw_modules_mappings', dest='hw_modules_mappings',
              type='string', default=DEFAULT_HW_MODULES_MAPPINGS,
              help='HW modules mappings.')

    parser.add_option('--testsets', dest='testsets',
              type='string', default=DEFAULT_TESTSET,
              help='The test sets to run.')

    parser.add_option('--dbUser', dest='dbUser',
              type='string', default=DB_USER,
              help='Username to access database')
    
    parser.add_option('--dbPass', dest='dbPass',
              type='string', default=DB_PASS,
              help='Password to access database')
    
    parser.add_option('--dbHost', dest='dbHost',
              type='string', default=DB_HOST,
              help='Database host')
    
    parser.add_option('--dbName', dest='dbName',
              type='string', default=DB_NAME,
              help='Database Name')

    parser.add_option('--optimize_with_virtual', dest='optimize_with_virtual',
              action="store_true", default=False,
              help='Optimize test case executiong using virtual ports')    

    parser.add_option('--misc_script_directories', dest='misc_script_directories',
              type='string', default=DEFAULT_MISC_SCRIPT_DIR,
              help='Misc Script locations in perforce as a python dict')


    parser.add_option('--test_script_directories', dest='test_script_directories',
              type='string', default=DEFAULT_TEST_SCRIPT_DIR,
              help='Test Script locations in perforce, seperated by ,')


    parser.add_option('--chassis_slot_port', dest='chassis_slot_port',
              type='string', default=CHASSIS_SLOT_PORT,
              help='Chassis Slot Port')

    parser.add_option('--outputXML', dest='out_xml_file',
              type='string', default=DEFAULT_OUT_XML,
              help='Output xml file.')

    parser.add_option('--test-suite-name', dest='ts_name',
              type='string', default=DEFAULT_TESTSUITE_NAME,
              help='Name of the TestSuite')

    parser.add_option('--emails', dest='email_recp',
              type='string', default=DEFAULT_EMAILS,
              help='Email for report receipients.')

    parser.add_option('--email_server', dest='email_server',
              type='string', default=DEFAULT_EMAIL_SERVER,
              help='Email Server')

    parser.add_option('--agent_host_details', dest='agent_host_details',
              type='string', default=DEFAULT_agenthost_details,
              help='Thot Agent Host Details')

    parser.add_option('--query_testcases', dest='query_testcases',
              type='string', default='',
              help='Specify Test Cases to Query')

    parser.add_option('--query_testtypes', dest='query_testtypes',
              type='string', default='',
              help='Specify Test Types to Query')

    parser.add_option('--query_script_types', dest='query_scripttypes',
              type='string', default='',
              help='Specify Script Types to Query')

    parser.add_option('--query_mst', dest='query_market_segment',
              type='string', default='',
              help='Specify Market Segment to Query')

    parser.add_option('--min_stc_version', dest='query_min_stc_version',
              type='string', default='',
              help='Specify Min STC Version to Query')

    parser.add_option('--max_exec_time', dest='max_exec_time',
              type='string', default='',
              help='Specify Max test case execution time in seconds')

    parser.add_option('--priority', dest='query_priority',
              type='string', default='',
              help='Specify priority to Query')


    parser.add_option('--hw_details', dest='hw_details',
              type='string', default=DEFAULT_available_hw_info,
              help='Available HW to run Tests')

    parser.add_option('--agents_per_host', dest='max_agents_per_host',
              type='int', default=DEFAULT_AGENTS_PER_HOST,
              help='Maximum agents that can run in parallel on host')

    parser.add_option('--scripttimer', dest='script_timer',
              type='int', default='0',
              help='Maximum number of seconds for the test script to complete')

    parser.add_option('--serverconfig-database', dest='srv_cfg_database',
              type='string', default=DEFAULT_DATABASE_SERVER_CONFIG,
              help='Database Server Config details.')

    parser.add_option('--serverconfig-graphserver', dest='srv_cfg_graph',
              type='string', default=DEFAULT_GRAPH_SERVER_CONFIG,
              help='Graph Server Config details.')

    parser.add_option('--agentexit', dest='agent_exit',
              type='string', default=DEFAULT_AGENT_EXIT,
              help='Command Analysis Config details.')

    parser.add_option('--dbupdate', dest='db_update',
              type='string', default=DEFAULT_DB_UPDATE,
              help='DB Update Config details.')

    parser.add_option('--event_onstart', dest='event_onstart',
              type='string', default='',
              help='Details for the event on start point.')
    
    parser.add_option('--event_postsuite', dest='event_postsuite',
              type='string', default='',
              help='Details for the event on post suite point.')

    parser.add_option('--event_entrypoint', dest='event_entrypoint',
              type='string', default='',
              help='Details for the event entry point.')

    parser.add_option('--upgrade', dest='sw_upgrade',
              type='string', default='true',
              help='Software upgrade required?.')

    parser.add_option('--apupgrade', dest='ap_upgrade',
              type='string', default='true',
              help='Application upgrade required?.')

    parser.add_option('--fwupgrade', dest='fw_upgrade',
              type='string', default='true',
              help='Firmware upgrade required?.')

    parser.add_option('--smupgrade', dest='sm_upgrade',
              type='string', default='false',
              help='Suite Master application upgrade required?.')

    parser.add_option('--scpillog', dest='scpillog',
              type='string', default='false',
              help='Cookie log required?.')

    parser.add_option('--chassislog', dest='chassislog',
              type='string', default='false',
              help='Chassis log required?.')

    parser.add_option('--monitorportgroup', dest='monitorportgroup',
              type='string', default='false',
              help='Monitor Port Group required?.')

    parser.add_option('--smarttest_dbupdate', dest='smarttest_dbupdate',
              type='string', default=DEFAULT_SMARTTEST_DB_UPDATE,
              help='Smart Test Db update details.')

    parser.add_option('--suite_user', dest='suite_user',
              type='string', default=DEFAULT_SUITE_USER,
              help='Test Suite User details.')

    parser.add_option('--env_analysis', dest='env_analysis',
              type='string', default=DEFAULT_ENV_ANALYSIS,
              help='Test Suite Environment Analysis details.')

    parser.add_option('--commandanalysis', dest='command_analysis',
              type='string', default=DEFAULT_COMMAND_ANALYSIS,
              help='Agent Exit Config details.')

    parser.add_option('--test-results-dir', dest='test_results_dir',
              type='string', default=DEFAULT_TEST_RESULTS_DIR,
              help='Details for the testResultsDirectory')

    parser.add_option('--testcase-state', dest='testcase_state',
              type='string', default=str(STAPP_TESTCASE_ACTIVE),
              help='Comma Seperated list of test case state like active, inactive, etc')

    parser.add_option('--app_build_location', dest='app_bld_loc',
              type='string', default='',
              help='The location to the Application Build')

    parser.add_option('--app_build_version', dest='app_bld_version',
              type='string', default='',
              help='The version to the Application Build')

    parser.add_option('--virtual_server', dest='virtual_server',
              type='string', default=VIRTUAL_SERVER,
              help='The virtual server')

    parser.add_option('--virtual_server_options', dest='virtual_server_opts',
              type='string', default=VIRTUAL_SERVER_OPTS,
              help='The virtual server Options')

    parser.add_option('--optimize_for_diskspace', dest='opt_diskspace',
              action="store_true", default=OPT_FOR_DISKSPACE,
              help='Add options for optimising diskpace usage on agents')

    parser.add_option('--thgroup', dest='thgroup',
              type='string', default=DEFAULT_THOT_THGROUP,
              help='What to use for Thot THGroup attribute')

    parser.add_option('--config_file', dest='config_file',
              type='string', default='',
              help='Configuration File with all options')

    parser.add_option('--qmanager_off', dest='qmanager_off',
              action="store_true", default=False,
              help='qmanager fetaure disabled (no alloaction of virtual ports)')   

    parser.add_option('--lab_server_list', dest='lab',
              type='string', default='',
              help='LabServer IP List')

    parser.add_option('--Roma_MacAddr', dest='Roma_MacAddr',
              type='string', default='',
              help='Roma Mac Address List')

    parser.add_option('--APInfo', dest='APInfo',
              type='string', default='',
              help='AP information')

    parser.add_option('--avnext_controller', dest='avnext',
              type='string', default='',
              help='AVNEXT Controller IP')

    parser.add_option('--bll_par', dest='bll_par',
              action="store_true", default=False,
              help='Parsing bll information as a variable to the test script')  
 
    parser.add_option('--l4l7_par', dest='l4l7_par',
              action="store_true", default=False,
              help='Parsing l4l7 information as a variable to the test script')    

    parser.add_option('--misc_files_from_db', dest='misc_files_from_db',
              type='string', default='',
              help='Retrive Misc Files information from Database')
              
    parser.add_option('--rerunTCFAIL', dest='rerunTCFAIL',
              type='string', default='false',
              help='Rerun testcases whose verdicts are FAIL')
    parser.add_option('--rerunTCNA', dest='rerunTCNA',
              type='string', default='false',
              help='Rerun testcases whose verdicts are NA')

    config_file = "STR-Config.ini"
    cfg_options = dict()
    if config_file is not None and len(config_file) > 0:
        scfg_parser = SMTConfigParser()
        ok_read = scfg_parser.read(config_file)
        if len(ok_read) > 0:
            cfg_options.update(scfg_parser.as_dict().get('default'))
    
    if len(cfg_options) > 0:
        parser.set_defaults(**cfg_options)

    (options, args) = parser.parse_args()

    '''option_dict = vars(options)
    for x in list(option_dict.keys()):
        if option_dict[x] == [] or option_dict[x] is None:
            del option_dict[x]

    all_opt = cfg_options.update(option_dict)
    options._update_careful(all_opt)
    '''
    initDb(options)
    
    tag_str = options.tagsStr
    tags_list = tag_str.split(',')
    tags_list = filter(bool, tags_list)
    tags_list = list(set(tags_list)) #removing duplicate tags by creating set first.
    
    if options.tagsFile is not None and len(options.tagsFile) > 0:
        tags_list += parse_tags_file(options.tagsFile)
    
    if tags_list == None or not len(tags_list) > 0:
        tags_list_q = get_all_tags()
    else:
        tags_list_q = tags_list

    print 'Generating for tags: [%s]' % ', '.join(map(str, tags_list))
    min_ver_str = options.query_min_stc_version
    min_ver_list = min_ver_str.split(',')
    min_ver_list = filter(bool, min_ver_list)
    min_ver_list = list(set(min_ver_list)) #removing duplicate tc by creating set first.

    tm_list = options.hw_modules.split(',')
    tm_list = filter(bool, tm_list)
    if len(min_ver_list) > 0:
        print "updating  hw_module list"
        query_tm_list = filter_modules(tm_list,min_ver_list)
        tm_list = compare_module_list(tm_list,query_tm_list,min_ver_list)
    
    print 'Generating for test modules (empty means all.): [%s]' % ', '.join(map(str, tm_list))
    
    tm_mappings = ast.literal_eval(options.hw_modules_mappings)
    for tm in tm_mappings:
        for mo in tm_mappings[tm]:
            if not mo in tm_list:
                #delete it from list
                print 'delete'

    ts_list = options.testsets.split(',')
    ts_list = filter(bool, ts_list)
    print 'Generating for test sets: [%s]' % ', '.join(map(str, ts_list))

    chassis_type_map = {}
    if not len(options.hw_chassis) == 0:
        chassis_type_map = ast.literal_eval(options.hw_chassis)
        chassis_type_map = reverse_chassis_type_map(chassis_type_map)

    mfd_dict = ast.literal_eval(options.misc_script_directories)

    tcname_str = options.query_testcases
    tcname_list = tcname_str.split(',')
    tcname_list = filter(bool, tcname_list)
    tcname_list = list(set(tcname_list)) #removing duplicate tc by creating set first.

    tctype_str = options.query_testtypes
    tctype_list = tctype_str.split(',')
    tctype_list = filter(bool, tctype_list)
    tctype_list = list(set(tctype_list)) #removing duplicate tc by creating set first.

    sttype_str = options.query_scripttypes
    sttype_list = sttype_str.split(',')
    sttype_list = filter(bool, sttype_list)
    sttype_list = list(set(sttype_list)) #removing duplicate tc by creating set first.

    if not len(options.query_scripttypes) == 0:    
    AGENT_TYPE = sttype_list[0]
        print 'Script type --->',sttype_list[0]

    mst_str = options.query_market_segment
    mst_list = mst_str.split(',')
    mst_list = filter(bool, mst_list)
    mst_list = list(set(mst_list)) #removing duplicate tc by creating set first.

    
    max_exec_str = options.max_exec_time
    max_exec_list = max_exec_str.split(',')
    max_exec_list = filter(bool, max_exec_list)
    max_exec_list = list(set(max_exec_list)) #removing duplicate tc by creating set first.

    priority_str = options.query_priority
    priority_list = priority_str.split(',')
    priority_list = filter(bool, priority_list)
    priority_list = list(set(priority_list)) #removing duplicate tc by creating set first.
    
    #Test Case directory list.
    tsd_dict = ast.literal_eval(options.test_script_directories)
    for tsd in tsd_dict:   
    AGENT_TSD = tsd    
        print 'test_script_directories --->',tsd
    
    agenthost_details = ast.literal_eval(options.agent_host_details)
    
    available_hw_info = ast.literal_eval(options.hw_details)

    max_agents_per_host = options.max_agents_per_host

    tst_rslt_dir = ast.literal_eval(options.test_results_dir)
    
    gbl_script_timer = options.script_timer

    tc_state_str = options.testcase_state
    tc_state_list = tc_state_str.split(',')
    tc_state_list = filter(bool, tc_state_list)
    tc_state_list = list(set(tc_state_list)) #removing duplicate tags by creating set first.
    
    thgroup_to_use = options.thgroup
    
    AgentManager = ThotAgentManager()
    AgentManager.set_max_agents_per_agent_host(max_agents_per_host)
    AgentManager.set_available_agents(agenthost_details)


    email_re = options.email_recp.split(',')
    
    emails = dict()
    for email_recepient in email_re:
        em_name, em_email = email_recepient.split('=')
        emails[em_name] = em_email
    
    #runTest()
    
    scr_name = os.path.basename(__file__)
    generated_on = str(datetime.datetime.now())
    
    build_info = parse_bll_il_l4l7_versions()
    
    # Configure one attribute with set()
    test_suite = Element('TestSuite', { 'name': options.ts_name })  
    
    test_suite.append(Comment('Generated by ' + scr_name + ' on ' + generated_on))

    AgentManager.set_test_suite(test_suite)

    trd = SubElement(test_suite, 'TestResultsDirectory', tst_rslt_dir)

    if options.opt_diskspace == True:
        #Add option for repos
        cnt = 0
        repos = SubElement(test_suite, 'ResourceRepositories ', {})
        for agent in agenthost_details:
            agt = agenthost_details.get(agent)
            cnt += 1
            attrs = {'id': "rp%s" % (cnt) , 'hostname' : agt['hostname'],
                     'root': '/home/thot/thot_repo', 'type' : 'perforce',
                     'p4WS' : "thot_%s" % (agt['hostname'])}
            rep = SubElement(repos,'Repo',attrs)
            SubElement(rep, 'SubDir', {'name' : '.',
                                       'source' : AGENT_TSD
                                       })

    tc_suite_setup = SubElement(test_suite, 'Setup',
                                { 
                                 'enabled': options.sw_upgrade,
                                })

    tc_suite_setup_ap = add_setup_application(tc_suite_setup,options.ap_upgrade)
    
    
    add_setup_application_hosts(tc_suite_setup_ap, agenthost_details)

    if options.sm_upgrade == 'true': 
          add_setup_application_sm(tc_suite_setup_ap)

    if options.qmanager_off: 
          VIRTUAL_TAG = 'stcv-qemu-x'
    

    tc_suite_setup_fw = SubElement(tc_suite_setup, 'FirmwareDownload',
                                {'enabled': options.fw_upgrade,
                                 'platform': 'windows'
                                })


    tc_suite_setup_fw_il = add_setup_il(tc_suite_setup)
    
    chassis_list = parse_csp_to_chassis(available_hw_info)
    
    add_setup_il_chassis(tc_suite_setup_fw, chassis_list)

    add_setup_hardwarelistupdate(tc_suite_setup)

    #Add Notification
    pp = pprint.PrettyPrinter(indent=4)
    #pp.pprint(emails)

    # noti = add_notification_emails(test_suite, emails)
    # add_email_server_to_notification(noti, options.email_server)
    # add_format_to_notification(noti)
    
    if (not len(options.srv_cfg_database) == 0) and (not len(options.srv_cfg_graph) == 0):
        srv_cfg = SubElement(test_suite, 'ServerConfig')
    
    if not len(options.srv_cfg_database) == 0:
        srv_cfg_database = ast.literal_eval(options.srv_cfg_database)
        srv_db = SubElement(srv_cfg, 'Database', srv_cfg_database)

    if not len(options.srv_cfg_graph) == 0:
        srv_cfg_graph = ast.literal_eval(options.srv_cfg_graph)
        gsrv_db = SubElement(srv_cfg, 'GraphServer', srv_cfg_graph)

    grp_report = SubElement(test_suite, 'GroupReport',
                                { 'emailEnabled': 'false',
                                  'GroupOrder' : "TH_alphabetical"
                                })

    if not len(options.env_analysis) == 0:
        db_ea = ast.literal_eval(options.env_analysis)
        env = SubElement(test_suite, 'EnvAnalysis', db_ea)
        
    if not len(options.suite_user) == 0:
        db_su = ast.literal_eval(options.suite_user)
        usr = SubElement(test_suite, 'User', db_su)

    if not len(options.agent_exit) == 0:
        agent_exit = ast.literal_eval(options.agent_exit)
        agnt_ext = SubElement(test_suite, 'AgentExit', agent_exit)

    if not len(options.command_analysis) == 0:
        cmd_analysis = ast.literal_eval(options.command_analysis)
        cmd_ana = SubElement(test_suite, 'CommandAnalysis', cmd_analysis)

    if not len(options.db_update) == 0:
        db_up = ast.literal_eval(options.db_update)
        db_up_el = SubElement(test_suite, 'DBUpdate', db_up)

    if not len(options.smarttest_dbupdate) == 0:
        db_sm_up = ast.literal_eval(options.smarttest_dbupdate)
        db_sn_up_el = SubElement(test_suite, 'STCEngResultsDBUpdate', db_sm_up)

    if (not len(options.event_entrypoint) == 0):
        entpnt = ast.literal_eval(options.event_entrypoint)
        evnt_entpnt = SubElement(test_suite, 'Event', entpnt)

    if (not len(options.event_postsuite) == 0):
        event_str = options.event_postsuite
        event_list = event_str.split(';;')
        for event_item in event_list:
            entpnt = ast.literal_eval(event_item)
            evnt_entpnt = SubElement(test_suite, 'Event', entpnt)

    
    if (not len(options.event_onstart) == 0):
    event_str = options.event_onstart
        event_list = event_str.split(';;')
        for event_item in event_list:
            entpnt = ast.literal_eval(event_item)
            evnt_entpnt = SubElement(test_suite, 'Event', entpnt)


    icnt = SubElement(test_suite, 'iCentralUpdate', 
                                { 'enabled': 'false',
                                })

    unique_testcases_to_run = fetch_test_scripts_list(tags_list, tm_list, ts_list, testcases=tcname_list, testtypes=tctype_list, scripttypes=sttype_list, mstlist=mst_list,     minverlist=min_ver_list, maxexeclist=max_exec_list, prioritylist=priority_list)

    print "Total test cases found: %s" % len(unique_testcases_to_run)
    
    sorted_testcases = sort_test_scripts_by_module(unique_testcases_to_run, tm_list)    

    print "Total SORTED test modules found: %s" % len(sorted_testcases)

    #Virtual Server Opt.
    v_svr_opt = ast.literal_eval(options.virtual_server_opts)
    
    vms = VmManager(id=v_svr_opt.get('id','smarttest'), url=options.virtual_server)

    VIRTUAL_TAG = v_svr_opt.get('virtual_tag','stcv-qemu')

    if options.qmanager_off: 
          VIRTUAL_TAG = 'stcv-qemu-x'
 
    print "VIRTUAL_TAG is -->  {0}".format(VIRTUAL_TAG)

    equip_provs = {}
    if VIRTUAL_TAG in sorted_testcases:
        print " starting equip_provs function" 
        equip_provs = provision_equip(vms, len(sorted_testcases[VIRTUAL_TAG]), max_ports=v_svr_opt.get('max_port_pairs',0),group_size=v_svr_opt.get('group_size',2),vm_mem=v_svr_opt.get('vm_mem', None), cores=v_svr_opt.get('cores', None) )
        print(equip_provs)
    available_hw_info = dict(available_hw_info.items() + equip_provs.items())
    chassis_type_map = add_vm_port_into_chassis_type_map(equip_provs, chassis_type_map)
    modules = fetch_all_modules()
    module_dict = {}
    for module in modules:
        module_dict[module.name]=module
        
    

    for hw in sorted_testcases:
        if hw in available_hw_info.keys():
            hw_csp_idx = 0
            tcs = sorted_testcases[hw]
            hw_csp = available_hw_info[hw]
            available_port_cnt = len(hw_csp)
            total_test_scripts = len(tcs)
            if available_port_cnt == 0:
                continue
            tcs_list = []
            for val in tcs.itervalues():
                tcs_list.append(val)
            tc_chunks = chunks (tcs_list, available_port_cnt)
            for (agent_num, tc_chunk) in enumerate(tc_chunks):
                if not len(tc_chunk):
                    continue
                hw_csp_val = hw_csp[hw_csp_idx]
                agent_name = "%s-%s" % (hw , hw_csp_idx)
                chassis_type = find_chassis_type(hw_csp_val, chassis_type_map)
                if module_dict[hw].rerun_on_not_pass:
                    agent_info = {'name' : agent_name, 'chassisType' : chassis_type, 'moduleType': hw, 'rerunTCFAIL': options.rerunTCFAIL, 'rerunTCNA': options.rerunTCNA}
                else:
                    agent_info = {'name' : agent_name, 'chassisType' : chassis_type, 'moduleType': hw}
                tc = AgentManager.add_new_agent(agent_info)
                prepare_test_agent(tc,options.opt_diskspace,hw_csp_val,options.scpillog,options.monitorportgroup,options.chassislog)
                add_test_scripts(tc, tc_chunk, hw_csp_val, options.bll_par, options.l4l7_par, build_info['bll'], build_info['l4l7'], options.lab, options.misc_files_from_db,options.avnext,options.Roma_MacAddr,options.APInfo)
                hw_csp_idx += 1

        #Handle the Virtual Ports

    print prettify(test_suite, options.out_xml_file)
    print "Done Generating"
