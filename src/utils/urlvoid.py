"""

homepage: http://www.urlvoid.com/
api key: e8dd26ad8ddb15fb0247cbd141271e5e6ae763c1
"""
import sys
import urllib2
import xml
import re

class URLVoid:
	def __init__(self):
		api_key = 'e8dd26ad8ddb15fb0247cbd141271e5e6ae763c1'
		self.base_url = "http://api.urlvoid.com/api1000/" \
				"e8dd26ad8ddb15fb0247cbd141271e5e6ae763c1/host/"

	def process(self, domain):
		url = self.base_url + domain + '/'
		data = urllib2.urlopen(url).read()
		return data

def main(argv):
	domains = ['everlastinghelp.com', \
			'sina.com.cn']
	# define constants 
	reputation = URLVoid()
	for domain in domains:
		print domain
		print reputation.process(domain)
		"""
		data = urllib2.urlopen("http://www.urlvoid.com/scan/" +
				domain).read()
		print data
		m = re.search('http://www\.urlvoid\.com/images/primages/pr[0-9]\.gif',
				data)
		print m.group(0)
		"""
	
if __name__ == "__main__":
	main(sys.argv[1:])

