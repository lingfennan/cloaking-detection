import sys, getopt, math
from threading import Thread
from learning_detection_util import write_proto_to_file, read_proto_from_file, valid_instance, average_distance, centroid_distance, read_proto_from_file
from thread_computer import ThreadComputer
import proto.cloaking_detection_pb2 as CD
import wot



def get_domain(landing_url):
	return landing_url.split('://')[-1].split('/')[0]

def get_bad(bar_points, filename, outfilename):
	observed_sites = CD.ObservedSites()
	read_proto_from_file(observed_sites, filename)
	domain_set = set();

	for site in observed_sites.site:
		for observation in site.observation:
			url_domain = get_domain(observation.landing_url)
			domain_set.add(url_domain)

	domain_list = list(domain_set)
	bad_domains = wot.filt(domain_list,bar_points)
	bad_observed_sites = CD.ObservedSites()


	for site in observed_sites.site:
		observation_list = list()
		for observation in site.observation:
			if get_domain(observation.landing_url) in bad_domains:
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
	

