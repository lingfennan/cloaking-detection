import collections
import re
import sys
from simhash import Simhash
from bs4 import BeautifulSoup
import utils.proto.cloaking_detection_pb2 as CD


'''
from HTMLParser import HTMLParser
# Strip the tags to get text
class MLStripper(HTMLParser):
	def __init__(self):
		self.reset()
		self.fed = []
	def handle_data(self, d):
		self.fed.append(d)
	def get_data(self):
		return ''.join(self.fed)

def strip_tags(html):
	s = MLStripper()
	s.feed(html)
	result = s.get_data()
	return " ".join(result.split())
'''

def visible_text(html, twice=True):
	texts = BeautifulSoup(data).findAll(text=True)
	def visible(element):
		if element.parent.name in ['style', 'script', '[document]', 'head', 'title']:
			return False
		elif re.match('<!--.*-->', element.encode('utf-8')):
			return False
		return True
	visible_texts = filter(visible, texts)
	# Perform strip tags for the second time, because there are tags remained
	# And this time, the input may not be a correct html file.
	res = " ".join(" ".join(visible_texts).split())
	if twice:
		return " ".join(re.sub('<[^<]+?>', '', res).split())
	return res

class Html_Simhash_Computer(object):
	# input is CD.SimhashConfig
	def __init__(self, simhash_config):
		if isinstance(simhash_config, CD.SimhashConfig):
			self.simhash_config = simhash_config
		else:
			raise Exception("Bad parameter")

	def build_by_features(self, features):
		print features
		if isinstance(features, collections.Iterable):
			return Simhash(features).value
		else:
			raise Exception("Bad parameter")

	def _extract_html_text(self, text):
		html_text = CD.HtmlText()
		words = text.split()
		word_set = list(set(words))  # remove duplicates
		for w in word_set:
			word = html_text.word.add()
			word.name = w
		# Note, the simhash has xrange(max(len(content)-width+1, 1))
		# Doesn't know why.
		bi_gram_set = list(set([" ".join(words[i:i+2]) for i in xrange(len(words)-1)]))
		for w in bi_gram_set:
			bi_gram = html_text.bi_gram.add()
			bi_gram.name = w
		tri_gram_set = list(set([" ".join(words[i:i+3]) for i in xrange(len(words)-2)]))
		for w in tri_gram_set:
			tri_gram = html_text.tri_gram.add()
			tri_gram.name = w
		return html_text

	class HtmlDomSet:
		node = set()
		bi_node = set()
		tri_node = set()

	def _extract_html_node(self, node, html_dom_set):
		# current node is tag
		if node.name is not None:
			# process node
			node_str = node.name
			for attr_name in node.attrs.keys():
				node_str += '_' + attr_name
			html_dom_set.node.add(node_str)
			if node.parent:
				parent = node.parent
				parent_str = parent.name
				for attr_name in parent.attrs.keys():
					parent_str += '_' + attr_name
				html_dom_set.bi_node.add(parent_str + ',' + node_str)
			if node.parent and node.parent.parent:
				grand = node.parent.parent
				grand_str = grand.name
				for attr_name in grand.attrs.keys():
					grand_str += '_' + attr_name
				html_dom_set.tri_node.add(grand_str + ',' + parent_str + ',' + node_str)
			for child in node.children:
				# print str(child.name) + ":" + str(type(child))
				self._extract_html_node(child, html_dom_set)
	
	def _extract_html_dom(self, tree):
		html_dom = CD.HtmlDom()
		html_dom_set = self.HtmlDomSet()
		# Traverse the tree
		# ROOT_TAG_NAME = u'[document]'
		self._extract_html_node(tree, html_dom_set)
		for n in html_dom_set.node:
			node = html_dom.node.add()
			node.name = n
		for n in html_dom_set.bi_node:
			bi_node = html_dom.bi_node.add()
			bi_node.name = n
		for n in html_dom_set.tri_node:
			tri_node = html_dom.tri_node.add()
			tri_node.name = n
		return html_dom

	def build_by_text(self, html_text):
		if isinstance(html_text, CD.HtmlText):
			features = list()
			if self.simhash_config.usage.gram:
				for feature in html_text.word:
					features.append(feature.name)
			if self.simhash_config.usage.bi_gram:
				for feature in html_text.bi_gram:
					features.append(feature.name)
			if self.simhash_config.usage.tri_gram:
				for feature in html_text.tri_gram:
					features.append(feature.name)
			return self.build_by_features(features)
		else:
			raise Exception("Bad parameter")
	
	def build_by_dom(self, html_dom):
		if isinstance(html_dom, CD.HtmlDom):
			features = list()
			if self.simhash_config.usage.gram:
				for feature in html_dom.node:
					features.append(feature.name)
			if self.simhash_config.usage.bi_gram:
				for feature in html_dom.bi_node:
					features.append(feature.name)
			if self.simhash_config.usage.tri_gram:
				for feature in html_dom.tri_node:
					features.append(feature.name)
			return self.build_by_features(features)
		else:
			raise Exception("Bad parameter")
	
	def compute_simhash(self, data):
		result = list()
		if self.simhash_config.simhash_type in [CD.SimhashConfig.TEXT, CD.SimhashConfig.TEXT_DOM]:
			text = visible_text(data)
			html_text = self._extract_html_text(text)
			result.append(self.build_by_text(html_text))
		if self.simhash_config.simhash_type in [CD.SimhashConfig.DOM, CD.SimhashConfig.TEXT_DOM]:
			soup = BeautifulSoup(data)
			html_dom = self._extract_html_dom(soup)
			result.append(self.build_by_dom(html_dom))
		return result

# HtmlText

# HtmlDom
# Read Dom Tree
# https://docs.python.org/2/library/xml.dom.html
# filename = 'utils/data/forever21.html'
filename = 'utils/data/example.html'
data = open(filename, 'r').read()
# print visible_text(data)



config = CD.SimhashConfig()
config.simhash_type = CD.SimhashConfig.TEXT
config.usage.tri_gram = True
res = Html_Simhash_Computer(config).compute_simhash(data)
print '%x' % res[0]


config.simhash_type = CD.SimhashConfig.DOM
res = Html_Simhash_Computer(config).compute_simhash(data)
print '%x' % res[0]

