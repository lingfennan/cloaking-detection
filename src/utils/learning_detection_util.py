import collections
import numpy as np
import re
import sys
import scipy.cluster.hierarchy as h
from Queue import Queue
from urllib import urlencode
from urlparse import urlparse, urlunparse, parse_qs
import proto.cloaking_detection_pb2 as CD


"""
Below are util functions.
"""
def _strip_parameter(link):
	"""
	Strip parameter values and set protocol to null for URLs, e.g.
	http://pan.baidu.com/share/link?shareid=3788206378&uk=2050235229 ->
	pan.baidu.com/share/link?sharedid=&uk=
	"""
	parsed_link = urlparse(link)
	query = parse_qs(parsed_link.query)
	for key in query:
		query[key] = ''
	parsed_link = parsed_link._replace(query=urlencode(query, True))
	parsed_link.scheme = ''
	return urlunparse(parsed_link)


def _split_path_by_data(path, index):
	"""
	Assumes the path follows pattern $PREFIX/data/$DETAIL_PATH
	Split by data and get $PREFIX or $DETAIL_PATH
	This is used to maintain consistence between paths of different programs (craw.py and cluster_learning.py).
	@parameter
	path: file path following format $PREFIX/data/$DETAIL_PATH
	index: index of elements to return
	@return
	either $PREFIX or $DETAIL_PATH
	"""
	if index > 1 or index < 0:
		raise Exception("Index out of range")
	parts = path.split('data')
	if len(parts) == 2:
		return parts[index]
	else:
		raise Exception("More than one 'data' or no 'data'.")

def load_observed_sites(site_list_filenames):
	"""
	@parameter
	site_list_filenames: load observed sites from list of site_list_filename.
	@return
	observed_sites: structure data that aggregate by site.
	path_list: the list of path that can be used for simhash computing.
	"""
	observed_sites = CD.ObservedSites()
	site_observations_map = dict()
	path_list = list()
	for site_list_filename in site_list_filenames:
		crawl_log = CD.CrawlLog()
		read_proto_from_file(crawl_log, site_list_filename)
		site_list = [[result.file_path, result.landing_url] for result in crawl_log.result \
				if result.success == True]
		prefix = _split_path_by_data(site_list_filename, 0)
		for path, link in site_list:
			# $prefix/data/$detail_path
			path = prefix + 'data' + _split_path_by_data(path, 1)
			key = _strip_parameter(link)
			if key not in site_observations_map:
				site_observations_map[key] = list()
			site_observations_map[key].append([link, path])
			path_list.append(path)
	for site in site_observations_map:
		observed_site = observed_sites.site.add()
		observed_site.name = site
		for link, path in site_observations_map[site]:
			observation = observed_site.observation.add()
			observation.landing_url = link 
			observation.file_path = path 
	return observed_sites, path_list

def merge_observed_sites(observed_sites_filenames):
	"""
	Different from load_observed_sites which extracts site name and fill observed_sites.
	Load observed_sites from multiple files and merge them.
	@parameter
	site_list_filenames: observed site list files to merge.
	@return
	observed_sites: the merged result.
	"""
	observed_sites = CD.ObservedSites()
	observed_sites_map = dict()
	for observed_sites_filename in observed_sites_filenames:
		temp_observed_sites = CD.ObservedSites()
		read_proto_from_file(temp_observed_sites, observed_sites_filename)
		for observed_site in temp_observed_sites.site:
			if observed_site.name in observed_sites_map:
				observed_sites_map[observed_site.name].MergeFrom(observed_site)
			else:
				observed_sites_map[observed_site.name] = CD.SiteObservations()
				observed_sites_map[observed_site.name].CopyFrom(observed_site)
	observed_sites.config.CopyFrom(temp_observed_sites.config)
	for site_name in observed_sites_map:
		observed_site = observed_sites.site.add()
		observed_site.CopyFrom(observed_sites_map[site_name])
	return observed_sites

def write_proto_to_file(proto, filename):
	f = open(filename, "wb")
	f.write(proto.SerializeToString())
	f.close()

def read_proto_from_file(proto, filename):
	f = open(filename, "rb")
	proto.ParseFromString(f.read())
	f.close()


"""
Below are util functions used by algorithms et al.
"""
def aggregate_simhash(observed_site, simhash_type):
	"""
	read the simhashs for observed_site, return unique simhash with count for each of them.
	currently, only simhash_type TEXT and DOM are supported. TEXT_DOM is not.
	"""
	simhash_item_vector = list()
	simhash_dict = dict()
	simhash_sample_file_path = dict()
	for observation in observed_site.observation:
		if simhash_type == CD.TEXT:
			simhash_value = observation.text_simhash
		elif simhash_type == CD.DOM:
			simhash_value = observation.dom_simhash
		elif simhash_type == CD.TEXT_DOM:
			raise Exception("TEXT_DOM simhash are not supported by now! Use either TEXT or DOM!")
		if simhash_value in simhash_dict:
			simhash_dict[simhash_value] += 1
		else:
			simhash_dict[simhash_value] = 1
			simhash_sample_file_path[simhash_value] = observation.file_path
	for key in simhash_dict:
		simhash_item = CD.SimhashItem()
		simhash_item.simhash = key
		simhash_item.count = simhash_dict[key]
		simhash_item.sample_file_path = simhash_sample_file_path[key]
		simhash_item_vector.append(simhash_item)
	return simhash_item_vector

def valid_instance(source, target):
	if isinstance(source, target):
		return True
	else:
		raise Exception("Bad parameter")

def average_distance(pattern, s):
	"""
	Compute the average distance from s to all items in pattern.
	"""
	valid_instance(pattern, CD.Pattern)
	total_dist = 0
	total_count = 0
	for item in pattern.item:
		total_count += item.count
		total_dist += hamming_distance(item.simhash, s) * item.count
	return float(total_dist) / total_count

def centroid_distance(pattern, s):
	"""
	Compute the distance from s to centroid of pattern.
	@parameter
	pattern: the pattern to compare against, pattern.centroid and pattern.size are used
	s: simhash value to be compared
	@return
	dist: the distance from s to centroid of pattern.
	"""
	"""
	############################################
	example:
	pattern: size = 8, centroid = [1,0,0,5,0,0,0,0, 8,0,0,0,0,0,0,0, 0,0,0,0,0,0,0,0, ...]
	s: [10000000 10000000 00000000 ...]
	total_dist: 8-1 + 5 + 8-8 = 12
	dist: 12 / 8 = 1.5
	"""
	valid_instance(pattern, CD.Pattern)
	total_dist = 0
	base = 1
	for centroid in pattern.centroid:
		if s & base:
			total_dist += pattern.size - centroid
		else:
			total_dist += centroid
		base = base << 1
	return float(total_dist) / pattern.size

def hamming_distance(u, v, f = 64):
	"""
	compute the hamming distance between u and v, f is the bit size of both u and v
	"""
	x = (u ^ v) & ((1 << f) - 1)
	ans = 0
	while x:
		ans += 1
		x &= x-1
	return ans

def _get_key(numbers):
	number_str = ''
	for number in sorted(numbers):
		number_str += str(number) + ','
	return number_str

def connected_components(adj_list, weight_list, minimum_cluster_size):
	"""
	@parameter
	adj_list: has property (1) i = adj_list[i][0] (2) adj_list[i][1:] are the neighbors for i
		eg. [[0, 1, 2], [1, 3], [2, 5], [3], [4, 6], [5], [6]]
	@return
	clusters: connected components in adj_list
	"""
	clusters = list()
	visited_nodes = set()
	size = len(adj_list)
	for i in xrange(size):
		if i in visited_nodes:
			continue
		q = Queue()
		s = set()
		q.put(adj_list[i][0])
		while not q.empty():
			current_node = q.get()
			s.add(current_node)
			visited_nodes.add(current_node)
			# push in the neighbors of current node
			for node in adj_list[current_node][1:]:
				if node not in visited_nodes:
					q.put(node)
		size_s = 0
		for node in s:
			size_s += weight_list[node]
		if size_s >= minimum_cluster_size:
			clusters.append(s)
	return clusters

def adjacency_list(dist_mat, num_points, threshold):
	valid_instance(dist_mat, np.ndarray)
	adj_list = list()
	index = 0
	for i in xrange(num_points):
		neighbors = list()
		neighbors.append(i) # record the node itself
		adj_list.append(neighbors)
	for i in xrange(num_points):
		for j in range(i+1, num_points):
			if dist_mat[index] <= threshold:
				adj_list[i].append(j)
				adj_list[j].append(i)
			# increase for each j
			index += 1
	return adj_list

def compute_left_out_ratio(dist_mat, weight_list, threshold, min_cluster_size):
	vector_size = len(weight_list)
	adj_list = adjacency_list(dist_mat, vector_size, threshold)
	clusters = connected_components(adj_list, weight_list, min_cluster_size)
	# compute left out ratio below
	# left out ratio = (total_size - merged_size) * 100 / total_size
	total_size = weight_list.sum()
	merged_size = 0
	for cluster in clusters:
		cluster_size = 0
		for index in cluster:
			cluster_size += weight_list[index]
		if cluster_size >= min_cluster_size:
			merged_size += cluster_size
	return float(total_size - merged_size)*100 / total_size, clusters

def hierarchical_clustering(dist_mat, weight_list, min_cluster_size, left_out_ratio):
	# paced search
	# test 1, 1*2, 1*2^2, 1*2^3, ...
	dist = 1
	multiplier = 2
	current_ratio = 100
	previous_ratio = 100
	current_ratio, current_clusters = compute_left_out_ratio(dist_mat, weight_list, dist, min_cluster_size)
	if current_ratio <= left_out_ratio:
		# dist = 1 is enough
		return current_clusters
	else:
		# start paced search, dist *= multiplier
		while current_ratio > left_out_ratio and dist <= 64:
			dist = dist * multiplier
			previous_ratio = current_ratio
			current_ratio, current_clusters = compute_left_out_ratio(dist_mat, weight_list, dist, min_cluster_size)
	if current_ratio > left_out_ratio:
		# this is problematic
		raise Exception("End ratio greater than left out ratio, paced search failed.!")
	# binary search
	# test (start + end) / 2
	start = dist / multiplier
	start_ratio = previous_ratio
	end = dist
	end_ratio = current_ratio
	end_clusters = current_clusters
	while end - start > 1:
		current = (end + start) / 2
		current_ratio, current_clusters = compute_left_out_ratio(dist_mat, weight_list, current, min_cluster_size)
		if current_ratio > left_out_ratio:
			start = current
			start_ratio = current_ratio
		elif current_ratio < left_out_ratio:
			end = current
			end_ratio = current_ratio
			end_clusters = current_clusters
		else:
			end = current
			break
	return end_clusters

def distance_matrix(simhash_item_vector):
	"""
	The returned format follows scipy.spatial.distance.pdist
	(http://docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.distance.pdist.html)
	"""
	# stores the result matrix, the diagonal line are zeros.
	size = len(simhash_item_vector)
	shape = size * (size - 1) / 2
	# the maximum distance is 64, therefore int8 is enough
	dist_mat = np.zeros(shape, dtype = np.int8)
	weight_list = np.zeros(size, dtype = int)
	# key is <number, number>, this is used to reduce computation overhead
	dist_map = dict()
	index = 0
	for i in xrange(size):
		weight_list[i] = simhash_item_vector[i].count
		for j in range(i+1, size):
			key = _get_key([simhash_item_vector[i].simhash, simhash_item_vector[j].simhash])
			if key in dist_map:
				dist_mat[index] = dist_map[key]
			else:
				distance = hamming_distance(simhash_item_vector[i].simhash, simhash_item_vector[j].simhash)
				dist_map[key] = distance
				dist_mat[index] = distance
			# increase for each j
			index += 1
	return dist_mat, weight_list

def compute_model(learned_site):
	"""
	Compute centroid, mean and std for each pattern.
	@parameter
	learned_site: patterns for learned_site.name, centroid, size, mean and std are not set.
	@return
	learned_site: centroid, size, mean and std are set. Performs in-place operation.
	"""
	for pattern in learned_site.pattern:
		# set size and centroid
		total_size = 0
		centroid = np.zeros((64,), dtype=int)
		for item in pattern.item:
			total_size += item.count
			simhash = item.simhash
			base = 1
			for index in xrange(64):
				if simhash & base:
					centroid[index] += item.count
				base = base << 1
		pattern.size = total_size
		for c in centroid:
			pattern.centroid.append(long(c))
		# set mean and std
		dist_list = list()  # the list of dist for each simhash_item
		for item in pattern.item:
			"""
			Difference from compute_model_old. Need to prove that normal distribution still hold. (TODO)
			New: Compute centroid and compare simhash to centroid, which takes into account the current simhash itself.
			Old: Compute avg_dist from simhash to all the other simhash, which doesn't consider current simhash.
			"""
			dist = centroid_distance(pattern, item.simhash)
			for j in xrange(item.count):
				dist_list.append(dist)
		dist_array = np.array(dist_list)
		pattern.mean = np.mean(dist_array)
		pattern.std = np.std(dist_array)
		# set threshold (TODO)

		# set percentile
		[p50, p75, p90, p95, p97, p99] = np.percentile(dist_array, [50,75,90,95,97,99])
		pattern.percentile.p99 = int(p99)
		pattern.percentile.p97 = int(p97)
		pattern.percentile.p95 = int(p95)
		pattern.percentile.p90 = int(p90)
		pattern.percentile.p75 = int(p75)
		pattern.percentile.p50 = int(p50)
		# set cdf
		hist, edges = np.histogram(dist_array, bins=np.arange(66))
		hist = np.cumsum(hist)
		edges = edges[0:65]
		for x, count in zip(edges, hist):
			"""
			x range in [0, 64], so there are 65 points.
			"""
			p = pattern.cdf.point.add()
			p.x = int(x)
			p.count = int(count)
	return learned_site

# This method is deprecated because the comptation cost is high.
# But can be used to verify implementation of new method.
def compute_model_old(learned_site):
	"""
	Compute mean and std for each pattern.
	@parameter
	learned_site: patterns for learned_site.name, mean and std are not set.
	@return
	learned_site: mean and std are set. Performs in-place operation.
	"""
	for pattern in learned_site.pattern:
		# The following code are to compute mean and std for pattern
		total_size = 0
		pattern_size = 0
		item_list = list()  # the list of simhash_item in this pattern
		# avg_dist_list can be improved, use self defined std instead (TODO)
		avg_dist_list = list()  # the list of avg_dist for each simhash_item
		for item in pattern.item:
			total_size += item.count
			pattern_size += 1
			item_list.append(item)
		for i in xrange(pattern_size):
			dist_i = 0
			for j in xrange(pattern_size):
				# doesn't compute the distance to the pattern itself
				if i == j:
					continue
				dist_i += item_list[j].count * hamming_distance(item_list[i].simhash, item_list[j].simhash)
			for j in xrange(item_list[i].count):
				avg_dist_list.append(dist_i / (total_size - 1))
		avg_dist_array = np.array(avg_dist_list)
		pattern.mean = np.mean(avg_dist_array)
		pattern.std = np.std(avg_dist_array)
	return learned_site

"""
Below are implementations of four suuported clustering algorithm.
"""
def HammingTreshold(cluster_config, observed_site):
	"""
	@parameter
	cluster_config: configuration for clustering, this one uses thres and minimum_cluster_size
	observed_site: observations of a site to be learned
	@return
	learned_site: the learned sites
	"""
	valid_instance(cluster_config, CD.ClusterConfig)
	valid_instance(observed_site, CD.SiteObservations)
	simhash_item_vector = aggregate_simhash(observed_site, cluster_config.simhash_type)
	vector_size = len(simhash_item_vector)
	learned_site = CD.SitePatterns()
	learned_site.name = observed_site.name
	# Compute the learned site
	num_observation = 0
	for s in simhash_item_vector:
		num_observation += s.count
	if vector_size == 0 or num_observation < cluster_config.minimum_cluster_size:
		return None
	elif vector_size == 1:
		# Only one simhash, just one pattern.
		pattern = learned_site.pattern.add()
		item = pattern.item.add()
		item.CopyFrom(simhash_item_vector[0])
	else:
		dist_mat, weight_list = distance_matrix(simhash_item_vector)
		adj_list = adjacency_list(dist_mat, vector_size, cluster_config.algorithm.thres)
		clusters = connected_components(adj_list, weight_list, cluster_config.minimum_cluster_size)
		for cluster in clusters:
			pattern = learned_site.pattern.add()
			for index in cluster:
				item = pattern.item.add()
				item.CopyFrom(simhash_item_vector[index])
	# Compute the cluster information.
	learned_site = compute_model(learned_site)
	return learned_site

def KMeans(cluster_config, observed_site):
	"""
	@parameter
	cluster_config: configuration for clustering, this one uses k and minimum_cluster_size
	observed_site: observations of a site to be learned
	@return
	learned_site: the learned sites
	"""
	valid_instance(cluster_config, CD.ClusterConfig)
	valid_instance(observed_site, CD.SiteObservations)

def SpectralClustering(cluster_config, observed_site):
	"""
	@parameter
	cluster_config: configuration for clustering, this one uses k and minimum_cluster_size
	observed_site: observations of a site to be learned
	@return
	learned_site: the learned sites
	"""
	valid_instance(cluster_config, CD.ClusterConfig)
	valid_instance(observed_site, CD.SiteObservations)

def HierarchicalClustering(cluster_config, observed_site):
	"""
	Learn clusters through hierarchical clustering.
	@parameter
	cluster_config: configuration for clustering, this one uses left_out_ratio and minimum_cluster_size
	observed_site: observations of a site to be learned
	@return
	learned_site: the learned sites
	"""
	valid_instance(cluster_config, CD.ClusterConfig)
	valid_instance(observed_site, CD.SiteObservations)
	simhash_item_vector = aggregate_simhash(observed_site, cluster_config.simhash_type)
	vector_size = len(simhash_item_vector)
	learned_site = CD.SitePatterns()
	learned_site.name = observed_site.name
	# Compute the learned site
	num_observation = 0
	for s in simhash_item_vector:
		num_observation += s.count
	if vector_size == 0 or num_observation < cluster_config.minimum_cluster_size:
		return None
	elif vector_size == 1:
		# Only one simhash, just one pattern.
		pattern = learned_site.pattern.add()
		item = pattern.item.add()
		item.CopyFrom(simhash_item_vector[0])
	else:
		dist_mat, weight_list = distance_matrix(simhash_item_vector)
		left_out_ratio = cluster_config.algorithm.left_out_ratio
		"""
		linkage_mat = h.linkage(dist_mat, method = 'single')
		# linkage matrix are sorted by distance between clusters
		# how to do the cut, hierarchical clustering is used to get cut threshold
		cut_thres = cut_threshold(linkage_mat, weight_list, left_out_ratio)
		this is to use third library to do the cut.
		cluster = h.fcluster(linkage_mat, cut_thres, criterion='distance')
		"""
		clusters = hierarchical_clustering(dist_mat, weight_list, \
				cluster_config.minimum_cluster_size, left_out_ratio) 
		for cluster in clusters:
			pattern = learned_site.pattern.add()
			for index in cluster:
				item = pattern.item.add()
				item.CopyFrom(simhash_item_vector[index])
	# Compute the cluster information.
	learned_site = compute_model(learned_site)
	return learned_site

