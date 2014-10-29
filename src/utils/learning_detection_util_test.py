import numpy as np
from learning_detection_util import hierarchical_clustering, load_observed_sites, _strip_parameter
import proto.cloaking_detection_pb2 as CD

def _prepare_observed_site():
	observed_site = CD.SiteObservations()
	observation = observed_site.add()

def test_HammingDistance():
	cluster_config = CD.ClusterConfig()
	observed_site = _prepare_observed_site()
	HammingThreshold(cluster_config, observed_site)

def test_HierarchicalClustering():
	cluster_config = CD.ClusterConfig()
	observed_site = _prepare_observed_site()
	HierarchicalClustering(cluster_config, observed_site)

def test_hierarchical_clustering():
	# node: 0, 1, 2, 3
	# weight: 10, 8, 1, 10
	# 0,1:18; 2,3:11
	dist_mat = np.array([1,7,10,10,8,1])
	weight_list = np.array([10,8,1,10])
	min_cluster_size = 5
	left_out_ratio = 10
	clusters = hierarchical_clustering(dist_mat, weight_list, min_cluster_size, left_out_ratio)
	print "result should be: [[0,1],[2,3]]"
	print clusters

	dist_mat = np.array([1,7,10,10,10,8,10,1,10,10])
	weight_list = np.array([10,8,1,10,2])
	min_cluster_size = 5
	left_out_ratio = 10
	clusters = hierarchical_clustering(dist_mat, weight_list, min_cluster_size, left_out_ratio)
	print "result should be: [[0,1],[2,3]]"
	print clusters

	dist_mat = np.array([1,7,10,10,10,8,10,1,10,10])
	weight_list = np.array([10,8,1,10,4])
	min_cluster_size = 5
	left_out_ratio = 10
	clusters = hierarchical_clustering(dist_mat, weight_list, min_cluster_size, left_out_ratio)
	print "result should be: [[0,1,2,3,4]]"
	print clusters

	dist_mat = np.array([15,15,10,9,10,8,10,1,10,10])
	weight_list = np.array([10,8,1,10,4])
	min_cluster_size = 5
	left_out_ratio = 10
	clusters = hierarchical_clustering(dist_mat, weight_list, min_cluster_size, left_out_ratio)
	print "result should be: [[0,4],[1,2,3]]"
	print clusters

	dist_mat = np.array([15,15,10,9,10,8,10,10,10,10])
	weight_list = np.array([10,8,1,10,4])
	min_cluster_size = 5
	left_out_ratio = 10
	clusters = hierarchical_clustering(dist_mat, weight_list, min_cluster_size, left_out_ratio)
	print "result should be: [[0,4],[1,3]]"
	print clusters


def test_observed_sites():
	site_list_filenames = ['data/US_list_10.20141010-180519.selenium.crawl/html_path_list']
	s, p = load_observed_sites(site_list_filenames)
	print s
	print p

def test__strip_parameter():
	link = 'http://www.walmart.com/search/search-ng.do?search_query=Bicycles&adid=22222222220202379358&wmlspartner=wmtlabs&wl0=e&wl1=g&wl2=c&wl3=30633615476&wl4=&veh=sem'
	print link
	print _strip_parameter(link)

if __name__=="__main__":
	test__strip_parameter()
	test_observed_sites()
	test_hierarchical_clustering()

