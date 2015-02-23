"""
1. Do statistics about the dataset and aims at help
tuning the parameters.
2. Collect stats for writing paper.
Example Usage:
	# histogram the number of features extracted from each observation. feature type is TEXT or DOM
	python statistics.py -f feature_hist -i inputfile -t feature_type

	# count failure in inputfile. This stat can be used to estimated the success rate of visiting.
	python statistics.py -f count_failure -i inputfile -l links_to_check
"""

import numpy as np
import sys, getopt
import matplotlib.pyplot as plt
import pylab as pl
from learning_detection_util import write_proto_to_file, read_proto_from_file
import proto.cloaking_detection_pb2 as CD

def feature_hist(filename, feature_type, allow_repeat = True):
	if feature_type == "TEXT":
		count_attr_name = "text_feature_count"
		simhash_attr_name = "text_simhash"
	elif feature_type == "DOM":
		count_attr_name = "dom_feature_count"
		simhash_attr_name = "dom_simhash"
	else:
		print "Wrong type of feature {0}".format(feature_type)
		return
	observed_sites = CD.ObservedSites()
	read_proto_from_file(observed_sites, filename)
	feature_count_list = list()
	count = 0
	ob_count = 0

	added_site_set = set()
	for site in observed_sites.site:
		count += 1
		ob_count += len(site.observation)
		if not allow_repeat:
			if site.name in added_site_set:
				continue
			else:
				added_site_set.add(site.name)
		for observation in site.observation:
			feature_count = getattr(observation, count_attr_name)
			simhash_value = getattr(observation, simhash_attr_name)
			if feature_count < 4:
				print observation
			feature_count_list.append(feature_count)
	print "there are {0} websites".format(count)
	print "there are {0} urls".format(ob_count)
	feature_count_array = np.array(feature_count_list)
	for i in range(len(feature_count_array)):
		feature_count_array[i] += 1

	MIN, MAX = 1, 100000 if feature_type == "TEXT" else 1000 
	#feature_count_array = np.log2(np.add(feature_count_array, 1))
	#hist, bins = np.histogram(feature_count_array, bins=np.logspace(MIN,
	#	MAX, 50))

	pl.figure()
	pl.hist(feature_count_array, bins=10 ** np.linspace(np.log10(MIN),
		np.log10(MAX), 50), color='black', alpha=0.5)
	pl.gca().set_xscale("log")
	pl.title(feature_type.lower() + ' feature count statistics', fontsize=20)
	pl.ylabel('Number of Websites', fontsize=20)
	pl.xlabel('Number of extracted ' + feature_type.lower() + ' features', fontsize=20)
	#pl.show()
	pl.savefig(filename + ".pdf")
	"""
	hist, bins = np.histogram(feature_count_array, bins=10 **
			np.linspace(np.log10(MIN), np.log10(MAX), 50))
	print hist, bins 
	width = 0.7 * (bins[1] - bins[0])
	center = (bins[:-1] + bins[1:]) / 2
	fig, ax = plt.subplots()
	ax.bar(center, hist, align='center', width=width)
	ax.set_xscale('log')
	# pyplot.yscale('log')
	fig.savefig(filename + ".svg")
	"""

def suc_fail_counter(filename, links_to_check):
	links_to_check = links_to_check.split(',') if links_to_check else list()
	crawl_log = CD.CrawlLog()
	read_proto_from_file(crawl_log, filename)
	suc_counter = 0
	fail_counter = 0
	for result_search in crawl_log.result_search:
		for result in result_search.result:
			for link in links_to_check:
				if link == result.url:
					print result.url
					if result.success:
						print "succeeded and file path is:\n{0}".format(result.file_path)
					else:
						print "failed"
				elif link == result.landing_url:
					print result.landing_url
					if result.success:
						print "succeeded and file path is:\n{0}".format(result.file_path)
					else:
						print "failed"
			if result.success:
				suc_counter += 1
			else:
				fail_counter += 1
	print 'succeeded: {0}'.format(suc_counter)
	print 'failed: {0}'.format(fail_counter)

def main(argv):
	has_function = False
	help_msg = "statistics.py -f <function> [-i <inputfile> -t <feature_type> -a] [-i <inputfile> -l <links_to_check>], valid functions are feature_hist, count_failure"
	try:
		opts, args = getopt.getopt(argv, "hf:i:t:l:a", ["function=",
			"ifile=", "type=", "links=", "allow_repeat"])
	except getopt.GetoptError:
		print help_msg
		sys.exit(2)
	links_to_check = None
	allow_repeat = False
	for opt, arg in opts:
		if opt == "-h":
			print help_msg
			sys.exit()
		elif opt in ("-f", "--function"):
			function = arg
			has_function = True
		elif opt in ("-i", "--ifile"):
			inputfile = arg
		elif opt in ("-t", "--type"):
			feature_type = arg
		elif opt in ("-l", "--links"):
			links_to_check = arg
		elif opt in ("-a", "--allow_repeat"):
			allow_repeat = True
		else:
			print help_msg
			sys.exit(2)
	if not has_function:
		print help_msg
		sys.exit()
	if function == "feature_hist":
		feature_hist(inputfile, feature_type, allow_repeat)
	elif function == "count_failure":
		suc_fail_counter(inputfile, links_to_check)
	else:
		print help_msg
		sys.exit(2)

if __name__ == "__main__":
	main(sys.argv[1:])

