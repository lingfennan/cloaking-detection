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
	# checking purpose. Flag -a, --avg_dist is a switch to use average distance or not.
	python data_util.py -f plot_sim_distance -i sites_file [-o outfile] -s DOM\TEXT -t LearnedSites\ObservedSites [-a -d]
"""

import math
import subprocess
import sys, getopt
import time
# For REMOTE_DRIVER
import util
from learning_detection_util import _split_path_by_data, show_proto, sites_file_path_set, intersect_observed_sites, read_proto_from_file, write_proto_to_file, aggregate_simhash
from learning_detection_util import hamming_distance
from crawl_util import collect_site_for_plot
from util import evaluation_form
import proto.cloaking_detection_pb2 as CD


def _get_simhash_type(simhash_type, return_proto=False):
	if "text" in simhash_type.lower():
		simhash_type = "text_simhash"
		type_proto = CD.TEXT
	elif "dom" in simhash_type.lower():
		simhash_type = "dom_simhash"
		type_proto = CD.DOM
	else:
		raise Exception("wrong type of simhash_type!")
	return simhash_type if not return_proto else type_proto

def simhash_vector_distance(simhash_item_vector, avg_dist=True, dedup=False):
	"""
	Give simhash item vector (s1, c1), (s2, c2), (s3, c3), compute one of the following two
	1. average distance list
	[avg(s1 to rest) * c1, avg(s2 to rest) * c2, avg(s3 to rest) * c3]
	2. distance list, this is actually problematic (TODO)
	[(s1, s2) * c2, (s1, s3) * c3, (s2, s3) *c3]
	"""
	# compute the distance array
	# the number of observations
	total_size = 0
	# the average distance list
	avg_dist_list = list()
	# the distance list
	dist_list = list()
	# the number of distinct simhashs
	pattern_size = len(simhash_item_vector)
	for item in simhash_item_vector:
		total_size += item.count
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
				if dedup:
					dist_i += dist_i_j
				else:
					dist_i += simhash_item_vector[j].count * dist_i_j
			if dedup:
				avg_dist_list.append(float(dist_i) /
					(pattern_size - 1))
				continue
			for j in xrange(simhash_item_vector[i].count):
				avg_dist_list.append(float(dist_i) / (total_size - 1))
		return avg_dist_list
	else:	
		print "This method is problematic when simhash count is more than 1. use with care!"
		for i in range(pattern_size):
			for j in range(i+1, pattern_size):
				dist_i_j = hamming_distance(simhash_item_vector[i].simhash, \
						simhash_item_vector[j].simhash)
				for k in xrange(simhash_item_vector[j].count):
					dist_list.append(dist_i_j)
					if dedup:
						break
		return dist_list

def plot_sim_distance(inputfile, outfile, simhash_type, proto_type,
		avg_dist=True, dedup = False):
	simhash_type = _get_simhash_type(simhash_type, True)
	sites = getattr(CD, proto_type)()
	read_proto_from_file(sites, inputfile)
	out_f = open(outfile, "w")
	if proto_type == "LearnedSites":
		for learned_site in sites.site:
			out_f.write(learned_site.name + "," + str(len(learned_site.pattern)) + "\n")
			for pattern in learned_site.pattern:
				dist_list = simhash_vector_distance(pattern.item, avg_dist, dedup)
				out_f.write("pattern\n" + "\n".join([str(d) for d in
					dist_list]) + "\n")
		out_f.close()
	elif proto_type == "ObservedSites":
		for observed_site in sites.site:
			out_f.write(observed_site.name + "," + str(len(observed_site.observation)) + "\n")
			simhash_item_vector = aggregate_simhash(observed_site, simhash_type)
			dist_list = simhash_vector_distance(simhash_item_vector,
					avg_dist, dedup)
			out_f.write("\n".join([str(d) for d in dist_list]) + "\n")
		out_f.close()
	else:
		raise Exception("Wrong proto! Only LearnedSites and ObservedSites can be used!")

def plot_simhash(inputfile, outfile, simhash_type, proto_type):
	simhash_type = _get_simhash_type(simhash_type)
	sites = getattr(CD, proto_type)()
	read_proto_from_file(sites, inputfile)
	out_f = open(outfile, "w")
	if proto_type == "LearnedSites":
		for site in sites.site:
			site_size = 0
			for pattern in site.pattern:
				site_size += pattern.size
			out_f.write(site.name + "," + str(site_size) + "\n")
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
	<simhash_type> -t <proto_type> -a --dedup], valid functions are
	append_prefix, compute_list, show_proto, intersect_sites,
	collect_observations, plot_simhash, plot_sim_distance"""
	try:
		opts, args = getopt.getopt(argv, "hf:p:o:t:i:m:l:s:ad",
				["function=", "prefix=", "outfile=",
					"proto_type=", "ifile=", "mode=",
					"link=", "simhash_type=", "avg_dist",
					"dedup"])
	except getopt.GetoptError:
		print help_msg
		sys.exit(2)
	outfile = None
	avg_dist = False
	dedup = False
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
		elif opt in ("-d", "--dedup"):
			dedup = True
		else:
			print help_msg
			sys.exit(2)
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
				avg_dist, dedup)
	else:
		print help_msg
		sys.exit(2)

if __name__ == "__main__":
	main(sys.argv[1:])

