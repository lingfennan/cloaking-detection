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
"""

import subprocess
import sys, getopt
import time
# For REMOTE_DRIVER
import util
from learning_detection_util import _split_path_by_data, show_proto, sites_file_path_set, intersect_observed_sites, read_proto_from_file, write_proto_to_file
from crawl_util import collect_site_for_plot
from util import evaluation_form
import proto.cloaking_detection_pb2 as CD

def plot_simhash(inputfile, outfile, simhash_type, proto_type):
	if "text" in simhash_type.lower():
		simhash_type = "text_simhash"
	elif "dom" in simhash_type.lower():
		simhash_type = "dom_simhash"
	else:
		raise Exception("wrong type of simhash_type!")
	sites = getattr(CD, proto_type)()
	read_proto_from_file(sites, inputfile)
	out_f = open(outfile, "w")
	if proto_type == "LearnedSites":
		for site in sites.site:
			out_f.write(site.name + "\n")
			for pattern in site.pattern:
				for item in pattern.item:
					item_str = "%0.16x" % item.simhash
					item_str_array = [item_str for i in range(item.count)]
					out_f.write("\n".join(item_str_array) + "\n")
		out_f.close()
	elif proto_type == "ObservedSites":
		for site in sites.site:
			out_f.write(site.name + "\n")
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
	help_msg = "data_util.py -f <function> [-p <prefix>][-p <prefix> -o <outfile>][-i <inputfile> -t <proto_type>][-o <outfile>][-i <site_list> -l <server_link> -o <outdir> -m <mode>][-i <inputfile> -o <outfile> -s <simhash_type> -p <proto_type>], valid functions are append_prefix, compute_list, show_proto, intersect_sites, collect_observations, plot_simhash"
	try:
		opts, args = getopt.getopt(argv, "hf:p:o:t:i:m:l:s:", ["function=", "prefix=", "outfile=", "proto_type=", "ifile=", "mode=", "link=", "simhash_type="])
	except getopt.GetoptError:
		print help_msg
		sys.exit(2)
	outfile = None
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
	else:
		print help_msg
		sys.exit(2)

if __name__ == "__main__":
	main(sys.argv[1:])

