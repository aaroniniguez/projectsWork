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
dir_path = os.path.dirname(os.path.realpath(__file__))
import smtplib
from email.mime.text import MIMEText

def sendEmail(sender='sync@spirent.com', toList=['aaron.iniguez@spirent.com'], ccList=[], subject='', text=''):
    mail = MIMEText(text)
    mail['Subject'] = subject
    mail['From'] = sender
    mail['To'] = ", ".join(toList)
    mail['CC'] = ", ".join(ccList)
    s = smtplib.SMTP('smtprelay.spirent.com')
    s.sendmail(sender, toList, mail.as_string())
    s.quit()
def getResourceRepo(xml_file):
    print "Getting Resources"
    resources = {}
    xmldoc = xml.dom.minidom.parse(xml_file)
    #check if resourcerepositories tax exists
    if not xmldoc.getElementsByTagName("ResourceRepositories"):
        print "No ResourceRepositories in xml file"
        return resources    
    insertItem = xmldoc.getElementsByTagName("ResourceRepositories")[0]
    for child in insertItem.childNodes:
        if (child.attributes):
            hostname = child.attributes['hostname']
            p4WS = child.attributes['p4WS']
            resources[hostname.value] =p4WS.value
            print hostname.value, p4WS.value
    return resources
def checkForErrors(p4WS,logFile, errorSearch = []):
    for error in errorSearch:
        with open(logFile,"r") as f:
            for line in f:
                if error in line:
                    return True
    return False
#returns hostname if syncerror
def Sync(password, user, host, p4WS, perforceHost, perforceLocation, perforceUser, plinkloc):
    perforce = perforceLocation +" -s -p "+perforceHost+" -u "+perforceUser+" -c " + p4WS + " sync //"+p4WS+"/..."
    #windows
    if os.name == "nt":
        cmd = plinkloc+" -ssh "+host+" -l "+user+" -pw "+password+" \""+perforce+"\""
        process = subprocess.Popen(cmd,shell=True,stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    else:
        cmd = "sshpass -p "+password+" ssh -o StrictHostKeyChecking=no "+user+"@"+host+" \""+perforce+"\""
        process = subprocess.Popen(cmd,shell=True,stdin=subprocess.PIPE,stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    out,err = process.communicate()
    logfile = p4WS.replace(".cal.ci.spirentcom.com","")+".log"
    if not os.path.exists(dir_path+"/logs"):
        print "Creating logs directory "+dir_path+"/logs" 
        os.makedirs(dir_path+"/logs")
    print "\nSaving sync log:\n" ,logfile
    log_path = dir_path+"/logs/"+logfile
    f = open(log_path,"w")
    f.write(out)
    f.close()
    if checkForErrors(p4WS, log_path,["can't update"]):
        return p4WS
def main():
    curFileName = os.path.realpath(__file__).split("/")[-1]
    parser = optparse.OptionParser("usage: %prog [options] arg1 arg2 arg3")
    parser.add_option("--plink", action = "store", type = "string", dest = "plink_location", help="plink location",default="c:\plink")
    parser.add_option("-p", "--password", action = "store", type = "string", dest = "password", help="host password",default="thot123")
    parser.add_option("-u", "--user", action = "store", type = "string", dest = "user", help="host user",default="thot")
    parser.add_option("--perforcehost", action = "store", type = "string", dest = "perforce_host", help="perforce host",default="perforce.spirentcom.com:1666")
    parser.add_option("--perforceloction", action = "store", type = "string", dest = "perforce_location", help="perforce location",default="~/THoT/P4/p4")
    parser.add_option("--perforceuser", action = "store", type = "string", dest = "perforce_user", help="perforce user",default="scmthot")
    parser.add_option("--inputxml", action = "store", type = "string", dest = "xml_file", help="xml file")
    parser.add_option("--sendemail", action = "store", type = "string", dest = "email", help="Email of the person who will recieve error emails")
    (options, args) = parser.parse_args()
    print"******* Input variables ********\n"
    for key,value in vars(options).iteritems():
        print key, ":", value
    print"************************************\n"
    if options.xml_file == None or options.email ==None:
        print "Please enter an xml file and a email"
        print "Example:\npython "+curFileName+" --inputxml testFile.xml --sendemail aaron.iniguez@spirent.com"
        sys.exit(1)
    else: 
        hosts = getResourceRepo(options.xml_file)
        failures = []
        for host,p4WS in hosts.iteritems():
            errorSync = Sync(options.password, options.user, host, p4WS, options.perforce_host, options.perforce_location, options.perforce_user, options.plink_location)
            if errorSync:
                failures.append(errorSync)
        if len(failures) > 0: 
            sendEmail(toList=[options.email],subject = "Sync Failed",text="Sync Failure in:\n"+ "\n".join(failures))
if __name__ == "__main__":
    main()
