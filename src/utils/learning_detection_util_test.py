import numpy as np
from learning_detection_util import hierarchical_clustering, load_observed_sites, _strip_parameter, average_distance, read_proto_from_file, _split_path_by_data, intersect_observed_sites, sites_file_path_set
import proto.cloaking_detection_pb2 as CD

def assert_equal(actual_value, expected_value):
	if not actual_value == expected_value:
		print "result should be: "
		print expected_value
		print "but actual value is: "
		print actual_value

def check_equal(first_file, second_file):
	first_observed_sites = CD.ObservedSites()
	read_proto_from_file(first_observed_sites, first_file)
	second_observed_sites = CD.ObservedSites()
	read_proto_from_file(second_observed_sites, second_file)
	first_observed_sites_map = dict()
	for observed_site in first_observed_sites.site:
		first_observed_sites_map[observed_site.name] = observed_site
	for observed_site in second_observed_sites.site:
		if not observed_site.name in first_observed_sites_map:
			return False
		if not observed_site == first_observed_sites_map[observed_site.name]:
			return False
	return True

############################ Tests for specific functions ##########################
def test_intersect_observed_sites():
	observed_sites_list = ["../../data/abusive_words_9_category.computed/test.user.dom.cloaking",
			"../../data/abusive_words_9_category.computed/test.user.text.cloaking"]
	result = None
	for filename in observed_sites_list:
		observed_sites = CD.ObservedSites()
		read_proto_from_file(observed_sites, filename)
		files = sites_file_path_set(observed_sites)
		result = result & files if result else files
	result_sites = intersect_observed_sites(*observed_sites_list)
	new_set = sites_file_path_set(result_sites)
	assert_equal(result, new_set)

def test_load_observed_sites():
	site_list_filenames = ['../../data/abusive_words_9_category.selenium.crawl/search_crawl_log.20150122-193448.0c41fc41f4f009d24c0b61d24fd9a527_8']
	s, p = load_observed_sites(site_list_filenames)
	print s
	print p

def test_check_equal():
	first_file = "../../data/abusive_words_9_category.computed/test.google.dom.learned"
	second_file = "../../data/abusive_words_9_category.computed/test.google.text.learned"
	assert_equal(check_equal(first_file, second_file), False)
	assert_equal(check_equal(first_file, first_file), True)

def test__split_path_by_data():
	path = "../../data/US_web_search_list.Chrome.20141110-185317.selenium.crawl/crawl_log.dom.learned"
	first = _split_path_by_data(path, 0)
	second = _split_path_by_data(path, 1)
	assert_equal(first, "../../")
	assert_equal(second, "/US_web_search_list.Chrome.20141110-185317.selenium.crawl/crawl_log.dom.learned")

def test__strip_parameter():
	link = "http://www.walmart.com/search/search-ng.do?search_query=Bicycles&adid=22222222220202379358&wmlspartner=wmtlabs&wl0=e&wl1=g&wl2=c&wl3=30633615476&wl4=&veh=sem"
	parsed_link = "//www.walmart.com/search/search-ng.do?adid=&search_query=&veh=&wl0=&wl1=&wl2=&wl3=&wl4=&wmlspartner="
	print link
	print _strip_parameter(link)
	assert_equal(_strip_parameter(link), parsed_link)
	link = "//books.google.com/books?ei=&source=&ved=&sig=&pg=&hl=&lpg=&sa=&ots=&id=&ved=1234&dq=#v=onepage&q=online%20cash%20game%20stats&f=false"
	parsed_link = "//books.google.com/books?dq=&ei=&hl=&id=&lpg=&ots=&pg=&sa=&sig=&source=&ved=&ved="
	print link
	print _strip_parameter(link)
	assert_equal(_strip_parameter(link), parsed_link)

def _prepare_observed_site():
	observed_site = CD.SiteObservations()
	observation = observed_site.add()
	return observed_site

def test_HammingThreshold():
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
	assert_equal(clusters, [set([0,1]), set([2,3])])

	dist_mat = np.array([1,7,10,10,10,8,10,1,10,10])
	weight_list = np.array([10,8,1,10,2])
	min_cluster_size = 5
	left_out_ratio = 10
	clusters = hierarchical_clustering(dist_mat, weight_list, min_cluster_size, left_out_ratio)
	assert_equal(clusters, [set([0,1]), set([2,3])])

	dist_mat = np.array([1,7,10,10,10,8,10,1,10,10])
	weight_list = np.array([10,8,1,10,4])
	min_cluster_size = 5
	left_out_ratio = 10
	clusters = hierarchical_clustering(dist_mat, weight_list, min_cluster_size, left_out_ratio)
	assert_equal(clusters, [set([0,1,2,3,4])])

	dist_mat = np.array([15,15,10,9,10,8,10,1,10,10])
	weight_list = np.array([10,8,1,10,4])
	min_cluster_size = 5
	left_out_ratio = 10
	clusters = hierarchical_clustering(dist_mat, weight_list, min_cluster_size, left_out_ratio)
	assert_equal(clusters, [set([0,4]), set([1,2,3])])

	dist_mat = np.array([15,15,10,9,10,8,10,10,10,10])
	weight_list = np.array([10,8,1,10,4])
	min_cluster_size = 5
	left_out_ratio = 10
	clusters = hierarchical_clustering(dist_mat, weight_list, min_cluster_size, left_out_ratio)
	assert_equal(clusters, [set([0,4]), set([1,3])])

def test_average_distance():
	pattern = CD.Pattern()
	item = pattern.item.add()
	item.simhash = 0x0000000000001111
	item.count = 10
	item = pattern.item.add()
	item.simhash = 0x1111000000000000
	item.count = 10
	item = pattern.item.add()
	item.simhash = 0x0011000000000011
	item.count = 10
	pattern.mean = 4
	pattern.std = 0
	test_1 = 0x0011000000000011
	test_2 = 0x0011000000001100
	test_3 = 0x1111111100000000
	dist_1 = average_distance(pattern, test_1)
	dist_2 = average_distance(pattern, test_2)
	dist_3 = average_distance(pattern, test_3)
	assert_equal(dist_1, float(8)/3)
	assert_equal(dist_2, 4)
	assert_equal(dist_3, 8)

if __name__=="__main__":
	test_intersect_observed_sites()
	test__strip_parameter()
	test__split_path_by_data()
	test_load_observed_sites()
	test_hierarchical_clustering()
	test_average_distance()
	test_check_equal()
