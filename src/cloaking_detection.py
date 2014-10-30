import sys, getopt
import simhash
from threading import Thread
from html_simhash_computer import Html_Simhash_Computer
from utils.learning_detection_util import write_proto_to_file, read_proto_from_file, valid_instance
from utils.thread_computer import ThreadComputer
import utils.proto.cloaking_detection_pb2 as CD

class CloakingDetection(object):
	def __init__(self, detection_config, learned_sites):
		valid_instance(detection_config, CD.DetectionConfig)
		valid_instance(learned_sites, CD.LearnedSites)
		self.detection_config = detection_config
		self.leanred_sites = learned_sites
	
	def _normal_distribution_detection(self, observation):
		None

	def _gradient_descent_detection(self, observation):
		None

	def is_cloaking(self, observation):
		valid_instance(observation, CD.Observation)
		if self.detection_config.algorithm == CD.DetectionConfig.NORMAL_DISTRIBUTION:
			return _normal_distribution_detection(observation)
		elif self.detection_config.algorithm == CD.DetectionConfig.GRADIENT_DESCENT:
			return _gradient_descent_detection(observation)
			
	def detect(self, observed_sites):
		valid_instance(observed_sites, CD.ObservedSites)
		for observed_site in observed_sites.site:


def cloaking_detection(learned_sites_filename, observed_sites_filename):
	detection_config = CD.DetectionConfig()
	detection_config.algorithm = CD.DetectionConfig.NORMAL_DISTRIBUTION
	detection_config.std_constant = 3
	learned_sites = CD.LearnedSites()
	read_proto_from_file(learned_sites, learned_sites_filename)
	observed_sites = CD.ObservedSites()
	read_proto_from_file(observed_sites, observed_sites_filename)
	detector = CloakingDetection(detection_config, learned_sites)
	cloaking_sites = detector.detect(observed_sites)
	out_filename = observed_sites_filename + '.cloaking'
	write_proto_to_file(cloaking_sites, out_filename)

def main(argv):
	has_function = False
	help_msg = 'cloaking_detection.py -f <function> [-i <inputfile> -l <learnedfile>], valid functions are detect'
	try:
		opts, args = getopt.getopt(argv, "hf:i:l:", ["function=", "ifile=", "lfile="])
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
		elif opt in ("-l", "--lfile"):
			learnedfile = arg
		else:
			print help_msg
			sys.exit(2)
	if not has_function:
		print help_msg
		print 'Testing'
		test()
		sys.exit()
	if function == 'detect':
		cloaking_detection(learnedfile, inputfile)
	else:
		print help_msg
		sys.exit(2)

if __name__ == "__main__":
	main(sys.argv[1:])

