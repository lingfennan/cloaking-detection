import MySQLdb
import sys, getopt, math
from threading import Thread
from learning_detection_util import write_proto_to_file, read_proto_from_file, valid_instance, average_distance, centroid_distance, read_proto_from_file
from thread_computer import ThreadComputer
import proto.cloaking_detection_pb2 as CD


def output_db(cursor, output_filename):
	observed_sites = CD.ObservedSites()
	for(url, userFilePath) in cursor:
		site = observed_sites.site.add();
		site.name = url;
		site_observation = site.observation.add();
		site_observation.landing_url = url;
		site_observation.file_path = userFilePath;
	write_proto_to_file(observed_sites, output_filename);
		

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

