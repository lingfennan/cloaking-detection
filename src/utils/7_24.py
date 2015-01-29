# prototyping 7x24 website visits

import sys, getopt
# import crawl

def scheduler(methodName, websiteList):
	print methodName, websiteList
	print "this is the time"
	# getattr(crawl, methodName)(websiteList)


def main(argv):
	help_msg = "7_14.py -m <methodName> -l <websiteList>"
	try:
		opts, args = getopt.getopt(argv, "hl:m:", ["websiteList=", "methodName="])
	except getopt.GetoptError:
		print help_msg
		sys.exit(2)
	for opt, arg in opts:
		if opt == "-h":
			print help_msg
			sys.exit()
		elif opt in ("-l", "--list"):
			websiteList = arg
		elif opt in ("-m", "--method"):
			methodName = arg
		else:
			print help_msg
			sys.exit(2)
	scheduler(methodName, websiteList)
	
if __name__ == "__main__":
	main(sys.argv[1:])

