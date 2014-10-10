import simhash

from html_simhash_computer import Html_Simhash_Computer
import utils.proto.cloaking_detection_pb2 as CD

class ClusterLearning(object):
	def __init__(self, cluster_config=None):
		if not cluster_config:
			self.cluster_config = None
		elif isinstance(cluster_config, CD.ClusterConfig):
			self.cluster_config = cluster_config
		else:
			raise Exception("Bad parameter")

	def compute_simhash(self, observed_sites, simhash_config):
		if (not isinstance(observed_sites, CD.ObservedSites)) or (not isinstance(simhash_config, CD.SimhashConfig)):
			raise Exception("Bad parameter")
		computer = Html_Simhash_Computer()

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




