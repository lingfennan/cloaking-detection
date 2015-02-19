import logging
import sys, getopt
import numpy as np
from sklearn.cross_validation import StratifiedKFold, cross_val_score
from cloaking_detection import CloakingDetection, compute_metrics, remove_noise
from cloaking_detection import sites_name_set
from cluster_learning import ClusterLearning
from utils.learning_detection_util import write_proto_to_file, read_proto_from_file, valid_instance
from utils.learning_detection_util import get_simhash_type
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
	def __init__(self, simhash_config, outfile):
		# load learned sites map, which maps site name to related patterns
		self.best_params = dict()
		self.best_params['score'] = 0.0
		self.best_params['train_inconsistent'] = 1.2
		self.best_params['test_inconsistent'] = 3
		self.best_params['test_diameter'] = 15
		self.simhash_config = CD.SimhashConfig()
		self.simhash_config.CopyFrom(simhash_config)
		self.outf = open(outfile, 'a')

	def fit(self, learn_train, detect_train, y_train):
		learn_train = list_to_sites(learn_train, self.simhash_config)
		detect_train = list_to_sites(detect_train, self.simhash_config)
		min_params = dict()
		min_params['score'] = 0
		test_params = dict()
		# for t1 in np.arange(0.0, 0.5, 0.1):
		# for t1 in np.arange(0.5, 3.1, 0.5):
		for t1 in np.arange(-0.5, 1.0, 0.1):
			test_params['train_inconsistent'] = t1
			cluster_learner = ClusterLearning()
			cluster_config = CD.ClusterConfig()
			cluster_config.algorithm.name = CD.Algorithm.HIERARCHICAL_CLUSTERING
			cluster_config.algorithm.inconsistent_coefficient = t1
			logger = logging.getLogger("global")
			logger.info("learning with coefficient: {0}".format(t1))
			learned_sites = cluster_learner.learn(learn_train, cluster_config)
			logger.info("learning complete!")
			# for t2 in np.arange(0.0, 1.0, 0.1):
			# for t2 in np.arange(0.5, 6.0, 1):
			for t2 in np.arange(0.5, 1.5, 0.1):
				test_params['test_inconsistent'] = t2
				# for r in np.arange(5, 21, 5):
				# for r in np.arange(5, 31, 5):
				for r in np.arange(10, 20, 1):
					test_params['test_diameter'] = r
					logger.info("testing with coefficient: {0}, min_radius: {1}".format(t2, r))
					current_score = self.score_learned(learned_sites, detect_train, y_train, test_params) 
					logger.info("testing complete, f1 score is: {0}".format(current_score))
					if current_score < min_params['score']:
						min_params['score'] = current_score
						min_params['train_inconsistent'] = t1
						min_params['test_inconsistent'] = t2
						min_params['test_diameter'] = r
		if min_params['score'] < self.best_params['score']:
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
		rate, pr, errors = compute_metrics(cloaking_sites, X_expected, total_size)
		logger = logging.getLogger("global")
		logger.warning(test_params)
		logger.warning(rate)
		logger.warning(pr)
		logger.warning(errors)
		# write to file for plotting
		res_str = ",".join([ str(test_params["train_inconsistent"]),
				str(test_params["test_inconsistent"]),
				str(test_params["test_diameter"]) ]) + "\n"
		res_str += ",".join([ str(rate[0]), str(rate[1]) ]) + "\n"
		self.outf.write(res_str)
		"""
		if pr[0] + pr[1] == 0:
			return 0
		else:
			return 2 * pr[0] * pr[1] / (pr[0] + pr[1]) 
		"""
		return self.objective(errors)

	def score(self, learn_test, detect_test, y_test):
		learn_test = list_to_sites(learn_test, self.simhash_config)
		detect_test = list_to_sites(detect_test, self.simhash_config)
		cluster_learner = ClusterLearning()
		cluster_config = CD.ClusterConfig()
		cluster_config.algorithm.name = CD.Algorithm.HIERARCHICAL_CLUSTERING
		cluster_config.algorithm.inconsistent_coefficient = self.best_params["train_inconsistent"]
		logger = logging.getLogger("global")
		logger.info("validating now, best parameters are:")
		logger.info(self.best_params)
		logger.info("learning with coefficient: {0}".format(self.best_params["train_inconsistent"]))
		learned_test_sites = cluster_learner.learn(learn_test, cluster_config)
		logger.info("learning complete!")
		return self.score_learned(learned_test_sites, detect_test, y_test,
				self.best_params)

def cross_validation(to_detect, to_learn, expected, noise, outfile):
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

		estimator = Estimator(filt_to_detect_sites.config, outfile)
		estimator.fit(learn_train, detect_train, y_train)
		best_params.append(estimator.best_params)
		scores.append(estimator.score(learn_test, detect_test, y_test))
		# filt_cloaking_sites = remove_noise(both_detected, noise_sites)
		# cross_val_score(svc, X_digits, y_digits, cv=kfold, n_jobs=-1)
	print "best_parameters"
	print best_params
	print scores

def main(argv):
	has_function = False
	help_msg = """cross_validation.py -f <function> [-i <inputfile> -l
		<trainfile> -e <expectedfile> -o <outfile>] cross_validation"""
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
	coefficient = 1
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
		noisefile = expectedfile + ".noise"
		cross_validation(inputfile, trainfile, expectedfile, noisefile,
				outfile)
	else:
		print help_msg
		sys.exit(2)

if __name__ == "__main__":
	main(sys.argv[1:])

