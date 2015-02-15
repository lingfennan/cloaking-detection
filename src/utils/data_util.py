"""
Example Usage:
	# append path prefix to path in file, from file_list
	# Note: prefix is the path prescending data/XXX, for example ../../data/XXX, "../../" should be the prefix
	ls ../../data/abusive_words_9_category.computed/*.list | python data_util.py -f append_prefix -p prefix

	# create the crawl_log file list for simhash_computer to compute
	# Note: prefix is the path prescending data/XXX, for example ../../data/XXX, "../../" should be the prefix
	ls ../../data/abusive_words_9_category.selenium.crawl/*.google | python data_util.py -f compute_list -p prefix -o outfile

	# intersect observed sites
	ls ../../data/abusive_words_9_category.selenium.crawl/*.cloaking | python data_util.py -f intersect_sites -o outfile

	# visit site list periodically. In order to generate plots.
	python data_util.py -f collect_observations -i site_list -l server_link -o outdir -m user
	
	# output the simhash from ObservedSites or LearnedSites for plotting purpose.
	python data_util.py -f plot_simhash -i sites_file [-o outfile] -s DOM\TEXT -t LearnedSites\ObservedSites

	# output the distance between simhashes from ObservedSites or LearnedSites for plotting and model
	# checking purpose. Flag -a, --avg_dist is a switch to use average
	# not.
	python data_util.py -f plot_sim_distance -i sites_file [-o outfile] -s DOM\TEXT -t LearnedSites\ObservedSites [-a]

	# get_domains, this is used to generate a domain list for get domain
	# scores to use
	ls ../../data/all.computed/* | python data_util.py -f get_domains -o ../../data/all.computed/all_domains

	# get_domain_scores
	python data_util.py -f get_domain_scores -i ../../data/all.computed/all_domains -o ../../data/all.computed/all_domains.score

	# remove duplicate websites, ad/search.user.list is the input
	# This funciton will fetch dom and text observed sites for each item in list, compare
	# with dom and text observed sites by Google, if there is exact
	# duplicate, then remove.
	# 
	# Remove failures now. remove the crawl failure ones.
	python data_util.py -f dedup -i computed_crawl_list

	# filter observed sites
	python data_util.py -f domain_filter -i ../../data/all.computed/filter_list

	# merge sites
	ls ../data/all.computed/*.intersect | python data_util.py -f merge_sites -o ../../data/all.computed/search.detection_results

	# de-noise sites
	python data_util.py -f de_noise -i <inputfile> -t <proto_type> [-o <outfile>]
"""

import math
import os
import random
import subprocess
import sys, getopt
import time
# For REMOTE_DRIVER
import util
import logging
#from export_db_cloaking_websites import export_db_to_file
from learning_detection_util import _split_path_by_data, show_proto, sites_file_path_set, intersect_observed_sites, read_proto_from_file, write_proto_to_file, aggregate_simhash
from learning_detection_util import hamming_distance, merge_observed_sites, valid_instance
from learning_detection_util import interact_query, de_noise, get_simhash_type
from crawl_util import collect_site_for_plot
from util import evaluation_form, top_domain
from url_filter import get_bad
from wot import domain_scores
import proto.cloaking_detection_pb2 as CD



def get_learned_eval(learned_file, observed_file):
	learned_sites = CD.LearnedSites()
	read_proto_from_file(learned_sites, learned_file)
	observed_sites = CD.ObservedSites()
	read_proto_from_file(observed_sites, observed_file)
	observed_sites_list = list()
	for observed_site in observed_sites.site:
		observed_sites_list.append(observed_site.name)
	learned_sites_map = dict()
	for learned_site in learned_sites.site:
		learned_sites_map[learned_site.name] = learned_site
	result_sites = CD.LearnedSites()
	for site_name in observed_sites_list:
		if site_name not in learned_sites_map:
			print "Detected cloaking: {0} not in learned sites, \
					Strange!".format(site_name)
			continue
		result_site = result_sites.site.add()
		result_site.CopyFrom(learned_sites_map[site_name])
	return result_sites

def load_split_observed_sites(filename):
	if not os.path.exists(filename):
		count = 0
		split_files = list()
		while True:
			split_file = filename.replace('list', 'list_' +
					str(count))
			if not os.path.exists(split_file):
				break
			split_files.append(split_file)
			count += 1
		observed_sites = merge_observed_sites(split_files)
	else:
		observed_sites = CD.ObservedSites()
		read_proto_from_file(observed_sites, filename)
	return observed_sites

def build_site_simhash_dict(observed_sites):
	"""
	Return two dict, one maps site name to all the simhashs,
	the other maps site name to observed site
	"""
	valid_instance(observed_sites, CD.ObservedSites)
	site_simhash_dict = dict()
	observed_sites_dict = dict()
	attr_name = get_simhash_type(observed_sites.config.simhash_type)
	for observed_site in observed_sites.site:
		if not observed_site.name in site_simhash_dict:
			site_simhash_dict[observed_site.name] = set()
			observed_sites_dict[observed_site.name] = observed_site
		for observation in observed_site.observation:
			site_simhash_dict[observed_site.name].add(getattr(observation,
				attr_name))
	return site_simhash_dict, observed_sites_dict

def _add_observed_site(to_observed_sites, observed_sites_dict, site_name):
	"""
	Performs in place operation
	"""
	observed_site = to_observed_sites.site.add()
	observed_site.CopyFrom(observed_sites_dict[site_name])

def dedup(text_file):
	"""
	1. dom_file, google_text_file, google_dom_file are deducted from text_file
	2. google files can be split. we first check whether unsplit exisits, if
	not we merge all the split ones.
	3. The observed sites are output to correponding filename + '.dedup'

	@parameter
	text_file: text observed sites file
	@return
	number of websites after deduplicate
	"""
	dom_file = text_file.replace('text', 'dom')
	user_text_observed_sites = CD.ObservedSites()
	read_proto_from_file(user_text_observed_sites, text_file)
	logger = logging.getLogger("global")
	logger.info("processing {0}".format(text_file))
	logger.info("before dedup: {0}".format(len(user_text_observed_sites.site)))
	user_dom_observed_sites = CD.ObservedSites()
	read_proto_from_file(user_dom_observed_sites, dom_file)
	google_text_file = text_file.replace('user', 'google')
	google_text_observed_sites = load_split_observed_sites(google_text_file)
	google_dom_file = dom_file.replace('user', 'google')
	google_dom_observed_sites = load_split_observed_sites(google_dom_file)

	user_text_dict, user_text_sites_dict = build_site_simhash_dict(user_text_observed_sites)
	user_dom_dict, user_dom_sites_dict = build_site_simhash_dict(user_dom_observed_sites)
	google_text_dict, google_text_sites_dict = build_site_simhash_dict(google_text_observed_sites)
	google_dom_dict, google_dom_sites_dict = build_site_simhash_dict(google_dom_observed_sites)

	# how to define exact match
	user_text_remained = CD.ObservedSites()
	user_dom_remained = CD.ObservedSites()
	google_text_remained = CD.ObservedSites()
	google_dom_remained = CD.ObservedSites()
	text_failure = set([0])
	failure_count = 0
	# if the feature set is empty, then this is the hash value.
	text_zero = set([18446744073709551615])
	zero_count = 0
	google_failure_count = 0
	google_zero_count = 0
	for site_name in user_text_dict:
		if ((not site_name in google_text_dict) or
				(not site_name in google_dom_dict)):
			continue
		if (user_text_dict[site_name] == text_failure):
			failure_count += 1
			continue
		elif (user_text_dict[site_name] == text_zero):
			zero_count += 1
			continue
		elif (google_text_dict[site_name] == text_failure):
			google_failure_count += 1
			continue
		elif (google_text_dict[site_name] == text_zero):
			google_zero_count += 1
			continue
		text_common = user_text_dict[site_name] & google_text_dict[site_name] 
		dom_common = user_dom_dict[site_name] & google_dom_dict[site_name]
		if (text_common == user_text_dict[site_name] and 
				dom_common == user_dom_dict[site_name]):
			continue
		else:
			_add_observed_site(user_text_remained, user_text_sites_dict, site_name)
			_add_observed_site(user_dom_remained, user_dom_sites_dict, site_name)
			_add_observed_site(google_text_remained, google_text_sites_dict, site_name)
			_add_observed_site(google_dom_remained, google_dom_sites_dict, site_name)

	user_text_remained.config.CopyFrom(user_text_observed_sites.config)
	user_dom_remained.config.CopyFrom(user_dom_observed_sites.config)
	google_text_remained.config.CopyFrom(google_text_observed_sites.config)
	google_dom_remained.config.CopyFrom(google_dom_observed_sites.config)
	write_proto_to_file(user_text_remained, text_file + ".dedup")
	write_proto_to_file(user_dom_remained, dom_file + ".dedup")
	write_proto_to_file(google_text_remained, google_text_file + ".dedup")
	write_proto_to_file(google_dom_remained, google_dom_file + ".dedup")
	logger.info("after dedup: {0}".format(len(user_text_remained.site)))
	logger.info("failure count: {0}, zero feature count: {1}".format(failure_count, zero_count))
	logger.info("google failure count: {0}, google zero feature \
			count: {1}".format(google_failure_count, google_zero_count))
	return len(user_text_remained.site)


def _output_sample_sites(original_label_list, filenames, outfile):
	"""
	Output the sample sites, either google or user

	@parameter
	oringinal_label_list: the selected websites
	filenames: observed sites filenames
	outfile: output filename
	"""
	observed_sites = merge_observed_sites(filenames)
	observed_sites_map = dict()
	for observed_site in observed_sites.site:
		observed_sites_map[observed_site.name] = observed_site
	sample_sites = CD.ObservedSites()
	sample_sites.config.CopyFrom(observed_sites.config)
	sample_list = list()
	for label in original_label_list:
		sample_list.append(observed_sites_map[label])
	for observed_site in sample_list:
		sample_site = sample_sites.site.add()
		sample_site.CopyFrom(observed_site)
	write_proto_to_file(sample_sites, outfile)

def _replace_list_by(to_replace_list, src, dst):
	valid_instance(to_replace_list, list)
	return [item.replace(src, dst) for item in to_replace_list]

def sample(text_filenames, outfile, sample_size):
	dom_filenames = _replace_list_by(text_filenames, 'text', 'dom')
	google_text_filenames = _replace_list_by(text_filenames, 'user',
			'google')
	google_dom_filenames = _replace_list_by(dom_filenames, 'user', 'google')

	text_observed_sites = merge_observed_sites(text_filenames)
	observed_site_list = list()
	url_set = set()
	for observed_site in text_observed_sites.site:
		observed_site_list.append(observed_site)
		for observation in observed_site.observation:
			url_set.add(observation.landing_url)
	logger = logging.getLogger("global")
	logger.info("there are {0} urls".format(len(url_set)))
	logger.info("there are {0} observed sites".format(len(observed_site_list)))
	random.shuffle(observed_site_list)
	# test_size is number of sites, actual observation should be more than this.
	sample_sites = CD.ObservedSites()
	sample_sites.config.CopyFrom(text_observed_sites.config)
	sample_list = observed_site_list[0:sample_size]
	original_label_list = [observed_site.name for observed_site in sample_list]
	for observed_site in sample_list:
		sample_site = sample_sites.site.add()
		sample_site.CopyFrom(observed_site)
	sample_filename = outfile + ".user.sample.text"
	write_proto_to_file(sample_sites, sample_filename)


	_output_sample_sites(original_label_list, dom_filenames, outfile + ".user.sample.dom")
	_output_sample_sites(original_label_list, google_text_filenames,
			outfile + '.google.sample.text')
	_output_sample_sites(original_label_list, google_dom_filenames, outfile
			+ '.google.sample.dom')

def get_domains(observed_sites_list, outfile):
	domain_set = set()
	for filename in observed_sites_list:
		observed_sites = CD.ObservedSites()
		read_proto_from_file(observed_sites, filename)
		for site in observed_sites.site:
			for observation in site.observation:
				url_domain = top_domain(observation.landing_url)
				domain_set.add(url_domain)
	open(outfile, 'w').write("\n".join(domain_set))

def simhash_vector_distance(simhash_item_vector, avg_dist=True):
	"""
	Give simhash item vector (s1, c1), (s2, c2), (s3, c3), compute one of the following two
	1. average distance list
	[avg(s1 to rest), avg(s2 to rest), avg(s3 to rest)]
	2. distance list
	[(s1, s2), (s1, s3), (s2, s3)]
	"""
	# compute the distance array
	# the average distance list
	avg_dist_list = list()
	# the distance list
	dist_list = list()
	# the number of distinct simhashs
	pattern_size = len(simhash_item_vector)
	if avg_dist:
		if pattern_size == 1:
			return [0]
		for i in xrange(pattern_size):
			dist_i = 0
			for j in xrange(pattern_size):
				# doesn't compute the distance to the pattern itself
				if i == j:
					continue
				dist_i_j = hamming_distance(simhash_item_vector[i].simhash, \
						simhash_item_vector[j].simhash)
				dist_i += dist_i_j
			avg_dist_list.append(float(dist_i) / (pattern_size - 1))
		return avg_dist_list
	else:	
		for i in range(pattern_size):
			for j in range(i+1, pattern_size):
				dist_i_j = hamming_distance(simhash_item_vector[i].simhash, \
						simhash_item_vector[j].simhash)
				dist_list.append(dist_i_j)
		return dist_list

def plot_sim_distance(inputfile, outfile, simhash_type, proto_type,
		avg_dist=True):
	simhash_type = get_simhash_type(simhash_type, True)
	sites = getattr(CD, proto_type)()
	read_proto_from_file(sites, inputfile)
	out_f = open(outfile, "w")
	if proto_type == "LearnedSites":
		for learned_site in sites.site:
			out_f.write(learned_site.name + "," + str(len(learned_site.pattern)) + "\n")
			for pattern in learned_site.pattern:
				dist_list = simhash_vector_distance(pattern.item,
						avg_dist)
				out_f.write("pattern\n" + "\n".join([str(d) for d in
					dist_list]) + "\n")
		out_f.close()
	elif proto_type == "ObservedSites":
		for observed_site in sites.site:
			out_f.write(observed_site.name + "," + str(len(observed_site.observation)) + "\n")
			simhash_item_vector = aggregate_simhash(observed_site, simhash_type)
			dist_list = simhash_vector_distance(simhash_item_vector,
					avg_dist)
			out_f.write("\n".join([str(d) for d in dist_list]) + "\n")
		out_f.close()
	else:
		raise Exception("Wrong proto! Only LearnedSites and ObservedSites can be used!")

def plot_simhash(inputfile, outfile, simhash_type, proto_type):
	simhash_type = get_simhash_type(simhash_type)
	sites = getattr(CD, proto_type)()
	read_proto_from_file(sites, inputfile)
	out_f = open(outfile, "w")
	if proto_type == "LearnedSites":
		for site in sites.site:
			observation_size = 0
			for pattern in site.pattern:
				for item in pattern.item:
					observation_size += item.count
			out_f.write(site.name + "," + str(observation_size) + "\n")
			for pattern in site.pattern:
				for item in pattern.item:
					item_str = "%0.16x" % item.simhash
					item_str_array = [item_str for i in range(item.count)]
					out_f.write("\n".join(item_str_array) + "\n")
		out_f.close()
	elif proto_type == "ObservedSites":
		for site in sites.site:
			out_f.write(site.name + "," + str(len(site.observation)) + "\n")
			for observation in site.observation:
				simhash_str = "%0.16x" % getattr(observation, simhash_type)
				out_f.write(simhash_str + "\n")
		out_f.close()
	else:
		raise Exception("Wrong proto! Only LearnedSites and ObservedSites can be used!")

def compute_list(crawl_log_list, outfile, prefix):
	open(outfile, 'w').write("\n".join(crawl_log_list))
	append_prefix([outfile], prefix)

def append_prefix(inputfile_list, prefix):
	for filename in inputfile_list:
		path_list = filter(bool, open(filename, 'r').read().split('\n'))
		path_list = [prefix + "data" + _split_path_by_data(path, 1) for path in path_list]
		open(filename, 'w').write("\n".join(path_list))

def main(argv):
	has_function = False
	help_msg = """data_util.py -f <function> [-p <prefix>][-p <prefix> -o
	<outfile>][-i <inputfile> -t <proto_type>][-o <outfile>][-i <site_list>
	-l <server_link> -o <outdir> -m <mode>][-i <inputfile>-o <outfile> -s
	<simhash_type> -t <proto_type>][-i <inputfile> -o <outfile> -s
	<simhash_type> -t <proto_type> -a] [-o <outfile>] [-i <inputfile> -o
	<outfile>] [-i <inputfile>] [-i <text_filt>] [-i <inputfile> -c <count>
	-o <outfile>] [-o <outfile>] [-i <inputfile> -l <leanredfile> -o <outfile>], valid functions are
	append_prefix, compute_list, show_proto, intersect_sites,
	collect_observations, plot_simhash, plot_sim_distance, get_domains,
	get_domain_scores, domain_filter, dedup, sample, merge_sites,
	get_learned_eval, [-i <table_name> -o <outfie>] export_db
	[-i <inputfile> -o <outfile>] de_noise"""
	try:
		opts, args = getopt.getopt(argv, "hf:p:o:t:i:m:l:s:ac:",
				["function=", "prefix=", "outfile=",
					"proto_type=", "ifile=", "mode=",
					"link=", "simhash_type=", "avg_dist",
					"count"])
	except getopt.GetoptError:
		print help_msg
		sys.exit(2)
	hasinputfile = False
	outfile = None
	avg_dist = False
	for opt, arg in opts:
		if opt == "-h":
			print help_msg
			sys.exit()
		elif opt in ("-f", "--function"):
			function = arg
			has_function = True
		elif opt in ("-p", "--prefix"):
			prefix = arg
		elif opt in ("-o", "--outfile"):
			outfile = arg
		elif opt in ("-i", "--ifile"):
			inputfile = arg
			hasinputfile = True
		elif opt in ("-t", "--proto_type"):
			proto_type = arg
		elif opt in ("-m", "--mode"):
			mode = arg
		elif opt in ("-l", "--link"):
			link = arg
		elif opt in ("-s", "--simhash_type"):
			simhash_type = arg
		elif opt in ("-a", "--avg_dist"):
			avg_dist = True
		elif opt in ("-c", "--count"):
			count = arg
		else:
			print help_msg
			sys.exit(2)
	if hasinputfile:
		logging.basicConfig(filename= inputfile + "_running_log_" + function, level=logging.DEBUG)
		logging.getLogger("global")
	if not has_function:
		print help_msg
		sys.exit()
	if function == "append_prefix":
		inputfile_list = [line[:-1] for line in sys.stdin]
		append_prefix(inputfile_list, prefix)
	elif function == "compute_list":
		crawl_log_list = [line[:-1] for line in sys.stdin]
		compute_list(crawl_log_list, outfile, prefix)
	elif function == "show_proto":
		show_proto(inputfile, proto_type)
	elif function == "intersect_sites":
		observed_sites_list = [line[:-1] for line in sys.stdin]
		result_sites = intersect_observed_sites(*observed_sites_list)
		write_proto_to_file(result_sites, outfile)
		evaluation_form(outfile, outfile + ".eval", "ObservedSites")
	elif function == "collect_observations":
		if link:
			util.REMOTE_DRIVER = link
		site_list = filter(bool, open(inputfile, 'r').read().split('\n'))
		site_set = set(site_list)
		outdir = outfile
		collect_site_for_plot(site_set, outdir, mode)
	elif function == "plot_simhash":
		if not outfile:
			outfile = inputfile + ".plot_cluster"
		plot_simhash(inputfile, outfile, simhash_type, proto_type)
	elif function == "plot_sim_distance":
		if not outfile:
			outfile = inputfile + ".plot_sim_distance"
		plot_sim_distance(inputfile, outfile, simhash_type, proto_type,
				avg_dist)
	elif function == "get_domains":
		observed_sites_list = [line[:-1] for line in sys.stdin]
		get_domains(observed_sites_list, outfile)
	elif function == "get_domain_scores":
		domains = filter(bool, open(inputfile, 'r').read().split('\n'))
		result = domain_scores(domains, outfile)
	elif function == "domain_filter":
		"""
		Three steps for computed sites.
		1. filter known benign
		2. de-duplicate
		3. sample $count number of sites
		"""
		bar_points = 60
		observed_sites_list = filter(bool, open(inputfile, 'r').read().split('\n'))
		for filename in observed_sites_list:
			get_bad(bar_points, filename, filename + ".filt")
	elif function == "dedup":
		text_filenames = filter(bool, open(inputfile, 'r').read().split('\n'))
		count = 0
		for filename in text_filenames:
			if ((not 'text' in filename) or ('google' in filename) or
					('dom' in filename)):
				response = interact_query("The input file doesn't seem to \
						be valid! Press [Yes/No] to continue or exit!")
				if not response:
					sys.exit(0)
			count += dedup(filename)

		logger = logging.getLogger("global")
		logger.info("total sites after dedup: {0}".format(count))
	elif function == "sample":
		text_filenames = filter(bool, open(inputfile, 'r').read().split('\n'))
		sample(text_filenames, outfile, int(count))
		evaluation_form(outfile + '.user.sample.text', outfile +
				".user.sample.text.eval", "ObservedSites")
		evaluation_form(outfile + '.google.sample.text', outfile +
				".google.sample.text.eval", "ObservedSites")
	elif function == "merge_sites":
		observed_sites_names = [line[:-1] for line in sys.stdin]
		observed_sites = merge_observed_sites(observed_sites_names)
		logger = logging.getLogger("global")
		logger.info("total sites after merge: {0}".format(len(observed_sites.site)))
		write_proto_to_file(observed_sites, outfile)
	elif function == "get_learned_eval":
		"""
		-l learned_file -i detected_file
		"""
		learned_file = link
		observed_file = inputfile
		result_sites = get_learned_eval(learned_file, observed_file)
		write_proto_to_file(result_sites, outfile)
		evaluation_form(outfile, outfile + ".eval", "LearnedSites")
	elif function == "export_db":
		"""
		-i table_name -o outfile
		"""
		export_db_to_file(inputfile, outfile)
		export_db_to_file(inputfile, outfile + ".noise", ["PageBroken"])
	elif function == "de_noise":
		"""
		remove noise: index.html not found, feature count = 0
		"""
		if "learn" in inputfile:
			response = interact_query("The input file seems to \
					be learned sites, we only support observed \
					sites! Press [Yes/No] to continue or exit!")
			if not response:
				sys.exit(0)

		logger = logging.getLogger("global")
		logger.info("processing {0}".format(inputfile))
		de_noise_config = CD.DeNoiseConfig()
		de_noise_config.zero_feature = True
		original = CD.ObservedSites()
		read_proto_from_file(original, inputfile)
		observed_sites = de_noise(original, de_noise_config)
		logger.info("before de-noise {0}".format(len(original.site)))
		logger.info("after de-noise: {0}".format(len(observed_sites.site)))
		outfile = outfile if outfile else inputfile
		write_proto_to_file(observed_sites, outfile)
	else:
		print help_msg
		sys.exit(2)

if __name__ == "__main__":
	main(sys.argv[1:])

