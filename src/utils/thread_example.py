#!/usr/bin/python

import Queue
import threading
import time

exitFlag = 0

class myThread (threading.Thread):
    def __init__(self, threadID, name, q, lock):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.q = q
	self.lock = lock
    def run(self, ):
        print "Starting " + self.name
        process_data(self.name, self.q, self.lock)
        print "Exiting " + self.name

def process_data(threadName, q, lock):
    while not exitFlag:
	queueLock.acquire()
        if not q.empty():
            data = q.get()
	    queueLock.release()
            print "%s processing %s" % (threadName, data)
        else:
	    None
	    queueLock.release()
        time.sleep(1)

threadList = ["Thread-1", "Thread-2", "Thread-3", "Thread-4", "Thread-5", "Thread-6"]
nameList = ["One", "Two", "Three", "Four", "Five", "Six", "Seven", "Nine", "Ten", "Eleven", "Tweleve", "Thirteen", "Fourteen", "Fifteen"]
queueLock = threading.Lock()
workQueue = Queue.Queue()
threads = []
threadID = 1

# Create new threads
for tName in threadList:
    thread = myThread(threadID, tName, workQueue, queueLock)
    thread.start()
    threads.append(thread)
    threadID += 1

# Fill the queue
queueLock.acquire()
for word in nameList:
    workQueue.put(word)
queueLock.release()

# Wait for queue to empty
while not workQueue.empty():
    pass

# Notify threads it's time to exit
exitFlag = 1

# Wait for all threads to complete
for t in threads:
    t.join()
print "Exiting Main Thread"
