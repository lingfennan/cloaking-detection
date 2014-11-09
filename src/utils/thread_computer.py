import Queue
import threading
import time
import utils.proto.cloaking_detection_pb2 as CD

class _ThreadWorker(threading.Thread):
	"""
	Thread-safe. With queue and exit_checker
	@parameter
	ID: Identifier for current thread
	name: name for current thread
	q: queue has the list that threads need to fetch and iterate parameter from.
	lock: lock for the q
	exit_checker: signal all the threads to exit
	runnable_object: the object to run
	function: the member function to the runnable_object to call
	default_paras: the parameters for function, first parameter is element in q, default paras are after that.
	"""
	def __init__(self, ID, name, q, lock, exit_checker, runnable_object, function, para_type, default_paras=None):
		threading.Thread.__init__(self)
		self.ID = ID
		self.name = name
		self.q = q
		self.lock = lock
		self.exit_checker = exit_checker
		self.runnable_object = runnable_object
		self.function = function
		self.para_type = para_type
		self.default_paras = default_paras
		self.result = list()
	def run(self):
		while not self.exit_checker.exit_flag:
			self.lock.acquire()
			if not self.q.empty():
				item = self.q.get()
				self.lock.release()
				if self.para_type == CD.FILE_PATH:
					data = open(item, 'r').read()
				elif self.para_type == CD.NORMAL:
					data = item
				if self.default_paras:
					res = getattr(self.runnable_object, self.function)(data, *self.default_paras)
				else:
					res = getattr(self.runnable_object, self.function)(data)
				print "%s processing %s" % (self.name, item)
				self.result.append([item, res])
			else:
				self.lock.release()
			time.sleep(1)

class ThreadComputer(object):
	"""
	Thead-safe computer. Performs [runnable_object.function(open(para, 'r').read()) for para in para_list].
	or [runnable_object.function(para) for para in para_list]
	@parameter
	runnable_object: should have member function 'maximum_threads', 'para_type', and function.
	function: should accept open(element, 'r').read() or element in para_list as input.
	para_list: element should be accepted by function.

	@return
	self.result
	"""
	def __init__(self, runnable_object, function, para_list, default_paras=None):
		self.runnable_object = runnable_object
		self.maximum_threads = runnable_object.maximum_threads()
		self.para_type = runnable_object.para_type()
		self.function = function
		self.para_list = para_list
		self.default_paras = default_paras
		self.exit_flag = 0

		self.lock = threading.Lock()
		self.q = Queue.Queue()
		self.create_threads()
		self.compute()

	def create_threads(self):
		threads = []
		name_list = ["Thread-{0}".format(i) for i in xrange(self.maximum_threads)]
		print "created {0} threads".format(len(name_list))
		ID = 0
		for name in name_list:
			thread = _ThreadWorker(ID, name, self.q, self.lock, self, self.runnable_object, self.function, self.para_type, self.default_paras)
			thread.start()
			threads.append(thread)
			ID += 1
		self.threads = threads

	def compute(self):
		self.lock.acquire()
		for para in self.para_list:
			self.q.put(para)
		self.lock.release()
		while not self.q.empty():
			pass
		self.exit_flag = 1
		self.result = []
		for thread in self.threads:
			thread.join()
			self.result.extend(thread.result)

if __name__ == "__main__":
	class x:
		def __init__(self, para_type):
			self.para_type = para_type
		def maximum_threads(self):
			return 6
		def para_type(self):
			return self.para_type
		def show_name(self, name):
			return "here"
	# para_list = ["One", "Two", "Three", "Four", "Five", "Six", "Seven", "Nine", "Ten", "Eleven", "Tweleve", "Thirteen", "Fourteen", "Fifteen"]
	para_list = ["data/US_list_10.20141010-180519.selenium.crawl/91532f0a84878d909e2deed33e9932cf/b99a36376c27dd1cd63c8ebc39736c9f/index.html", "data/US_list_10.20141010-180519.selenium.crawl/91532f0a84878d909e2deed33e9932cf/8593de79497c2d4367165602733b7db3/index.html", "data/US_list_10.20141010-180519.selenium.crawl/91532f0a84878d909e2deed33e9932cf/bc28edc7b8cfabdd6f9a15817060c2c4/index.html", "data/US_list_10.20141010-180519.selenium.crawl/91532f0a84878d909e2deed33e9932cf/ba000d713046d86ccc31db44968baeb2/index.html", "data/US_list_10.20141010-180519.selenium.crawl/91532f0a84878d909e2deed33e9932cf/02b6345901e1142aca2d31f1f295d646/index.html", "data/US_list_10.20141010-180519.selenium.crawl/91532f0a84878d909e2deed33e9932cf/d1627f8b9ed63e02b7e94e1a03a023d8/index.html", "data/US_list_10.20141010-180519.selenium.crawl/91532f0a84878d909e2deed33e9932cf/0a2b977d58d498290042dc2da6709afb/index.html", "data/US_list_10.20141010-180519.selenium.crawl/91532f0a84878d909e2deed33e9932cf/704454d927cdcff3de6271757e63a3c9/index.html"]
	print len(para_list), "len_pata_list"
	computer = ThreadComputer(x(CD.FILE_PATH), 'show_name', para_list)
	print computer.result

	computer = ThreadComputer(x(CD.NORMAL), 'show_name', para_list)
	print computer.result
