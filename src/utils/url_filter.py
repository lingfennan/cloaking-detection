import sys, getopt, math
import simhash
from threading import Thread
from html_simhash_computer import HtmlSimhashComputer
from utils.learning_detection_util import write_proto_to_file, read_proto_from_file, valid_instance, average_distance, centroid_d    istance, read_proto_from_file
from utils.thread_computer import ThreadComputer
import utils.proto.cloaking_detection_pb2 as CD
import wot


def main(argv):
	observed_sites = CD.ObservedSites()
	read_proto_from_file(observed_sites, filename)
	domain_set = set();

	for site in observed_sites.site:
		for observation in site.observation:
			url_domain = get_domain(observation.landing_url)
			domainSet.add(url_domain)
	domain_list = list(domain_set)
	bad_domains = wot.filt(domain_list)
	for site in observed_sites.site:
		for observation in site.observation:
			if url_domain in bad_domains:
				to_add = bad_observed_si

			
			
	

