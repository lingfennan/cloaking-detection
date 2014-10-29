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

DELIMETER = "#Delimeter#"
# To be compatible with program finished at Google
COMMA = ","

def hex_md5(string):
	# util function to return md5 in hex of the input string.
	m = hashlib.md5()
	m.update(string.encode('utf-8'))
	return m.hexdigest()


def fetch_url(url, browser, browser_type, user_agent, user_agent_md5_dir, filehandles):
	if not len(filehandles) == 4:
		raise Exception("Wrong number of parameters. filehandles should have size 4.")
	[htmls_f, url_md5_LP_f, success_f, failure_f] = filehandles
	browser.get(url)
	url_md5 = hex_md5(url)
	# record whether url loading failed!
	success = True
	try:
		if browser_type == 'Chrome' and (('404 Not Found' in browser.title) or ('Error 404' in browser.title) or ('is not available' in browser.title)):
			success = False
		elif browser_type == 'Firefox' and (('404 Not Found' in browser.title) or ('Error 404' in browser.title) or ('Problem loading page' in browser.title)):
			success = False
		else:
			#############
			# md5 the original url
			url_md5_dir = user_agent_md5_dir + url_md5 + '/'
			mkdir_if_not_exist(url_md5_dir)
			# get the landing url
			landing_url = browser.current_url
			landing_url_md5 = hex_md5(landing_url)
			# get the whole page source
			response = browser.execute_script("return document.documentElement.innerHTML;")
			response_filename = url_md5_dir + 'index.html'
			f = open(response_filename, 'w')
			f.write(response.encode('utf-8'))
			f.close()

			# md5 - landing page mapping logs
			htmls_f.write(response_filename + COMMA + landing_url + '\n')
			url_md5_LP_f.write(url_md5 + DELIMETER + landing_url + '\n')
	except:
		try:
			# except (UnexpectedAlertPresentException, WebDriverException) as e:
			success = False
			print sys.exc_info()[0]
			browser.quit()
			browser = start_browser(browser_type, incognito=False, user_agent=user_agent)
			return
		except:
			# In case browser.quit() freezes, keyboard interrupt and continue the program after that
			return
	if success:
		print browser.title
		log_str = url_md5 + DELIMETER + url + DELIMETER + landing_url_md5 + DELIMETER + landing_url + '\n'
		success_f.write(log_str)
	else:
		log_str = url_md5 + DELIMETER + url + '\n'
		# diable the following line because UnexpectedAlertPresentException can not access browser.title
		# print browser.title
		print log_str
		failure_f.write(log_str)



class Crawler:
	# 1. Because we are working on visiting URLs or ad clickstrings (from Google ads), assume we don't need the referer file.
	# 2. If we really need referer, one way is to directly do crawling from hot search words.
	def __init__(self, url_file, user_agent_file, threads=10):
		# Prepare the output directory
		now = datetime.now().strftime("%Y%m%d-%H%M%S")
		self.base_dir = url_file + '.' + now + '.selenium.crawl/'
		mkdir_if_not_exist(self.base_dir)
		# Prepare the input
		self.urls = filter(bool, open(url_file, 'r').read().split('\n'))
		self.user_agents = filter(bool, open(user_agent_file, 'r').read().split('\n'))
		# self.referers = filter(bool, open(referer_file, 'r').read().split('\n'))
		self.threads = threads

		# Prepare log files
		self.htmls_f = open(self.base_dir + 'html_path_list', 'a')
		self.md5_UA_f = open(self.base_dir + 'md5_UA.log', 'a')  # user agent
	
	def new_session(self, user_agent, threads):
		user_agent_md5 = hex_md5(user_agent)
		user_agent_md5_dir = self.base_dir + user_agent_md5 + '/'
		mkdir_if_not_exist(user_agent_md5_dir)

		# md5 - user agent mapping logs
		self.md5_UA_f.write(user_agent_md5 + ":" + user_agent + "\n")

		# the user could create multiple sessions
		# for each session, the program can be threaded
		if 'Chrome' in user_agent:
			self.browser_type = 'Chrome'
		elif 'Firefox' in user_agent:
			self.browser_type = 'Firefox'
		elif 'bot' in user_agent:
			self.browser_type = 'Firefox'
		else:
			self.browser_type = 'Firefox'
		browser = start_browser(self.browser_type, incognito=False, user_agent=user_agent)

		# url md5 - landing url logs
		url_md5_LP_f = open(user_agent_md5_dir + 'landing_page', 'w')
		success_f = open(user_agent_md5_dir + 'success', 'w')
		failure_f = open(user_agent_md5_dir + 'failure', 'w')

		for url in self.urls:
			fetch_url(url, browser, self.browser_type, user_agent, user_agent_md5_dir, [self.htmls_f, url_md5_LP_f, success_f, failure_f])
		browser.quit()

def main(argv):
	"""
	crawler = Crawler('', '', '')
	crawler.new_session('', 'Mozilla/5.0 (iPhone; CPU iPhone OS 7_0 like Mac OS X; en-us) AppleWebKit/537.51.1 (KHTML, like Gecko) Version/7.0 Mobile/11A465 Safari/9537.53', '', 10)
	crawler.new_session('', 'Mozilla/5.0 (Linux; <Android Version>; <Build Tag etc.>) AppleWebKit/<WebKit Rev> (KHTML, like Gecko) Chrome/<Chrome Rev> Mobile Safari/<WebKit Rev>', '', 10)
	"""
	if not len(argv) == 2:
		return
	crawler = Crawler(argv[0], argv[1])
	for user_agent in crawler.user_agents:
		crawler.new_session(user_agent, 10)

if __name__ == "__main__":
	main(sys.argv[1:])


