import sys, getopt
import csv
import logging
import os
import platform
import re
import random
import time
from datetime import datetime
from itertools import izip
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.keys import Keys
from learning_detection_util import read_proto_from_file, write_proto_to_file
import selenium.webdriver.chrome.service as service
import proto.cloaking_detection_pb2 as CD

"""
Dependencies:
	selenium: Refer to https://pypi.python.org/pypi/selenium for installation instructions.

Example Usage:
	# merge logs to one file, -o specifies the prefix of the output file. The trailing part are generated using parameters in -c.
	ls learn_0_100_purify/logs_type_* | python util.py -f merge_logs -o learn_0_100_purify/plot_logs -c '1,1,1,1,2,,2'

	# format click strings into url list. Specifically, append http://www.google.com to each click string.
	python util.py -f format_links -i click_string -o url_list [-a]

	# generate test_list.test and test_list.mismatch
	python util.py -f generate_test -i computed_observed_sites -n test_list_size -m mismatch_list_size

	# aggregate average distance distribution for each URL patterns, the result is used to show distance distribution within patterns.
	python util.py -f pattern_distance_distribution -i file.dist -o stats_file

	# visit Google trends data and collect information from there, report.csv for each configuration is downloaded..
	# output directory is output_dir + 'csv.' + date + '/'
	python util.py -f hot_search_words -b Chrome -i credentials -o trend/

	# get hot search words list from downloaded csv, visit and get ad clickstrings.
	ls ../../data/trend/*2013*Web\ Search.csv | python util.py -f ad_list -o ../../data/US_2013_WS_list

	# read learned_sites or observed_sites, output URL/file_path pair for automated evaluation.
	python util.py -f evaluation_form -i sites_filename -o out_filename -p proto_buffer
"""

# hot_search_words 
LEVEL = 2

# hot_search_words, ad_list
if platform.system() == 'Darwin':
	CHROMEDRIVER_PATH = '../../data/trend/mac_chromedriver'
	DOWNLOAD_PATH = '/Users/ruian/Downloads/'
elif platform.system() == 'Linux':
	CHROMEDRIVER_PATH = '../../data/trend/linux_chromedriver'
	DOWNLOAD_PATH = '/home/ruian/Downloads/'
else:
	print 'System {0} not supported'.format(platform.system())
	sys.exit(1)

# start chrome driver separately to save time and resources
# driver_service = service.Service(CHROMEDRIVER_PATH)
# driver_service.start()
# Remote Driver Address
REMOTE_DRIVER="http://localhost:5555/wd/hub"

####################################################################################
def evaluation_form(sites_filename, out_filename, proto):
	sites = getattr(CD, proto)()
	read_proto_from_file(sites, sites_filename)
	out_f = open(out_filename, "w")
	if proto == "LearnedSites":
		for site in sites.site:
			for pattern in site.pattern:
				out_f.write(site.name + "\n" + \
						pattern.item[0].sample_file_path + "\n")
		out_f.close()
	elif proto == "ObservedSites":
		for site in sites.site:
			for observation in site.observation:
				out_f.write(site.name + "\n" + observation.file_path + "\n")
		out_f.close()
	else:
		raise Exception("Wrong proto! Only LearnedSites and ObservedSites can be used!")

####################################################################################
def safe_quit(browser):
	try:
		browser.quit()
	except	WebDriverException:
		logger = logging.getLogger("global")
		logger.error("Error in safe_quit")
		logger.error(sys.exc_info()[0])

def mkdir_if_not_exist(directory):
	if not os.path.exists(directory):
		os.makedirs(directory)

def get_clickstring(words_file, browser_type):
	clickstring_set = set()
	words = filter(bool, open(words_file, 'r').read().split('\n'))
	browser = start_browser(browser_type, incognito=True)
	for word in words:
		try:
			# google search advertisements
			url = 'https://www.google.com/?gws_rd=ssl#q='
			url += '+'.join(word.split(' '))
			browser.get(url)
			time.sleep(4)
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
	safe_quit(browser)
	return clickstring_set

def ad_list(report_list, outputfile, browser_type):
	hot_word_set = set()
	rising_word_set = set()
	for report_file in report_list:
		lines = open(report_file, 'r').read().split('\n')
		# whether we have started to retrieve data
		started_hw = False
		started_rw = False
		for line in lines:
			if started_hw or started_rw:
				line = line.split(',')
				if len(line) == 2:
					if started_hw:
						hot_word_set.add(line[0])
					elif started_rw:
						rising_word_set.add(line[0])
				else:
					started_hw = False
					started_rw = False
			else:
				if line == 'Top searches':
					started_hw = True
				if line == 'Rising searches':
					started_rw = True
	hot_word_file = outputfile + '.hw'
	rising_word_file = outputfile + '.rw'
	word_file = outputfile + '.w'
	intersect_word_file = outputfile + '.iw'
	open(hot_word_file, 'w').write('\n'.join(hot_word_set))
	open(rising_word_file, 'w').write('\n'.join(rising_word_set))
	open(word_file, 'w').write('\n'.join(hot_word_set | rising_word_set))
	# which file should we use to get the ad clickstring list
	open(intersect_word_file, 'w').write('\n'.join(hot_word_set & rising_word_set))
	clickstring_set = get_clickstring(word_file, browser_type)
	open(outputfile, 'w').write('\n'.join(clickstring_set))

####################################################################################
def trend_query_url(trend_url, params):
	params_str_list = list()
	for k,v in params.items():
		params_str_list.append(k + '=' + v)
	trend_url += '&'.join(params_str_list)
	return trend_url

class QuoteError(Exception):
	def __init__(self, progress):
		self.progress = progress 
	def __str__(self):
		return repr(self.progress)

def sign_in_gmail(browser, username, password):
	# if chrome
	browser.get("http://mail.google.com")
	emailid = browser.find_element_by_id("Email")
	emailid.send_keys(username)
	passw = browser.find_element_by_id("Passwd")
	passw.send_keys(password)
	signin = browser.find_element_by_id("signIn")
	signin.click()
	time.sleep(5)

def download_csv(browser):
	time.sleep(5)
	settings_button = browser.find_element_by_id('settings-menu-button')	# Find settings button
	settings_button.click()
	exportMI_button = browser.find_element_by_id('exportMI')	# Find download csv button
	exportMI_button.click()

def collapse_all(popup):
	items_to_collapse = popup.find_elements_by_css_selector(".goog-tree-item[aria-level='1'][aria-expanded='true']")
	for item in items_to_collapse:
		collapse_item = item.find_element_by_css_selector(".goog-tree-expand-icon[type='expand']")
		collapse_item.click()

def load_progress(browser, picker_ids, popup_ids, progress, previous, enforce_geo_us=True):
	current_picker = 0
	config_list = list()
	for picker_id, popup_id in izip(picker_ids, popup_ids):
		# Try to click less buttons to save time
		if previous and previous[0][current_picker] == progress[current_picker]:
			if picker_id == 'resPckrcat_anchor':
				if previous[0][current_picker+1] == progress[current_picker+1]:
					# If for category, both selection hasn't changed, then don't click it.
					# This may be redundant, because, it seems if the selection changes, subselection will definitely change.
					# But I kept it here, for complete reasoning.
					config_list.append(previous[1][current_picker])
					config_list.append(previous[1][current_picker+1])
					aria_level_2_size = previous[2]
					current_picker += 2
					continue
			else:
				# If for this picker_id, nothing has changed, then don't click it
				config_list.append(previous[1][current_picker])
				current_picker += 1
				continue

		picker = browser.find_element_by_id(picker_id)
		picker.click()
		popup = browser.find_element_by_id(popup_id)
		# for category, do subselection
		if picker_id == 'resPckrcat_anchor':
			# collapse all expaneded items
			collapse_all(popup)
			# click aria-level 1 and 2
			selection = popup.find_elements_by_css_selector(".goog-tree-item[aria-level='1']")
			item = selection[progress[current_picker+1]]
			config_list.append(item.text)
			expand_item = item.find_element_by_css_selector(".goog-tree-expand-icon[type='expand']")
			expand_item.click()
			subselection = item.find_elements_by_css_selector(".goog-tree-item[aria-level='2']")
			subitem = subselection[progress[current_picker]]
			config_list.append(subitem.text)
			subitem.click()

			aria_level_2_size = len(subselection)
			current_picker += 2
		else:
			items = popup.find_elements_by_class_name('goog-tree-item')
			if len(items) == 0:
				items = popup.find_elements_by_class_name('goog-menuitem')

			if current_picker == 0 and enforce_geo_us:
				item = items[0] # default world wide
				for i in items:
					if i.text == 'United States':
						item = i
						break
			else:
				item = items[progress[current_picker]]
			# print item.text
			config_list.append(item.text)
			item.click()
			current_picker += 1
	return config_list, aria_level_2_size

def get_end(browser, picker_ids, popup_ids, aria_level_2_size):
	count = [1, 1, 1, 1, 1]
	current_picker = 0
	for picker_id, popup_id in izip(picker_ids, popup_ids):
		picker = browser.find_element_by_id(picker_id)
		picker.click()
		popup = browser.find_element_by_id(popup_id)
		# for category, do subselection
		if picker_id == 'resPckrcat_anchor':
			selection = popup.find_elements_by_css_selector(".goog-tree-item[aria-level='1']")
			count[current_picker+1] = len(selection)
			count[current_picker] = aria_level_2_size
			current_picker += 2
		else:
			items = popup.find_elements_by_class_name('goog-tree-item')
			# if no goog-tree-item is found, then look for goog-menuitem
			if len(items) == 0:
				items = popup.find_elements_by_class_name('goog-menuitem')
			count[current_picker] = len(items)
			current_picker += 1
	time.sleep(2)
	end = count
	end[0] = 9
	end[1] -= 1
	# end[4] = 2
	return end

class Progress:
	def __init__(self, current_file='../../data/trend/.progress', start=None):
		try:
			self.current_file = current_file
			values = filter(bool, open(self.current_file, 'r').read().split('\n'))
			self.current = [int(value)  for value in values ]
			if len(self.current) == 0:
				raise Exception
		except:
			if start:
				self.current = list(start)
			else:
				self.current = None
	
	def next(self, low_bound, high_bound):
		if not self.current:
			self.current = list(low_bound)
		# [4] is the higher bit, [0] is the lower bit
		# Find the lowest incrementable bit, increment it, 
		# and set the lower bits to low_bound.
		width = len(low_bound)
		if width != len(high_bound):
			print 'Error: low_bound and high_bound should have same number of elements!'
			sys.exit(1)
		has_next = False
		for i in range(0, width):
			if self.current[i] >= low_bound[i] and self.current[i] < high_bound[i]-1:
				has_next = True
				self.current[i] += 1
				for lower_bits in range(0, i):
					self.current[lower_bits] = low_bound[lower_bits]
				break
			elif self.current[i] < low_bound[i]:
				print 'Error: progress value cannot be smaller than low_bound value!'
		if has_next:
			return self.current
		else:
			return None

	def save(self):
		current_str = [str(c) for c in self.current]
		open(self.current_file, 'w').write('\n'.join(current_str))

def picker_popup(browser, picker_ids, popup_ids, output_dir):
	to_prefix = output_dir
	# preset variables
	from_prefix = DOWNLOAD_PATH
	max_tries = 5

	# geo: 8 is United States 
	# dat: last one is select dates
	# cat: category is special because its a two level selection, it will either be [selection] or [selection, sub_selection]
	# gprop: iterate through all the values
	start = [8, 0, 0, 0, 0]
	# need to update the end
	progress = Progress()
	current = progress.current
	previous = None
	while(current):
		print current
		# use previous and current, compare to see if there is update on the corresponding index, try to speed up the program
		# 'aria-level 2' size, which can be used to update end[3] 
		[filename, aria_level_2_size] = load_progress(browser, picker_ids, popup_ids, current, previous)
		config_list = filename
		filename = '_'.join(filename) + '.csv'
		print filename
		download_csv(browser)
		# Wait until the report file is available and rename it.
		counter = 0
		while counter < max_tries:
			time.sleep(2)
			try:
				os.rename(from_prefix + 'report.csv', to_prefix + filename)
				break
			except OSError as e:
				print "I/O error({0}): {1}".format(e.errno, e.strerror)
			counter += 1
		# The daily quote limit has been reached.
		if counter == max_tries:
			safe_quit(browser)
			raise QuoteError

		# a. save progress only when this one is finished
		# b. restarting program will execute this one again
		progress.save()
		end = get_end(browser, picker_ids, popup_ids, aria_level_2_size)
		previous = [list(current), config_list, aria_level_2_size]
		current = progress.next(start, end)

def restart_browser(browser_type, incognito=False, user_agent=None, use_tor=False, browser=None, interval=0):
	if browser:
		safe_quit(browser)
	time.sleep(interval)
	new_browser = start_browser(browser_type, incognito, user_agent, use_tor)
	new_browser.set_page_load_timeout(15)
	return new_browser

# not really useful because this parameter is used to run
def set_platform(user_agent, capabilities):
	ua_lower = user_agent.lower()
	if "windows" in ua_lower:
		capabilities["platform"] = "WINDOWS"
	elif "macintosh" in ua_lower:
		capabilities["platform"] = "MAC"
	elif "linux" in ua_lower:
		capabilities["platform"] = "LINUX"
	
def start_browser(browser_type, incognito=False, user_agent=None, use_tor=False):
	if browser_type == CD.CrawlConfig.FIREFOX:
		# configure firefox to download by default
		fp = webdriver.FirefoxProfile()
		if incognito:
			fp.set_preference("browser.private.browsing.autostart", True)
		if user_agent:
			fp.set_preference("general.useragent.override", user_agent)
		if use_tor:
			fp.set_preference("network.proxy.type", 1)
			fp.set_preference("network.proxy.socks", "127.0.0.1")
			fp.set_preference("network.proxy.socks_port", 9050)
		fp.set_preference("browser.download.folderList",2)
		fp.set_preference("browser.download.manager.showWhenStarting", False)
		# fp.set_preference("browser.download.dir",getcwd())
		fp.set_preference("browser.download.dir", DOWNLOAD_PATH)
		fp.set_preference("browser.helperApps.neverAsk.saveToDisk","text/csv")
		browser = webdriver.Firefox(firefox_profile=fp)
	elif browser_type == CD.CrawlConfig.CHROME:
		# configure chrome to disable the warning 'ignore-certificate-errors'
		options = webdriver.ChromeOptions()
		if incognito:
			options.add_argument("--incognito")
		if user_agent:
			options.add_argument("--user-agent=\"" + user_agent + "\"")
		if use_tor:
			PROXY = "socks5://127.0.0.1:9050"
			options.add_argument("--proxy-server=%s" % PROXY)
		options.add_experimental_option("excludeSwitches", ["ignore-certificate-errors"])
		capabilities = options.to_capabilities()
		# browser = webdriver.Chrome(executable_path=CHROMEDRIVER_PATH, chrome_options=options)
		# browser = webdriver.Remote(driver_service.service_url, desired_capabilities=capabilities)
		browser = webdriver.Remote(REMOTE_DRIVER, capabilities)
	elif browser_type == CD.CrawlConfig.HTMLUNIT:
		capabilities = webdriver.DesiredCapabilities.HTMLUNITWITHJS.copy()
		#capabilities["userAgent"] = '"{0}"'.format(user_agent)
		browser = webdriver.Remote(REMOTE_DRIVER, capabilities)
	else:
		print 'Invalid browser type, or browser type not handled currently.'
		sys.exit(2)
	return browser

def hot_search_words(credentials, output_dir, browser_type='Firefox'):
	# generate a unique output directory each run
	now = datetime.now().strftime("%Y%m%d-%H%M%S")
	output_dir = output_dir + 'csv.' + now + '/'
	mkdir_if_not_exist(output_dir)

	# load user credentials, and shuffle order of the accounts
	usr_pwds = filter(bool, open(credentials, 'r').read().split('\n'))
	random.shuffle(usr_pwds)
	for usr_pwd in usr_pwds:
		[usr, pwd] = usr_pwd.split('\t')
		try:
			# valid options for browser_type is: Firefox, Chrome
			trend_url = "http://www.google.com/trends/explore#"
			params = {'geo':'US', 'date':'today%2012-m', 'cat':'0-3', 'cmpt':'q'}
			# start browser
			if browser_type == 'Firefox':
				browser_type = CD.CrawlConfig.FIREFOX
			elif browser_type == 'Chrome':
				browser_type = CD.CrawlConfig.CHROME
			browser = start_browser(browser_type) #, use_tor=True)
			# download csv requires sign-in
			# sign_in_gmail(browser, 'lingfennan', 'lingfennan123')
			sign_in_gmail(browser, usr, pwd)

			# download all the keywords and manipulate them
			url = trend_query_url(trend_url, params)
			browser.get(url)
			
			picker_ids = ['resPckrgeo_anchor', 'resPckrdate_anchor', 'resPckrcat_anchor', 'resPckrgprop_anchor']
			popup_ids = ['resPckrgeo_content', 'resPckrdate_content', 'resPckrcat_content', 'resPckrgprop_content']
			picker_popup(browser, picker_ids, popup_ids, output_dir)
			safe_quit(browser)
		except QuoteError as e:
			print 'Current progress is', e.progress
		except:
			print 'Unknown error:', sys.exc_info()[0]
			raise

####################################################################################
def pattern_distance_distribution(inputfile, outputfile):
	lines = [line for line in open(inputfile, 'r').read().split('\n') if (line and line[0] == '[')]
	distance_distribution = dict()
	total = 0
	for line in lines:
		[key, value] = line.split(')')
		key = float(filter(bool, re.split('\[ |, |\s', key))[0])
		value = float(filter(bool, value.split(' '))[0])

		total = total + value
		if key in distance_distribution:
			distance_distribution[key] = distance_distribution[key] + value
		else:
			distance_distribution[key] = value

	print distance_distribution
	percentage = list()
	for k in sorted(distance_distribution):
		percentage.append(str(k) +',' + str(distance_distribution[k]/total))
	print percentage
	open(outputfile, 'w').write('\n'.join(percentage))

####################################################################################
def top_domain(URL):
	return URL.split('://')[-1].split('?')[0].split('/')[0]


def generate_test(observed_sites_filename, test_size=5000, positive_size=1000):
	text_observed_sites_filename = observed_sites_filename + ".text"
	dom_observed_sites_filename = observed_sites_filename + ".dom"
	if not (os.path.exists(dom_observed_sites_filename) and os.path.exists(text_observed_sites_filename)):
		raise Exception("Computed observed sites file doesn't exist!")

	# select for text simhash first
	computed_observed_sites_filename = text_observed_sites_filename
	observed_sites = CD.ObservedSites()
	read_proto_from_file(observed_sites, computed_observed_sites_filename)
	observed_site_list = list()
	for observed_site in observed_sites.site:
		observed_site_list.append(observed_site)
	random.shuffle(observed_site_list)
	# test_size is number of sites, actual observation should be more than this.
	test_sites = CD.ObservedSites()
	mismatch_sites = CD.ObservedSites()
	test_sites.config.CopyFrom(observed_sites.config)
	mismatch_sites.config.CopyFrom(observed_sites.config)

	test_list = observed_site_list[0:test_size]
	mismatch_list = test_list[0:positive_size]
	# original_label_list and mismatch_label_mapping is used in dom select.
	original_label_list = [observed_site.name for observed_site in test_list]
	mismatch_label_mapping = dict()
	for observed_site in mismatch_list:
		# observed_site in test_list are also changed.
		current_label = observed_site.name
		mismatch_label = random.sample(observed_site_list, 1)[0].name
		while (top_domain(current_label) == top_domain(mismatch_label)):
			mismatch_label = random.sample(observed_site_list, 1)[0].name
		observed_site.name = mismatch_label
		mismatch_site = mismatch_sites.site.add()
		mismatch_site.CopyFrom(observed_site)
		mismatch_label_mapping[current_label] = mismatch_label
	for observed_site in test_list:
		test_site = test_sites.site.add()
		test_site.CopyFrom(observed_site)
	mismatch_sites_filename = computed_observed_sites_filename + ".mismatch"
	test_sites_filename = computed_observed_sites_filename + ".test"
	write_proto_to_file(mismatch_sites, mismatch_sites_filename)
	write_proto_to_file(test_sites, test_sites_filename)

	# select for dom simhash now
	computed_observed_sites_filename = dom_observed_sites_filename
	observed_sites = CD.ObservedSites()
	read_proto_from_file(observed_sites, computed_observed_sites_filename)
	observed_sites_map = dict()
	for observed_site in observed_sites.site:
		observed_sites_map[observed_site.name] = observed_site
	test_sites = CD.ObservedSites()
	mismatch_sites = CD.ObservedSites()
	test_sites.config.CopyFrom(observed_sites.config)
	mismatch_sites.config.CopyFrom(observed_sites.config)

	test_list = list()
	for label in original_label_list:
		test_list.append(observed_sites_map[label])
	for label in mismatch_label_mapping:
		observed_sites_map[label].name = mismatch_label_mapping[label]
		mismatch_site = mismatch_sites.site.add()
		mismatch_site.CopyFrom(observed_sites_map[label])
	for observed_site in test_list:
		test_site = test_sites.site.add()
		test_site.CopyFrom(observed_site)
	mismatch_sites_filename = computed_observed_sites_filename + ".mismatch"
	test_sites_filename = computed_observed_sites_filename + ".test"
	write_proto_to_file(mismatch_sites, mismatch_sites_filename)
	write_proto_to_file(test_sites, test_sites_filename)

"""
def generate_test(inputfile, output_dir, test_number):
	# given input list, generate a test list with test_number instances, write to output_dir + 'test_list_$(test_number)',
	# generate an expected mismatch list with test_number/10 instances, write to output_dir + 'test_list_$(test_number).mismatch'
	records = filter(bool, open(inputfile, 'r').read().split('\n'))
	random.shuffle(records)
	# test_list is path and URL of the files to test. This is the test data.
	test_list = records[0:test_number]
	# path_list is path of the files to test, this can be used to select the mismatch data.
	path_list = list()
	URL_list = list()
	# test_map maps path to URL
	test_map = dict()
	for test_instance in test_list:
		[path, URL] = test_instance.split(',')
		path_list.append(path)
		URL_list.append(URL)
		test_map[path] = URL
	mismatch_number = test_number / 10
	random.shuffle(path_list)
	mismatch_path_list = path_list[0:mismatch_number]
	for mismatch_path in mismatch_path_list:
		URL = random.sample(URL_list, 1)[0]
		while (top_domain(test_map[mismatch_path]) == top_domain(URL)):
			URL = random.sample(URL_list, 1)[0]
		test_map[mismatch_path] = URL
	# prepare the content and write it to file
	test_list_filename  = '{0}/test_list_{1}'.format(output_dir, test_number)
	test_list_mismatch_filename = '{0}/test_list_{1}.mismatch'.format(output_dir, test_number)
	test_content = list()
	test_mismatch_content = list()
	for k in test_map:
		test_content.append(','.join([k, test_map[k]]))
	for path in mismatch_path_list:
		test_mismatch_content.append(','.join([path, test_map[path]]))

	# Only need to check whether test_list_filename directory exists, because the mismatch list is under the same directory.
	if not os.path.exists(os.path.dirname(test_list_filename)):
	    os.makedirs(os.path.dirname(test_list_filename))
	open(test_list_filename, 'w').write('\n'.join(test_content))
	open(test_list_mismatch_filename, 'w').write('\n'.join(test_mismatch_content))
"""

####################################################################################
def format_links(inputfile, outputfile, all_info):
	prefix = 'http://www.google.com'
	urls = open(inputfile, 'r').read()
	urls = filter(bool, urls.split('\n'))
	# in clickstrings, comma could show up. need further discussion.
	if all_info:
		urls = [url.split(',')[-1] for url in urls]
	urls = [prefix + url.split(' ')[1] for url in urls if len(url.split(' ')) == 3]
	print 'Parsed {0} click string into urls'.format(len(urls))
	open(outputfile, 'w').write('\n'.join(urls) + '\n')

####################################################################################
def merge_logs(merge_list, outputfile, config):
	# for the output filename, program will append suffix generated from config
	content = list()
	plot_logs = dict()

	# Record the minimum and maximum values
	params_value = dict()
	params_name = ['Simhash Type', 'Text Weight', 'Dom Weight', 'Page Stats Weight', 'Dom Level', 'Hamming Distance Threshold', 'Min Cluster Size']

	for merge_file in merge_list:
		lines = open(merge_file, 'r').read().split('\n')
		# whether we have started to retrieve data
		started = False
		# the key is read, waiting for the value (stats)
		waiting_for_stats = False
		for line in lines:
			params = line.split(',')
			if waiting_for_stats:
				if len(params) != 3:
					print "Error format, values not following key"
					return
				waiting_for_stats = False
				values = [float(param.split('=')[-1]) for param in params]
				plot_logs[key] = values
			elif len(params) == 7:
				waiting_for_stats = True
				started = True
				params = [param.split('=')[-1] for param in params]

				for param, param_name in izip(params, params_name):
					if param_name in params_value:
						params_value[param_name].append(int(param))
					else:
						params_value[param_name] = [int(param)]

				key = ','.join(params)
			elif started:
				# ignore the beginning, after we start to read config and stats.
				# ignore the trailing part, too.
				break


	# In the output file, the first line is the plot name, second line is the x,y label,
	# third line is the legend names.
	plot_name = ''
	x_y_label = ''
	legend_names = list()

	p = config.split(',')
	temp_plot_name = list()
	type_only = False
	# For TEXT AND DOM, only use type as the title
	type_map = {'1': 'TEXT', '2': 'DOM', '3': 'PAGESTATS', '4': 'TEXT_PAGESTATS', '5': 'DOM_PAGESTATS', '6': 'TEXT_DOM_PAGESTATS'}
	for param, name in izip(p, params_name):
		if param != '':
			if not type_only:
				if name == 'Simhash Type':
					temp_plot_name.append(name + '=' + type_map[param])
				else:
					temp_plot_name.append(name + '=' + param)
			if name == 'Simhash Type' and (param == '1' or param == '2'):
				type_only = True
		else:
			x_y_label = x_y_label + name + ','

	# Prepare the first three lines
	plot_name = ','.join(temp_plot_name)
	x_y_label = x_y_label + 'Statistics'
	legend_names = 'Purity,Density'

	outputfile_config = '{0}_type_{1}_tw_{2}_dw_{3}_psw_{4}_dl_{5}_h_{6}_mcs_{7}'.format(outputfile, p[0], p[1], p[2], p[3], p[4], p[5], p[6])
	outputf = open(outputfile_config, 'w')
	outputf.write('\n'.join([plot_name, x_y_label, legend_names]) + '\n')

	# Output the actual data
	min_params = list()
	max_params = list()
	output_key_index = 0
	counter = 0
	for param, name in izip(p, params_name):
		if param == '':
			output_key_index = counter
			min_params.append(min(params_value[name]))
			max_params.append(max(params_value[name]))
		else:
			min_params.append(int(param))
			max_params.append(int(param))
		counter = counter + 1

	for simtype in range(min_params[0], max_params[0] + 1):
		for tw in range(min_params[1], max_params[1] + 1):
			for dw in range(min_params[2], max_params[2] + 1):
				for psw in range(min_params[3], max_params[3] + 1):
					for dl in range(min_params[4], max_params[4] + 1):
						for h in range(min_params[5], max_params[5] + 1):
							for mcs in range(min_params[6], max_params[6] + 1):
								key = '{0},{1},{2},{3},{4},{5},{6}'.format(simtype, tw, dw, psw, dl, h, mcs)
								if key not in plot_logs:
									continue
								# ignore the f1 score, which is not meaningful now.
								# values = '{0},{1},{2}'.format(plot_logs[key][0], plot_logs[key][1], plot_logs[key][2])
								values = '{0},{1}'.format(plot_logs[key][0], plot_logs[key][1])
								output_key = [simtype, tw, dw, psw, dl, h, mcs]
								output_key_str = str(output_key[output_key_index])
								outputf.write('\n'.join([output_key_str, values]) + '\n')

def main(argv):
	has_function = False
	help_msg = 'util.py -f <function>  [-o <outputfile> -c <config>] [-i <click_string> -o <url_list>] [-i <inputfile> -n <test_number> -m <mismatch_number>] [-i <file.dist> -o <stats_file>] [-b <browser_type> -i <credentials> -o <output_dir>] [-b <browser_type> -o <ad_list>] [-i <inputfile> -o <outputfile> -p <proto>], valid functions are merge_logs, format_links, generate_test, pattern_distance_distribution, hot_search_words, ad_list, evaluation_form'
	try:
		opts, args = getopt.getopt(argv, "hf:i:o:c:n:b:m:p:a", ["function=", "ifile=", "ofile=", "config=", "test_number=", "browser_type=", "mismatch_number=", "proto="])
	except getopt.GetoptError:
		print help_msg
		sys.exit(2)
	# For merge_html
	all_info = False
	for opt, arg in opts:
		if opt == '-h':
			print help_msg
			sys.exit()
		elif opt in ("-f", "--function"):
			function = arg
			has_function = True
		elif opt in ("-i", "--ifile"):
			inputfile = arg
		elif opt in ("-o", "--ofile"):
			outputfile = arg
		elif opt in ("-a"):
			all_info = True
		elif opt in ("-c", "--config"):
			config = arg
		elif opt in ("-n", "--test_number"):
			test_number = int(arg)
		elif opt in ("-m", "--mismatch_number"):
			mismatch_number = int(arg)
		elif opt in ("-b", "--browser_type"):
			browser_type = arg
		elif opt in ("-p", "--proto"):
			proto = arg
		else:
			print help_msg
			sys.exit(2)
	if not has_function:
		print help_msg
		sys.exit(2)
	if function == 'merge_logs':
		# for the output filename, program will append suffix generated from config
		print 'function is', function
		merge_list = [line[:-1] for line in sys.stdin]
		merge_logs(merge_list, outputfile, config)
	elif function == 'format_links':
		print 'function is', function
		format_links(inputfile, outputfile, all_info)
	elif function == 'generate_test':
		print 'function is', function
		generate_test(inputfile, test_number, mismatch_number)
	elif function == 'pattern_distance_distribution':
		print 'function is', function
		pattern_distance_distribution(inputfile, outputfile)
	elif function == 'hot_search_words':
		print 'function is', function
		output_dir = outputfile
		hot_search_words(inputfile, output_dir, browser_type)
	elif function == 'ad_list':
		print 'function is', function
		report_list = [line[:-1] for line in sys.stdin]
		ad_list(report_list, outputfile, browser_type)
	elif function == "evaluation_form":
		print 'function is', function
		evaluation_form(inputfile, outputfile, proto)
	else:
		print help_msg
		sys.exit(2)

if __name__ == "__main__":
	main(sys.argv[1:])
