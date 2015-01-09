# Usage:
# python search_and_craw.py
#
#
#
# search 
#

# from util import ad_list, hot_search_words
from selenium.webdriver.common.action_chains import ActionChains
from crawl import UrlFetcher, set_browser_type
from learning_detection_util import valid_instance
from thread_computer import ThreadComputer
import proto.cloaking_detection_pb2 as CD

class Search:
	def ad_links(self, browser):
		clickstring_set = set()
		try:
			ads_ad_list = browser.find_elements_by_class_name('ads-ad')
			# print word
			for ads_ad in ads_ad_list:
				tags = ads_ad.find_elements_by_tag_name('a')
				for tag in tags:
					clickstring = tag.get_attribute('href')
					clickstring_set.add(clickstring)
					# print clickstring
					break
		except:
			continue
		return clickstring_set

	def search_results(self, browser):
		clickstring_set = set()
		try:
			search_list = browser.find_elements_by_class_name('g')
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
			continue
		return clickstring_set

	def search(self, browser, search_term, search_config):
		"""
		Search search_term in browser. Return True if search succeeded.
		@parmeter
		search_term: the words to search
		browser: browser handle controlled by selenium
		result_type: either ad_links or search_results
		top_count: the number of top search results to be inspected
		@return
		result_set: the set of results
		"""
		valid_instance(search_config, CD.SearchConfig):
		start = 0
		result_set = set()
		while start < search_config.count:
			try:
				# google search advertisements
				url = 'https://www.google.com/?gws_rd=ssl#q='
				url += '+'.join(search_term.split(' '))
				url += '&start=' + start
				browser.get(url)
				if search_config.result_type == \
						CD.SearchConfig.AD:
					result_set = result_set | self.ad_links(browser)
				elif search_ocnfig.result_type == \
						CD.SearchConfig.SEARCH:
					result_set = result_set | self.search_results(browser)
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
	def collect():
		None
	def google_suggest():
		None


# for each word, start a browser session to do google search on it,
# click and visit the landing page. directly visit the advertisement link
#
class Visit:
	def __init__(self, crawl_config):
		# user_agent, user_agent_md5_dir should be set.
		self.crawl_config = crawl_config
		set_browser_type(self.crawl_config)

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

