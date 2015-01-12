"""

homepage: http://www.urlvoid.com/
api key: e8dd26ad8ddb15fb0247cbd141271e5e6ae763c1
"""
import sys
import urllib2
import xml

class URLVoid:
	def __init__(self):
		api_key = 'e8dd26ad8ddb15fb0247cbd141271e5e6ae763c1'
		self.base_url = "http://api.urlvoid.com/api1000/" \
				"e8dd26ad8ddb15fb0247cbd141271e5e6ae763c1/host/"

	def process(self, domain):
		url = self.base_url + domain + '/'
		data = urllib2.urlopen(url)
		return data

def main(argv):
	domains = ['example.COM', 'www.EXAMPLE.NET', 'everlastinghelp.com']
	# define constants 
	reputation = URLVoid()
	for domain in domains:
		print reputation.process(domain)
	
if __name__ == "__main__":
	main(sys.argv[1:])

