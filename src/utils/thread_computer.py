import Queue
import threading
import time

class _ThreadWorker(threading.Thread):
	"""
	Thread-safe. With queue and exit_checker
	"""
	def __init__(self, ID, name, q, lock, exit_checker, runnable_object, function):
		threading.Thread.__init__(self)
		self.ID = ID
		self.name = name
		self.q = q
		self.lock = lock
		self.exit_checker = exit_checker
		self.runnable_object = runnable_object
		self.function = function
		self.result = list()
	def run(self):
		while not self.exit_checker.exit_flag:
			self.lock.acquire()
			if not self.q.empty():
				file_path = self.q.get()
				self.lock.release()
				data = open(file_path, 'r').read()
				res = getattr(self.runnable_object, self.function)(data)
				print "%s processing %s" % (self.name, file_path)
				self.result.append([file_path, res])
			else:
				self.lock.release()
			time.sleep(1)

class ThreadComputer(object):
	"""
	Thead-safe computer. Performs [runnable_object.function(open(para, 'r').read()) for para in para_list].
	@parameter
	runnable_object: should have member function 'maximum_threads', and function.
	function: should accept open(element, 'r').read() in para_list as input.
	para_list: element should be accepted by function.

	@return
	self.result
	"""
	def __init__(self, runnable_object, function, para_list):
		self.runnable_object = runnable_object
		self.maximum_threads = runnable_object.maximum_threads()
		self.function = function
		self.para_list = para_list
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
			thread = _ThreadWorker(ID, name, self.q, self.lock, self, self.runnable_object, self.function)
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
		def maximum_threads(self):
			return 6
		def show_name(self, name):
			return "here"
	# para_list = ["One", "Two", "Three", "Four", "Five", "Six", "Seven", "Nine", "Ten", "Eleven", "Tweleve", "Thirteen", "Fourteen", "Fifteen"]
	para_list = ["data/US_list_10.20141010-180519.selenium.crawl/91532f0a84878d909e2deed33e9932cf/b99a36376c27dd1cd63c8ebc39736c9f/index.html", "data/US_list_10.20141010-180519.selenium.crawl/91532f0a84878d909e2deed33e9932cf/8593de79497c2d4367165602733b7db3/index.html", "data/US_list_10.20141010-180519.selenium.crawl/91532f0a84878d909e2deed33e9932cf/bc28edc7b8cfabdd6f9a15817060c2c4/index.html", "data/US_list_10.20141010-180519.selenium.crawl/91532f0a84878d909e2deed33e9932cf/ba000d713046d86ccc31db44968baeb2/index.html", "data/US_list_10.20141010-180519.selenium.crawl/91532f0a84878d909e2deed33e9932cf/02b6345901e1142aca2d31f1f295d646/index.html", "data/US_list_10.20141010-180519.selenium.crawl/91532f0a84878d909e2deed33e9932cf/d1627f8b9ed63e02b7e94e1a03a023d8/index.html", "data/US_list_10.20141010-180519.selenium.crawl/91532f0a84878d909e2deed33e9932cf/0a2b977d58d498290042dc2da6709afb/index.html", "data/US_list_10.20141010-180519.selenium.crawl/91532f0a84878d909e2deed33e9932cf/704454d927cdcff3de6271757e63a3c9/index.html"]
	print len(para_list), "len_pata_list"
	computer = ThreadComputer(x(), 'show_name', para_list)
	print computer.result

