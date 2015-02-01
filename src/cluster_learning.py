"""
How to use:
python cluster_learning.py -f compute -i <inputfile_list> [-o <outputfile> -t <simhash_type> -g]
python cluster_learning.py -f learn -i <inputfile_list> [-o <outputfile>]
"""

import sys, getopt
import simhash
from threading import Thread
from html_simhash_computer import HtmlSimhashComputer
from utils.learning_detection_util import add_failure, load_observed_sites, merge_observed_sites, write_proto_to_file, read_proto_from_file, valid_instance
from utils.learning_detection_util import HammingTreshold, KMeans, SpectralClustering, HierarchicalClustering, interact_query
from utils.thread_computer import ThreadComputer
from utils.util import evaluation_form
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
		if simhash_config.crawl_log_landing_url_as_observation_landing_url:
			url_field = "landing_url"
		else:
			url_field = "url"
		observed_sites, path_list = load_observed_sites(site_list_filenames,
				url_field)  
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

def compute(site_list_filenames, outfile = None, simhash_type = None, is_google = False):
	# this branch simhash_type == None, TEXT, TEXT_DOM
	if not simhash_type == "DOM":
		text_out_filename = outfile + ".text" if outfile else site_list_filenames[0] + ".text"
		cluster_learner = ClusterLearning()
		simhash_config = CD.SimhashConfig()
		simhash_config.simhash_type = CD.TEXT
		simhash_config.discard_failure = not is_google
		simhash_config.crawl_log_landing_url_as_observation_landing_url = not is_google
		simhash_config.usage.tri_gram = True
		res = cluster_learner.compute_simhash(site_list_filenames, simhash_config)
		write_proto_to_file(res, text_out_filename)
	# this branch simhash_type == None, DOM, TEXT_DOM
	if not simhash_type == "TEXT":
		dom_out_filename = outfile + ".dom" if outfile else site_list_filenames[0] + ".dom"
		cluster_learner = ClusterLearning()
		simhash_config = CD.SimhashConfig()
		simhash_config.simhash_type = CD.DOM
		simhash_config.discard_failure = not is_google
		simhash_config.crawl_log_landing_url_as_observation_landing_url = not is_google
		simhash_config.usage.tri_gram = False
		res = cluster_learner.compute_simhash(site_list_filenames, simhash_config)
		write_proto_to_file(res, dom_out_filename)

def learn(observed_sites_filenames, outfile = None):
	out_filename = outfile + ".learned" if outfile else observed_sites_filenames[0] + ".learned"
	cluster_learner = ClusterLearning()
	cluster_config = CD.ClusterConfig()
	cluster_config.algorithm.name = CD.Algorithm.HIERARCHICAL_CLUSTERING
	cluster_config.algorithm.left_out_ratio = 5 # left out ratio is 5%
	cluster_config.minimum_cluster_size = 2
	res = cluster_learner.learn(observed_sites_filenames, cluster_config)
	write_proto_to_file(res, out_filename)

def main(argv):
	has_function = False
	help_msg = 'cluster_learning.py -f <function> [-i <inputfile> -t <simhash_type> -o <outputfile> -g] [-i <inputfile> -o <outputfile>], valid functions are compute, learn'
	outputfile = None
	simhash_type = None
	is_google = False
	try:
		opts, args = getopt.getopt(argv, "hf:i:o:t:g", ["function=", "ifile=", "ofile=", "type=", "is_google"])
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
		elif opt in ("-g", "--is_google"):
			is_google = True
		else:
			print help_msg
			sys.exit(2)
	if not has_function:
		print help_msg
		sys.exit()
	if function == 'compute':
		"""
		Compute simhash for crawl log files in site_list_filenames.
		If the files records google observation, ask whether to:
		1. keep failure
		2. aggregate by landing url
		3. learn right after compute
		"""
		site_list_filenames = filter(bool, open(inputfile, 'r').read().split('\n'))
		compute_and_learn = False
		if 'google' in site_list_filenames[0].lower():
			if not is_google:
				out_str = "Warning: Google observation failure are discarded!\n" \
						"Warning: Google observation aggregated by " \
						"landing url!\n Do you want to continue?[Y/N]"
				if not interact_query(out_str):
					sys.exit(0)
			# Whether to learn after compute
			out_str = "Do you want to learn cluster after compute?[Y/N]"
			compute_and_learn = interact_query(out_str)
		compute(site_list_filenames, outputfile, simhash_type, is_google)
		if compute_and_learn:
			learn([outputfile + ".dom"], None)
			learned_file = outputfile + ".dom.learned"
			evaluation_form(learned_file, learned_file + ".eval", "LearnedSites")
			learn([outputfile + ".text"], None)
			learned_file = outputfile + ".text.learned"
			evaluation_form(learned_file, learned_file + ".eval", "LearnedSites")
	elif function == 'learn':
		observed_sites_filenames = filter(bool, open(inputfile, 'r').read().split('\n'))
		learn(observed_sites_filenames, outputfile)
	else:
		print help_msg
		sys.exit(2)

if __name__ == "__main__":
	main(sys.argv[1:])

