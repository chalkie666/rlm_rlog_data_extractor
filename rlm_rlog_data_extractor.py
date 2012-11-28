#! /usr/bin/env python

"""
 Unit: Imaris license server log data extraction
 Project: License server log data extraction
 Created: 12.08.2008, DJW
 Description:

 lm_rlog_data_extractor.py

 Copyright (C) 2008 MPI-CBG IPF

 License: GPL v3.

 This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
__author__ = "MPI-CBG IPF <http://www.mpi-cbg.de/>"
__version__ = "$Revision: 1.0 $"
__date__ = "$Date: 2005/01/13 13:42:03 $"

        

"""
python rlm log file parser / data extractor, Dan White MPI-CBG IPF

What does it need to do?:
parse a reprise license manager .rlog file from a rlm server for Imaris and do these things:
1) calculate time duration product "imarisbase" was used by each different host computer
    (identified by its network name or IP, which can be traced to a cost centre by admin)
2) Calculate number of genuine DENYs for imarisbase to see how much usage is prevented by limited license number. 
3) output as a csv for import into excel, which is human readable/understandable, semi colon delimited data. 


Design: use PyParsing for the parsing, much nicer and easier to edit grammar then using regex. Pyparsing lives at http://sourceforge.net/projects/pyparsing/

1) Define log file "grammar" BNF for pyparsing module to read for IN, OUT and DENY entries 
    a) What happens if pyparsing tries to read a line that isnt described? Handle exception with a try - except-continue method
    b) Allow non interesting fields to be ignored: Make grammar for all fields of OUT IN and DENY rlog entry lines, just in case - more future proof.  

2) Read log file in one go, and use readlines to get rlog entry lines. 
    a) pyparsing module uses BNF definitions for fields and returns a  python list containing raw parsed strings, 
    and also a dictionary as the last entry in the list, which has keys and values for all the fields in the rlog line,
    which makes it easy to fish out the desired values by using the keys. 
    Regular expressions make my eyes hurt, and they are hard to modify for new situations. 
    Pyparsing's use of BNF grammar is a nice way to do this more transparently and in a way that is much easier to modify later.  
    b) We must ignore line entries for wich we have no valid grammar description, and move on to the next one
    ie. when the first list item is not IN, OUT or DENY - use try - except-continue
    c) read sucessfully parsed lines as lists of strings (and the dictionary from .setResultsName), 
    into master lists containing all grabbed data strings for lines we want
    d) while pyparsing, one has the possibility to also change the data types from the parsed string to int or whatever, 
        can also edit the string here if we like. 
        eg a simple parse action to remove the opening and closing quotation marks, such as:
            quotedString.setParseAction( lambda t: t[0][1:-1] )
        We wanted to use setParseAction to turn the time and date strings into datetime objects...
        but datetime.strptime needs a string as the 1st argument not a ParseResults object... Hmmmm
            File "parse_reformat_time.py", line 25, in <lambda>
            date.setParseAction( lambda tokens: datetime.strptime(tokens, '%m/%d') )
            TypeError: strptime() argument 1 must be string, not ParseResults
        At the same time as making the lists, we can also make a dictionaries containing the same data.
        That's done using using .setResultsName("name") in the grammar definition, 
        and the dictionaries appear as the last item in each of the sublists for each successfully parsed rlog line. 
         
3) For each "host" having valid OUT lines for imarisbase, 
    find corresponding license IN lines, and calculate license out durations for each "host" 
    a) for each OUT, look for the IN with the same or closest datetime after the OUT's datetime, 
        which shares the same host and user and server_handle. 
        For item in main list - to iterate though all main-OUT-list items
            The dictionaries for each succesfull parsed rlog line list item contain:
                'time': [('14:11:52', 17)], 'date': [('07/28', 16)]
            so we should be able to fish them out with the date and time keys,
            then convert the strings into python datetime objects for doing time maths.  
    b) compare date and time of OUT and corresponding IN, find difference, use datetime module 
        - can do a datatime-datetime to get time duration license was out
    c) add license out duration result to a running total for license out duration for that host. 

4) Find DENY entries for imarisbase where last_attempt is not 0
    a) ignore DENYs where last_attempt is 0, these are invalid as the host looks again
    b) make a list of valid denys
    c) calculate number of valid DENYs - its just the len of the list!


5) Write .CSV file containing human / excel readable results
    a) Print out list of machine names with corresponding duration of license usage    
    b) use semicolon as delimiter as that works in excel
    c) at top of CSV file write the start and end of dates covered by log file?
    d) print number of valid denys for imaris base, so we know about license number insufficiency. 
    e) Other maths?



RLM Checkout entry  BNF:

The Grammar to use is defined in the rlmdocs online at 
http://www.reprisesoftware.com/RLM_Enduser.html
Appendix A - Reportlog File Format

Backus-Naur Form : meta syntax to describe context-free grammar of entries in our rlm log files
This one is upside down so it looks like you would write it in python, 
defining the most basic features first. 

digit                        ::= '0'..'9'
sec                          ::= digit+
min                          ::= digit+
hour                         ::= digit+
month                        ::= digit+
day                          ::= digit+
date                         ::= month'/'day
timeHHMM                     ::= hour':'min
timeHHMMSS                   ::= hour':'min':'sec
last_attempt                 ::= 0 | !0
product                      ::= imarisbase | !imarisbase
rlm-rlog-checkout-entry      ::= OUT product version pool_num user host "isv_def" count cur_use cur_resuse server_handle share_handle process_id "project" "requested_product" "requested_version" date timeHHMMSS EOL

(from rlm docs checkout entry format is
OUT product version pool# user host "isv_def" count cur_use cur_resuse server_handle share_handle process_id "project" "requested product" "requested version" mm/dd hh:mm:ss 
)

                        
RLM Checkin entry BNF is a bit different from checkout, fewer fields in the line, but we need same info which is also present

rlm-rlog-checkin-entry       ::= IN why product version user host "isv_def" count cur_use cur_resuse server_handle date timeHHMMSS

(from rlm docs checkin entry format is
IN why product version user host "isv_def" count cur_use cur_resuse server_handle mm/dd hh:mm:ss 
)



RLM license denial entry BNF again is different from checkout:

rlm-rlog-denial-entry        ::= DENY product version user host "isv_def" count why last_attempt date timeHHMM

(from rlm docs license denial entry format is
DENY product version user host "isv_def" count why last_attempt mm/dd hh:mm
)

NOTE:
The last_attempt parameter is 0 if the application will attempt another checkout, 
or non-zero if this is the last attempt it will make to check the license out. T
hus, denials with last_attempt set to 0 are not "true" denials of the license to the application, 
they are simply denials of the license at this license server. 
A report writer should only report application license denials when last_attempt is set to a non-zero value.

"""

""" Import the python modules we need. Note pyparsing might not be available by default on all systems, eg OS X and Win
so you might have to get it and install it on your system:
http://pyparsing.wikispaces.com/
"""

from pyparsing import Word, Literal, Combine, Optional, White, OneOrMore, oneOf, ParseException, nums, alphas, alphanums, hexnums, srange #pyparsing lives at http://sourceforge.net/projects/pyparsing/
from datetime import datetime, timedelta
from optparse import OptionParser  #use optparse for command line option parsing, ie. to define log file and output file names

"""  here is how to set the grammar to use functions on parsed strings, and also to set result names
could use labmda functions, groups, 
num = Word(nums)
date = Combine(num + "/" + num + "/" + num)

def validateDateString(tokens):
    try:
        time.strptime(tokens[0], "%m/%d/%Y")
    except ValueError,ve:
        raise ParseException("Invalid date string (%s)" % tokens[0])
date.setParseAction(validateDateString)

schoolName = OneOrMore( Word(alphas) )
schoolName.setParseAction( lambda tokens: " ".join(tokens) )
score = Word(nums).setParseAction(lambda tokens: int(tokens[0]))
schoolAndScore = Group( schoolName.setResultsName("school") + \
        score.setResultsName("score") )
gameResult = date.setResultsName("date") + schoolAndScore.setResultsName("team1") + \
        schoolAndScore.setResultsName("team2")
"""


""" basic grammars for building others - Word, nums, alphanums and alphas are already defined by pyparsing
"""
numtwodig = Word(nums, exact=2)     # exacly 2 digits
alphanum = Word(alphanums)          # a word consisting of any number of alphanumerical characters
doubleQuote = Literal('""')         # lirterally: ""

""" grammar for all fields in IN, OUT and DENY lines made up of above most basic grammar and other basic definitions
See the rlm manual for these definitions.
http://www.reprisesoftware.com/RLM_Enduser.html
Appendix A - Reportlog File Format
"""


product = Literal("imarisbase")                # we only count lines that are for the imarisbase module, other availible modules always follow
version = Combine( (Word(nums) + "." + Word(nums) ) )      # version should be something like 6.1
poolNum = Word(nums)                           # a number, is an internal server pool identifier.
user = Word(alphanums+"!@#$%^&*-_")   # | Literal("lmf user") this Literal doesnt work bacause of the space in it!  
                                        #username might be "lmf user" containing a space... but in fact seems to have underscore lmf_user 
                                        #even when there isnt one really when the user logs in. Maybe just 1 word, and might contain funny chars
#user = Word(alphanums+"!@#$%^&*-_") + Optional(White() + Literal("user") ) # this line matches "lmf user" and other names with spaces, but breaks script for some reason!
host = Word(alphanums+".-")                 # host might be host-name-here.mpi-cbg.de or MSWINHOST or labname-number-number or something else. 
isvDef = doubleQuote                            # currently unused so nothing between the 2 double quotes
count = Word(nums)                            #should be a number
curUse = Word(nums)                            #should be a number
curReuse = Word(nums)                            #should be a number
serverHandle = Word(hexnums)                            #should be a hexadecimal number a few digits long
shareHandle = Word(hexnums)                             #should be a hexadecimal number a few digits long
processId = Word(hexnums)                            #should be a hexadecimal number a few digits long
project = doubleQuote                            # currently unused so nothing between the 2 double quotes, but = RLM_PROJECT env var, max 32 alphas
requestedProduct = doubleQuote                            # currently unused so nothing between the 2 double quotes
requestedVersion = doubleQuote                            # currently unused so nothing between the 2 double quotes
date = Combine(numtwodig + "/" + numtwodig)                                # date should be as mm/dd
timeHHMMSS = Combine(numtwodig + ":" + numtwodig + ":" + numtwodig)        #time as hh:mm:ss
timeHHMM = Combine(numtwodig + ":" + numtwodig)                            #time as hh:mm:ss
whyIn = oneOf("1 2 3 4 5 6 7")       #srange("[1-7]") doesnt work?         #should be a number from 1-7
whyDeny = Literal("0") | Word(nums+"-")                                    # IS 0 or a negative number up to 2 digits. 
lastAttemptReal = Word( srange("[1-9]"))                            # 0 means it was a bogus deny since it tried again. Must be a non 0 number.


"""final big string list grammars to parse for, to get list objects for each IN, OUT and DENY line in rlog

here is what a valid IN line looks like:
IN 1 imarisbase 6.0 heisenberg_lab heisenberg-8-434 "" 1 0 0 55 05/26 11:32:55
and in our grammar it looks like:
IN why product version user host "isv_def" count cur_use cur_resuse server_handle mm/dd hh:mm:ss 

a valid out is
OUT imarisbase 6.0 9 heisenberg_lab heisenberg-8-434 "" 1 1 0 26e 26e 410 "" "" "" 06/16 10:57:52
OUT product version pool# user host "isv_def" count cur_use cur_resuse server_handle share_handle process_id "project" "requested product" "requested version" mm/dd hh:mm:ss 

deny is
DENY product version user host "isv_def" count why last_attempt mm/dd hh:mm

We use token.setResultsName("key") to make the key value dictionary for easily fishing results out later, 
much better thean indexing a list, which might change size if we change things later. 
Dictionary is not sensetive to that.  

We also use ( ) for long lines not \ because apparently it's better. 
"""

rlmRlogCheckoutEntry = ( Literal("OUT").setResultsName("checkedOut") + product.setResultsName("product") + 
    version.setResultsName("version") + 
    poolNum + user.setResultsName("user") + host.setResultsName("host") + 
    isvDef.setResultsName("isDef") + 
    count.setResultsName("count") + curUse + curReuse + serverHandle.setResultsName("serverHandle") + 
    shareHandle + processId + project + 
    requestedProduct + requestedVersion + 
    date.setResultsName("date") + timeHHMMSS.setResultsName("time") 
    )

rlmRlogCheckinEntry = ( Literal("IN").setResultsName("checkedIn") + whyIn + product.setResultsName("product") + 
    version.setResultsName("version") + 
    user.setResultsName("user") + host.setResultsName("host") + 
    isvDef.setResultsName("isDef") + 
    count.setResultsName("count") + curUse + curReuse + serverHandle.setResultsName("serverHandle") + 
    date.setResultsName("date") + timeHHMMSS.setResultsName("time")
    )
    
rlmRlogDenyEntry = ( Literal("DENY").setResultsName("denied") + product.setResultsName("product") + 
    version.setResultsName("version") + 
    user.setResultsName("user") + host.setResultsName("host") + isvDef.setResultsName("isDef") + 
    count.setResultsName("count")  + whyDeny.setResultsName("whyDeny") + 
    lastAttemptReal.setResultsName("lastAttemptReal") + 
    date.setResultsName("date") + timeHHMM.setResultsName("time") 
    )


"""
here we use optparse python module to make a standard unix like command line interface that does help and reads command line arguments.
"""

commandLineUsage = "usage: %prog -l LOGFILE -r RESULTS"   #use optparse module for command line option parsing for filenames
commandLineOptionParser = OptionParser(usage=commandLineUsage) # and for making the script command line usage help
                                          
commandLineOptionParser.add_option("-l", "--log", 
                                   action="store", type="string", dest="logfile",
                                   help="define name of input LOGFILE", metavar="LOGFILE")
commandLineOptionParser.add_option("-r", "--results", 
                                   action="store", type="string", dest="results",
                                   help="define name of file for RESULTS", metavar="RESULTS")
(commandLineOptions, args) = commandLineOptionParser.parse_args()  #parses the command line and puts filenames supplied in commandLineOptionParser.results and commandLineOptionParser.logfile
print commandLineOptions.logfile, "is the logfile"
print commandLineOptions.results, "is the results file"
print args, "are the left over command line option arguments. There should be none!"

if (commandLineOptions.logfile == None) or (commandLineOptions.results == None):
    commandLineOptionParser.error("you must give command line options: -l LOGFILE -r RESULTS") #check that both log file and results file names are specified on command line




""" here we set the absolute path to the imaris.rlog file, or just the file name if it's in the same dir.
We use .readlines to read a line at a time into the logic below"""


#rlogFile = open ( 'bitplane042009.rlog', 'r' )  #NB bitplance.rlog from summer 08 seems to contain some nonsense, eg second outs before first in, and server_handle mistakes?
rlogFile = open (commandLineOptions.logfile, 'r')
info = rlogFile.readlines()               

testlog = """\
you can put test rlog data here
just cut and pase from .rlog file, then change the pasrse statements from info to testlog
by uncomnenting iouyt the testlog lines, and commenting ourt the info lines. 
Or you can change the filename in the open statement above to whatever file name""".splitlines()



""" Here we parse line by line using parseString looking for INs, the PUT, then DENYs,
letting non matching grammar lines 
be ignored or print an exception mesage, then optionally print the list of INs, OUTs and DENYs matches

parse lines of the log files using grammars set above to get IN OUT and DENY lines

We use .splitlines to feed lines of log to pyparse grammar if we use test dat internal to the script,
we use .readlines for am external data file. 

We can use these methods foir parsing :
        
parseString
Applies the grammar to the given input text (eg. a readline read line)

scanString
Scans through the input text looking for matches; scanString is a generator function that returns the matched tokens, 
and the start and end location within the text, as each match is found.

searchString
A simple wrapper around scanString, returning a list containing each set of matched tokens within its own sublist.
(this might be a good one???)

transformString
Another wrapper around scanString, to simplify replacing matched tokens with modified text or replacement strings, 
or to strip text that matches the grammar.

Below we use parseString
use .append(thing) to append thing to a list of lists 
Each successfully parsed line of the log is a sublist within each of the three master lists. 
Each sublist contains two items:
    0) A list of strings which are the data matched from the sucessfully parsed rlog lines
    1) a dictionary of tokens/value pairs of the form 'date': [('07/28', 9)]
        where the value is a tuple of date then index number (alphabetical order number?)
        
Dictionary entries for each successfully parsed line look like:  'date': [('07/28', 9)]
with key names made using setResultsName in the grammar definitions. 

We can use the dictionaries later for finding the right information to do further processing on, 
instead of trying to find the right piece of info in a list by indexing etc. 
Should be more robust, as we dont have to rely on the order of info in the sublists,
which might change if we miodify the grammar etc. 
"""

""" parse input data for valid IN lines for imarisbase in imaris.rlog file line by line from .readlines
Lines have to match the grammar above exactly as defined by the variable rlmRlogCheckinEntry
"""
listOfCheckins = []
print "parsing rlog for IN lines for imarisbase"
#for line in testlog:
for line in info:
    try:
        checkin = rlmRlogCheckinEntry.parseString(line)
        listOfCheckins.append(checkin)
        print "found IN line in rlog for imarisbase"
    except ParseException,pe:     # catch lines that don't match the grammar. Option to print error message, or continue. 
        continue
        #print "Parsing exception - doesn't match grammar:", pe.msg
        #print line
        #print " "*(pe.col-1) + "^"


           
""" as above but look for OUTs
"""
listOfCheckouts = []
print "parsing rlog for OUT lines for imarisbase"
#for line in testlog:
for line in info:
    try:
        checkout = rlmRlogCheckoutEntry.parseString(line)
        listOfCheckouts.append(checkout)
        print "found OUT line in rlog for imarisbase"
    except ParseException,pe:
        continue
        #print "Parsing exception - doesn't match grammar:", pe.msg
        #print line
        #print " "*(pe.col-1) + "^"


     
"""  as above but look for DENYs
"""  

listOfDenys = []
print "parsing rlog for valid DENY lines for imarisbase"
#for line in testlog:
for line in info:    
    try:
        deny = rlmRlogDenyEntry.parseString(line)
        listOfDenys.append(deny)
        print "found DENY line in rlog for imarisbase"
    except ParseException,pe:
        continue
        #print "Parsing exception - doesn't match grammar:", pe.msg
        #print line
        #print " "*(pe.col-1) + "^"
      
        
"""option to print master lists of sucessfully parsed rlog lines for INs OUTs and DENYs"""
#print listOfCheckins  
print "This is the master list of successfully parsed .rolg lines for license OUTs:", listOfCheckouts  #these are our base for looking for the corresponding IN lines
#print listOfDenys


""" call dump() to return a string showing the token dictionary
which is nested in as the last item in the list from the last successful rlog line parse,
followed by a hierarchical listing of keys and values, 
for last line sucessfully parsed for IN, OUT and DENY"""

#print checkin.dump()
#print checkout.dump()
#print deny.dump()


""" 
For each "host" , ie. need to make a list of all the "hosts" that are in valid "OUT" "imarisbase" lines 
then iterate through IN lines to find the matching IN line, 
then calculate duration license was out, and running total of license out duration for that 'host' :
 
1) Make list of hosts that are in rlog file that have valid license OUT lines (contains module: 'imarisbase')
    if host IS NOT in hostlist, add host to hostlist
2) For each host in hostlist:
    Find valid OUT lines (contains module: 'imarisbase' ) for the current 'host'
    Find corresponding IN line (same 'host'  AND the first occuring equal or greater 'datetime' (AND 'serverHandle'? ))
    Calculate duration that license was out (IN datetime - OUT datetime)
    Add that duration to a running total duration for that host 
"""

""" Here we will find the valid hosts (OUT line contains contains product: 'imarisbase' and checkedOut: 'OUT')
"""


"""
this does not work... just add all hosts found

hostList = []
for outListEntry in listOfCheckouts:
        if outListEntry['host'] not in hostList:
            hostList.append( str(outListEntry['host'] ) )
print "Found computer host names that took a license:", hostList

"""


hostList = []  #start with empty list

for entry in listOfCheckouts:    #listOfCheckouts is the data list to get unique hosts from 
    
    if hostList == []: # this is the initialization check, you could also start off with newList = [oldList[0]] but I find this cleaner, just a matter of taste
        hostList.append(str(entry["host"])) # need something to iterate through in the list to start with!
        print "this is the first host in the hostList", hostList
        continue  # go to top of loop
    
    addCurrentHost = True # we will keep a flag to check if the current host must be added, 
                            #because appending directly to the listOfHosts list in the loop that follows will mess up the for loop
    
    for checkHost in hostList:
        print entry["host"], checkHost
        if entry["host"] == checkHost : addCurrentHost = False #if the key values match, its not a unique host, so add flag is False
        
    if addCurrentHost: # if this is true, then
        hostList.append(str(entry["host"]))   #append the current host to listOfHosts as a dictionary key value pair
        print "added host", entry["host"], "to the list of hosts"        
    else: continue

print "Found computer host names that took a license:", hostList





print "Extracting time and date info for imarisbase license check out durations for each computer host identified as having taken a license out"


"""Iterate through the hosts in the hostList, through outListEntries in ListOfCheckouts,
finding corresponding In and OUT lines by their identical 'user' 'host' (and 'serverHandle'?) values
and having the first encountered datetime of IN > OUT
Then find duration license was out for: subtract datetime of IN from OUT
and add that to a running total of duration of license out time for that host. 

The below code works, but it seems that serverHandle is not always unique to each OUT,
as in the big log file test data of summer 08, there are instances where one OUT matches with several INS... 
or even where the matching IN line has a different server_handle...

imaris bloke tells me that you can have more than 1 OUT to the same machine for running multiple instances of imaris
on the same computer at the same time but only using 1 license!!!!! 
So can have a second OUT to the same machine ith different server handle, and NO corresponding IN!!!
Well that screws up the whole thing!!!! 

Dear Dan,

The same license can be checked out several times by a user. This enables the user to start multiple copies of Imaris without using multiple 'seats' of the floating license.
So this is not a bug but a feature which gives additional value to the customers.

I hope this helps.

Best regards,

Dieter
dieter@bitplane.com
support@bitplane.com


Need to only use the first matching IN, so use a "break" in the if statement after it finds the first hit, 
otherwise we can get matching hits with much later times that make the total duration very large and wrong. 

an see a way around the multtiple OUTs to same machine for multiple imaris instances..
"""

"""convert date and time in all the 3 sets of dictionaires to datetime format
so can do time maths easily, eg:

from datetime import datetime
>>> datetime.strptime("2007-03-04 21:08:12", "%Y-%m-%d %H:%M:%S")
datetime.datetime(2007, 3, 4, 21, 8, 12)

We could do this at parse time with .setParseActions(some lambda function using datetime.strptime)?
but we are doing it later on here instead, just before the actual time duration calculation. 
"""

""" maybe the below could be made nicer using defs?"""


results = [] #make an empty list for the dictionaries containing the duration results for each host, outside the for loop!

for theHost in hostList:
    print "marker 1, looking for lines for", theHost
    hostDurationRunningTotal = timedelta() # declare variable here, outside for loop, for running total duration as a datetime.timedelta 
    for outListEntry in listOfCheckouts:     # for liop irterating through all the hists in he list of hosts
        #print "marker 2, seeing if outListEntry contains ", theHost
        if outListEntry['host'] == theHost:
            outDateStamp = str(outListEntry['date'] )   # get the date info from the dictionalry from the matching line
            #print outDateStamp
            #outDateStampStrp = datetime.strptime(outDateStamp, "%m/%d"  )
            #print outDateStampStrp

            outTimeStamp = str(outListEntry['time'] ) # get the date info from the dictionary from the matching line
            #print outTimeStamp
            #outTimeStampStrp = datetime.strptime(outTimeStamp, "%H:%M:%S" )
            #print outTimeStampStrp
    
            outDateTimeStamp = outDateStamp + outTimeStamp   # concatenate date and time strings together in one string
            #print outDateTimeStamp
            outDateTimeStampStrp = datetime.strptime(outDateTimeStamp, "%m/%d%H:%M:%S" )  # use .strptime to make a datetime object from the parsed string
            print outDateTimeStampStrp, theHost
        #else:
            #continue  

            
                                      
            for inListEntry in listOfCheckins:    # for loop iterating through all the inListEntries checkin master list
                #print "marker 3 looking at inList Entry"
                inDateTimeStampStrp = ( datetime.strptime( ( str(inListEntry['date'] ) + 
                                                             str(inListEntry['time'] ) ), "%m/%d%H:%M:%S" ) # do the INs datetime conversion here. 
                                      )
                if (
                    (inListEntry['host'] == theHost)   # check inlist entry line data for several matching values
                    and
                    (inListEntry['host'] == outListEntry['host'] )
                    and
                    #inListEntry['serverHandle'] == outListEntry['serverHandle']  #server_handle is not reliable, but should be. Is wroing if why is 2 (auto license in after imaris crash?)
                    #and                                                # if second instance of imaris is started on host, uses same license but diff server handle
                                                                        # and no matching IN line with that server handle is ever generated, 
                    inListEntry['user'] == outListEntry['user']
                    and 
                    inDateTimeStampStrp > outDateTimeStampStrp   # in datetime must be greater than out datetime!
                   ):
                    outInDuration = inDateTimeStampStrp - outDateTimeStampStrp  # calculate duration the license was out for. 
                    #print "marker 4, IN found for OUT, calculated duration"  
                    #print "the host name is", theHost
                    print "the single license out duration is", outInDuration
                    hostDurationRunningTotal = hostDurationRunningTotal + outInDuration   # add the license out duration to a running total duration for that host we are ciurrently looking at. 
                    #print "running total duration for ", theHost, "is", hostDurationRunningTotal 
                    break     # dont look for any more matching IN lines, the first one is the right one! 
                else:
                    #print "marker 5, non matching inListEntry"
                    continue
            
            #print "marker 6, finished scan of listOfCheckins"
            
        else:
            #print"marker 7, this outListEntry doesnt contain ", theHost
            continue
        
    hostResults = {'hostname': theHost, 'totalDuration': hostDurationRunningTotal}   # make a dictionary containing the host and total duration
    print "marker 8, these are the results for host:", theHost, str(hostResults['totalDuration'])
    
    results.append(hostResults)    # append the dictionary for each host to a list of dictionaries for all the hosts. 

print "marker 9, here are the unformatted results!", results


print "Writing human readable .csv formatted results of the imaris license server rlog file analysis to Imaris-rLog-results.csv and also print to screen:"


resultsFile = open(commandLineOptions.results, 'w+')    # open the results file in write mode
for resultsLine in results:                            # iterate through the results list and extract strings for printing and saving in the results file
    hostNameForLine = resultsLine['hostname']
    totDurForLine = resultsLine['totalDuration']
    resultLine = hostNameForLine + str(totDurForLine)
    print hostNameForLine, ";", totDurForLine
    resultsFile.write(hostNameForLine)
    resultsFile.write(";")                              # excel understands semi comon delimited data
    resultsFile.write( (str(totDurForLine) ) )
    resultsFile.write("\n")                             # a new line at the end of each line of data
  

"""Lastly we need to calculate the total number of valid DENYs"""
denyNumber = len(listOfDenys)                                     #simply the length of the valid denys list, number of items in the list. 
print "Valid imarisbase license denials detected ;", denyNumber
resultsFile.write("Valid imarisbase license denials detected ;")
resultsFile.write( str(denyNumber) )
resultsFile.write("\n")

resultsFile.close()     # its nice to close the file. 

print "Done! Have a nice time analysing the results!"

"""just a comment"""