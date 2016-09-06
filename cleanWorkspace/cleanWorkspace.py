#Author: Aaron Iniguez
######################################
import os
import optparse
import sys
import re
import subprocess
import xml.etree.ElementTree as ET
import xml.etree.ElementTree
from xml.dom.minidom import parse
import xml.dom.minidom
import tempfile

#get node xml file and look for the tag remoteFS(the root home directory of the node)
def setVariables(inputServer,inputcli_jar,username="ainiguez",password="Impossible123"):
    global server
    global cli_jar
    global authentication
    cli_jar = inputcli_jar
    server = inputServer
    authentication = " --username "+username+" --password "+password
def getRootDir(node):
    process = subprocess.Popen('java -Xmx2048m -jar '+cli_jar+' -s '+server+' get-node '+node+authentication,shell=True,stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    print "Getting Root Directory for node: "+node
    out,err = process.communicate()
    if err:
        print err
    try:
        e = xml.etree.ElementTree.XML(out)
        return e.find('remoteFS').text
    except:
        raise Exception("Couldn't find remoteFS tag in "+node+" xml file:"+server+"computer/"+node+"/config.xml")
def getJobNode(job):
    process = subprocess.Popen('java -Xmx2048m -jar '+cli_jar+' -s '+server+' get-job '+job+authentication,shell=True,stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    print "Getting node for job: "+job
    out,err = process.communicate()
    if err:
        print err
    try:
        e = xml.etree.ElementTree.XML(out)
    except:
        return getJobNode(job)
    try: 
        foundNode = e.find('assignedNode').text
        return foundNode
    except:
        return None
def getAllJobs(view):
    #get all the jobs
    process = subprocess.Popen('java -Xmx2048m -jar '+cli_jar+' -s '+server+' list-jobs "'+ view+'"'+authentication,shell=True, stderr=subprocess.PIPE,stdout=subprocess.PIPE)
    print "Getting all Jobs from view: "+view
    out,err = process.communicate()
    if err:
        print err
    jobs = out.split("\n")
    #remove last newline element
    jobs.pop()
    return jobs
def turnOnForceSync(job):
    temp_JobXml = tempfile.NamedTemporaryFile()
    #get the jobs xml config
    print "Enabling One Time Force Sync for job: "+job
    process = subprocess.Popen('java -Xmx2048m -jar '+ cli_jar +' -s '+server+' get-job '+job + ' > '+temp_JobXml.name+authentication,shell=True, stderr=subprocess.PIPE,stdout=subprocess.PIPE)
    out,err = process.communicate()
    if err:
        print err
    xmldoc = xml.dom.minidom.parse(temp_JobXml.name)
    #xml to be inserted that enables one time force synce
    updatedText = """
    <scm class="hudson.plugins.perforce.PerforceSCM" plugin="perforce@1.3.31">
	    <configVersion>2</configVersion>
		<p4Passwd></p4Passwd>
		<p4Port></p4Port>
		<p4Client></p4Client>
		<projectOptions>noallwrite clobber nocompress unlocked nomodtime rmdir</projectOptions>
		<p4SysDrive></p4SysDrive>
		<p4SysRoot></p4SysRoot>
		<p4Tool>p4</p4Tool>
		<useClientSpec>false</useClientSpec>
		<useStreamDepot>false</useStreamDepot>
		<forceSync>true</forceSync>
		<alwaysForceSync>false</alwaysForceSync>
		<dontUpdateServer>false</dontUpdateServer>
		<disableAutoSync>false</disableAutoSync>
		<disableChangeLogOnly>false</disableChangeLogOnly>
		<disableSyncOnly>false</disableSyncOnly>
		<showIntegChanges>false</showIntegChanges>
		<useOldClientName>false</useOldClientName>
		<createWorkspace>true</createWorkspace>
		<updateView>true</updateView>
		<dontRenameClient>false</dontRenameClient>
		<updateCounterValue>false</updateCounterValue>
		<dontUpdateClient>false</dontUpdateClient>
		<exposeP4Passwd>false</exposeP4Passwd>
		<wipeBeforeBuild>false</wipeBeforeBuild>
		<quickCleanBeforeBuild>false</quickCleanBeforeBuild>
		<restoreChangedDeletedFiles>false</restoreChangedDeletedFiles>
		<wipeRepoBeforeBuild>false</wipeRepoBeforeBuild>
		<firstChange>0</firstChange>
		<fileLimit>0</fileLimit>
		<excludedFilesCaseSensitivity>true</excludedFilesCaseSensitivity>
		<slaveClientNameFormat></slaveClientNameFormat>
		<lineEndValue>local</lineEndValue>
		<useViewMask>false</useViewMask>
		<useViewMaskForPolling>true</useViewMaskForPolling>
		<useViewMaskForSyncing>false</useViewMaskForSyncing>
		<useViewMaskForChangeLog>false</useViewMaskForChangeLog>
		<pollOnlyOnMaster>false</pollOnlyOnMaster>
	</scm>
	"""
    xmldoc1 = xml.dom.minidom.parseString(updatedText)
    insertItem = xmldoc1.getElementsByTagName("scm")[0]
    xmldoc.documentElement.replaceChild(insertItem,xmldoc.getElementsByTagName("scm")[0])
    #updated xml containing new inserted xml
    temp_UpdatedJob = tempfile.NamedTemporaryFile()
    f = open(temp_UpdatedJob.name,"w")
    f.write(xmldoc.toxml())
    f.close()
    process = subprocess.Popen('java -Xmx2048m -jar ' + cli_jar + ' -s '+server+' update-job '+job + ' < '+temp_UpdatedJob.name+authentication,shell=True, stderr=subprocess.PIPE,stdout=subprocess.PIPE)
    out,err = process.communicate()
    if err:
        print err
	#delete saved file
    temp_JobXml.close()
    temp_UpdatedJob.close()
    return
def getIlNodes(view):
    #get all the jobs
    jobs = getAllJobs(view)
    cleanjobs = []
    for job in jobs:
        #exclude some jobs
        if "_il" in job:
            matching = re.match(r'\S+_il_ci$',job)
            matching1 = re.match(r'\S+_il_ci_join$',job)
            matching2 = re.match(r'\S+_il_ftp_centralboot_packaging$',job)
            matching3 = re.match(r'\S+_il_chvm_rest_api$',job)
            if not (matching or matching1 or matching2 or matching3 or matching):
                cleanjobs.append(job)
    nodes = {}
    for job in cleanjobs:
        node = getJobNode(job)
        if node:
            nodes[job] = node
        else:
            nodes[job] = None
    return nodes
def deleteClientSpec(branchName):
    #cmd = "ls"
    #
    cmd = "export P4PORT=perforce.spirentcom.com:1666;export P4USER=scmbuild;for i in `p4 clients | grep "+branchName+" | grep release_il_ | grep -v _il_ci_| awk '{print $2}'`; do p4 -u p4admin -P SpirentSCM client -d -f $i;done"
    pipe = subprocess.Popen(cmd,stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,shell=True)
    out,err = pipe.communicate()
    if err:
        print err
def buildJob(job,parameters=None):
    if parameters:
        cmd = "java -Xmx2048m -jar "+ cli_jar + " -s "+ server+" build "+job+" -p "+parameters+authentication
    else:
        cmd = "java -Xmx2048m -jar "+ cli_jar + " -s "+ server+" build "+job+authentication
    print "Starting job " + job 
    pipe = subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE, shell=True)
    out, err = pipe.communicate()
    if err:
        print err
def cleanUpWorkspace(node):
    #check if node exists on the jenkins server
    cmd = "java -jar "+cli_jar+" -s "+server+" get-node "+node+authentication
    print "Checking if node exists: "+node
    pipe = subprocess.Popen(cmd,stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,shell=True)
    out,err = pipe.communicate()
    if err:
        print err
    if "No such node" in err:
        return
    # node exists so clean it up
    #
    command = "rm -rf "+getRootDir(node)+"/workspace/*"
    cmd = "sshpass -p spirent ssh -o StrictHostKeyChecking=no "+node+" \""+command+";\""
    pipe = subprocess.Popen(cmd,stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,shell=True)
    print "Cleaning node: "+node+" at "+getRootDir(node)
    out,err = pipe.communicate()
    if err:
        print err
def startIlJobs(view):
    jobs = getAllJobs(view)
    for job in jobs:
        matching = re.match(r'\S+_il_ci$',job)
        if matching:
            #
            buildJob(job)
            return
    raise Exception("*_il_ci job not found, cannot start")
def startBllJobs(view):
    #exclude *_bll_ci and *_bll_ci_join
    jobs = getAllJobs(view) 
    startJobs = []
    for job in jobs:
        if "_bll" in job: 
            matching = re.match(r'\S+_bll_linux_ci$',job)
            matching1 = re.match(r'\S+_bll_linux_x64_ci$',job)
            matching2 = re.match(r'\S+_bll_windows_ci$',job)
            if matching or matching1 or matching2:
                startJobs.append(job)
    for job in startJobs:
        #
        buildJob(job,'P4CLEANWORKSPACE=true')
def startUIJobs(view):
    jobs = getAllJobs(view)
    for job in jobs:
        matching = re.match(r'\S+_ui_ci$',job)
        if matching:
            #
            buildJob(job,'P4CLEANWORKSPACE=true')
    return
def main():
    curFileName = os.path.realpath(__file__).split("/")[-1]
    parser = optparse.OptionParser("usage: %prog [options] arg1 arg2 arg3")
    parser.add_option("-u", "--username", action = "store", type = "string", dest = "username",default="ainiguez", help="jenkins server username"  )
    parser.add_option("-p", "--password", action = "store", type = "string", dest = "password",default="Impossible123", help="jenkins server password"  )
    parser.add_option("-s", "--jenkinsserver", action = "store", type = "string", dest = "server_link", help="The jenkins server link"  )
    parser.add_option("-c", "--clijar",action = "store", type = "string", dest = "cli_jar",  help="The jenkins-cli jar location such as C:\Program Files (x86)\Jenkins\war\WEB-INF "  )
    parser.add_option("-v", "--jobview", action = "store", type = "string", dest = "job_view",default="All", help="The jenkins job view where jobs need updation"  )
    parser.add_option("-b", "--branchname", action = "store", type = "string", dest = "branch_name", help="The branch name"  )
    (options, args) = parser.parse_args()
    print"******* Input variables ********\n"
    for key,value in vars(options).iteritems():
        print key, ":", value
    print"************************************\n"
    if options.branch_name == None or options.server_link == None or options.cli_jar == None:
        print "Please enter arguments correctly: The branch name, the Jenkins server link, cli_jar location"
        print "Example:\npython "+curFileName+" -s http://jenkins-patch-02.cal.ci.spirentcom.com:8080/ -b 4.63_rel -c "+os.getcwd()
        sys.exit(1)
    elif "//" not in options.server_link or options.server_link.count(":") < 2:
        print "Malformed server link: Server link should look like: http://jenkins-rel.cal.ci.spirentcom.com:8080/"
    else:
        cli_jar = os.path.join(options.cli_jar, "jenkins-cli.jar")
        setVariables(options.server_link,cli_jar,options.username,options.password)
        if os.path.isfile(cli_jar):
            #IL jobs
            print "Geting all IL nodes for view: "+options.job_view
            print "-"*40
            nodes = getIlNodes(options.job_view)
            print "Cleaning up Workspace for all IL nodes: "
            print "-"*40
            for key,value in nodes.iteritems():
                cleanUpWorkspace(value)
            print "Deleting Client Specs"
            print "-"*40
            deleteClientSpec(options.branch_name)
            print "Starting IL jobs: "
            print "-"*40
            startIlJobs(options.job_view)
            #BLL jobs
            print "Starting BLL jobs: "
            print "-"*40
            startBllJobs(options.job_view)
            #UI jobs
            startUIJobs(options.job_view)
            #Packaging
            jobs = getAllJobs(options.job_view)
            for job in jobs:
                matching = re.match(r'\S+_il_centralboot_packaging',job)
                if matching:
                    #get its node
                    jobNode = getJobNode(job)
                    #clean up workspace
                    cleanUpWorkspace(jobNode)
                    #
                    turnOnForceSync(job)
        else:
            print "***Error: Couldn't find ", cli_jar
            sys.exit(1)  
if __name__ == "__main__":
    main()
