import sys, getopt
from utils.learning_detection_util import add_failure, load_observed_sites, merge_observed_sites, write_proto_to_file, read_proto_from_file, valid_instance
from utils.learning_detection_util import HammingTreshold, KMeans, SpectralClustering, HierarchicalClustering, interact_query
import utils.proto.cloaking_detection_pb2 as CD
from cluster_learning import ClusterLearning

def test_learner():
	in_filenames = ['../data/abusive_words.20150115-154913.selenium.crawl/91532f0a84878d909e2deed33e9932cf/ad_crawl_log_0.text']
	out_filename = in_filenames[0] + '.learned'
	cluster_learner = ClusterLearning()
	cluster_config = CD.ClusterConfig()
	cluster_config.algorithm.name = CD.Algorithm.HAMMING_THRESHOLD
	cluster_config.algorithm.thres = 5
	cluster_config.algorithm.left_out_ratio = 5  # left out ratio is 5%
	res = cluster_learner.learn(in_filenames, cluster_config)
	# write_proto_to_file(res, out_filename)
	print "result for hamming threhold clustering"
	print res

	cluster_config.algorithm.name = CD.Algorithm.HIERARCHICAL_CLUSTERING
	cluster_config.algorithm.left_out_ratio = 5  # left out ratio is 5%
	res = cluster_learner.learn(in_filenames, cluster_config)
	# write_proto_to_file(res, out_filename)
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
	# write_proto_to_file(res, out_filename)
	print res

	out_filename = '../data/abusive_words.20150115-154913.selenium.crawl/91532f0a84878d909e2deed33e9932cf/ad_crawl_log_2.dom'
	cluster_learner = ClusterLearning()
	simhash_config = CD.SimhashConfig()
	simhash_config.simhash_type = CD.DOM
	simhash_config.usage.tri_gram = False
	res = cluster_learner.compute_simhash(site_list_filenames, simhash_config)
	# write_proto_to_file(res, out_filename)
	print res

	# cluster_config = CD.ClusterConfig()
	out_filename = '../data/abusive_words.20150115-154913.selenium.crawl/91532f0a84878d909e2deed33e9932cf/ad_crawl_log_2.text_dom'
	cluster_learner = ClusterLearning()
	simhash_config = CD.SimhashConfig()
	simhash_config.simhash_type = CD.TEXT_DOM
	simhash_config.usage.tri_gram = False
	res = cluster_learner.compute_simhash(site_list_filenames, simhash_config)
	# write_proto_to_file(res, out_filename)
	print res

if __name__=="__main__":
	test_learner()
	test_computer()

