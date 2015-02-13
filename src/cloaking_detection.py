"""
How to use:
python cloaking_detection.py -f detect -i <inputfile> -l <learnedfile> [-r <min_radius> -n <std_constant>, -t <simhash_type> default to TEXT]

python cloaking_detection.py -f evaluate -i <inputfile> -l <learnedfile> -e <expectedfile> [-t <simhash_type>]

"""

import numpy as np
import sys, getopt, math
import simhash
from threading import Thread
from html_simhash_computer import HtmlSimhashComputer
from utils.learning_detection_util import write_proto_to_file, read_proto_from_file, valid_instance, average_distance, centroid_distance, sites_file_path_set
from utils.learning_detection_util import intersect_observed_sites
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

	def _inconsistent_coefficient_detection(self, site_name, ob_simhash):
		"""
		@parameter
		site_name: site name of observation
		ob_simhash: simhash of observation
		@return
		True if the site is learned and this observation is not seen,
		o.w. False
		"""
		if not site_name in self.learned_sites_map:
			# If current site is not learned, return False.
			return False
		for pattern in self.learned_sites_map[site_name]:
			try:
				dist = centroid_distance(pattern, ob_simhash)
			except:
				raise Exception("You probably used ObservedSites as LearnedSites")
			if len(pattern.link_heights) > 0:
				link_heights = [link_height for link_height in
						pattern.link_heights]
				link_heights.append(dist)
				link_heights = np.array(link_heights)
				y_k_1 = np.mean(link_heights)
				y_k_2 = np.std(link_heights)
				z_k_3 = dist - self.detection_config.min_radius
				thres = self.detection_config.inconsistent_coefficient
				if (z_k_3 - y_k_1) / y_k_2 < thres:
					return False
			else:
				thres = self.detection_config.min_radius
				if dist < thres:
					return False
		return True
	
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
			# dist = average_distance(pattern, ob_simhash), deprecated
			try:
				dist = centroid_distance(pattern, ob_simhash)
			except:
				raise Exception("You probably used ObservedSites as LearnedSites")
			# less or equal, have equal because std may be zero.
			# if dist <= pattern.mean + self.detection_config.std_constant * pattern.std:
			thres = pattern.mean + self.detection_config.std_constant * pattern.std
			if dist <= max(thres, self.detection_config.min_radius):
				return False 
		return True 

	def _gradient_descent_detection(self, site_name, ob_simhash):
		return True

	def _joint_distribution_detection(self, site_name, ob_simhash):
		"""
		@parameter
		site_name: site name of observation
		ob_simhash: simhash of observation
		@return
		True if the site is learned and this observation is not seen ow False
		"""
		if not site_name in self.learned_sites_map:
			return False
		prob_array = []
		for pattern in self.learned_sites_map[site_name]:
			dist = centroid_distance(pattern, ob_simhash)
			""" dist==0 is the centroid"""
			if dist==0:
				return False
			for point in pattern.cdf.point:
				if(int(math.ceil(dist-1)) == point.x): 
					"""point.count == 0 is the centroid"""
					#the prob is not belong to this pattern
					prob_array.append((pattern.size-point.count)/ float(pattern.size))

		prob_result = 0.0
		for p1 in prob_array:
			prob_tmp = p1
			for p2 in prob_array:
				if prob_array.index(p1)==prob_array.index(p2):
					continue
				prob_tmp = prob_tmp*(1.0-p2)
			prob_result += prob_tmp
		print prob_result
		if prob_result <=0.4:
			return True
		return False

	def _percentile_detection(self, site_name, ob_simhash):
		p = 'p' + str(self.detection_config.p)
		if not site_name in self.learned_sites_map:
			return False
		for pattern in self.learned_sites_map[site_name]:
			dist = centroid_distance(pattern, ob_simhash)
			# use percentile 97 for now
			if dist <= getattr(pattern.percentile, p):
				return False
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
		elif self.detection_config.algorithm == CD.DetectionConfig.JOINT_DISTRIBUTION:
			detection_algorithm = "_joint_distribution_detection"
		elif self.detection_config.algorithm == CD.DetectionConfig.PERCENTILE:
			detection_algorithm = "_percentile_detection"
		elif self.detection_config.algorithm == CD.DetectionConfig.INCONSISTENT_COEFFICIENT:
			detection_algorithm = "_inconsistent_coefficient_detection"
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
		cloaking_sites.config.CopyFrom(observed_sites.config)
		# iterate through all the URLs
		size = 0
		for observed_site in observed_sites.site:
			result = self.get_cloaking_site(observed_site)
			if result:
				cloaking_site = cloaking_sites.site.add()
				cloaking_site.CopyFrom(result)
				size += len(cloaking_site.observation)
		print "total site {0}".format(len(observed_sites.site))
		print "cloaking site {0}".format(len(cloaking_sites.site))
		"""
		for site in cloaking_sites.site:
			print site.name
		print "cloaking count"
		print size
		"""
		return cloaking_sites

def cloaking_detection(learned_sites_filename, observed_sites_filename, simhash_type,
		min_radius = 0, std_constant = 3, inconsistent_coefficient = 2):
	valid_instance(min_radius, float)
	valid_instance(std_constant, int)
	valid_instance(inconsistent_coefficient, float)
	detection_config = CD.DetectionConfig()
	# detection_config.algorithm = CD.DetectionConfig.JOINT_DISTRIBUTION
	# detection_config.algorithm = CD.DetectionConfig.NORMAL_DISTRIBUTION
	detection_config.algorithm = CD.DetectionConfig.INCONSISTENT_COEFFICIENT
	# detection_config.algorithm = CD.DetectionConfig.PERCENTILE
	detection_config.p = 99
	detection_config.min_radius = min_radius
	detection_config.std_constant = std_constant
	detection_config.inconsistent_coefficient = inconsistent_coefficient
	if simhash_type:
		if simhash_type.upper() == "DOM":
			detection_config.simhash_type = CD.DOM
		elif simhash_type.upper() == "TEXT":
			detection_config.simhash_type = CD.TEXT
		elif simhash_type.upper() == "TEXT_DOM":
			detection_config.simhash_type = CD.TEXT_DOM
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
	# evaluation(cloaking_sites, expected, total)
	# print cloaking_sites
	return cloaking_sites


def compute_metrics(detected, expected, total):
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
	detected_names = sites_name_set(detected)
	expected_names = sites_name_set(expected)
	detected_size = len(detected_names)
	true_total = len(expected_names)
	false_total = total - true_total
	true_positive = len(detected_names & expected_names)
	false_positive = detected_size - true_positive
	true_positive_rate = float (true_positive) / true_total
	false_positive_rate = float (false_positive) / false_total
	precision = float (true_positive) / detected_size
	recall = true_positive_rate
	rate = [true_positive_rate, false_positive_rate]
	pr = [precision, recall]
	return rate, pr

def sites_name_set(observed_sites):
	valid_instance(observed_sites, CD.ObservedSites)
	name_set = set()
	for site in observed_sites.site:
		name_set.add(site.name)
	return name_set

def remove_noise(cloaking_sites, noise_sites):
	valid_instance(cloaking_sites, CD.ObservedSites)
	valid_instance(noise_sites, CD.ObservedSites)
	new_observed_sites = CD.ObservedSites()
	noise_set = sites_name_set(noise_sites)
	for observed_site in cloaking_sites.site:
		if not observed_site.name in noise_set:
			new_observed_site = new_observed_sites.site.add()
			new_observed_site.CopyFrom(observed_site)
	new_observed_sites.config.CopyFrom(cloaking_sites.config)
	print "Before de-noise: {0}".format(len(cloaking_sites.site))
	print "After de-noise: {0}".format(len(new_observed_sites.site))
	return new_observed_sites

def evaluate(learned_sites_filename, observed_sites_filename, simhash_type,
		min_radius, std_constant, coefficient, expected_sites_filename,
		noise_sites_filename):
	cloaking_sites = cloaking_detection(learned_sites_filename,
			observed_sites_filename, simhash_type, min_radius = float(min_radius),
			std_constant = std_constant, inconsistent_coefficient = float(coefficient))
	expected_sites = CD.ObservedSites()
	read_proto_from_file(expected_sites, expected_sites_filename)
	observed_sites = CD.ObservedSites()
	read_proto_from_file(observed_sites, observed_sites_filename)
	noise_sites = CD.ObservedSites()
	read_proto_from_file(noise_sites, noise_sites_filename)

	filt_cloaking_sites = remove_noise(cloaking_sites, noise_sites)
	filt_observed_sites = remove_noise(observed_sites, noise_sites)
	total = len(filt_observed_sites.site)
	print compute_metrics(filt_cloaking_sites, expected_sites, total)


def evaluate_both(observed_sites_filename, text_detected_sites_filename,
		dom_detected_sites_filename, expected_sites_filename,
		noise_sites_filename):
	expected_sites = CD.ObservedSites()
	read_proto_from_file(expected_sites, expected_sites_filename)
	observed_sites = CD.ObservedSites()
	read_proto_from_file(observed_sites, observed_sites_filename)
	noise_sites = CD.ObservedSites()
	read_proto_from_file(noise_sites, noise_sites_filename)
	both_detected = intersect_observed_sites(text_detected_sites_filename,
			dom_detected_sites_filename)
	filt_cloaking_sites = remove_noise(both_detected, noise_sites)
	filt_observed_sites = remove_noise(observed_sites, noise_sites)
	total = len(filt_observed_sites.site)
	print compute_metrics(filt_cloaking_sites, expected_sites, total)

def main(argv):
	has_function = False
	help_msg = """cloaking_detection.py -f <function> [-i <inputfile> -l
		<learnedfile> -t <simhash_type> -r <min_radius> -n <std_constant> -c
		<coefficient][-i <testfile> -l <learnedfile> -e <expectedfile> -t
		<simhash_type> -r <min_radius> -n <std_constant> -c
		<coefficient>] [-i <totalfile> -l <detected_text_file> -e
		<expectedfile>], valid functions are detect, evaluate,
		evaluate_both"""
	try:
		opts, args = getopt.getopt(argv, "hf:i:l:e:t:r:n:c:",
				["function=", "ifile=", "lfile=", "efile=",
					"type=", "radius=", "constant=",
					"coefficient="])
	except getopt.GetoptError:
		print help_msg
		sys.exit(2)
	simhash_type = None
	min_radius = 0
	std_constant = 3
	coefficient = 1
	for opt, arg in opts:
		if opt == "-h":
			print help_msg
			sys.exit()
		elif opt in ("-f", "--function"):
			function = arg
			has_function = True
		elif opt in ("-i", "--ifile"):
			inputfile = arg
		elif opt in ("-l", "--lfile"):
			learnedfile = arg
		elif opt in ("-e", "--efile"):
			expectedfile = arg
		elif opt in ("-t", "--type"):
			simhash_type = arg
		elif opt in ("-r", "--radius"):
			min_radius = arg
		elif opt in ("-n", "--constant"):
			std_constant = arg
		elif opt in ("-c", "--coefficient"):
			coefficient = arg
		else:
			print help_msg
			sys.exit(2)
	if not has_function:
		print help_msg
		sys.exit()
	if function == "detect":
		cloaking_detection(learnedfile, inputfile, simhash_type,
				float(min_radius), int(std_constant),
				float(coefficient))
	elif function == "evaluate":
		noisefile = expectedfile + ".noise"
		evaluate(learnedfile, inputfile, simhash_type,
				float(min_radius), int(std_constant),
				float(coefficient), expectedfile, noisefile)
	elif function == "evaluate_both":
		noisefile = expectedfile + ".noise"
		textfile  = learnedfile
		domfile = textfile.replace("text", "dom")
		evaluate_both(inputfile, textfile, domfile, expectedfile, noisefile)
	else:
		print help_msg
		sys.exit(2)

if __name__ == "__main__":
	main(sys.argv[1:])

