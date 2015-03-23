import collections
import re
import sys
from simhash import Simhash
from bs4 import BeautifulSoup
from Queue import Queue
from utils.learning_detection_util import valid_instance
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
	# add html.decode('utf-8') to avoid UnicodeEncodeError
	texts = BeautifulSoup(html.decode('utf-8')).findAll(text=True)
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

class HtmlDomSet(object):
	def __init__(self):
		self.node = set()
		self.bi_node = set()
		self.tri_node = set()

class HtmlSimhashComputer(object):
	# input is CD.SimhashConfig
	def __init__(self, simhash_config):
		if valid_instance(simhash_config, CD.SimhashConfig):
			self.simhash_config = simhash_config

	def maximum_threads(self):
		return self.simhash_config.maximum_threads

	def para_type(self):
		return CD.FILE_PATH

	def build_by_features(self, features):
		# print len(features)
		if valid_instance(features, collections.Iterable):
			return Simhash(features)

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


	def _extract_one_node(self, node, html_dom_set):
		# process node information
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

	def _extract_html_node_iterative(self, node, html_dom_set):
		q = Queue()
		q.put(node)
		while not q.empty():
			current_node = q.get()
			try:
				if current_node.name is not None:
					# extract info from current node
					self._extract_one_node(current_node, html_dom_set)
					for child in current_node.children:
						q.put(child)
			except:
				print current_node
				print sys.exc_info()[0]

	def _extract_html_node_recursive(self, node, html_dom_set):
		# current node is tag
		try:
			name = node.name
			if name is not None:
				# process node
				node_str = name
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
					self._extract_html_node_recursive(child, html_dom_set)
		except RuntimeError:
			print sys.exc_info()[0]
			return
	
	def _extract_html_dom(self, tree, iterative=True):
		html_dom = CD.HtmlDom()
		html_dom_set = HtmlDomSet()
		# Traverse the tree
		# ROOT_TAG_NAME = u'[document]'
		if iterative:
			self._extract_html_node_iterative(tree, html_dom_set)
		else:
			self._extract_html_node_recursive(tree, html_dom_set)
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
		if valid_instance(html_text, CD.HtmlText):
			# weighted features are not supported by now
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
			return [self.build_by_features(features), len(features)]
	
	def build_by_dom(self, html_dom):
		if valid_instance(html_dom, CD.HtmlDom):
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
			return [self.build_by_features(features), len(features)]
	
	def compute_simhash(self, data, iterative=True):
		"""
		@parameter
		data: content of html file
		@return
		result: one of [[text_simhash, feature_count]], [[dom_simhash, feature_count]],
		[[text_simhash, feature_count], [dom_simhash, feature_count]]
		"""
		result = list()
		if self.simhash_config.simhash_type in [CD.TEXT, CD.TEXT_DOM]:
			text = visible_text(data)
			html_text = self._extract_html_text(text)
			result.append(self.build_by_text(html_text))
		if self.simhash_config.simhash_type in [CD.DOM, CD.TEXT_DOM]:
			soup = BeautifulSoup(data.decode('utf-8'))
			html_dom = self._extract_html_dom(soup, iterative)
			result.append(self.build_by_dom(html_dom))
		return result

