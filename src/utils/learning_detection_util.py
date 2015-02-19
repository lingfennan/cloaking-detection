import collections
import numpy as np
import re
import sys
from scipy.spatial.distance import pdist
from scipy.cluster.hierarchy import fcluster
from scipy.cluster.hierarchy import fclusterdata
from scipy.cluster.hierarchy import linkage
from Queue import Queue
from urllib import urlencode
from urlparse import urlparse, urlunparse, parse_qs, urldefrag
import proto.cloaking_detection_pb2 as CD


"""
Below are util functions.
"""
def sites_name_set(observed_sites):
	valid_instance(observed_sites, CD.ObservedSites)
	name_set = set()
	for site in observed_sites.site:
		name_set.add(site.name)
	return name_set

def get_simhash_type(simhash_type, return_proto=False):
	"""
	Return proto or attribute name for simhash_type
	@parameter
	simhash_type: type of simhash specified, can either be str or CD.SimhashType
	return_proto: bool
	@return
	simhash_type: text_simhash/dom_simhash or CD.TEXT/CD.DOM
	"""
	if isinstance(simhash_type, str):
		if "text" in simhash_type.lower():
			simhash_type = "text_simhash"
			type_proto = CD.TEXT
		elif "dom" in simhash_type.lower():
			simhash_type = "dom_simhash"
			type_proto = CD.DOM
		else:
			raise Exception("wrong type of simhash_type!")
	elif simhash_type == CD.TEXT:
		simhash_type = 'text_simhash'
	elif simhash_type == CD.DOM:
		simhash_type = 'dom_simhash'
	else:
		raise Exception("wrong type of simhash_type!")
	return simhash_type if not return_proto else type_proto

def valid_observation(observation, config):
	"""
	@parameter
	observation: Obervation
	config: DeNoiseConfig
	@return
	whether this observation is valid
	"""
	valid_instance(observation, CD.Observation)
	valid_instance(config, CD.DeNoiseConfig)
	if config.empty_file_path and (not observation.HasField("file_path")):
		return False
	if config.zero_simhash and getattr(observation, config.simhash_name) == 0:
		return False
	if config.zero_feature and getattr(observation, config.feature_name) < config.feature_count_threshold:
		return False
	return True

def de_noise(observed_sites, config):
	"""
	Remove noise from observed_sites and return the cleaned one.
	@parameter
	observed_sites: the observed_sites to remove noise from
	config: what is considered as noise
	@return
	de_noise: the de-noise result
	"""
	valid_instance(observed_sites, CD.ObservedSites)
	valid_instance(config, CD.DeNoiseConfig)
	original = observed_sites
	de_noise = CD.ObservedSites()
	de_noise.config.CopyFrom(original.config)
	simhash_type = original.config.simhash_type
	if simhash_type == CD.TEXT:
		config.feature_name = "text_feature_count"
	elif simhash_type == CD.DOM:
		config.feature_name = "dom_feature_count"
	else:
		raise Exception("Wrong simhash_type")
	config.simhash_name = get_simhash_type(simhash_type)
	for observed_site in original.site:
		has_valid_ob = False
		de_noise_site = CD.SiteObservations()
		de_noise_site.name = observed_site.name
		for observation in observed_site.observation:
			if valid_observation(observation, config):
				has_valid_ob = True
				de_noise_ob = de_noise_site.observation.add()
				de_noise_ob.CopyFrom(observation)
		if has_valid_ob:
			add_site = de_noise.site.add()
			add_site.CopyFrom(de_noise_site)
	return de_noise

def ob_file_path_set(site):
	"""
	Get the file_path set from SiteObservations.
	"""
	valid_instance(site, CD.SiteObservations)
	result = set()
	for observation in site.observation:
		result.add(observation.file_path)
	return result

def sites_file_path_set(observed_sites):
	"""
	Get the file_path set from ObservedSites.
	"""
	valid_instance(observed_sites, CD.ObservedSites)
	result = set()
	for site in observed_sites.site:
		result |= ob_file_path_set(site)
	return result

def interact_query(out_str):
	print out_str
	line = sys.stdin.readline()
	if "y" in line.lower():
		return True
	elif "n" in line.lower():
		return False
	else:
		print "Unrecognized option!"
		sys.exit(1)

def show_proto(inputfile, proto_type):
	proto = getattr(CD, proto_type)()
	read_proto_from_file(proto, inputfile)
	print proto
	print len(proto.site)

def _strip_parameter(link):
	"""
	For one URL
	1.Strip parameter values 
	2.Set protocol to null for URLs, e.g.
	3.Order the parameter names
	4.Keep multiple instances of same parameter
	e.g.
	http://pan.baidu.com/share/link?shareid=3788206378&uk=2050235229 ->
	//pan.baidu.com/share/link?sharedid=&uk=

	Blank values are kept.
	"""
	# encode in ascii to avoid UnicodeEncodeError
	link = link.encode('ascii')
	link, frag = urldefrag(link)
	parsed_link = urlparse(link)
	query = parse_qs(parsed_link.query, keep_blank_values=True)
	for key in query:
		if isinstance(query[key], collections.Iterable):
			query[key] = ['' for i in range(len(query[key]))]
		else:
			query[key] = ''
	# set urlendcode(,True) enables multiple values for the same parameter
	query = collections.OrderedDict(sorted(query.items()))
	parsed_link = parsed_link._replace(query=urlencode(query, True))
	parsed_link = parsed_link._replace(scheme='')
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

def add_failure(observed_sites, site_list_filenames):
	"""
	Add failure assign simhash as 0.
	This provide a way to distinguish failure from
	blank page. 0 (failure) vs. md5(0) (blank page).

	@parameter
	observed_sites: the sites to add, this function performs in place add
	site_list_filenames: list of site_list_filename, which is CrawlLog
	@return
	more_observed_sites: structure data that aggregate by site after adding failure
	"""
	site_observations_map = dict()
	for site in observed_sites.site:
		site_observations_map[site.name] = list()
		for observation in site.observation:
			site_observations_map[site.name].append(observation)
	for site_list_filename in site_list_filenames:
		crawl_log = CD.CrawlLog()
		read_proto_from_file(crawl_log, site_list_filename)
		# get failure sites list
		site_list = [result.url for result_search in crawl_log.result_search \
				for result in result_search.result if not result.success]
		for link in site_list:
			key = _strip_parameter(link)
			if key not in site_observations_map:
				site_observations_map[key] = list()
			observation = CD.Observation()
			observation.landing_url = link
			if observed_sites.config.simhash_type in [CD.TEXT, CD.TEXT_DOM]:
				observation.text_simhash = 0
				observation.text_feature_count = 0
			if observed_sites.config.simhash_type in [CD.DOM, CD.TEXT_DOM]:
				observation.dom_simhash = 0
				observation.dom_feature_count = 0
			site_observations_map[key].append(observation)
	more_observed_sites = CD.ObservedSites()
	more_observed_sites.config.CopyFrom(observed_sites.config)
	for site in site_observations_map:
		observed_site = more_observed_sites.site.add()
		observed_site.name = site
		for ob in site_observations_map[site]:
			observation = observed_site.observation.add()
			observation.CopyFrom(ob)
	return more_observed_sites

def load_observed_sites(site_list_filenames, url_field="landing_url"):
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
		site_list = [[result.file_path, getattr(result, url_field)] \
				for result_search in crawl_log.result_search \
				for result in result_search.result if result.success]
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

def merge_observed_sites(observed_sites_filenames, allow_repeat = False):
	"""
	Different from load_observed_sites which extracts site name and fill observed_sites.
	Load observed_sites from multiple files and merge them.
	@parameter
	site_list_filenames: observed site list files to merge.
	Previous implementation just concat the repeated fields. However, this
	wastes a lot of space. We want to have unique ones stored.
	@return
	observed_sites: the merged result.
	"""
	observed_sites = CD.ObservedSites()
	observed_sites_map = dict()
	for observed_sites_filename in observed_sites_filenames:
		temp_observed_sites = CD.ObservedSites()
		read_proto_from_file(temp_observed_sites, observed_sites_filename)
		for observed_site in temp_observed_sites.site:
			if not observed_site.name in observed_sites_map:
				observed_sites_map[observed_site.name] = CD.SiteObservations()
				observed_sites_map[observed_site.name].name = observed_site.name
			if allow_repeat:
				observed_sites_map[observed_site.name].MergeFrom(observed_site)
			else:
				existing = ob_file_path_set(observed_sites_map[observed_site.name])
				for ob in observed_site.observation:
					if not ob.file_path in existing:
						existing.add(ob.file_path)
						to_add = observed_sites_map[observed_site.name].observation.add()
						to_add.CopyFrom(ob)
	if temp_observed_sites.HasField("config"):
		observed_sites.config.CopyFrom(temp_observed_sites.config)
	else:
		print "The merged sites doesn't have config, make sure it's correct"
	for site_name in observed_sites_map:
		observed_site = observed_sites.site.add()
		observed_site.CopyFrom(observed_sites_map[site_name])
	return observed_sites

def intersect_observed_sites(site_filename, to_add_site_filename):
	"""
	Load observed_sits from multiple files and intersect them.
	@parameter
	observed_sites_filenames: observed site list files to intersect.
	@return
	observed_sites: the intersect result.
	"""
	observed_sites = CD.ObservedSites()
	temp_observed_sites_map = dict()
	temp_observed_sites = CD.ObservedSites()
	read_proto_from_file(temp_observed_sites, site_filename)
	observed_sites.config.CopyFrom(temp_observed_sites.config)
	for observed_site in temp_observed_sites.site:
		temp_observed_sites_map[observed_site.name] = CD.SiteObservations()
		temp_observed_sites_map[observed_site.name].CopyFrom(observed_site)
	to_add_map = dict()
	to_add = CD.ObservedSites()
	read_proto_from_file(to_add, to_add_site_filename)
	for observed_site in to_add.site:
		to_add_map[observed_site.name] = CD.SiteObservations()
		to_add_map[observed_site.name].CopyFrom(observed_site)
	for name in temp_observed_sites_map:
		if name in to_add_map:
			temp_site = temp_observed_sites_map[name]
			to_add_site = to_add_map[name]
			result_set = ob_file_path_set(temp_site) & ob_file_path_set(to_add_site)
			if len(result_set) == 0:
				continue
			observed_site = observed_sites.site.add()
			observed_site.name = name
			for observation in temp_site.observation:
				if observation.file_path in result_set:
					ob = observed_site.observation.add()
					ob.CopyFrom(observation)
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
		if (not simhash_value in simhash_sample_file_path) and observation.HasField("file_path"):
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

def uint_to_bool(u, size = 64):
	"""
	Read from high bit to low bit and fill them in the bool array
	"""
	bool_array = np.zeros(size, dtype=bool)
	base = 1
	for index in range(size):
		if u & base:
			bool_array[size-index-1] = True
		base = base << 1
	return bool_array

def prepare_matrix(simhash_item_vector):
	vector_size = len(simhash_item_vector)
	mat = np.zeros((vector_size, 64), dtype=np.bool)
	for i in range(vector_size):
		item = simhash_item_vector[i]
		mat[i] = np.copy(uint_to_bool(item.simhash))
	return mat

def get_indexes(cluster_label):
	cluster_dict = dict()
	vector_size = len(cluster_label)
	for i in range(vector_size):
		cluster_id = cluster_label[i]
		if not cluster_id in cluster_dict:
			cluster_dict[cluster_id] = list()
		cluster_dict[cluster_id].append(i)
	clusters = list()
	for cluster_id in cluster_dict:
		clusters.append(cluster_dict[cluster_id])
	return clusters

"""
Below are functions used by deprecated version of hierarchical clustering
"""
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
	for i in range(size):
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
	for i in range(num_points):
		neighbors = list()
		neighbors.append(i) # record the node itself
		adj_list.append(neighbors)
	for i in range(num_points):
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
	for i in range(size):
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

def compute_mce_threshold(learned_site):
	"""
	Deprecated.

	Compute minimum classification error threshold for each pattern.
	@parameter
	learned_site: patterns for learned_site.name, mce_threshold is not set.
	@return 
	learned_site: mce_threshold is set. Performs in-place operation.
	"""
	# set threshold (TODO)
	for pattern in learned_site.pattern:
		for item in pattern.item:
			item_dist_list = [centroid_distance(p, item.simhash) for p \
					in learned_site.pattern]
	return learned_site


def compute_deprecated_stats(pattern):
	"""
	Deprecated.
	These are the stats not being used now.

	set mean and std
	"""
	dist_list = list()  # the list of dist for each simhash_item
	for item in pattern.item:
		"""
		Difference from compute_model_old. Need to prove that normal distribution still hold. (TODO)
		New: Compute centroid and compare simhash to centroid, which takes into account the current simhash itself.
		Old: Compute avg_dist from simhash to all the other simhash, which doesn't consider current simhash.
		"""
		dist = centroid_distance(pattern, item.simhash)
		dist_list.append(dist)
	dist_array = np.array(dist_list)
	pattern.mean = np.mean(dist_array)
	pattern.std = np.std(dist_array)
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

def compute_hierarchical_stats(pattern):
	"""
	Compute the linkage, and record the link heights.
	"""
	y = prepare_matrix(pattern.item)
	Z = linkage(y, method='average', metric='hamming')
	for row in Z:
		pattern.link_heights.append(row[2])

def compute_model(learned_site):
	"""
	Compute centroid, mean and std for each pattern.
	@parameter
	learned_site: patterns for learned_site.name, centroid, size, mean and std are not set.
	@return
	learned_site: centroid, size, mean and std are set, link_heights. Performs in-place operation.
	"""
	for pattern in learned_site.pattern:
		# set size and centroid
		centroid = np.zeros((64,), dtype=int)
		for item in pattern.item:
			simhash = item.simhash
			base = 1
			for index in range(64):
				if simhash & base:
					centroid[index] += 1
				base = base << 1
		pattern.size = len(pattern.item)
		for c in centroid:
			pattern.centroid.append(long(c))
		compute_deprecated_stats(pattern)
		compute_hierarchical_stats(pattern)
	return learned_site

def compute_model_old(learned_site):
	"""
	Deprecated
	This method is deprecated because the comptation cost is high.
	But can be used to verify implementation of new method.

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
		for i in range(pattern_size):
			dist_i = 0
			for j in range(pattern_size):
				# doesn't compute the distance to the pattern itself
				if i == j:
					continue
				dist_i += item_list[j].count * hamming_distance(item_list[i].simhash, item_list[j].simhash)
			for j in range(item_list[i].count):
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

def ScipyHierarchicalClustering(cluster_config, observed_site):
	valid_instance(cluster_config, CD.ClusterConfig)
	valid_instance(observed_site, CD.SiteObservations)
	simhash_item_vector = aggregate_simhash(observed_site, cluster_config.simhash_type)
	vector_size = len(simhash_item_vector)
	learned_site = CD.SitePatterns()
	learned_site.name = observed_site.name

	if vector_size == 0:
		return None
	elif vector_size == 1:
		# Only one simhash, just one pattern.
		pattern = learned_site.pattern.add()
		for simhash_item in simhash_item_vector:
			item = pattern.item.add()
			item.CopyFrom(simhash_item)
	else:
		# suppose there are m observations, there will be m-1 links in
		# the clustering. Specifying the cluster algorithm to use depth
		# m-1, will take into consideration of all the links in the
		# sub-trees.
		y = prepare_matrix(simhash_item_vector)
		'''
		Z = linkage(y, method='average', metric='hamming')
		cluster_label = fcluster(Z, t = cluster_config.algorithm.inconsistent_coefficient,
				criterion='inconsistent',
				depth = cluster_config.algorithm.inconsistent_depth)
		cluster_label = fclusterdata(X = y, t = cluster_config.algorithm.inconsistent_coefficient, 
				criterion = 'inconsistent',
				depth = cluster_config.algorithm.inconsistent_depth,
				metric = 'hamming', method = 'average')
		'''
		cluster_label = fclusterdata(X = y, t = cluster_config.algorithm.inconsistent_coefficient, 
				criterion = 'inconsistent',
				depth = vector_size - 1,
				metric = 'hamming', method = 'average')
		clusters = get_indexes(cluster_label)
		for cluster in clusters:
			pattern = learned_site.pattern.add()
			for index in cluster:
				item = pattern.item.add()
				item.CopyFrom(simhash_item_vector[index])
	# Compute the cluster information.
	learned_site = compute_model(learned_site)
	return learned_site

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
	if vector_size == 0:
		return None
	elif vector_size <= cluster_config.minimum_cluster_size:
		# Only one simhash, just one pattern.
		pattern = learned_site.pattern.add()
		for simhash_item in simhash_item_vector:
			item = pattern.item.add()
			item.CopyFrom(simhash_item)
	else:
		dist_mat, weight_list = distance_matrix(simhash_item_vector)
		if not cluster_config.use_simhash_count:
			weight_list = np.ones(vector_size, dtype = int)
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

