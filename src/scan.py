"""
scan parameters must be numerical
-s=a:1-2,b:3-4,c:7-10
-p=name:haha,value:hehe
-o=outfile
-m=cloaking_detection
-f=cloaking_detection

Example usage:
	python scan.py -m cloaking_detection -f cloaking_detection -p simhash_type:TEXT,learned_sites_filename:*.text.learned,observed_sites_filename:*.text -s min_radius:0-4,std_constant:3-6 -o outfile
	e.g.
	python scan.py -m cloaking_detection -f cloaking_detection -p simhash_type:TEXT,learned_sites_filename:../data/abusive_words_9_category.computed/test.google.text.learned,observed_sites_filename:../data/abusive_words_9_category.computed/test.user.text -s min_radius:0-6,std_constant:3-6 -o ../data/abusive_words_9_category.computed/test.user.text.r0_6n3_6.log

"""




from itertools import izip
from utils.util import Progress
import sys, getopt

def _parse_para(para_str, expected_type="list"):
	"""
	return list containing key, value pairs
	"""
	res = filter(bool, para_str.split(','))
	res_list = list()
	res_dict = dict()
	for para in res:
		para = para.split(':')
		res_list.append([para[0], para[1]])
		res_dict[para[0]] = para[1]
	if expected_type == "list":
		return res_list
	elif expected_type == "dict":
		return res_dict
	else:
		print "Expected type not supported!"
		return None

def _low_bound(para_list):
	return [para[1][0] for para in para_list]

def _high_bound(para_list):
	return [para[1][1] for para in para_list]

def _name_list(para_list):
	return [para[0] for para in para_list]

def _build_para_dict(name_list, value_list):
	if not len(name_list)  == len(value_list):
		print "Dimension of para name and para value doesn't match"
		return None
	para_dict = dict()
	for name, value in izip(name_list, value_list):
		para_dict[name] = value
	return para_dict

def scan(module, function, scan_parameters, noscan_parameters):
	m = __import__(module)
	noscan_para_dict = _parse_para(noscan_parameters,"dict")
	scan_parameters = _parse_para(scan_parameters)
	scan_name_list = _name_list(scan_parameters)
	# prepare lower bound and higher bound
	for i in range(len(scan_parameters)):
		scan_parameters[i][1] = [int(value) for value in scan_parameters[i][1].split('-')]
	progress = Progress()
	low_bound = _low_bound(scan_parameters)
	high_bound = _high_bound(scan_parameters)
	current = low_bound
	while current:
		scan_para_dict = _build_para_dict(scan_name_list, current)
		print scan_para_dict
		kargs = dict(noscan_para_dict.items() + scan_para_dict.items())
		getattr(m, function)(**kargs)
		current = progress.next(low_bound, high_bound)

def main(argv):
	help_msg = "scan.py -m <module> -f <function> -p <parameters> -s <scan_parameters> -o <outfile>"
	outfile = None
	try:
		opts, args = getopt.getopt(argv, "hf:m:s:p:o:", ["function=", "module=", "scan=", "parameter=", "outfile="])
	except getopt.GetoptError:
		print help_msg
		sys.exit(2)
	for opt, arg in opts:
		if opt == "-h":
			print help_msg
			sys.exit()
		elif opt in ("-f", "--function"):
			function = arg
		elif opt in ("-m", "--module"):
			module = arg
		elif opt in ("-s", "--scan"):
			scan_parameters = arg
		elif opt in ("-p", "--parameter"):
			noscan_parameters = arg
		elif opt in ("-o", "--outfile"):
			outfile = arg
		else:
			print help_msg
			sys.exit(2)
	if outfile:
		sys.stdout = open(outfile, 'w')
	scan(module, function, scan_parameters, noscan_parameters)

if __name__ == "__main__":
	main(sys.argv[1:])


