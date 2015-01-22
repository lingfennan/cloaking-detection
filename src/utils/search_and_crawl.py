"""
Example Usage:
	# search words from $WORD_FILE and crawl the search results and ads.
	python search_and_crawl.py -f search -i word_file

	# revisit the landing pages in search and crawl phase as Google bot.
	ls ../../data/abusive_words.selenium.crawl/XXX/ad_crawl_log* | python search_and_crawl.py -f revisit -i word_file  -n number_of_visits

"""
import logging
import random
import subprocess
import sys, getopt
import time
from datetime import datetime
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.common.action_chains import ActionChains
from crawl import UrlFetcher, set_browser_type, hex_md5
from learning_detection_util import valid_instance, write_proto_to_file, read_proto_from_file
from thread_computer import ThreadComputer
from util import start_browser, restart_browser, mkdir_if_not_exist, Progress
import proto.cloaking_detection_pb2 as CD

def killall(name):
	p = subprocess.Popen(['killall', name], stdout=subprocess.PIPE)
	output, error = p.communicate()
	logging.info(output)
	logging.error(error)
	return False if error else True

def switch_vpn_state(connected):
	if connected:
		p = subprocess.Popen(['/opt/cisco/anyconnect/bin/vpn', 'disconnect'], stdout=subprocess.PIPE)
	else:
		p1 = subprocess.Popen(['printf', '"0\nrduan9\nZettaikatu168\ny"'], stdout=subprocess.PIPE)
		p = subprocess.Popen(['/opt/cisco/anyconnect/bin/vpn', '-s', 'connect', 'anyc.vpn.gatech.edu'],
				stdin=p1.stdout, stdout=subprocess.PIPE)
		p1.stdout.close()
	output, error = p.communicate()
	logging.info(output)
	logging.error(error)
	# whether switch was successful
	return False if error else True

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
		valid_instance(crawl_config, CD.CrawlConfig)
		self.crawl_config = CD.CrawlConfig()
		self.crawl_config.CopyFrom(crawl_config)
		set_browser_type(self.crawl_config)
	
	def __del__(self):
		# disconnect if connected
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
			logging.error("error in ad_links")
			logging.error(sys.exc_info()[0])
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
			logging.error("error in search_results")
			logging.error(sys.exc_info()[0])
		return clickstring_set

	def search(self, search_term):
		"""
		Search search_term in browser. Return True if search succeeded.
		@parmeter
		search_term: the words to search
		@return
		result_set: the set of results
		"""
		# start browser
		self.browser = start_browser(self.crawl_config.browser_type, incognito=False,
				user_agent=self.crawl_config.user_agent)
		self.browser.set_page_load_timeout(15)
		switch_vpn_state(True)
		self.connected = False

		# search 
		start = 0
		ad_set = set()
		search_set = set()
		while start < self.crawl_config.count:
			try:
				# google search advertisements or results
				url = 'https://www.google.com/?gws_rd=ssl#q='
				url += '+'.join(search_term.split(' '))
				# append start when the start is greater than zero
				if start > 0:
					url += '&start={0}'.format(start)
				self.browser.get(url)
				# wait until page load complete
				elem = wait_find_element(self.browser, 'id', 'ires')
				if elem is None:
					raise Exception("Page load failed.")
				time.sleep(random.randint(1, 5))
				ad_set = ad_set | self.ad_links()
				search_set = search_set | self.search_results()
				start = start + 10
			except:
				# For robustness, don't throw errors here.
				self.browser.quit()
				logging.error("error in search")
				logging.error(sys.exc_info()[0])
				if switch_vpn_state(self.connected):
					self.connected = not self.connected
				self.browser = restart_browser(self.crawl_config.browser_type,
						incognito=False,
						user_agent=self.crawl_config.user_agent,
						browser=self.browser)
		self.browser.quit()
		return ad_set, search_set 

# Iterate through all the popular words.
# For the word list.  # start = [8, 1, 0, 0, 0], end = [8, 2, , , 1]
# means [US, past 7 days, all categories, sub categories, web search]
class SearchTerm:
	def __init__(self, filename):
		words = filter(bool, open(filename, 'r').read().split('\n'))
		# Record and store progress
		progress_filename = filename + '.progress'
		self.progress = Progress(current_file = progress_filename)
		# Load progress
		if self.progress.current:
			self.word_list = words[self.progress.current[0]:]
		else:
			self.word_list = words
		self.counter = 0
	
	def current(self):
		"""
		the index of word in word list
		"""
		return self.progress.current
	
	def counter(self):
		"""
		times next() has been called, ie. progress of current session.
		"""
		return self.counter

	def next(self):
		self.progress.next([0], [len(self.word_list)])
		self.progress.save()
		self.counter += 1
	
	def get_word_list(self):
		return self.word_list
	
	def expand_word_list(self, expand_type):
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
	def __init__(self, crawl_config, max_word_per_file=5):
		# user_agent, user_agent_md5_dir should be set.
		valid_instance(crawl_config, CD.CrawlConfig)
		self.crawl_config = CD.CrawlConfig()
		self.crawl_config.CopyFrom(crawl_config)
		set_browser_type(self.crawl_config)
		self.first = True 
		self.max_word_per_file = max_word_per_file 
		self.counter = 0
		self.partition = 0

	def update_crawl_config(self, crawl_config):
		valid_instance(crawl_config, CD.CrawlConfig)
		self.crawl_config = CD.CrawlConfig()
		self.crawl_config.CopyFrom(crawl_config)
		set_browser_type(self.crawl_config)
	
	def __del__(self):
		if not self.counter % self.max_word_per_file == 0:
			self.write_crawl_log()

	def visit(self, clickstring_set, search_term):
		"""
		Count how many times this visit has been called, ie.
		how many words has been searched and visited so far.

		Note: some of the words might have empty advertisement
		clickstring_set, these words are counted but not logged.
		"""
		self.counter += 1
		if len(clickstring_set) == 0:
			return
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
		if self.first:
			self.first = False
			self.current_log = CD.CrawlLog()
		result_search = self.current_log.result_search.add()
		result_search.CopyFrom(current_search)
		if self.counter % self.max_word_per_file == 0:
			return self.write_crawl_log()
	
	def write_crawl_log(self, partition_suffix=True):
		crawl_log_dir = self.crawl_config.crawl_log_dir
		if (not crawl_log_dir) or crawl_log_dir == "":
			crawl_log_dir = self.crawl_config.user_agent_md5_dir
		current_log_filename = crawl_log_dir + self.crawl_config.log_filename
		if partition_suffix:
			current_log_filename += "_" + str(self.partition)
		self.partition += 1
		# Write global crawl_log
		write_proto_to_file(self.current_log, current_log_filename)
		# After write, reset variables
		self.current_log = CD.CrawlLog()
		return current_log_filename

	def visit_landing_url(self, crawl_log):
		valid_instance(crawl_log, CD.CrawlLog)
		# prepare landing_url_set
		landing_url_set = set()
		for result_search in crawl_log.result_search:
			for result in result_search.result:
				# landing_url exists only if crawl is successful
				if result.success:
					landing_url_set.add(result.landing_url)
		mkdir_if_not_exist(self.crawl_config.user_agent_md5_dir)
		# crawl web pages
		url_fetcher = UrlFetcher(self.crawl_config)
		thread_computer = ThreadComputer(url_fetcher, 'fetch_url',
				landing_url_set)
		url_fetcher.quit()
		# create and fill current_search, including urls, search_term etc.
		current_search = CD.CrawlSearchTerm()
		for p, s in thread_computer.result:
			result = current_search.result.add()
			result.CopyFrom(s)
		# update current_log
		if self.first:
			self.first = False
			self.current_log = CD.CrawlLog()
		result_search = self.current_log.result_search.add()
		result_search.CopyFrom(current_search)

def search_and_crawl(word_file, max_word_per_file=50):
	"""
	search words in word_file, get clickstring for search results and ads,
	then visit these clickstrings.
	@parameter
	word_file: the filename containing the words to search
	max_word_per_file: the maximum number of words to store in one crawl_log file
	"""
	# define constants 
	user_UA = "Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/" \
			"537.36 (KHTML, like Gecko) Chrome/37.0.2049.0 Safari/537.36"
	user_suffix = "selenium.crawl/"
	now_suffix = datetime.now().strftime(".%Y%m%d-%H%M%S")

	# compute base_dir and start logging
	base_dir = '.'.join([word_file, user_suffix])
	mkdir_if_not_exist(base_dir)
	logging.basicConfig(filename=base_dir+'running_log'+now_suffix, level=logging.DEBUG)

	# set crawl_config
	crawl_config = CD.CrawlConfig()
	crawl_config.maximum_threads = 6
	crawl_config.user_agent = user_UA
	crawl_config.user_agent_md5_dir = base_dir + hex_md5(crawl_config.user_agent) \
			+ now_suffix + '/'

	# print crawl_config.user_agent
	words = SearchTerm(word_file)
	search = Search(crawl_config)
	crawl_config.result_type = CD.AD
	crawl_config.log_filename = 'ad_crawl_log' + now_suffix
	ad_visit = Visit(crawl_config, max_word_per_file)
	crawl_config.result_type = CD.SEARCH
	crawl_config.log_filename = 'search_crawl_log' + now_suffix
	search_visit = Visit(crawl_config, max_word_per_file)
	"""
	word_list = words.get_word_list()
	print 'word list size ', len(word_list)
	print word_list
	word_list = list()
	word_list.append('Essay Writing')
	word_list.append('Porn sale')
	for word in word_list:
	"""
	for word in words.get_word_list():
		ad_set, search_set = search.search(word)
		# print clickstring_set
		ad_visit.visit(ad_set, word)
		search_visit.visit(search_set, word)
		words.next()

def revisit(crawl_log_file_list, word_file, n):
	"""
	visit landing urls in crawl_log_file n times
	@parameter
	crawl_log_file_list: list of filenames of crawl_log
	word_file: file containing words in crawl_log_file, used for creating base_dir
	n: number of times to visit
	"""
	# google_UA is not used in search and crawl. Used in later visit.
	google_UA = "AdsBot-Google (+http://www.google.com/adsbot.html)"
	google_suffix = 'google.crawl/'
	for i in range(int(n)):
		# the time label is set for each iteration of visit
		now_suffix = datetime.now().strftime(".%Y%m%d-%H%M%S")
		for crawl_log_file in crawl_log_file_list:
			# compute base_dir and start logging
			base_dir = '.'.join([word_file, google_suffix])
			mkdir_if_not_exist(base_dir)
			logging.basicConfig(filename=base_dir+'running_log'+now_suffix, level=logging.DEBUG)

			# set crawl_config
			crawl_config = CD.CrawlConfig()
			crawl_config.maximum_threads = 6
			crawl_config.user_agent = google_UA
			crawl_config.user_agent_md5_dir = base_dir + hex_md5(crawl_config.user_agent) \
					+ now_suffix + '/'

			google_crawl_log = crawl_log_file.split('/')[-1] + '.google'
			crawl_config.log_filename = google_crawl_log + now_suffix
			revisit = Visit(crawl_config)
			crawl_log = CD.CrawlLog()
			read_proto_from_file(crawl_log, crawl_log_file)
			revisit.visit_landing_url(crawl_log)
			revisit.write_crawl_log(False)

def search_and_revisit(word_file, n):
	"""
	This function does the following things.
	1. Search each word in word file.
	2. Grab the top 200 returned results and corresponding ads
	3. Visit all the results and ads with "chrome user agent", repeat n times
	4. Visit all the landing pages in step 3 with "google ads bot user agent"

	@parameter
	word_file: the filename containing the words to search
	n: repeat step 3 for n times

	@output
	Following are output of this function
	Running log:
	[WORD_FILE].selenium.crawl/running_log.[SEARCH_TIME]
	"chrome user agent" result is:
	[WORD_FILE].selenium.crawl/ad_crawl_log.[SEARCH_TIME].[WORD_MD5]
	[WORD_FILE].selenium.crawl/search_crawl_log.[SEARCH_TIME].[WORD_MD5]
	[WORD_FILE].selenium.crawl/[WORD_MD5]/[UA_MD5].[SEARCH_TIME]/[URL_MD5]/index.html
	"google ads bot user agent" result is:
	[WORD_FILE].selenium.crawl/ad_crawl_log.[SEARCH_TIME].[WORD_MD5].google
	[WORD_FILE].selenium.crawl/search_crawl_log.[SEARCH_TIME].[WORD_MD5].google
	[WORD_FILE].selenium.crawl/[WORD_MD5]/[UA_MD5].[SEARCH_TIME].revisit.[REVISIT_TIME]/[URL_MD5]/index.html
	"""
	# prepare search and visit
	user_UA = "Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/" \
			"537.36 (KHTML, like Gecko) Chrome/37.0.2049.0 Safari/537.36"
	user_suffix = "selenium.crawl/"
	search_now_suffix = datetime.now().strftime(".%Y%m%d-%H%M%S")
	word_md5_delimiter = "WORD_MD5"

	# compute base_dir and start logging
	base_dir = '.'.join([word_file, user_suffix])
	mkdir_if_not_exist(base_dir)
	logging.basicConfig(filename=base_dir+'running_log'+search_now_suffix, level=logging.DEBUG)

	# set search and visit crawl_config
	search_config = CD.CrawlConfig()
	search_config.maximum_threads = 8
	search_config.user_agent = user_UA
	ad_crawl_config = CD.CrawlConfig()
	ad_crawl_config.CopyFrom(search_config)
	ad_crawl_config.result_type = CD.AD
	ad_crawl_config.crawl_log_dir = base_dir
	ad_log_filename_prefix = 'ad_crawl_log' + search_now_suffix
	ad_dir_prefix = base_dir + word_md5_delimiter + "/" + \
			hex_md5(ad_crawl_config.user_agent) + search_now_suffix + '/'
	search_crawl_config = CD.CrawlConfig()
	search_crawl_config.CopyFrom(search_config)
	search_crawl_config.result_type = CD.SEARCH
	search_crawl_config.crawl_log_dir = base_dir
	search_log_filename_prefix = 'search_crawl_log' + search_now_suffix
	search_dir_prefix = base_dir + word_md5_delimiter + "/" + \
			hex_md5(search_crawl_config.user_agent) + search_now_suffix + '/'

	# print crawl_config.user_agent
	words = SearchTerm(word_file)
	search = Search(search_config)
	ad_visit = Visit(ad_crawl_config, 1)
	search_visit = Visit(search_crawl_config, 1)

	# prepare the revisit
	google_UA = "AdsBot-Google (+http://www.google.com/adsbot.html)"

	# set revisit crawl_config
	revisit_crawl_config = CD.CrawlConfig()
	revisit_crawl_config.maximum_threads = 8
	revisit_crawl_config.user_agent = google_UA
	# base directory uses search_now_suffix to correlate these two
	revisit_dir_prefix = base_dir + word_md5_delimiter + "/" + \
			hex_md5(revisit_crawl_config.user_agent) + search_now_suffix
	revisit_crawl_config.crawl_log_dir = base_dir

	# search, visit and revisit each word
	for word in words.get_word_list():
		print "Processing {0} word: {1}".format(words.current(), word)
		# update word_md5 related directories
		word_md5 = hex_md5(word)
		ad_crawl_config.log_filename = ad_log_filename_prefix + "." + word_md5
		ad_crawl_config.user_agent_md5_dir = word_md5.join(
				ad_dir_prefix.split(word_md5_delimiter))
		search_crawl_config.log_filename = search_log_filename_prefix + "." + word_md5
		search_crawl_config.user_agent_md5_dir = word_md5.join(
				search_dir_prefix.split(word_md5_delimiter))
		ad_visit.update_crawl_config(ad_crawl_config)
		search_visit.update_crawl_config(search_crawl_config)
		
		# search and crawl
		ad_set, search_set = search.search(word)
		ad_crawl_log_filename = ad_visit.visit(ad_set, word)
		search_crawl_log_filename = search_visit.visit(search_set, word)

		# revisit
		crawl_log_file_list = [ad_crawl_log_filename, search_crawl_log_filename]
		for crawl_log_file in crawl_log_file_list:
			revisit_crawl_config.log_filename = crawl_log_file.split('/')[-1] + '.google'
			revisit = Visit(revisit_crawl_config)
			for i in range(int(n)):
				# the time label is set for each iteration of visit
				revisit_now_suffix = datetime.now().strftime(".%Y%m%d-%H%M%S")
				revisit_crawl_config.user_agent_md5_dir = word_md5.join(
						revisit_dir_prefix.split(word_md5_delimiter)) + \
						'.revisit_time' + revisit_now_suffix + '/'
				revisit.update_crawl_config(revisit_crawl_config)
				crawl_log = CD.CrawlLog()
				read_proto_from_file(crawl_log, crawl_log_file)
				revisit.visit_landing_url(crawl_log)
			revisit.write_crawl_log(False)
		words.next()
		# kill zombie process peridically
		if words.counter() % 20 == 0:
			killall('chrome')

def main(argv):
	has_function = False
	help_msg = "search_and_crawl.py -f <function> [-i <inputfile>] [-i <inputfile> -n <number>] [-i <inputfile> -n <number>], valid functions are search, revisit, search_and_revisit"
	try:
		opts, args = getopt.getopt(argv, "hf:i:n:", ["function=", "ifile=", "number="])
	except getopt.GetoptError:
		print help_msg
		sys.exit(2)
	for opt, arg in opts:
		if opt == "-h":
			print help_msg
			sys.exit()
		elif opt in ("-f", "--function"):
			function = arg
			has_function = True
		elif opt in ("-i", "--ifile"):
			inputfile = arg
		elif opt in ("-n", "--number"):
			number = arg
		else:
			print help_msg
			sys.exit(2)
	if not has_function:
		print help_msg
		sys.exit()
	if function == "search":
		search_and_crawl(inputfile)
	elif function == "revisit":
		crawl_log_file_list = [line[:-1] for line in sys.stdin]
		revisit(crawl_log_file_list, inputfile, number)
	elif function == "search_and_revisit":
		search_and_revisit(inputfile, number)
	else:
		print help_msg
		sys.exit(2)

if __name__ == "__main__":
	main(sys.argv[1:])

