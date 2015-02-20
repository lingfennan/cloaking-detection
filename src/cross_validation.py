import logging
import sys, getopt
import numpy as np
from sklearn.cross_validation import StratifiedKFold, cross_val_score
from cloaking_detection import CloakingDetection, compute_metrics, remove_noise
from cloaking_detection import sites_name_set
from cluster_learning import ClusterLearning
from utils.learning_detection_util import write_proto_to_file, read_proto_from_file, valid_instance
from utils.learning_detection_util import get_simhash_type, intersect_observed_sites_util
import utils.proto.cloaking_detection_pb2 as CD

def list_to_sites(sites_list, config, y_list = None):
	"""
	Construct observed_sites from sites_list and y_list (if specified).
	Note: config is not filled here.

	@parameter
	sites_list: the list of observed site
	y_list: the label for each observed site, if y_list is specified, only
	aggregate observed site with label '1'.
	@return
	site: the result of aggregation
	"""
	sites = CD.ObservedSites()
	sites.config.CopyFrom(config)
	if isinstance(sites_list, CD.ObservedSites):
		# assume the other situation is ObservedSites
		sites_list = sites_list.site
	if y_list is not None:
		y_size = len(y_list)
		for i in range(y_size):
			if y_list[i] == 1:
				s = sites.site.add()
				s.CopyFrom(sites_list[i])
	else:
		for site in sites_list:
			s = sites.site.add()
			s.CopyFrom(site)
	return sites

class Estimator(object):
	def __init__(self, simhash_config, outfile=None, coefficient=None, radius=None, cloaking_sites=None):
		# load learned sites map, which maps site name to related patterns
		self.best_params = dict()
		'''
		self.best_params['score'] = -1
		self.best_params['train_inconsistent'] = 1.2
		self.best_params['test_inconsistent'] = 3
		self.best_params['test_diameter'] = 15
		'''
		self.simhash_config = CD.SimhashConfig()
		self.simhash_config.CopyFrom(simhash_config)
		if outfile:
			self.outf = open(outfile, 'a')
		else:
			self.outf = None
		if coefficient:
			self.coefficient = list(coefficient)
		else:
			self.coefficient = [0.3, 1.0, 1.5, 2.0]
		if radius:
			self.radius = list(radius)
		else:
			self.radius = [15,20]
		if cloaking_sites:
			self.cloaking_sites = CD.ObservedSites()
			self.cloaking_sites.CopyFrom(cloaking_sites)
		else:
			self.cloaking_sites = None
		self.coefficient_step = 0.1
		self.radius_step = 1.0

	def fit(self, learn_train, detect_train, y_train):
		learn_train = list_to_sites(learn_train, self.simhash_config)
		detect_train = list_to_sites(detect_train, self.simhash_config)
		min_params = dict()
		test_params = dict()
		# T_train
		for t1 in np.arange(self.coefficient[0], self.coefficient[1], self.coefficient_step):
			test_params['train_inconsistent'] = t1
			cluster_learner = ClusterLearning()
			cluster_config = CD.ClusterConfig()
			cluster_config.algorithm.name = CD.Algorithm.HIERARCHICAL_CLUSTERING
			cluster_config.algorithm.inconsistent_coefficient = t1
			logger = logging.getLogger("global")
			logger.info("learning with coefficient: {0}".format(t1))
			learned_sites = cluster_learner.learn(learn_train, cluster_config)
			logger.info("learning complete!")
			# T_test
			for t2 in np.arange(self.coefficient[2], self.coefficient[3], self.coefficient_step):
				test_params['test_inconsistent'] = t2
				# R_test
				for r in np.arange(self.radius[0], self.radius[1], self.radius_step):
					test_params['test_diameter'] = r
					logger.info("testing with coefficient: {0}, min_radius: {1}".format(t2, r))
					current_score = self.score_learned(learned_sites, detect_train, y_train, test_params) 
					logger.info("testing complete, f1 score is: {0}".format(current_score))
					"""
					the less the error, 
					the less the distance between train and test threshold, ie. uncertain area, the better.
					"""
					if (('score' not in min_params) or (current_score < min_params['score']) or
							(current_score == min_params['score'] and min_params['distance'] > t2 - t1)):
						min_params['score'] = current_score
						min_params['distance'] = t2 - t1
						min_params['train_inconsistent'] = t1
						min_params['test_inconsistent'] = t2
						min_params['test_diameter'] = r
		if (('score' not in self.best_params) or (min_params['score'] < self.best_params['score']) or 
				(current_score == min_params['score'] and min_params['distance'] > t2 - t1)):
			self.best_params = dict(min_params)
			logger.info(self.best_params)
		return min_params

	def objective(self, errors):
		"""
		Our objective is to minimize the number of errors: including
		type I error and type II error.
		"""
		return errors[0] + errors[1]

	def score_learned(self, learned_sites, detect_test, y_test, test_params):
		valid_instance(learned_sites, CD.LearnedSites)
		valid_instance(detect_test, CD.ObservedSites)
		total_size = len(y_test)
		# if X_test is ObservedSites, list_to_sites does nothing or
		# selection (y_test not None)
		X_test = list_to_sites(detect_test, self.simhash_config)
		X_expected = list_to_sites(detect_test, self.simhash_config, y_test)
		detection_config = CD.DetectionConfig()
		detection_config.algorithm = CD.DetectionConfig.INCONSISTENT_COEFFICIENT
		detection_config.min_radius = test_params['test_diameter']
		detection_config.inconsistent_coefficient = test_params['test_inconsistent']
		detection_config.simhash_type = self.simhash_config.simhash_type
		detector = CloakingDetection(detection_config, learned_sites)
		cloaking_sites = detector.detect(X_test)

		if self.cloaking_sites:
			cloaking_sites = intersect_observed_sites_util(self.cloaking_sites, cloaking_sites)
		else:
			"""
			This is only useful for integrated testing, text detection set cloaking_sites,
			dom detection read this and intersect its cloaking_sites with the one 
			from text and evaluate it.
			"""
			self.cloaking_sites = CD.ObservedSites()
			self.cloaking_sites.CopyFrom(cloaking_sites)

		rate, pr, errors = compute_metrics(cloaking_sites, X_expected, total_size)
		logger = logging.getLogger("global")
		logger.warning(test_params)
		logger.warning(rate)
		logger.warning(pr)
		logger.warning(errors)

		"""
		Record the latest test scores for further analysis
		"""
		self.rate = rate
		self.pr = pr
		self.errors = errors
		res_str = ",".join([ str(test_params["train_inconsistent"]),
				str(test_params["test_inconsistent"]),
				str(test_params["test_diameter"]) ]) + "\n"
		res_str += ",".join([ str(rate[0]), str(rate[1]) ]) + "\n"
		if self.outf:
			self.outf.write(res_str)
		return self.objective(errors)

	def score(self, learn_test, detect_test, y_test, test_params = None):
		if not test_params:
			test_params = dict(sef.best_params)
		learn_test = list_to_sites(learn_test, self.simhash_config)
		detect_test = list_to_sites(detect_test, self.simhash_config)
		cluster_learner = ClusterLearning()
		cluster_config = CD.ClusterConfig()
		cluster_config.algorithm.name = CD.Algorithm.HIERARCHICAL_CLUSTERING
		cluster_config.algorithm.inconsistent_coefficient = test_params["train_inconsistent"]
		logger = logging.getLogger("global")
		logger.info("validating now, best parameters are:")
		logger.info(test_params)
		logger.info("learning with coefficient: {0}".format(test_params["train_inconsistent"]))
		learned_test_sites = cluster_learner.learn(learn_test, cluster_config)
		logger.info("learning complete!")
		# write to file for plotting
		return self.score_learned(learned_test_sites, detect_test, y_test,
				test_params)

def cross_validation(to_detect, to_learn, expected, noise, outfile, coefficient=None, radius=None):
	to_learn_sites = CD.ObservedSites()
	read_proto_from_file(to_learn_sites, to_learn)
	expected_sites = CD.ObservedSites()
	read_proto_from_file(expected_sites, expected)
	print "number of expected_sites"
	print len(expected_sites.site)
	to_detect_sites = CD.ObservedSites()
	read_proto_from_file(to_detect_sites, to_detect)
	noise_sites = CD.ObservedSites()
	read_proto_from_file(noise_sites, noise)
	filt_to_detect_sites = remove_noise(to_detect_sites, noise_sites)
	filt_to_learn_sites = remove_noise(to_learn_sites, noise_sites)
	expected_set = sites_name_set(expected_sites)

	"""
	Following are Stratified-K-Fold.
	"""
	kfold = 5
	total_site_name_list = list()
	to_detect_sites_map = dict()
	for site in filt_to_detect_sites.site:
		total_site_name_list.append(site.name)
		to_detect_sites_map[site.name] = site
	to_learn_sites_map = dict()
	for site in filt_to_learn_sites.site:
		to_learn_sites_map[site.name] = site
	
	# prepare the train and test
	to_detect_sites_list = list()
	to_learn_sites_list = list()
	Y = list()
	for name in total_site_name_list:
		to_detect_sites_list.append(to_detect_sites_map[name])
		to_learn_sites_list.append(to_learn_sites_map[name])
		if name in expected_set:
			Y.append(1)
		else:
			Y.append(0)

	to_detect_sites_list = np.array(to_detect_sites_list)
	to_learn_sites_list = np.array(to_learn_sites_list)
	Y = np.array(Y)
	skf = StratifiedKFold(Y, kfold)
	scores = list()
	best_params = list()
	for train, test in skf:
		print "train size: {0}, test size: {1}".format(len(train),
				len(test))
		learn_train, learn_test = to_learn_sites_list[train], to_learn_sites_list[test]
		detect_train, detect_test = to_detect_sites_list[train], to_detect_sites_list[test]
		y_train, y_test = Y[train], Y[test]

		estimator = Estimator(filt_to_detect_sites.config, outfile, coefficient, radius)
		estimator.fit(learn_train, detect_train, y_train)
		best_params.append(estimator.best_params)
		scores.append(estimator.score(learn_test, detect_test, y_test))
		# filt_cloaking_sites = remove_noise(both_detected, noise_sites)
		# cross_val_score(svc, X_digits, y_digits, cv=kfold, n_jobs=-1)
	print "best_parameters"
	print best_params
	print scores


def plot_ROC(to_detect, to_learn, expected, noise, outfile, coefficient=None, radius=None):
	to_learn_sites = CD.ObservedSites()
	read_proto_from_file(to_learn_sites, to_learn)
	expected_sites = CD.ObservedSites()
	read_proto_from_file(expected_sites, expected)
	print "number of expected_sites"
	print len(expected_sites.site)
	to_detect_sites = CD.ObservedSites()
	read_proto_from_file(to_detect_sites, to_detect)
	noise_sites = CD.ObservedSites()
	read_proto_from_file(noise_sites, noise)
	filt_to_detect_sites = remove_noise(to_detect_sites, noise_sites)
	filt_to_learn_sites = remove_noise(to_learn_sites, noise_sites)
	expected_set = sites_name_set(expected_sites)

	"""
	Following are Stratified-K-Fold.
	"""
	kfold = 5
	total_site_name_list = list()
	to_detect_sites_map = dict()
	for site in filt_to_detect_sites.site:
		total_site_name_list.append(site.name)
		to_detect_sites_map[site.name] = site
	to_learn_sites_map = dict()
	for site in filt_to_learn_sites.site:
		to_learn_sites_map[site.name] = site
	
	# prepare the train and test
	to_detect_sites_list = list()
	to_learn_sites_list = list()
	Y = list()
	for name in total_site_name_list:
		to_detect_sites_list.append(to_detect_sites_map[name])
		to_learn_sites_list.append(to_learn_sites_map[name])
		if name in expected_set:
			Y.append(1)
		else:
			Y.append(0)

	to_detect_sites_list = np.array(to_detect_sites_list)
	to_learn_sites_list = np.array(to_learn_sites_list)
	Y = np.array(Y)
	skf = StratifiedKFold(Y, kfold)

	# scan the parameters and output the FPR and TPR
	params = dict()
	params['train_inconsistent'] = coefficient[0] 
	params['test_inconsistent'] = coefficient[1]
	# params['test_diameter'] = radius[0]
	outf = open(outfile, 'a')
	for r in np.arange(radius[0], radius[1], 1):
		tpr = np.zeros(5, dtype=np.float)
		fpr = np.zeros(5, dtype=np.float)
		params['test_diameter'] = r
		count = 0
		for train, test in skf:
			print "train size: {0}, test size: {1}".format(len(train),
					len(test))
			learn_train, learn_test = to_learn_sites_list[train], to_learn_sites_list[test]
			detect_train, detect_test = to_detect_sites_list[train], to_detect_sites_list[test]
			y_train, y_test = Y[train], Y[test]

			estimator = Estimator(filt_to_detect_sites.config)
			estimator.score(learn_test, detect_test, y_test, params)
			tpr[count] = estimator.rate[0]
			fpr[count] = estimator.rate[1]
			count += 1

		res_str = ",".join([ str(params["train_inconsistent"]),
				str(params["test_inconsistent"]),
				str(params["test_diameter"]) ]) + "\n"
		res_str += ",".join([ str(tpr.mean()), str(fpr.mean()) ]) + "\n"
		outf.write(res_str)


def integrated_plot_ROC(text_input, text_train, dom_input, dom_train, expected, noise, outfile,
		c_text_train, c_text_test, c_dom_train, c_dom_test, 
		r_text_start, r_text_end, r_dom_start, r_dom_end):
	text_to_learn_sites = CD.ObservedSites()
	read_proto_from_file(text_to_learn_sites, text_train)
	dom_to_learn_sites = CD.ObservedSites()
	read_proto_from_file(dom_to_learn_sites, dom_train)

	expected_sites = CD.ObservedSites()
	read_proto_from_file(expected_sites, expected)
	print "number of expected_sites"
	print len(expected_sites.site)
	text_to_detect_sites = CD.ObservedSites()
	read_proto_from_file(text_to_detect_sites, text_input)
	dom_to_detect_sites = CD.ObservedSites()
	read_proto_from_file(dom_to_detect_sites, dom_input)
	noise_sites = CD.ObservedSites()
	read_proto_from_file(noise_sites, noise)
	filt_text_to_detect_sites = remove_noise(text_to_detect_sites, noise_sites)
	filt_text_to_learn_sites = remove_noise(text_to_learn_sites, noise_sites)
	filt_dom_to_detect_sites = remove_noise(dom_to_detect_sites, noise_sites)
	filt_dom_to_learn_sites = remove_noise(dom_to_learn_sites, noise_sites)

	expected_set = sites_name_set(expected_sites)
	"""
	Following are Stratified-K-Fold.
	"""
	kfold = 5
	total_site_name_list = list()
	text_to_detect_sites_map = dict()
	for site in filt_text_to_detect_sites.site:
		total_site_name_list.append(site.name)
		text_to_detect_sites_map[site.name] = site
	text_to_learn_sites_map = dict()
	for site in filt_text_to_learn_sites.site:
		text_to_learn_sites_map[site.name] = site

	dom_to_detect_sites_map = dict()
	for site in filt_dom_to_detect_sites.site:
		dom_to_detect_sites_map[site.name] = site
	dom_to_learn_sites_map = dict()
	for site in filt_dom_to_learn_sites.site:
		dom_to_learn_sites_map[site.name] = site
	
	# prepare the train and test
	text_to_detect_sites_list = list()
	text_to_learn_sites_list = list()
	dom_to_detect_sites_list = list()
	dom_to_learn_sites_list = list()

	Y = list()
	for name in total_site_name_list:
		text_to_detect_sites_list.append(text_to_detect_sites_map[name])
		text_to_learn_sites_list.append(text_to_learn_sites_map[name])
		dom_to_detect_sites_list.append(dom_to_detect_sites_map[name])
		dom_to_learn_sites_list.append(dom_to_learn_sites_map[name])

		if name in expected_set:
			Y.append(1)
		else:
			Y.append(0)

	text_to_detect_sites_list = np.array(text_to_detect_sites_list)
	text_to_learn_sites_list = np.array(text_to_learn_sites_list)
	dom_to_detect_sites_list = np.array(dom_to_detect_sites_list)
	dom_to_learn_sites_list = np.array(dom_to_learn_sites_list)

	Y = np.array(Y)
	skf = StratifiedKFold(Y, kfold)

	# scan the parameters and output the FPR and TPR
	text_params = dict()
	text_params['train_inconsistent'] = c_text_train
	text_params['test_inconsistent'] = c_text_test
	dom_params = dict()
	dom_params['train_inconsistent'] = c_dom_train
	dom_params['test_inconsistent'] = c_dom_test

	# params['test_diameter'] = radius[0]
	outf = open(outfile + "_text_r_" + str(r_text_start), 'a')
	for t_r in np.arange(r_text_start, r_text_end, 1):
		text_params['test_diameter'] = t_r 
		for d_r in np.arange(r_dom_start, r_dom_end, 1):
			dom_params['test_diameter'] = d_r
			tpr = np.zeros(5, dtype=np.float)
			fpr = np.zeros(5, dtype=np.float)
			count = 0
			for train, test in skf:
				print "train size: {0}, test size: {1}".format(len(train),
						len(test))
				text_learn_train, text_learn_test = text_to_learn_sites_list[train], text_to_learn_sites_list[test]
				text_detect_train, text_detect_test = text_to_detect_sites_list[train], text_to_detect_sites_list[test]
				dom_learn_train, dom_learn_test = dom_to_learn_sites_list[train], dom_to_learn_sites_list[test]
				dom_detect_train, dom_detect_test = dom_to_detect_sites_list[train], dom_to_detect_sites_list[test]
				y_train, y_test = Y[train], Y[test]
				text_estimator = Estimator(filt_text_to_detect_sites.config)
				text_estimator.score(text_learn_test, text_detect_test, y_test, text_params)

				dom_estimator = Estimator(simhash_config = filt_dom_to_detect_sites.config, 
						cloaking_sites = text_estimator.cloaking_sites)
				dom_estimator.score(dom_learn_test, dom_detect_test, y_test, dom_params)
				tpr[count] = dom_estimator.rate[0]
				fpr[count] = dom_estimator.rate[1]
				count += 1

			res_str = ",".join([ str(dom_params["train_inconsistent"]),
					str(dom_params["test_inconsistent"]),
					str(dom_params["test_diameter"]) ]) + "\n"
			res_str += ",".join([ str(tpr.mean()), str(fpr.mean()) ]) + "\n"
			outf.write(res_str)

def main(argv):
	has_function = False
	help_msg = """cross_validation.py -f <function> [-i <inputfile> -t
		<trainfile> -e <expectedfile> -o <outfile> -c <min_train,max_train,min_test,max_test> -r <min_radius,max_radius>] cross_validation
		[-i <inputfile> integrated_cross_validation]
		[-i <inputfile> -t <trainfile> -e <expectedfile> -o <outfile>
		-c <train,test> -r <min_radius,max_radius>] plot_ROC
		[-i <inputfile> 
		-c <text_train,text_test,dom_train,dom_test>
		-r <text_min_radius,text_max_radius,dom_min_radius,text_max_radius>] integrated_plot_ROC
		"""
	try:
		opts, args = getopt.getopt(argv, "hf:i:l:e:t:r:n:c:o:",
				["function=", "ifile=", "lfile=", "efile=",
					"trainfile=", "ofile=", "radius=", "constant=",
					"coefficient="])
	except getopt.GetoptError:
		print help_msg
		sys.exit(2)
	hasinputfile = False
	simhash_type = None
	min_radius = 0
	std_constant = 3
	coefficient = '0,1,1,3'
	for opt, arg in opts:
		if opt == "-h":
			print help_msg
			sys.exit()
		elif opt in ("-f", "--function"):
			function = arg
			has_function = True
		elif opt in ("-i", "--ifile"):
			hasinputfile = True
			inputfile = arg
		elif opt in ("-l", "--lfile"):
			learnedfile = arg
		elif opt in ("-e", "--efile"):
			expectedfile = arg
		elif opt in ("-t", "--trainfile"):
			trainfile = arg
		elif opt in ("-o", "--ofile"):
			outfile = arg
		elif opt in ("-r", "--radius"):
			min_radius = arg
		elif opt in ("-n", "--constant"):
			std_constant = arg
		elif opt in ("-c", "--coefficient"):
			coefficient = arg
		else:
			print help_msg
			sys.exit(2)
	if hasinputfile:
		logging.basicConfig(filename= inputfile + "_running_log_" + function, level=logging.DEBUG)
		logging.getLogger("global")
	if not has_function:
		print help_msg
		sys.exit()
	if function == "cross_validation":
		# cross validation for one type
		coefficient = [float(c) for c in coefficient.split(',')]
		radius = [float(c) for c in min_radius.split(',')]
		noisefile = expectedfile + ".noise"
		cross_validation(inputfile, trainfile, expectedfile, noisefile,
				outfile, coefficient, radius)
	elif function == "integrated_plot_ROC":
		filenames = filter(bool, open(inputfile, 'r').read().split('\n'))
		text_input = filenames[0]
		text_train = filenames[1]
		dom_input = filenames[2]
		dom_train = filenames[3]
		expected = filenames[4]
		noise = filenames[5]
		outfile = filenames[6]
		[c_text_train, c_text_test, c_dom_train, c_dom_test] = [float(c) for c in coefficient.split(',')]
		[r_text_start, r_text_end, r_dom_start, r_dom_end] = [float(c) for c in min_radius.split(',')]
		integrated_plot_ROC(text_input, text_train, dom_input, dom_train,
				expected, noise, outfile,
				c_text_train, c_text_test, c_dom_train, c_dom_test, 
				r_text_start, r_text_end, r_dom_start, r_dom_end)
	elif function == "plot_ROC":
		coefficient = [float(c) for c in coefficient.split(',')]
		radius = [float(c) for c in min_radius.split(',')]
		noisefile = expectedfile + ".noise"
		plot_ROC(inputfile, trainfile, expectedfile, noisefile,
				outfile, coefficient, radius)
	else:
		print help_msg
		sys.exit(2)

if __name__ == "__main__":
	main(sys.argv[1:])

