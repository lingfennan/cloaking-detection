# Usage:
# python crawl.py $URL_FILE $USER_AGENT_FILE
#
#

import hashlib
import sys
import os
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import UnexpectedAlertPresentException
from selenium.common.exceptions import WebDriverException
from util import start_browser, mkdir_if_not_exist
from learning_detection_util import valid_instance, write_proto_to_file, read_proto_from_file
import proto.cloaking_detection_pb2 as CD

def hex_md5(string):
	# util function to return md5 in hex of the input string.
	m = hashlib.md5()
	m.update(string.encode('utf-8'))
	return m.hexdigest()

class FetchError(Exception):
	def __init__(self, url):
		self.url = url
	def __str__(self):
		return repr(self.url)

class UrlFetcher(object):
	def __init__(self, crawl_config):
		valid_instance(crawl_config, CD.CrawlConfig)
		self.crawl_config = crawl_config
		if 'Chrome' in self.crawl_config.user_agent:
			self.browser_type = 'Chrome'
		elif 'Firefox' in self.crawl_config.user_agent:
			self.browser_type = 'Firefox'
		elif 'bot' in self.crawl_config.user_agent:
			self.browser_type = 'Firefox'
		else:
			self.browser_type = 'Firefox'
		self.browser = start_browser(self.browser_type, incognito=False, \
				user_agent=self.crawl_config.user_agent)

	def maximum_threads(self):
		return self.crawl_config.maximum_threads

	def para_type(self):
		return CD.NORMAL

	def fetch_url(self, url):
		result = CD.CrawlResult()
		# record whether url loading failed!
		result.url = url
		result.url_md5 = hex_md5(url)
		result.success = True
		try:
			# may throw socket errors
			self.browser.get(result.url)
			if self.browser_type == 'Chrome' and \
					(('404 Not Found' in self.browser.title) \
					or ('Error 404' in self.browser.title) \
					or ('is not available' in self.browser.title)):
				result.success = False
			elif self.browser_type == 'Firefox' and \
					(('404 Not Found' in self.browser.title) \
					or ('Error 404' in self.browser.title) \
					or ('Problem loading page' in self.browser.title)):
				result.success = False
			else:
				#############
				# md5 the original url
				url_md5_dir = self.crawl_config.user_agent_md5_dir + result.url_md5 + '/'
				mkdir_if_not_exist(url_md5_dir)
				# get the landing url
				result.landing_url = self.browser.current_url
				result.landing_url_md5 = hex_md5(result.landing_url)
				# get the whole page source
				response = self.browser.execute_script("return document.documentElement.innerHTML;")
				result.file_path = url_md5_dir + 'index.html'
				f = open(result.file_path, 'w')
				f.write(response.encode('utf-8'))
				f.close()
		except:
			result.success = False
			# raise FetchError(result.url)
			self.browser = start_browser(self.browser_type, incognito=False, \
					user_agent=self.crawl_config.user_agent)
		return result

class Crawler:
	# 1. Because we are working on visiting URLs or ad clickstrings (from Google ads), assume we don't need the referer file.
	# 2. If we really need referer, one way is to directly do crawling from hot search words.
	def __init__(self, url_file, user_agent_file, crawl_config):
		# Prepare the output directory
		now = datetime.now().strftime("%Y%m%d-%H%M%S")
		self.base_dir = url_file + '.' + now + '.selenium.crawl/'
		mkdir_if_not_exist(self.base_dir)
		# Prepare the input
		self.urls = filter(bool, open(url_file, 'r').read().split('\n'))
		self.user_agents = filter(bool, open(user_agent_file, 'r').read().split('\n'))
		# self.referers = filter(bool, open(referer_file, 'r').read().split('\n'))
		self.crawl_config = crawl_config

		# Prepare log files
		# self.htmls_f = open(self.base_dir + 'html_path_list', 'a')
		self.md5_UA_f = open(self.base_dir + 'md5_UA.log', 'a')  # user agent
		crawl_log_filename = self.base_dir + 'crawl_log'
	
	def crawl(self):
		has_written = False
		for user_agent in self.user_agents:
			user_agent_md5 = hex_md5(user_agent)
			self.crawl_config.user_agent = user_agent
			self.crawl_config.user_agent_md5_dir = self.base_dir + user_agent_md5 + '/'
			mkdir_if_not_exist(self.crawl_config.user_agent_md5_dir)
			# md5 - user agent mapping logs
			self.md5_UA_f.write(user_agent_md5 + ":" + user_agent + "\n")
			# url md5 - landing url logs
			url_md5_LP_f = open(user_agent_md5_dir + 'landing_page', 'w')
			success_f = open(user_agent_md5_dir + 'success', 'w')
			failure_f = open(user_agent_md5_dir + 'failure', 'w')

			url_fetcher = UrlFetcher(crawl_config)
			thread_computer = ThreadComputer(url_fetcher, 'fetch_url', self.urls)

			crawl_log = CD.CrawlLog()
			if has_written:
				read_proto_from_file(crawl_log, crawl_log_filename)
			else:
				has_written = True
			for p, s in thread_computer.result:
				result = crawl_log.result.add()
				result.CopyFrom(s)
			write_proto_to_file(crawl_log, crawl_log_filename)

def main(argv):
	"""
	crawler = Crawler('', '', '')
	crawler.new_session('', 'Mozilla/5.0 (iPhone; CPU iPhone OS 7_0 like Mac OS X; en-us) AppleWebKit/537.51.1 (KHTML, like Gecko) Version/7.0 Mobile/11A465 Safari/9537.53', '', 10)
	crawler.new_session('', 'Mozilla/5.0 (Linux; <Android Version>; <Build Tag etc.>) AppleWebKit/<WebKit Rev> (KHTML, like Gecko) Chrome/<Chrome Rev> Mobile Safari/<WebKit Rev>', '', 10)
	"""
	if not len(argv) == 2:
		return
	crawl_config = CD.CrawlConfig()
	crawl_config.maximum_threads = 6
	crawler = Crawler(argv[0], argv[1], crawl_config)
	crawler.crawl()

if __name__ == "__main__":
	main(sys.argv[1:])

