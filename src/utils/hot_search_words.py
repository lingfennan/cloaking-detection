import csv
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from learning_detection_util import read_proto_from_file, write_proto_to_file
import proto.cloaking_detection_pb2 as CD

"""
Dependencies:
	selenium: Refer to https://pypi.python.org/pypi/selenium for installation instructions.

Example Usage:
	# visit Google trends data and collect information from there, report.csv for each configuration is downloaded..
	# output directory is output_dir + 'csv.' + date + '/'
	python util.py -f hot_search_words -b Chrome -i credentials -o trend/
"""


class HotSearchWords:
	def set_start(self, start):
		self.start = start
	def set_end(self, end):
		self.end = end
	def collect(self):
		None


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
	
	current_file = TREND_PROGRESS

	def __init__(self):
		try:
			values = filter(bool, open(self.current_file, 'r').read().split('\n'))
			self.current = [int(value)  for value in values ]
			if len(self.current) != 5:
				raise Exception
		except:
			self.current = [8, 0, 0, 0, 0]
	
	def next(self, start, end):
		# [4] is the higher bit, [0] is the lower bit
		# Find the lowest incrementable bit, increment it, and set the lower bits to start
		width = len(start)
		if width != len(end):
			print 'Error: start and end should have same number of elements!'
			sys.exit(1)
		has_next = False
		for i in range(0, width):
			if self.current[i] >= start[i] and self.current[i] < end[i]-1:
				has_next = True
				self.current[i] += 1
				for lower_bits in range(0, i):
					self.current[lower_bits] = start[lower_bits]
				break
			elif self.current[i] < start[i]:
				print 'Error: progress value cannot be smaller than start value!'
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
			browser.quit()
			raise QuoteError

		# a. save progress only when this one is finished
		# b. restarting program will execute this one again
		progress.save()
		end = get_end(browser, picker_ids, popup_ids, aria_level_2_size)
		previous = [list(current), config_list, aria_level_2_size]
		current = progress.next(start, end)
	
def start_browser(browser_type, incognito=False, user_agent=None, use_tor=False):
	if browser_type == 'Firefox' or browser_type == CD.CrawlConfig.FIREFOX:
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
	elif browser_type == 'Chrome' or browser_type == CD.CrawlConfig.CHROME:
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
		browser = webdriver.Chrome(executable_path=CHROMEDRIVER_PATH, chrome_options=options)
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
			browser.quit()
		except QuoteError as e:
			print 'Current progress is', e.progress
		except:
			print 'Unknown error:', sys.exc_info()[0]
			raise

####################################################################################
