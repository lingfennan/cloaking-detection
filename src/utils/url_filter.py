import sys, getopt, math
from threading import Thread
from learning_detection_util import write_proto_to_file, read_proto_from_file, valid_instance, average_distance, centroid_distance, read_proto_from_file
from thread_computer import ThreadComputer
import proto.cloaking_detection_pb2 as CD
import wot



def get_domain(landing_url):
	return landing_url.url.split('://')[-1].split('/')[0]

def getbad(argv,filename, outfilename):
	observed_sites = CD.ObservedSites()
	read_proto_from_file(observed_sites, filename)
	domain_set = set();

	for site in observed_sites.site:
		for observation in site.observation:
			url_domain = get_domain(observation.landing_url)
			domainSet.add(url_domain)

	domain_list = list(domain_set)
	bad_domains = wot.filt(domain_list)
	bad_observed_sites = CD.ObservedSites()

	for site in observed_sites.site:
		for observation in site.observation:
			if url_domain in bad_domains:
				to_add = bad_observed_sites.site.add()
				to_add.CopyFrom(observation)

	write_proto_from_file(bad_observed_sies, outfilename)
			

if __name__=="__main__":
	getbad(sys.argv[1:])
	

