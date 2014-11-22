from learning_detection_util import load_observed_sites, write_proto_to_file, read_proto_from_file, valid_instance
import proto.cloaking_detection_pb2 as CD

crawl_log = CD.CrawlLog()
in_filename = '../../data/US_web_search_list.Chrome.20141110-185317.selenium.crawl/crawl_log'
read_proto_from_file(crawl_log, in_filename)
suc_counter = 0
fail_counter = 0
for result in crawl_log.result:
	if result.success:
		suc_counter += 1
	else:
		fail_counter += 1

print suc_counter
print fail_counter
# print crawl_log

learned_sites = CD.LearnedSites()
in_filename = '../../data/US_web_search_list.Chrome.20141110-185317.selenium.crawl/20141110_crawl_log.dom.learned'
read_proto_from_file(learned_sites, in_filename)
print learned_sites
# suc_counter = 0
# fail_counter = 0
# for result in crawl_log.result:
# 	if result.success:
# 		suc_counter += 1
# 	else:
# 		fail_counter += 1
# 
# print suc_counter
# print fail_counter
