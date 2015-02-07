"""
References:
	wiki: https://www.mywot.com/wiki/API
	api: http://api.mywot.com/0.4/public_link_json2?hosts=example.COM/www.EXAMPLE.NET/&
	callback=process&key=<your API key>
	key: 2527e6e5cca9451a605eea8171b5c89314c74a7a 
	key: 494d0f03189d934b337198ea397a25e11161c9da
"""
import json
import sys
import urllib2

class WOT:
	def __init__(self):
		# api_key = '2527e6e5cca9451a605eea8171b5c89314c74a7a'
		api_key = '494d0f03189d934b337198ea397a25e11161c9da'
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
		return bad_domain, result
						

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

def filt(domains = ['example.net','everlastinghelp.com','13xa.com', 'google.com', 'sina.com.cn'], bar_points = 66):
	# define constants 
	block_size = 10
	bar_points = int(bar_points)
	reputation = WOT()
	#print reputation.process(domains)
	evaluationRes = []
	domain_count = len(domains)
	for i in range(0, domain_count, block_size):
		sub_domains = domains[i:i+block_size] if i + block_size <= domain_count \
				else domains[i:]
		result =  reputation.process(sub_domains)
		evaluationRes.extend(reputation.evaluate(result, bar_points)[0])
	return evaluationRes

def domain_scores(domains, outfile):
	block_size = 10
	bar_points = 85
	reputation = WOT()
	domain_count = len(domains)
	for i in range(0, domain_count, block_size):
		evaluationRes = []
		sub_domains = domains[i:i+block_size] if i + block_size <= domain_count \
				else domains[i:]
		result =  reputation.process(sub_domains)
		result_dict = reputation.evaluate(result, bar_points)[1]
		for key, value in result_dict:
			temp_list = list()
			temp_list.append(key)
			temp_list.extend(value)
			evaluationRes.append(temp_list)
		outf = open(outfile, 'a')
		for domain_score in evaluationRes:
			outf.write(",".join(domain_score))
	
if __name__ == "__main__":
	# print urllib2.urlopen('http://api.mywot.com/0.4/public_link_json?hosts=google.com/').read()
	# print urllib2.urlopen('https://api.mywot.com/0.4/public_link_json2?hosts=www.example.COM/&key=2527e6e5cca9451a605eea8171b5c89314c74a7a').read()
	filt(sys.argv[1:])

