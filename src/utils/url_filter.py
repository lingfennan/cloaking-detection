"""
Read ObservedSites from inputfile. For each site, filter the trusted domains and output the
remaining to outputfile.

Example Usage:
	python url_filter.py bar_points inputfile outputfile
"""


import sys, getopt, math
from threading import Thread
from learning_detection_util import write_proto_to_file, read_proto_from_file, valid_instance, average_distance, centroid_distance, read_proto_from_file
from thread_computer import ThreadComputer
from util import top_domain
import proto.cloaking_detection_pb2 as CD
import wot


def get_domain_reputation(domain_list, bar_points, 
		domain_database = '../../data/all.computed/all_domains.scores'):
	if not domain_database:
		print "Querying WOT service..."
		domain_database = '../../data/all.computed/all_domains.scores'
		wot.domain_scores(domain_list, domain_database)
		return get_domain_reputation(domain_list, bar_points)
	else:
		score_dict = dict()
		domain_scores = filter(bool, open(domain_database, 'r').read().split('\n'))
		for domain_score in domain_scores:
			domain = domain_score.split(',')[0]
			score = sum([int(s) for s in 
				domain_score.split(',')[1:]]) 
			score_dict[domain] = score
		bad_domain = set()
		unknown_domain = set()
		for domain in domain_list:
			if domain in score_dict:
				if score_dict[domain] <= bar_points:
					bad_domain.add(domain)
			else:
				unknown_domain.add(domain)
		if len(unknown_domain) > 0:
			# call self recursively
			print "Querying WOT service"
			bad_domain = bad_domain | set(wot.filt(unknown_domain, bar_points))
			wot.domain_scores(unknown_domain, domain_database)
		return bad_domain

def get_bad(bar_points, filename, outfilename):
	observed_sites = CD.ObservedSites()
	read_proto_from_file(observed_sites, filename)
	domain_set = set();

	for site in observed_sites.site:
		for observation in site.observation:
			url_domain = top_domain(observation.landing_url)
			domain_set.add(url_domain)

	domain_list = list(domain_set)
	bad_domains = get_domain_reputation(domain_list, bar_points)
	bad_observed_sites = CD.ObservedSites()
	bad_observed_sites.config.CopyFrom(observed_sites.config)

	for site in observed_sites.site:
		observation_list = list()
		for observation in site.observation:
			if top_domain(observation.landing_url) in bad_domains:
				observation_list.append(observation)
		if len(observation_list) == 0:
			continue
		bad_site = bad_observed_sites.site.add()
		bad_site.name = site.name
		for observation in observation_list:
			to_add = bad_site.observation.add()
			to_add.CopyFrom(observation)

	write_proto_to_file(bad_observed_sites, outfilename)
			

if __name__=="__main__":
	get_bad(sys.argv[1],sys.argv[2],sys.argv[3])
	
