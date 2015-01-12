"""
References:
	wiki: https://www.mywot.com/wiki/API
	api: http://api.mywot.com/0.4/public_link_json2?hosts=example.COM/www.EXAMPLE.NET/&
	callback=process&key=<your API key>
	key: 2527e6e5cca9451a605eea8171b5c89314c74a7a 
"""
import json
import sys
import urllib2

class WOT:
	def __init__(self):
		api_key = '2527e6e5cca9451a605eea8171b5c89314c74a7a'
		self.params = dict()
		self.params['key'] = api_key
		# self.params['callback'] = 'process'
		self.base_url = 'http://api.mywot.com/0.4/public_link_json2?'

	def process(self, domains):
		# prepare the api request URL
		self.params['hosts'] = '/'.join(domains) + '/'
		para_str = '&'.join([key + '=' + self.params[key] \
				for key in self.params])
		url = self.base_url + para_str
		print url
		# get JSON format content
		# content = urllib2.urlopen(url).read()
		data = json.load(urllib2.urlopen(url))
		return data

def main(argv):
	domains = ['example.COM', 'www.EXAMPLE.NET']
	# define constants 
	reputation = WOT()
	print reputation.process(domains)
	
if __name__ == "__main__":
	print urllib2.urlopen('http://api.mywot.com/0.4/public_link_json?hosts=google.com/').read()
	print urllib2.urlopen('https://api.mywot.com/0.4/public_link_json2?hosts=www.example.COM/&key=2527e6e5cca9451a605eea8171b5c89314c74a7a').read()
	main(sys.argv[1:])

