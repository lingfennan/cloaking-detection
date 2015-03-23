from html_simhash_computer import HtmlSimhashComputer
from utils.learning_detection_util_test import assert_equal
import utils.proto.cloaking_detection_pb2 as CD

def test_compute_simhash():
	# HtmlText, HtmlDom
	filenames= ['../data/abusive_words.google.crawl/f94453065ca51301ffc1c1dde571858e.20150117-194236/ad1e363dad787127ce99c4dd14b88acf/index.html',
			'../data/abusive_words.google.crawl/f94453065ca51301ffc1c1dde571858e.20150118-050800/0a008f435c0972ad57ddf29343c93995/index.html',
			'../data/abusive_words.google.crawl/f94453065ca51301ffc1c1dde571858e.20150118-183852/c9d56725a436d486b31b90b118ac9e69/index.html']
	# text_simhash for second one: 9414395266106367332
	# dom_simhash for second one: 4243381963081104893
	for filename in filenames:
		print filename
		data = open(filename, 'r').read()
		# print visible_text(data)

		config = CD.SimhashConfig()
		config.simhash_type = CD.TEXT
		config.usage.tri_gram = True
		res = HtmlSimhashComputer(config).compute_simhash(data)
		# print '%x' % res[0].value
		print res[0][0].value
		print res

		# iteratively extract dom features
		data = open(filename, 'r').read()
		config = CD.SimhashConfig()
		config.simhash_type = CD.DOM
		config.usage.tri_gram = False
		res = HtmlSimhashComputer(config).compute_simhash(data)
		# print '%x' % res[0].value
		print res[0][0].value
		print res

		# recursively extract dom features
		recursive_res = HtmlSimhashComputer(config).compute_simhash(data, False)
		assert_equal(recursive_res[0][0].value, res[0][0].value)

def test_yahoo():
	filename= '../data/example_inner.html'
	print filename
	
	data = open(filename, 'r').read()
	# print visible_text(data)

	config = CD.SimhashConfig()
	config.simhash_type = CD.TEXT
	config.usage.tri_gram = True
	res = HtmlSimhashComputer(config).compute_simhash(data)
	# print '%x' % res[0].value
	print res[0][0].value
	print res

	# iteratively extract dom features
	data = open(filename, 'r').read()
	config = CD.SimhashConfig()
	config.simhash_type = CD.DOM
	config.usage.tri_gram = False
	res = HtmlSimhashComputer(config).compute_simhash(data)
	# print '%x' % res[0].value
	print res[0][0].value
	print res

if __name__ == "__main__":
	# test_compute_simhash()
	test_yahoo()

