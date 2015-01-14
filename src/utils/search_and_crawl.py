"""
Usage:
python search_and_crawl.py $WORD_FILE
"""
import os
import random
import sys
import time
from datetime import datetime
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.common.action_chains import ActionChains
from crawl import UrlFetcher, set_browser_type, hex_md5
from learning_detection_util import valid_instance, write_proto_to_file, read_proto_from_file
from thread_computer import ThreadComputer
from util import start_browser, restart_browser, mkdir_if_not_exist
import proto.cloaking_detection_pb2 as CD

def switch_vpn_state(connected):
	if connected:
		os.system('/opt/cisco/anyconnect/bin/vpn disconnect')
	else:
		os.system('printf "0\nrduan9\nZettaikatu168\ny" | /opt/cisco/anyconnect/bin/vpn -s connect anyc.vpn.gatech.edu')

def wait_get_attribute(elem, value):
	counter = 0
	while counter < 10:
		try:
			attr = elem.get_attribute(value)
			break
		except:
			time.sleep(1)
			counter += 1
			attr = None
	return attr

def wait_find_element(browser, find_by, value):
	counter = 0
	while counter < 10:
		try:
			if find_by == 'id':
				elem = browser.find_element_by_id(value)
			elif find_by == 'class':
				elem = browser.find_element_by_class_name(value)
			elif find_by == 'tag':
				elem = browser.find_element_by_tag_name(value)
			else:
				raise Exception("Unsupported find_by!")
			break
		except:
			time.sleep(1)
			counter += 1
			elem = None
	return elem

def wait_find_elements(browser, find_by, value):
	counter = 0
	while counter < 10:
		try:
			if find_by == 'ids':
				elems = browser.find_elements_by_id(value)
			elif find_by == 'classes':
				elems = browser.find_elements_by_class_name(value)
			elif find_by == 'tags':
				elems = browser.find_elements_by_tag_name(value)
			else:
				raise Exception("Unsupported find_by!")
			break
		except:
			time.sleep(1)
			counter += 1
			elems = []
	return elems

class Search:
	def __init__(self, crawl_config):
		# user_agent should be set.
		self.crawl_config = crawl_config
		set_browser_type(self.crawl_config)
		self.browser = start_browser(self.crawl_config.browser_type, incognito=False,
				user_agent=self.crawl_config.user_agent)
		self.browser.set_page_load_timeout(15)
		switch_vpn_state(True)
		self.connected = False
	
	def __del__(self):
		self.browser.quit()
		if self.connected:
			switch_vpn_state(self.connected)
	
	def ad_links(self):
		clickstring_set = set()
		try:
			ads_ad_list = wait_find_elements(self.browser, 'classes', 'ads-ad')
			for ads_ad in ads_ad_list:
				tags = wait_find_elements(ads_ad, 'tags', 'a')
				for tag in tags:
					clickstring = wait_get_attribute(tag, 'href')
					clickstring_set.add(clickstring)
					break
		except:
			print "error in ad_links"
			print sys.exc_info()[0]
		return clickstring_set

	def search_results(self):
		clickstring_set = set()
		try:
			search_list = wait_find_elements(self.browser, 'classes', 'g')
			for result in search_list:
				title_elem = wait_find_element(result, 'tag', 'h3')
				if title_elem is None:
					continue
				title = title_elem
				link_elem = wait_find_element(title_elem, 'tag', 'a')
				ActionChains(self.browser).context_click(link_elem).perform()
				clickstring = wait_get_attribute(link_elem, 'href')
				# result_link is the link for intended landing
				# pages. Not being used now.
				result_link = wait_get_attribute(link_elem, 'data-href')
				clickstring_set.add(clickstring)
		except:
			print "error in search_results"
			print sys.exc_info()[0]
		return clickstring_set

	def search(self, search_term):
		"""
		Search search_term in browser. Return True if search succeeded.
		@parmeter
		search_term: the words to search
		@return
		result_set: the set of results
		"""
		start = 0
		ad_set = set()
		search_set = set()
		while start < self.crawl_config.count:
			try:
				# google search advertisements or results
				url = 'https://www.google.com/?gws_rd=ssl#q='
				url += '+'.join(search_term.split(' '))
				url += '&start={0}'.format(start)
				self.browser.get(url)
				# wait until page load complete
				elem = wait_find_element(self.browser, 'id', 'ires')
				if elem is None:
					raise Exception("Page load failed.")
				time.sleep(random.randint(1, 10))
				ad_set = ad_set | self.ad_links()
				search_set = search_set | self.search_results()
				start = start + 10
			except:
				# For robustness, don't throw errors here.
				print "error in search"
				print sys.exc_info()[0]
				switch_vpn_state(self.connected)
				# mark vpn state
				self.connected = not self.connected
				self.browser = restart_browser(self.crawl_config.browser_type,
						incognito=False,
						user_agent=self.crawl_config.user_agent,
						browser=self.browser)
		# restart browser
		self.browser = restart_browser(self.crawl_config.browser_type, incognito=False,
				user_agent=self.crawl_config.user_agent, browser=self.browser)
		return ad_set, search_set 
	
# Iterate through all the popular words.
# For the word list.
# start = [8, 1, 0, 0, 0], end = [8, 2, , , 1]
# means [US, past 7 days, all categories, sub categories, web search]
class WordSet:
	def __init__(self, filename):
		words = filter(bool, open(filename, 'r').read().split('\n'))
		self.word_set = set()
		for word in words:
			self.word_set.add(word)
	
	def get_word_set(self):
		return self.word_set
	
	def expand_word_set(self, expand_type):
		if expand_type == "suggest":
			self.google_suggest()	
		elif expand_type == "search":
			None
		else:
			None

	def collect(self):
		None

	def google_suggest(self):
		None

# for each word, start a browser session to do google search on it,
# click and visit the landing page. directly visit the advertisement link
#
class Visit:
	def __init__(self, crawl_config, max_word_per_file=50):
		# user_agent, user_agent_md5_dir should be set.
		self.crawl_config = crawl_config
		set_browser_type(self.crawl_config)
		self.first_search = True 
		self.max_word_per_file = max_word_per_file 
		self.counter = 0
		self.partition = 0
	
	def __del__(self):
		if not self.first_search:
			self.write_crawl_log()

	def visit(self, clickstring_set, search_term):
		if len(clickstring_set) == 0:
			return
		# specify which type of browser to use
		mkdir_if_not_exist(self.crawl_config.user_agent_md5_dir)
		# crawl web pages
		url_fetcher = UrlFetcher(self.crawl_config)
		thread_computer = ThreadComputer(url_fetcher, 'fetch_url',
				clickstring_set)
		url_fetcher.quit()
		# create and fill current_search, including urls, search_term etc.
		current_search = CD.CrawlSearchTerm()
		for p, s in thread_computer.result:
			result = current_search.result.add()
			result.CopyFrom(s)
		current_search.search_term = search_term
		current_search.result_type = self.crawl_config.result_type
		# update current_log
		if self.first_search:
			self.first_search = False
			self.current_log = CD.CrawlLog()
		result_search = self.current_log.result_search.add()
		result_search.CopyFrom(current_search)
		self.counter += 1
		if self.counter % self.max_word_per_file == 0:
			self.write_crawl_log()
	
	def write_crawl_log(self):
		# Write log for current user agent
		current_log_filename = self.crawl_config.user_agent_md5_dir + \
				'crawl_log_' + str(self.partition) 
		self.partition += 1
		# Write global crawl_log
		write_proto_to_file(self.current_log, current_log_filename)
		# After write, reset variables
		self.first_search = True

	def visit_landing_url(self, crawl_log):
		None

def main(argv):
	# define constants 
	user_UA = "Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/" \
			"537.36 (KHTML, like Gecko) Chrome/37.0.2049.0 Safari/537.36"
	# google_UA is not used in search and crawl. Used in later visit.
	google_UA = "AdsBot-Google (+http://www.google.com/adsbot.html)"
	word_file = argv[0]

	now = datetime.now().strftime("%Y%m%d-%H%M%S")
	base_dir = word_file + '.' + now + '.selenium.crawl/'

	crawl_config = CD.CrawlConfig()
	crawl_config.maximum_threads = 6
	crawl_config.user_agent = user_UA
	crawl_config.user_agent_md5_dir = base_dir + hex_md5(crawl_config.user_agent) + '/'

	# print crawl_config.user_agent
	# print google_UA
	words = WordSet(word_file)
	search = Search(crawl_config)
	crawl_config.result_type = CD.AD
	ad_visit = Visit(crawl_config)
	crawl_config.result_type = CD.SEARCH
	search_visit = Visit(crawl_config)
	"""
	word_set = words.get_word_set()
	print 'word set size ', len(word_set)
	print word_set
	word_set = set()
	word_set.add('Essay Writing')
	word_set.add('Porn sale')
	for word in word_set:
	"""
	for word in words.get_word_set():
		ad_set, search_set = search.search(word)
		# print clickstring_set
		ad_visit.visit(ad_set, word)
		search_visit.visit(search_set, word)

if __name__ == "__main__":
	main(sys.argv[1:])

