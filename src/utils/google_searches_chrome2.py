import urllib2
import codecs
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.keys import Keys
import time
import urllib
import re
import commands
import string
import sys
import time
import random
from nltk.tokenize import word_tokenize
from nltk.tag import pos_tag
from nltk.chunk import ne_chunk
from nltk.tokenize import word_tokenize, wordpunct_tokenize, sent_tokenize
from itertools import combinations

pwd = commands.getoutput('pwd')
index = string.rfind(pwd, '/')
date = pwd[index+1:]
logfile = 'log.txt'

times = 0
sleep_time = 1 
all_cookies = []
cookies = dict()
def createBrowser(port):
#	profile = webdriver.FirefoxProfile('/home/wei/.mozilla/firefox/azyxje77.default/')
#	profile = webdriver.FirefoxProfile()
	'''
	profile.set_preference('network.proxy.type',1)
	profile.set_preference('network.proxy.http','127.0.0.1')
	profile.set_preference('network.proxy.http_port',8118)
	profile.set_preference('network.proxy.ssl','127.0.0.1')
	profile.set_preference('network.proxy.ssl_port',8118)
	profile.set_preference('network.proxy.socks','127.0.0.1')
	profile.set_preference('network.proxy.socks_port',9050)
	profile.set_preference('network.http.keep-alive.timeout',20)
	profile.set_preference('network.proxy.no_proxies_on', '127.0.0.1, .google.com, .gatech.com, .googleadservices.com, .googletagservices.com, .gstatic.com, .googleapis.com, .doubleclick.net, .2mdn.net')
	profile.set_preference('webdriver.load.strategy','unstable')
	'''

#	browser = webdriver.Firefox(profile) # Get local session of firefox
	browser = webdriver.Chrome()
	browser.delete_all_cookies()
#	browser.set_page_load_timeout(5)
	return browser

def destroyBrowser(browser):
	browser.close()

def getSearchResults(browser, url, logfile):
	'''get the isp by query a specific url'''

	global times
	global all_cookies
	global cookies
	n = random.gauss(1,1)
#	print 'sleeping for', n, 'seconds to get', url
#	time.sleep(abs(n))
	time.sleep(abs(n)+1)
#	time.sleep(1)

	Elem = None
	while Elem is None:
		try:
			browser.get(url)
			time.sleep(1)

		except TimeoutException:
			pass
		Elem = waitFindingElement(browser)
		if Elem is None:
			log_f = open(logfile, 'a')
			log_f.write('page load failed. '+url+'\n')
			log_f.close()
	title_l = list()
	url_l = list()
	cite_l = list()
	date_l = list()
	result_elems = Elem.find_elements_by_class_name('g')
	for result_elem in result_elems:
		try:
			title_elem = result_elem.find_element_by_tag_name('h3')
			title = title_elem.text
		except NoSuchElementException:
			print 'NoTitleElement'
			continue

		link_elem = title_elem.find_element_by_tag_name('a')
		url = link_elem.get_attribute('href')

		cite_elem = result_elem.find_element_by_tag_name('cite')
		cite = cite_elem.text

		date = 'DEFAULT-DATE'
		f_elems = result_elem.find_elements_by_class_name('f')
		for elem in f_elems:
			class_name = elem.get_attribute('class')
			if class_name == 'f std':
				date = elem.text
#		print title,'\n',url,'\n',cite,'\n',abstract,'\n',date,'\n'
		title_l.append(title)
		url_l.append(url)
		cite_l.append(cite)
		date_l.append(date)
	return title_l, url_l, cite_l, date_l

def waitFindingElement(driver):
	counter = 0
	while counter < 45:
		try:
			elem = driver.find_element_by_id('ires')
			break
		except NoSuchElementException:
			time.sleep(1)
			counter += 1
			elem = None
	return elem


def dealWithKeyword(keyword):
	################## given one keyword, output the links #####################
	
	
	google_url = 'http://www.google.com/search?hl=en&num=100&q=dns+changer&tbo=d&tbs=cdr:1,cd_min:11/1/2011,cd_max:07/31/2012'

	output_file = 'dns_changer_search_results.txt'
	output_f = codecs.open(output_file, encoding='utf-8', mode='w')
	chrome = createBrowser(0)
	waiting = raw_input('Waiting for user to modify search settings')
	date_counter = dict()
	for page in range(0, 1):
		start = page * 100
		print 'start=['+str(start)+']'
		start_url = '&start='+str(start)
		url = google_url+start_url
		title_l, url_l, cite_l, date_l = getSearchResults(chrome, url, logfile)
		for j in range(0, len(title_l)):
			title = title_l[j]
			url = url_l[j]
			cite = cite_l[j]
			date = date_l[j]
			if date in date_counter:
				date_counter[date] += 1
			else:
				date_counter[date] = 1
			output_f.write(title+'\t')
			output_f.write(url+'\t')
			output_f.write(cite+'\t')
			output_f.write(date+'\n')
	output_f.close()
	destroyBrowser(chrome)

	date_map = dict()
	for date, num in date_counter.items():
		if date == 'DEFAULT-DATE':
			date_map[date] = num
			continue
		index1 = date.find(' ')
		month = date[:index1]
		index2 = date.find(',')
		day = date[index1+1:index2]
		day_num = int(day)
		if day_num < 10:
			day = '0'+day
		year = date[index2+2:]
		if month =='Jan':
			month = '01'
		elif month == 'Feb':
			month = '02'
		elif month == 'Mar':
			month = '03'
		elif month == 'Apr':
			month = '04'
		elif month == 'May':
			month = '05'
		elif month == 'Jun':
			month = '06'
		elif month == 'Jul':
			month = '07'
		elif month == 'Aug':
			month = '08'
		elif month == 'Sep':
			month = '09'
		elif month == 'Oct':
			month = '10'
		elif month == 'Nov':
			month = '11'
		elif month == 'Dec':
			month = '12'
		date = year+month+day
		date_map[date] = num

	output_file = 'dns_changer_search_dates.txt'
	output_f = codecs.open(output_file, encoding='utf-8', mode='w')
	for date, num in sorted(date_map.items()):
		output_f.write(date+'\t'+str(num)+'\n')
	output_f.close()
