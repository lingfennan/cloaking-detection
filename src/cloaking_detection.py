import sys, getopt
import simhash
from threading import Thread
from html_simhash_computer import Html_Simhash_Computer
from utils.learning_detection_util import load_observed_sites, write_proto_to_file, read_proto_from_file, valid_instance
from utils.thread_computer import ThreadComputer
import utils.proto.cloaking_detection_pb2 as CD

class CloakingDetection(object):
	def __init__(self, learned_sites):
		if valid_instance(learned_sites, CD.LearnedSites):
			self.leanred_sites = learned_sites

	def is_cloaking(self, observation):
		valid_instance(observation, CD.Observation)
			
	def detect(self, observed_sites):
		valid_instance(observed_sites, CD.ObservedSites)
		load_observed_sites(observed_sites)

def main(argv):
	has_function = False
	help_msg = 'cloaking_detection.py -f <function> [-i <inputfile>], valid functions are compute'
	try:
		opts, args = getopt.getopt(argv, "hf:i:", ["function=", "ifile="])
	except getopt.GetoptError:
		print help_msg
		sys.exit(2)
	for opt, arg in opts:
		if opt == '-h':
			print help_msg
			sys.exit()
		elif opt in ("-f", "--function"):
			function = arg
			has_function = True
		elif opt in ("-i", "--ifile"):
			inputfile = arg
		else:
			print help_msg
			sys.exit(2)
	if not has_function:
		print help_msg
		print 'Testing'
		test()
		sys.exit()
	if function == 'compute':
		site_list_filenames = [inputfile]
		compute(site_list_filenames)
	else:
		print help_msg
		sys.exit(2)

if __name__ == "__main__":
	main(sys.argv[1:])

