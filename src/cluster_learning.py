"""
How to use:
python cluster_learning.py -f compute -i <inputfile>
python cluster_learning.py -f learn -i <inputfile>
"""

import sys, getopt
import simhash
from threading import Thread
from html_simhash_computer import HtmlSimhashComputer
from utils.learning_detection_util import load_observed_sites, merge_observed_sites, write_proto_to_file, read_proto_from_file, valid_instance
from utils.learning_detection_util import HammingTreshold, KMeans, SpectralClustering, HierarchicalClustering
from utils.thread_computer import ThreadComputer
import utils.proto.cloaking_detection_pb2 as CD

class ClusterLearning(object):
	def __init__(self, cluster_config=None):
		if not cluster_config:
			self.cluster_config = None
		elif valid_instance(cluster_config, CD.ClusterConfig):
			self.cluster_config = cluster_config
	
	def compute_simhash(self, site_list_filenames, simhash_config):
		valid_instance(simhash_config, CD.SimhashConfig)
		observed_sites, path_list = load_observed_sites(site_list_filenames)  # Input is a list of site_list_filename
		simhash_computer = HtmlSimhashComputer(simhash_config)
		thread_computer = ThreadComputer(simhash_computer, 'compute_simhash', path_list)
		path_simhash_dict = dict()
		for p, s in thread_computer.result:
			path_simhash_dict[p] = s
		observed_sites.config.CopyFrom(simhash_config)
		for site in observed_sites.site:
			for observation in site.observation:
				if simhash_config.simhash_type in [CD.TEXT, CD.TEXT_DOM]:
					observation.text_simhash = path_simhash_dict[observation.file_path][0].value
				if simhash_config.simhash_type in [CD.DOM, CD.TEXT_DOM]:
					observation.dom_simhash = path_simhash_dict[observation.file_path][-1].value
		return observed_sites

	def learn(self, observed_sites_filenames, cluster_config=None):
		if (not cluster_config) and (not self.cluster_config):
			raise Exception("Cluster config missing")
		elif cluster_config and valid_instance(cluster_config, CD.ClusterConfig):
			self.cluster_config = cluster_config
		# learn the clusters
		observed_sites = merge_observed_sites(observed_sites_filenames)
		learned_sites = CD.LearnedSites()
		cluster_config.simhash_type = observed_sites.config.simhash_type
		for observed_site in observed_sites.site:
			# either TEXT or DOM can be handled now. TEXT_DOM is not supported.
			if cluster_config.algorithm.name == CD.Algorithm.HAMMING_THRESHOLD:
				result = HammingTreshold(cluster_config, observed_site)
			if cluster_config.algorithm.name == CD.Algorithm.K_MEANS:
				result = KMeans(cluster_config, observed_site)
			if cluster_config.algorithm.name == CD.Algorithm.SPECTRAL_CLUSTERING:
				result = SpectralClustering(cluster_config, observed_site)
			if cluster_config.algorithm.name == CD.Algorithm.HIERARCHICAL_CLUSTERING:
				result = HierarchicalClustering(cluster_config, observed_site)
			# If no pattern can be extracted, return None
			if result:
				learned_site = learned_sites.site.add()
				learned_site.CopyFrom(result)
		return learned_sites

def compute(site_list_filenames):
	text_out_filename = site_list_filenames[0] + '.text'
	cluster_learner = ClusterLearning()
	simhash_config = CD.SimhashConfig()
	simhash_config.simhash_type = CD.TEXT
	simhash_config.usage.tri_gram = True
	res = cluster_learner.compute_simhash(site_list_filenames, simhash_config)
	write_proto_to_file(res, text_out_filename)

	dom_out_filename = site_list_filenames[0] + '.dom'
	cluster_learner = ClusterLearning()
	simhash_config = CD.SimhashConfig()
	simhash_config.simhash_type = CD.DOM
	simhash_config.usage.tri_gram = False
	res = cluster_learner.compute_simhash(site_list_filenames, simhash_config)
	write_proto_to_file(res, dom_out_filename)

def learn(observed_sites_filenames):
	out_filename = observed_sites_filenames[0] + '.learned'
	cluster_learner = ClusterLearning()
	cluster_config = CD.ClusterConfig()
	cluster_config.algorithm.name = CD.Algorithm.HIERARCHICAL_CLUSTERING
	cluster_config.algorithm.left_out_ratio = 5 # left out ratio is 5%
	cluster_config.minimum_cluster_size = 5
	res = cluster_learner.learn(observed_sites_filenames, cluster_config)
	write_proto_to_file(res, out_filename)

def test_learner():
	in_filenames = ['utils/data/US_list_10.20141109-180617.selenium.crawl/crawl_log.text']
	out_filename = in_filenames[0] + '.learned'
	cluster_learner = ClusterLearning()
	cluster_config = CD.ClusterConfig()
	cluster_config.algorithm.name = CD.Algorithm.HAMMING_THRESHOLD
	cluster_config.algorithm.thres = 5
	cluster_config.algorithm.left_out_ratio = 5  # left out ratio is 5%
	res = cluster_learner.learn(in_filenames, cluster_config)
	write_proto_to_file(res, out_filename)
	print "result for hamming threhold clustering"
	print res

	cluster_config.algorithm.name = CD.Algorithm.HIERARCHICAL_CLUSTERING
	cluster_config.algorithm.left_out_ratio = 5  # left out ratio is 5%
	res = cluster_learner.learn(in_filenames, cluster_config)
	write_proto_to_file(res, out_filename)
	print "result for hierarchical clustering"
	print res


def test_computer():
	site_list_filenames = ['utils/data/US_list_10.20141109-180617.selenium.crawl/crawl_log']
	out_filename = 'utils/data/US_list_10.20141109-180617.selenium.crawl/crawl_log.text'
	cluster_learner = ClusterLearning()
	simhash_config = CD.SimhashConfig()
	simhash_config.simhash_type = CD.TEXT
	simhash_config.usage.tri_gram = True
	res = cluster_learner.compute_simhash(site_list_filenames, simhash_config)
	write_proto_to_file(res, out_filename)
	print res

	out_filename = 'utils/data/US_list_10.20141109-180617.selenium.crawl/crawl_log.dom'
	cluster_learner = ClusterLearning()
	simhash_config = CD.SimhashConfig()
	simhash_config.simhash_type = CD.DOM
	simhash_config.usage.tri_gram = False
	res = cluster_learner.compute_simhash(site_list_filenames, simhash_config)
	write_proto_to_file(res, out_filename)
	print res

	# cluster_config = CD.ClusterConfig()
	out_filename = 'utils/data/US_list_10.20141109-180617.selenium.crawl/crawl_log.text_dom'
	cluster_learner = ClusterLearning()
	simhash_config = CD.SimhashConfig()
	simhash_config.simhash_type = CD.TEXT_DOM
	simhash_config.usage.tri_gram = False
	res = cluster_learner.compute_simhash(site_list_filenames, simhash_config)
	write_proto_to_file(res, out_filename)
	print res

def main(argv):
	has_function = False
	help_msg = 'cluster_learning.py -f <function> [-i <inputfile>], valid functions are compute, learn'
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
		test_computer()
		test_learner()
		sys.exit()
	if function == 'compute':
		site_list_filenames = [inputfile]
		compute(site_list_filenames)
	elif function == 'learn':
		observed_sites_filename = inputfile
		learn(observed_sites_filename)
	else:
		print help_msg
		sys.exit(2)

if __name__ == "__main__":
	main(sys.argv[1:])

