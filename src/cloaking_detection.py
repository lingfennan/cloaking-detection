import sys, getopt
import simhash
from threading import Thread
from html_simhash_computer import Html_Simhash_Computer
from utils.learning_detection_util import write_proto_to_file, read_proto_from_file, valid_instance, average_distance
from utils.thread_computer import ThreadComputer
import utils.proto.cloaking_detection_pb2 as CD

class CloakingDetection(object):
	def __init__(self, detection_config, learned_sites):
		valid_instance(detection_config, CD.DetectionConfig)
		valid_instance(learned_sites, CD.LearnedSites)
		self.detection_config = detection_config
		# load learned sites map, which maps site name to related patterns
		self.learned_sites_map = dict()
		for site in learned_sites.site:
			self.learned_sites_map[site.name] = site.pattern
	
	def _normal_distribution_detection(self, site_name, ob_simhash):
		"""
		@parameter
		site_name: site name of observation
		ob_simhash: simhash of observation
		@return
		True if the site is learned and this observation is not seen, o.w. False
		"""
		if not site_name in self.learned_sites_map:
			# If current site is not learned, return False.
			return False
		for pattern in self.learned_sites_map[site_name]:
			avg_dist = average_distance(pattern, ob_simhash)
			# less or equal, have equal because std may be zero.
			if avg_dist <= pattern.mean + self.detection_config.std_constant * pattern.std:
				return False 
		return True 

	def _gradient_descent_detection(self, site_name, observation):
		return True

	def get_cloaking_site(self, observed_site):
		"""
		Read observed_site and compare with learned sites. Return cloaking_site
		@parameter
		observed_site: observations of a site to be tested
		@return
		cloaking_site: cloaking observations of this site. None if no observations are cloaking
		"""
		valid_instance(observed_site, CD.SiteObservations)
		cloaking_site = CD.SiteObservations()
		if self.detection_config.algorithm == CD.DetectionConfig.NORMAL_DISTRIBUTION:
			detection_algorithm = "_normal_distribution_detection"
		elif self.detection_config.algorithm == CD.DetectionConfig.GRADIENT_DESCENT:
			detection_algorithm = "_gradient_descent_detection"
		else:
			raise Exception("Unknown detection algorithm!")
		has_cloaking = False
		for observation in observed_site.observation:
			if self.detection_config.simhash_type == CD.TEXT:
				ob_simhash = observation.text_simhash
			elif self.detection_config.simhash_type == CD.DOM:
				ob_simhash = observation.dom_simhash
			else:
				raise Exception("Detection config only supports simhash_type TEXT and DOM")
			if getattr(self, detection_algorithm)(observed_site.name, ob_simhash):
				if not has_cloaking:
					has_cloaking = True
					cloaking_site.name = observed_site.name
				cloaking_observation = cloaking_site.observation.add()
				cloaking_observation.CopyFrom(observation)
		if not has_cloaking:
			return None
		else:
			return cloaking_site
			
	def detect(self, observed_sites):
		valid_instance(observed_sites, CD.ObservedSites)
		cloaking_sites = CD.ObservedSites()
		for observed_site in observed_sites.site:
			result = self.get_cloaking_site(observed_site)
			if result:
				cloaking_site = cloaking_sites.add()
				cloaking_site.CopyFrom(result)
		return cloaking_sites

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

