try:
	import requests
	import sys
	import os
	import optparse
	from requests import Request, Session
	from threading import *
except ImportError, e:
    print "Import error in %s : %s" % (__name__, e)
    import sys
    sys.exit()

def logger_debug(logger, message):
    if logger is not None:
        logger.debug(message)

# This method verifies if the parameters filled in by the user are correct in terms of #
# type and value range.																   #
def checkParameters(options):
	if not os.path.isfile(options.fileName):
		print "[-] " + options.fileName + " does not exist. \n"
		exit(0)
	if not os.access(options.fileName, os.R_OK):
		print "[-] " + options.fileName + " access denied. \n"
		exit(0)
	if options.nTimes and options.parallel:
		if options.nTimes < options.parallel:
			print '[-] the parallelism can not be greater than the number of requests'
			exit(0)
		if options.nTimes <= 0 or options.parallel <= 0:
			print '[-] Numbers below or equal to 0 are not allowed as requests or parallelism value'
			exit(0)
	elif options.nTimes:
		if options.nTimes <= 0:
			print '[-] Numbers below or equal to 0 are not allowed as number of request value'
			exit(0)
	elif options.parallel:
		print '[-] Parallelism value found with no number of request specified'
		exit(0)
	return True
		
# Function to parse the command line. It will return the options parsed  or exit if some #
# problem has been found during the arguments parsing or its checking                    #
def parseInput():
	try:
		parser = optparse.OptionParser("usage: requester.py -f,--file <request_file> [-n,--nRequest <number of times>] [-p,--parallel <threads in parallel>]\
[-P,--proxy <IP_addr:port>]")
		parser.add_option('-f', '--file', dest='fileName', type='string', help='specify the file containing the raw request')
		parser.add_option('-n', '--nRequest', dest='nTimes',type='int', help='specify how many times do you want to send the request')
		parser.add_option('-p', '--parallel', dest='parallel',type='int', help='specify how many threads do you want to run in parallel')
		parser.add_option('-P', '--proxy', dest='proxy',type='string', help='specify a Proxy to send the request through')
		(options, args) = parser.parse_args()
		if not options.fileName:
			print parser.usage
			exit(0)
		if checkParameters(options):
			return options
		else:
			print '[-] Error detected in the arguments'
			exit(0)
	except:
		print '[-] Exception parsing arguments'
		exit(0)

# This method will create a request from a fileName. The fileName parameter should have  #
# a valid path and the file content should be compliant with the Burp Suite or ZAP export#
# request format. Both Proxies provide the hability to extract a Request to a File. This #
# function will parse the File and Contruct a Request Object with the content.           #
def createRequestFromFile(fileName):
	try:
		lines = [line.strip() for line in open(fileName)]
		method = lines[0].split(' ')[0]
		url = lines[0].split(' ')[1]
		headers = {}
		content = {}
		inHeaders = True
		for line in lines[1:]:
			if not line:
				inHeaders = False
				continue
			if inHeaders:
				(key, value) = line.split(': ')
				headers.update({key:value})
			else:
				parameters = line.split('&')
				for parameter in parameters:
					(paramName, paramValue) = parameter.split('=')
					content.update({paramName:paramValue})
		request = Request(method,url,data=content,headers=headers)
		return request
	except:
		print '[-] Exception creating request from file'
		exit(0)

# This method will send a Request previously constructed from a File #	
screenLock = Semaphore(value=1)
def sendRequest(request,freeSlot,proxies):
	try:
		s = Session()
		prepRequest = s.prepare_request(request)
		resp = s.send(prepRequest,proxies=proxies)
		screenLock.acquire()
		print '[+] Request ended with code ' + str(resp.status_code)
		freeSlot.set()
	except:
		screenLock.acquire()
		print '[-] Request ended with errors'
		freeSlot.set()
	finally:
		screenLock.release()

# This method is designed to run all the Threads in Parallel taking into account the #
# parameters coming from the user command line										 #
def runThreads(nTimes, parallelThreads, proxy, request):
	try:
		if not nTimes:
			print '[i] Number of Request not Specified, 1 request will be send'
			nTimes = 1
		if not parallelThreads: 
			print '[i] Number of parallel Threads not specified, maximum parallelism established to 200 Threads'
			if nTimes < 200:
				parallelThreads = nTimes
			else:
				parallelThreads = 200
		if not proxy:
			print '[i] No proxy was found'
			proxies = None
		else:
			print '[i] Running requests through the proxy ' + proxy
			proxies = {'http':'http://' + proxy, 'https':'https://' + proxy}			
		print '[+] Running ' + str(nTimes) + ' Requests with a concurrence degree of ' + str(parallelThreads)		
		threadPool=[]
		freeSlot = Event() # necessary to coordinate the Threads
		for nThread in range(0,parallelThreads):
			threadPool.append(Thread(target=sendRequest, args=[request,freeSlot,proxies]))
		for nThread in range(0,parallelThreads):
			threadPool[nThread].start()
		remainTimes = nTimes - parallelThreads
		newThreadPool=[]
		for newThreads in range(0,remainTimes):
			freeSlot.wait()
			newThreadPool.append(Thread(target=sendRequest, args=[request,freeSlot,proxies]))
			newThreadPool[newThreads].start()
	except:
		print '[-] Error running the Treads'
		exit(0)

def main():
	parameters = parseInput()
	request = createRequestFromFile(parameters.fileName)
	runThreads(parameters.nTimes, parameters.parallel, parameters.proxy, request)
	
if __name__ == '__main__':
	main()
