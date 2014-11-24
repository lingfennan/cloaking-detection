from learning_detection_util import read_proto_from_file, write_proto_to_file
from learning_detection_util_test import assert_equal
from util import generate_test
import proto.cloaking_detection_pb2 as CD

def test_generate_test():
	filename = "../../data/US_web_search_list.Chrome.20141110-185317.selenium.crawl/crawl_log"
	generate_test(filename)
	text_test = filename + ".text.test"
	text_mismatch = filename + ".text.mismatch"
	dom_test = filename + ".dom.test"
	dom_mismatch = filename + ".dom.mismatch"
	text_test_sites = CD.ObservedSites()
	text_mismatch_sites = CD.ObservedSites()
	dom_test_sites = CD.ObservedSites()
	dom_mismatch_sites = CD.ObservedSites()
	read_proto_from_file(text_test_sites, text_test)
	read_proto_from_file(text_mismatch_sites, text_mismatch)
	read_proto_from_file(dom_test_sites, dom_test)
	read_proto_from_file(dom_mismatch_sites, dom_mismatch)
	assert_equal(len(text_test_sites.site), 5000)
	assert_equal(len(text_mismatch_sites.site), 1000)
	assert_equal(len(dom_test_sites.site), 5000)
	assert_equal(len(dom_mismatch_sites.site), 1000)
	text_test_set = set()
	text_mismatch_set = set()
	dom_test_set = set()
	dom_mismatch_set = set()
	for site in text_test_sites.site:
		text_test_set.add(site.name)
	for site in text_mismatch_sites.site:
		text_mismatch_set.add(site.name)
	for site in dom_test_sites.site:
		dom_test_set.add(site.name)
	for site in dom_mismatch_sites.site:
		dom_mismatch_set.add(site.name)
	assert_equal(text_test_set, dom_test_set)
	assert_equal(text_mismatch_set, dom_mismatch_set)

if __name__=="__main__":
	test_generate_test()
