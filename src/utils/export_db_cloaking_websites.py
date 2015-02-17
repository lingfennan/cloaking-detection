import MySQLdb
import sys, getopt, math
from threading import Thread
from learning_detection_util import write_proto_to_file, read_proto_from_file, valid_instance, average_distance, centroid_distance, read_proto_from_file
from thread_computer import ThreadComputer
import proto.cloaking_detection_pb2 as CD

def output_db(cursor, output_filename):
	observed_sites = CD.ObservedSites()
	url_site_map = dict()
	for (url, userFilePath) in cursor:
		if not url in url_site_map:
			url_site_map[url] = CD.SiteObservations()
			url_site_map[url].name = url
		ob = url_site_map[url].observation.add()
		ob.landing_url = url
		ob.file_path = userFilePath
	for url in url_site_map:
		site = observed_sites.site.add();
		site.CopyFrom(url_site_map[url])
	write_proto_to_file(observed_sites, output_filename)

def export_db_to_file(table, outfile, labels=None):
	cnx = MySQLdb.connect(host='localhost',user='root', passwd='asdf', db='LabelDB')
	cursor = cnx.cursor()
	if labels:
		enum = labels
	else:
		enum = ['Adult', 'Pharmacy', 'Cheat', 'Gambling', 'BadDomain', 'Phishing', 'Yes']
	label_str = " OR ".join(["label='" + e +"'" for e in enum])
	query = "SELECT url, userFilePath FROM " + table + " WHERE " + label_str
	print query
	cursor.execute(query)
	# output_db(cursor, 'cloaking_label_weiren')
	output_db(cursor, outfile)

	cursor.close();
	cnx.close();

