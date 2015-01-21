"""
How to use:
python cluster_learning.py -f compute -i <inputfiles> [-o <outputfile> -t <simhash_type>] (If there are multiple inputfiles, split them by comma)
python cluster_learning.py -f learn -i <inputfiles> [-o <outputfile>] (If there are multiple inputfiles, split them by comma)
"""

import sys, getopt
import simhash
from threading import Thread
from html_simhash_computer import HtmlSimhashComputer
from utils.learning_detection_util import add_failure, load_observed_sites, merge_observed_sites, write_proto_to_file, read_proto_from_file, valid_instance
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
		"""
		Compute simhash for site_list_filenames using configuration simhash_config

		@parameter
		site_list_filenames: a list of site_list_filename (CrawlLog)
		simhash_config: the configuration for simhash computing
		@return
		observed_sites: site observations aggregated by site
		"""

		# Input is a list of site_list_filename
		valid_instance(simhash_config, CD.SimhashConfig)
		observed_sites, path_list = load_observed_sites(site_list_filenames)  
		simhash_computer = HtmlSimhashComputer(simhash_config)
		thread_computer = ThreadComputer(simhash_computer, 'compute_simhash', path_list)
		path_simhash_dict = dict()
		for p, s in thread_computer.result:
			path_simhash_dict[p] = s
		observed_sites.config.CopyFrom(simhash_config)
		for site in observed_sites.site:
			for observation in site.observation:
				result = path_simhash_dict[observation.file_path]
				if simhash_config.simhash_type in [CD.TEXT, CD.TEXT_DOM]:
					observation.text_simhash = result[0][0].value
					observation.text_feature_count = result[0][1]
				if simhash_config.simhash_type in [CD.DOM, CD.TEXT_DOM]:
					observation.dom_simhash = result[-1][0].value
					observation.dom_feature_count = result[-1][1]
		if not simhash_config.discard_failure:
			observed_sites = add_failure(observed_sites, site_list_filenames)
		return observed_sites

	def learn(self, observed_sites_filenames, cluster_config=None):
		"""
		Learn clusters from observed_sites_filenames using cluster_config

		@parameter
		observed_sites_filenames: list of observed_sites to be learned
		cluster_config: configuration for clustering
		@return
		learned_sites: the learned clusters
		"""
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

def compute(site_list_filenames, outfile = None, simhash_type = None, keep_failure = False):
	# this branch simhash_type == None, TEXT, TEXT_DOM
	if not simhash_type == "DOM":
		text_out_filename = outfile + ".text" if outfile else site_list_filenames[0] + ".text"
		cluster_learner = ClusterLearning()
		simhash_config = CD.SimhashConfig()
		simhash_config.simhash_type = CD.TEXT
		simhash_config.discard_failure = not keep_failure
		simhash_config.usage.tri_gram = True
		res = cluster_learner.compute_simhash(site_list_filenames, simhash_config)
		write_proto_to_file(res, text_out_filename)
	# this branch simhash_type == None, DOM, TEXT_DOM
	if not simhash_type == "TEXT":
		dom_out_filename = outfile + ".dom" if outfile else site_list_filenames[0] + ".dom"
		cluster_learner = ClusterLearning()
		simhash_config = CD.SimhashConfig()
		simhash_config.simhash_type = CD.DOM
		simhash_config.discard_failure = not keep_failure
		simhash_config.usage.tri_gram = False
		res = cluster_learner.compute_simhash(site_list_filenames, simhash_config)
		write_proto_to_file(res, dom_out_filename)

def learn(observed_sites_filenames, outfile = None):
	out_filename = outfile + ".learned" if outfile else observed_sites_filenames[0] + ".learned"
	cluster_learner = ClusterLearning()
	cluster_config = CD.ClusterConfig()
	cluster_config.algorithm.name = CD.Algorithm.HIERARCHICAL_CLUSTERING
	cluster_config.algorithm.left_out_ratio = 5 # left out ratio is 5%
	cluster_config.minimum_cluster_size = 5
	res = cluster_learner.learn(observed_sites_filenames, cluster_config)
	write_proto_to_file(res, out_filename)

def test_learner():
	in_filenames = ['../data/abusive_words.20150115-154913.selenium.crawl/91532f0a84878d909e2deed33e9932cf/ad_crawl_log_0.text']
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
	site_list_filenames = ['../data/abusive_words.20150115-154913.selenium.crawl/91532f0a84878d909e2deed33e9932cf/ad_crawl_log_2']
	out_filename = '../data/abusive_words.20150115-154913.selenium.crawl/91532f0a84878d909e2deed33e9932cf/ad_crawl_log_2.text'
	cluster_learner = ClusterLearning()
	simhash_config = CD.SimhashConfig()
	simhash_config.simhash_type = CD.TEXT
	simhash_config.discard_failure = False
	simhash_config.usage.tri_gram = True
	res = cluster_learner.compute_simhash(site_list_filenames, simhash_config)
	write_proto_to_file(res, out_filename)
	print res

	out_filename = '../data/abusive_words.20150115-154913.selenium.crawl/91532f0a84878d909e2deed33e9932cf/ad_crawl_log_2.dom'
	cluster_learner = ClusterLearning()
	simhash_config = CD.SimhashConfig()
	simhash_config.simhash_type = CD.DOM
	simhash_config.usage.tri_gram = False
	res = cluster_learner.compute_simhash(site_list_filenames, simhash_config)
	write_proto_to_file(res, out_filename)
	print res

	# cluster_config = CD.ClusterConfig()
	out_filename = '../data/abusive_words.20150115-154913.selenium.crawl/91532f0a84878d909e2deed33e9932cf/ad_crawl_log_2.text_dom'
	cluster_learner = ClusterLearning()
	simhash_config = CD.SimhashConfig()
	simhash_config.simhash_type = CD.TEXT_DOM
	simhash_config.usage.tri_gram = False
	res = cluster_learner.compute_simhash(site_list_filenames, simhash_config)
	write_proto_to_file(res, out_filename)
	print res

def main(argv):
	has_function = False
	help_msg = 'cluster_learning.py -f <function> [-i <inputfile> -t <simhash_type> -k] [-i <inputfile>], valid functions are compute, learn'
	outputfile = None
	simhash_type = None
	keep_failure = False
	try:
		opts, args = getopt.getopt(argv, "hf:i:o:t:k", ["function=", "ifile=", "ofile=", "type=", "keepfailure"])
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
		elif opt in ("-o", "--ofile"):
			outputfile = arg
		elif opt in ("-t", "--type"):
			simhash_type = arg
		elif opt in ("-k", "--keepfailure"):
			keep_failure = True
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
		site_list_filenames = inputfile.split(',')
		if 'google' in site_list_filenames[0].lower() and not keep_failure:
			print "Warning: Google observation failure are discarded!"
			print "Do you want to continue?[Y/N]"
			line = sys.stdin.readline()
			if "y" in line.lower():
				pass
			elif "n" in line.lower():
				sys.exit(0)
			else:
				print "Unrecognized option!"
				sys.exit(1)
		compute(site_list_filenames, outputfile, simhash_type, keep_failure)
	elif function == 'learn':
		observed_sites_filenames = inputfile.split(',')
		learn(observed_sites_filenames, outputfile)
	else:
		print help_msg
		sys.exit(2)

if __name__ == "__main__":
	main(sys.argv[1:])

