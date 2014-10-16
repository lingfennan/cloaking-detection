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
	parsed_link = parsed_link._replace(query=urlencode(query, True))
	return urlunparse(parsed_link)

def load_observed_sites(site_list_filenames):
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
		site_list = filter(bool, open(site_list_filename, 'r').read().split('\n'))
		site_list = [path_link.split(',') for path_link in site_list]
		site_list_path = site_list_filename.split('/')
		prefix = ''
		"""
		Assumes the path follows pattern $PREFIX/data/$DETAIL_PATH
		iterate until we see "data", break and take the previous part as $PREFIX.
		In site_list_filename, only data/$DETAIL_PATH are recorded, therefore append prefix to it.
		"""
		for part in site_list_path:
			if not part == "data":
				prefix += part + "/"
			else:
				break
		relative_path = site_list[0][0]
		for path, link in site_list:
			path = prefix + path
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

def write_proto_to_file(proto, filename):
	f = open(filename, "wb")
	f.write(proto.SerializeToString())
	f.close()

def read_proto_from_file(proto, filename):
	f = open(filename, "rb")
	proto.ParseFromString(f.read())
	f.close()

if __name__=="__main__":
	link = 'http://www.walmart.com/search/search-ng.do?search_query=Bicycles&adid=22222222220202379358&wmlspartner=wmtlabs&wl0=e&wl1=g&wl2=c&wl3=30633615476&wl4=&veh=sem'
	print link
	print _strip_parameter(link)
	site_list_filenames = ['data/US_list_10.20141010-180519.selenium.crawl/html_path_list']
	s, p = load_observed_sites(site_list_filenames)
	print s
	print p

