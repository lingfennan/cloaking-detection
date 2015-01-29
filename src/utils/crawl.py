# Usage:
# python crawl.py $URL_FILE $USER_AGENT_FILE [$THREAD_NUMBER]
#
#

import hashlib
import logging
import Queue
import sys
import time
import threading
import os
from datetime import datetime
from selenium import webdriver
from util import start_browser, restart_browser, mkdir_if_not_exist, safe_quit
from learning_detection_util import valid_instance, write_proto_to_file, read_proto_from_file
from thread_computer import ThreadComputer
import proto.cloaking_detection_pb2 as CD


def collect_site_for_plot(site_list, mode="user"):
	"""
	Collect user and google observation for site in site_list.
	This is scheduled by 7_14.py. In order to show how hash values of
	websites change over time.
	"""
	user_UA = "Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/" \
			"537.36 (KHTML, like Gecko) Chrome/37.0.2049.0 Safari/537.36"
	google_UA = "AdsBot-Google (+http://www.google.com/adsbot.html)"
	crawl_config = CD.CrawlConfig()
	crawl_config.maximum_threads = 1
	crawl_config.browser_type = CD.CrawlConfig.CHROME
	if mode == "user":
		UAs = [user_UA]
	elif mode == "google":
		UAs = [google_UA]
	elif mode == "both":
		UAs = [user_UA, google_UA]
	else:
		raise Exception("Unknown mode {0}".format(mode))

	UAs = [user_UA, google_UA]
	for ua in UAs:
		crawl_config.user_agent = ua
		url_fetcher = UrlFetcher()


def hex_md5(string):
	# util function to return md5 in hex of the input string.
	m = hashlib.md5()
	m.update(string.encode('utf-8'))
	return m.hexdigest()

def set_browser_type(crawl_config):
	if 'Chrome' in crawl_config.user_agent:
		crawl_config.browser_type = CD.CrawlConfig.CHROME
	elif 'Firefox' in crawl_config.user_agent:
		crawl_config.browser_type = CD.CrawlConfig.FIREFOX
	elif 'bot' in crawl_config.user_agent:
		crawl_config.browser_type = CD.CrawlConfig.CHROME
	else:
		crawl_config.browser_type = CD.CrawlConfig.CHROME

class UrlFetcher(object):
	def __init__(self, crawl_config):
		valid_instance(crawl_config, CD.CrawlConfig)
		self.crawl_config = CD.CrawlConfig()
		self.crawl_config.CopyFrom(crawl_config)
		self.browser_queue = Queue.Queue()
		for i in xrange(self.crawl_config.maximum_threads):
			browser = start_browser(self.crawl_config.browser_type, incognito=False, \
					user_agent=self.crawl_config.user_agent)
			browser.set_page_load_timeout(15)
			self.browser_queue.put(browser)
		self.lock = threading.Lock()

	def quit(self):
		while not self.browser_queue.empty():
			browser = self.browser_queue.get()
			safe_quit(browser)
	
	def update_dir(self, new_dir):
		self.crawl_config.user_agent_md5_dir = new_dir

	def maximum_threads(self):
		return self.crawl_config.maximum_threads

	def para_type(self):
		return CD.NORMAL

	def fetch_url(self, url):
		while True:
			self.lock.acquire()
			if self.browser_queue.empty():
				self.lock.release()
				time.sleep(5)
			else:
				browser = self.browser_queue.get()
				self.lock.release()
				break
		result = CD.CrawlResult() # record whether url loading failed!
		result.url = url
		result.url_md5 = hex_md5(url)
		result.success = True
		try:
			# This line is used to handle alert: <stay on this page> <leave this page>
			browser.get(result.url)
			browser.execute_script("window.onbeforeunload = function() {};")
			time.sleep(1)
			if self.crawl_config.browser_type == CD.CrawlConfig.CHROME and \
					(('404 Not Found' in browser.title) \
					or ('403' in browser.title) \
					or ('Forbidden' in browser.title) \
					or ('not available' in browser.title) \
					or ('Problem loading page' in browser.title) \
					or ('Page not found' in browser.title) \
					or ('Error' in browser.title) \
					or ('Access denied' in browser.title) \
					or (browser.current_url == 'data:text/html,chromewebdata')):
				result.landing_url = browser.current_url
				result.landing_url_md5 = hex_md5(result.landing_url)
				result.success = False
			elif self.crawl_config.browser_type == CD.CrawlConfig.FIREFOX and \
					(('404 Not Found' in browser.title) \
					or ('403' in browser.title) \
					or ('Forbidden' in browser.title) \
					or ('not available' in browser.title) \
					or ('Problem loading page' in browser.title) \
					or ('Page not found' in browser.title) \
					or ('Error' in browser.title) \
					or ('Access denied' in browser.title)):
				result.landing_url = browser.current_url
				result.landing_url_md5 = hex_md5(result.landing_url)
				result.success = False
			else:
				#############
				# md5 the original url
				url_md5_dir = self.crawl_config.user_agent_md5_dir + result.url_md5 + '/'
				mkdir_if_not_exist(url_md5_dir)
				# get the landing url
				result.landing_url = browser.current_url
				result.landing_url_md5 = hex_md5(result.landing_url)
				# get the whole page source
				response = browser.execute_script("return document.documentElement.innerHTML;")
				result.file_path = url_md5_dir + 'index.html'
				f = open(result.file_path, 'w')
				f.write(response.encode('utf-8'))
				f.close()
			browser.delete_all_cookies()
			if len(browser.window_handles) > 1:
				# close all the other windows
				current_window_handle = browser.current_window_handle
				for handle in browser.window_handles:
					if handle != current_window_handle:
						browser.switch_to_window(handle)
						browser.close()
				# switch back to the current window
				browser.switch_to_window(current_window_handle)
		except:
			result.success = False
			browser = restart_browser(self.crawl_config.browser_type, incognito=False,
					user_agent=self.crawl_config.user_agent, browser=browser)
		self.browser_queue.put(browser)
		logger = logging.getLogger("global")
		logger.info("the length of the browser_queue")
		logger.info(self.browser_queue.qsize())
		return result

class Crawler:
	# 1. Because we are working on visiting URLs or ad clickstrings (from Google ads), assume we don't need the referer file.
	# 2. If we really need referer, one way is to directly do crawling from hot search words.
	def __init__(self, url_file, user_agent_file, crawl_config):
		valid_instance(crawl_config, CD.CrawlConfig)
		self.crawl_config = CD.CrawlConfig()
		self.crawl_config.CopyFrom(crawl_config)

		# Prepare the input
		self.urls = filter(bool, open(url_file, 'r').read().split('\n'))
		self.user_agents = filter(bool, open(user_agent_file, 'r').read().split('\n'))
		# self.referers = filter(bool, open(referer_file, 'r').read().split('\n'))

		# Prepare the output directory
		crawl_type = None
		for user_agent in self.user_agents:
			if "bot" in user_agent:
				crawl_type = "bot"
				break
		if not crawl_type:
			crawl_type = "user"
		now = datetime.now().strftime("%Y%m%d-%H%M%S")
		self.base_dir = url_file + '.' + crawl_type + '.' + now + '.selenium.crawl/'
		mkdir_if_not_exist(self.base_dir)

		# Prepare log files
		# self.htmls_f = open(self.base_dir + 'html_path_list', 'a')
		self.md5_UA_filename = self.base_dir + 'md5_UA.log'
		self.crawl_log_filename = self.base_dir + 'crawl_log'
	
	def crawl(self):
		has_written = False
		for user_agent in self.user_agents:
			user_agent_md5 = hex_md5(user_agent)
			self.crawl_config.user_agent = user_agent
			self.crawl_config.user_agent_md5_dir = self.base_dir + user_agent_md5 + '/'
			# specify which type of browser to use
			set_browser_type(self.crawl_config)
			mkdir_if_not_exist(self.crawl_config.user_agent_md5_dir)
			# md5 - user agent mapping logs
			md5_UA_f = open(self.md5_UA_filename, 'a')  # user agent
			md5_UA_f.write(user_agent_md5 + ":" + user_agent + "\n")
			md5_UA_f.close()
			# crawl web pages
			url_fetcher = UrlFetcher(self.crawl_config)
			thread_computer = ThreadComputer(url_fetcher, 'fetch_url', self.urls)
			url_fetcher.quit()
			# Write log for current user agent
			current_log = CD.CrawlLog()
			current_log_filename = self.crawl_config.user_agent_md5_dir + 'crawl_log'
			current_search = CD.CrawlSearchTerm()
			for p, s in thread_computer.result:
				result = current_search.result.add()
				result.CopyFrom(s)
				result_search = current_log.result_search.add()
				result_search.CopyFrom(current_search)
			write_proto_to_file(current_log, current_log_filename)
			# Write global crawl_log
			crawl_log = CD.CrawlLog()
			if has_written:
				read_proto_from_file(crawl_log, self.crawl_log_filename)
			else:
				has_written = True
			for r_s in current_log.result_search:
				result_search = crawl_log.result_search.add()
				result_search.CopyFrom(r_s)
			"""
			for s in current_log.result:
				result = crawl_log.result.add()
				result.CopyFrom(s)
			"""
			write_proto_to_file(crawl_log, self.crawl_log_filename)

def main(argv):
	"""
	crawler = Crawler('', '', '')
	crawler.new_session('', 'Mozilla/5.0 (iPhone; CPU iPhone OS 7_0 like Mac OS X; en-us) AppleWebKit/537.51.1 (KHTML, like Gecko) Version/7.0 Mobile/11A465 Safari/9537.53', '', 10)
	crawler.new_session('', 'Mozilla/5.0 (Linux; <Android Version>; <Build Tag etc.>) AppleWebKit/<WebKit Rev> (KHTML, like Gecko) Chrome/<Chrome Rev> Mobile Safari/<WebKit Rev>', '', 10)
	"""
	if len(argv) < 2 or len(argv) > 3:
		print "Wrong number of args! python crawl.py $URL_FILE $USER_AGENT_FILE [$THREAD_NUMBER]"
		sys.exit(1)
	crawl_config = CD.CrawlConfig()
	crawl_config.maximum_threads = 6
	# crawl_config.browser_type = CD.CrawlConfig.CHROME
	if len(argv) == 3:
		crawl_config.maximum_threads = int(argv[2])
	crawler = Crawler(argv[0], argv[1], crawl_config)
	crawler.crawl()

if __name__ == "__main__":
	main(sys.argv[1:])

