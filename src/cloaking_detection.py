"""
How to use:
python -f detect -i <inputfile> -l <learned_sites> [-t <simhash_type>]
"""

import sys, getopt
import simhash
from threading import Thread
from html_simhash_computer import HtmlSimhashComputer
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
		# iterate through all the URLs
		for observed_site in observed_sites.site:
			result = self.get_cloaking_site(observed_site)
			if result:
				cloaking_site = cloaking_sites.site.add()
				cloaking_site.CopyFrom(result)
		return cloaking_sites

def cloaking_detection(learned_sites_filename, observed_sites_filename, simhash_type=None):
	detection_config = CD.DetectionConfig()
	detection_config.algorithm = CD.DetectionConfig.NORMAL_DISTRIBUTION
	detection_config.std_constant = 3
	if simhash_type:
		if simhash_type == "DOM":
			detection_config.simhash_type = CD.DOM
		elif simhash_type == "TEXT":
			detection_config.simhash_type = CD.TEXT
		elif simhash_type == "TEXT_DOM":
			# Essentially we want to combine DOM and TEXT,
			# but how to do that is still not decided yet.
			None
		else:
			raise Exception("Invalid simhash_type. Only DOM and TEXT are supported.")
	learned_sites = CD.LearnedSites()
	read_proto_from_file(learned_sites, learned_sites_filename)
	observed_sites = CD.ObservedSites()
	read_proto_from_file(observed_sites, observed_sites_filename)
	detector = CloakingDetection(detection_config, learned_sites)
	cloaking_sites = detector.detect(observed_sites)
	out_filename = observed_sites_filename + '.cloaking'
	write_proto_to_file(cloaking_sites, out_filename)

	# how to get this
	# evaluation(cloaking_sites, expected, total)
	print cloaking_sites

def file_path_set(observed_sites):
	valid_instance(detected, CD.ObservedSites)
	result = set()
	for site in observed_sites.site:
		for observation in site.observation:
			result.add(observation.file_path)
	return result

def evaluation(detected, expected, total):
	"""
	Evaluate the result and return two kind of measures.
	(1) True positive rate/False positive rate, this can be used to plot ROC curve.
	TPR/FPR is independent of test size.
	(2) Precision/Recall. This is dependent on test size.
	@parameter
	detected: detected cloaking sites
	expected: expected cloaking sites
	total: total number of sites tested
	@return
	rate, pr: rate is true positive rate and false positive rate, pr is precision and recall
	"""
	valid_instance(detected, CD.ObservedSites)
	valid_instance(expected, CD.ObservedSites)
	detected_files = file_path_set(detected)
	expected_files = file_path_set(expected)
	detected_size = len(detected_files)
	true_total = len(expected_files)
	false_total = total - true_total
	true_positive = len(detected_files & expected_files)
	false_positive = detected_size - true_positive
	true_positive_rate = (float) true_positive / true_total
	false_positive_rate = (float) false_positive / false_total
	precision = (float) true_positive / detected_size
	recall = true_positive_rate
	rate = [true_positive_rate, false_positive_rate]
	pr = [precision, recall]
	return rate, pr

def main(argv):
	has_function = False
	help_msg = 'cloaking_detection.py -f <function> [-i <inputfile> -l <learnedfile> -t <simhash_type>], valid functions are detect'
	try:
		opts, args = getopt.getopt(argv, "hf:i:l:t:", ["function=", "ifile=", "lfile=", "type="])
	except getopt.GetoptError:
		print help_msg
		sys.exit(2)
	simhash_type = None
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
		elif opt in ("-t", "--type"):
			simhash_type = arg
		else:
			print help_msg
			sys.exit(2)
	if not has_function:
		print help_msg
		print 'Testing'
		test()
		sys.exit()
	if function == 'detect':
		cloaking_detection(learnedfile, inputfile, simhash_type)
	else:
		print help_msg
		sys.exit(2)

if __name__ == "__main__":
	main(sys.argv[1:])

