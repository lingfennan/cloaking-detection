import sys, getopt
from learning_detection_util import read_proto_from_file, show_proto
import proto.cloaking_detection_pb2 as CD

def main(argv):
	help_msg = "show_proto.py -i <inputfile> -t <proto_type>"
	try:
		opts, args = getopt.getopt(argv, "hi:t:", ["ifile=", "type="])
	except getopt.GetoptError:
		print help_msg
		sys.exit(2)
	for opt, arg in opts:
		if opt == "-h":
			print help_msg
			sys.exit()
		elif opt in ("-i", "--ifile"):
			inputfile = arg
		elif opt in ("-t", "--type"):
			proto_type = arg
		else:
			print help_msg
			sys.exit(2)
	show_proto(inputfile, proto_type)

if __name__ == "__main__":
	main(sys.argv[1:])

