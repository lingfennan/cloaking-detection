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
		#self.params['callback']='process'
		self.base_url = 'http://api.mywot.com/0.4/public_link_json2?'

	def evaluate(self, examples, bar_points):
		#input: the scores computed by WOT API
		#output: the scores concluded
		negative = []
		questionable = []
		neutral = []
		positive = []
		negative.extend(["101'","102'","103","104","105"])
		questionable.extend(["201", "202", "203", "204", "205", "206", "207"])
		neutral.extend(["301", "302", "303", "304"])
		positive.extend(["501"])
		

		result = dict()
		good_domain = []
		resultUrl = []

		for keysTier1,valuesTier1 in examples.items():
			negativePoints = 0
			questionablePoints = 0
			neutralPoints = 0
			positivePoints = 0
			#print "keysTier1: " + (keysTier1)
			for keysTier2, valuesTier2 in valuesTier1.items():
				#print  "keysTiers2: " + (keysTier2)
				#print  (valuesTier2)
				if keysTier2 == 'categories':
					#print 'valesTier2 type: ' 
					#print type(valuesTier2)
					for cid, score in valuesTier2.items():
						#print 'cid: ' + cid
						if cid in questionable:
							questionablePoints += int(score)
							#print 'questionablePoints:' + questionablePoints
						elif cid in negative:
							negativePoints += int(score)
						elif cid in neutral:
							neutralPoints += int(score)
						elif cid in positive:
							positivePoints += int(score)
				pointsList = []
				pointsList.extend([negativePoints, questionablePoints, neutralPoints, positivePoints])
				
				if positivePoints > bar_points:
					good_domain.append(keysTier1)
					result[keysTier1] = pointsList

		bad_domain = list(set(examples) - set(good_domain));	
		return bad_domain
						
					
		


	def process(self, domains):
		# prepare the api request URL
		self.params['hosts'] = '/'.join(domains) + '/'
		para_str = '&'.join([key + '=' + self.params[key] \
				for key in self.params])
		url = self.base_url + para_str
		#print url
		# get JSON format content
		# content = urllib2.urlopen(url).read()
		data = json.load(urllib2.urlopen(url))
		return data

def filt(argv,domains = ['example.net','everlastinghelp.com','13xa.com', 'google.com', 'sina.com.cn'], bar_points = 66):
	# define constants 
	reputation = WOT()
	#print reputation.process(domains)
	result =  reputation.process(domains)
	evaluationRes = reputation.evaluate(result, bar_points)
	print evaluationRes
	
if __name__ == "__main__":
	# print urllib2.urlopen('http://api.mywot.com/0.4/public_link_json?hosts=google.com/').read()
	# print urllib2.urlopen('https://api.mywot.com/0.4/public_link_json2?hosts=www.example.COM/&key=2527e6e5cca9451a605eea8171b5c89314c74a7a').read()
	filt(sys.argv[1:])

