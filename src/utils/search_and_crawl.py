"""
Usage:
python search_and_craw.py
"""

# from util import ad_list, hot_search_words
import sys
from datetime import datetime
from selenium.webdriver.common.action_chains import ActionChains
from crawl import UrlFetcher, set_browser_type, hex_md5
from learning_detection_util import valid_instance
from thread_computer import ThreadComputer
import proto.cloaking_detection_pb2 as CD

class Search:
	def __init__(self, crawl_config):
		# user_agent should be set.
		self.crawl_config = crawl_config
		set_browser_type(self.crawl_config)
		self.browser = start_browser(self.crawl_config.browser_type, incognito=False,
				user_agent=self.crawl_config.user_agent)
		self.browser.set_page_load_timeout(15)
	
	def ad_links(self):
		clickstring_set = set()
		try:
			ads_ad_list = self.browser.find_elements_by_class_name('ads-ad')
			# print word
			for ads_ad in ads_ad_list:
				tags = ads_ad.find_elements_by_tag_name('a')
				for tag in tags:
					clickstring = tag.get_attribute('href')
					clickstring_set.add(clickstring)
					# print clickstring
					break
		except:
			None
		return clickstring_set

	def search_results(self):
		clickstring_set = set()
		try:
			search_list = self.browser.find_elements_by_class_name('g')
			for result_elem in search_list:
				title_elem = result_elem.\
						find_element_by_tag_name('h3')
				title = title_elem.text
				link_elem = title_elem.\
						find_element_by_tag_name('a')
				ActionChains(driver).context_click(link_elem).perform()
				clickstring = link_elem.get_attribute('href')
				# result_link is the link for intended landing
				# pages. Not being used now.
				result_link = link_elem.get_attribute('data-href')
				clickstring_set.add(clickstring)
		except:
			None	
		return clickstring_set

	def search(self, search_term, search_config):
		"""
		Search search_term in browser. Return True if search succeeded.
		@parmeter
		search_term: the words to search
		result_type: either ad_links or search_results
		top_count: the number of top search results to be inspected
		@return
		result_set: the set of results
		"""
		valid_instance(search_config, CD.SearchConfig)
		start = 0
		result_set = set()
		while start < search_config.count:
			try:
				# google search advertisements
				url = 'https://www.google.com/?gws_rd=ssl#q='
				url += '+'.join(search_term.split(' '))
				url += '&start=' + start
				self.browser.get(url)
				if search_config.result_type == \
						CD.SearchConfig.AD:
					result_set = result_set | self.ad_links()
				elif search_ocnfig.result_type == \
						CD.SearchConfig.SEARCH:
					result_set = result_set | self.search_results()
				else:
					raise Exception("Unknown type of "
							"SearchConfig.ResultType.")
			except:
				# For robustness, don't throw errors here.
				None
			start = start + 10
		return result_set
	
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
	def __init__(self, crawl_config):
		# user_agent, user_agent_md5_dir should be set.
		self.crawl_config = crawl_config
		set_browser_type(self.crawl_config)
		self.browser = start_browser(self.crawl_config.browser_type, incognito=False,
				user_agent=self.crawl_config.user_agent)
		self.browser.set_page_load_timeout(15)

	def visit(clickstring_set):
		# specify which type of browser to use
		mkdir_if_not_exist(self.crawl_config.user_agent_md5_dir)
		# crawl web pages
		url_fetcher = UrlFetcher(self.crawl_config)
		thread_computer = ThreadComputer(url_fetcher, 'fetch_url',
				clickstring_set)
		url_fetcher.quit()
		# Write log for current user agent
		current_log = CD.CrawlLog()
		current_log_filename = self.crawl_config.user_agent_md5_dir + 'crawl_log'
		for p, s in thread_computer.result:
			result = current_log.result.add()
			result.CopyFrom(s)
		write_proto_to_file(current_log, current_log_filename)
		# Write global crawl_log
		crawl_log = CD.CrawlLog()
		if has_written:
			read_proto_from_file(crawl_log, self.crawl_log_filename)
		else:
			has_written = True
		for s in current_log.result:
			result = crawl_log.result.add()
			result.CopyFrom(s)
		write_proto_to_file(crawl_log, self.crawl_log_filename)

def main(argv):
	# define constants 
	user_UA = "Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/" \
			"537.36 (KHTML, like Gecko) Chrome/37.0.2049.0 Safari/537.36"
	google_UA = "AdsBot-Google (+http://www.google.com/adsbot.html)"
	word_file = argv[0]
	now = datetime.now().strftime("%Y%m%d-%H%M%S")
	base_dir = word_file + '.' + now + '.selenium.crawl/'

	crawl_config = CD.CrawlConfig()
	crawl_config.maximum_threads = 6
	crawl_config.user_agent = user_UA
	crawl_config.user_agent_md5_dir = base_dir + hex_md5(crawl_config.user_agent) + '/'

	print crawl_config.user_agent
	print google_UA
	search_config = CD.SearchConfig()
	words = WordSet(word_file)
	search = Search(crawl_config)
	visit = Visit(crawl_config)
	for word in words:
		clickstring_set = search.search(word, search_config)
		visit.visit(clickstring_set)

if __name__ == "__main__":
	main(sys.argv[1:])

