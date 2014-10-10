import collections
import re
import sys
from urllib import urlencode
from urlparse import urlparse, urlunparse, parse_qs
import proto.cloaking_detection_pb2 as CD

def _strip_parameter(link):
	parsed_link = urlparse(link)
	query = parse_qs(parsed_link.query)
	for key in query:
		query[key] = ''
	parsed_link = parsed_lnk._replace(query=urlencode(query, True))
	return urlunparse(parsed_link)

def load_observed_sites(site_list_filenames):
	observed_sites = CD.ObservedSites()
	site_observations_map = dict()
	for site_list_filename in site_list_filenames:
		site_list = filter(bool, open(site_list_filename, 'r').read().split('\n'))
		site_list = [path_link.split(',') for path_link in site_list]
		for path, link in site_list:
			site_observations_map[_strip_parameter(link)].append([link, path])
	for site in site_observations_map:
		observed_site = observed_sites.site.add()
		observed_site.name = site
		for link, path in site_observations_map[site]:
			observation = observed_site.observation.add()
			observation.landing_url = link 
			observation.file_path = path 
	return observed_sites

if __name__=="__main__":
	link = 'http://www.walmart.com/search/search-ng.do?search_query=Bicycles&adid=222222    22220202379358&wmlspartner=wmtlabs&wl0=e&wl1=g&wl2=c&wl3=30633615476&wl4=&veh=sem'
	print link
	print _strip_parameter(link)
	site_list_filenames = ['utils/data/US_list_10.20141010-180519.selenium.crawl/html_path_list']
	print load_observed_sites(site_list_filenames)

