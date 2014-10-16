import simhash
from threading import Thread
from html_simhash_computer import Html_Simhash_Computer
from utils.detection_util import load_observed_sites, write_proto_to_file, read_proto_from_file
from utils.thread_computer import ThreadComputer
import utils.proto.cloaking_detection_pb2 as CD

class ClusterLearning(object):
	def __init__(self, cluster_config=None):
		if not cluster_config:
			self.cluster_config = None
		elif isinstance(cluster_config, CD.ClusterConfig):
			self.cluster_config = cluster_config
		else:
			raise Exception("Bad parameter")
	
	def compute_simhash(self, site_list_filenames, simhash_config):
		if not isinstance(simhash_config, CD.SimhashConfig):
			raise Exception("Bad parameter")
		observed_sites, path_list = load_observed_sites(site_list_filenames)  # Input is a list of site_list_filename
		simhash_computer = Html_Simhash_Computer(simhash_config)
		thread_computer = ThreadComputer(simhash_computer, 'compute_simhash', path_list)
		path_simhash_dict = dict()
		for p, s in thread_computer.result:
			path_simhash_dict[p] = s
		for site in observed_sites.site:
			for observation in site.observation:
				if simhash_config.simhash_type in [CD.SimhashConfig.TEXT, CD.SimhashConfig.TEXT_DOM]:
					observation.text_simhash = path_simhash_dict[observation.file_path][0].value
				if simhash_config.simhash_type in [CD.SimhashConfig.DOM, CD.SimhashConfig.TEXT_DOM]:
					observation.dom_simhash = path_simhash_dict[observation.file_path][-1].value
		return observed_sites

	def learn(self, cluster_config=None):
		if (not cluster_config) and (not self.cluster_config):
			raise Exception("Cluster config missing")
		elif cluster_config:
			if isinstance(cluster_config, CD.ClusterConfig):
				self.cluster_config = cluster_config
			else:
				raise Exception("Bad parameter")
		# learn the clusters
		learned_sites = CD.LearnedSites()

	def KMeans(self, data):
		None

	def SpectralClustering(self, data):
		None

	def HierarchicalClustering(self, data):
		None



class CloakingDetection(object):
	def __init__(self, learned_sites):
		if isinstance(learned_sites, CD.LearnedSites):
			self.leanred_sites = learned_sites
		else:
			raise Exception("Bad parameter")

	def is_cloaking(self, observation):
		if not isinstance(observation, CD.Observation):
			raise Exception("Bad parameter")
			
	def detect(self, observed_sites):
		if not isinstance(observed_sites, CD.ObservedSites):
			raise Exception("Bad parameter")
		load_observed_sites(observed_sites)

if __name__ == "__main__":
	site_list_filenames = ['utils/data/US_list_10.20141010-180519.selenium.crawl/html_path_list']
	out_filename = 'utils/data/US_list_10.20141010-180519.selenium.crawl/html_path_list.text'
	cluster_learner = ClusterLearning()
	simhash_config = CD.SimhashConfig()
	simhash_config.simhash_type = CD.SimhashConfig.TEXT
	simhash_config.usage.tri_gram = True
	res = cluster_learner.compute_simhash(site_list_filenames, simhash_config)
	write_proto_to_file(res, out_filename)
	print res

	out_filename = 'utils/data/US_list_10.20141010-180519.selenium.crawl/html_path_list.dom'
	cluster_learner = ClusterLearning()
	simhash_config = CD.SimhashConfig()
	simhash_config.simhash_type = CD.SimhashConfig.DOM
	simhash_config.usage.tri_gram = False
	res = cluster_learner.compute_simhash(site_list_filenames, simhash_config)
	write_proto_to_file(res, out_filename)
	print res

	# cluster_config = CD.ClusterConfig()

	out_filename = 'utils/data/US_list_10.20141010-180519.selenium.crawl/html_path_list.text_dom'
	cluster_learner = ClusterLearning()
	simhash_config = CD.SimhashConfig()
	simhash_config.simhash_type = CD.SimhashConfig.TEXT_DOM
	simhash_config.usage.tri_gram = False
	res = cluster_learner.compute_simhash(site_list_filenames, simhash_config)
	write_proto_to_file(res, out_filename)
	print res

