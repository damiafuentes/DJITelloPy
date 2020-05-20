from .tello import Tello
from threading import Thread, Barrier
from queue import Queue


class TelloSwarm:
	@staticmethod
	def fromFile(path: str):
		with open(path, "r") as fd:
			ips = fd.readlines()

		return TelloSwarm.fromIps(ips)

	@staticmethod
	def fromIps(ips: list):
		if len(ips) == 0:
			raise Exception("No ips provided")

		tellos = []
		for ip in ips:
			tellos.append(Tello(ip.strip()))

		return TelloSwarm(tellos)

	def __init__(self, tellos: list):
		self.tellos = tellos
		self.barrier = Barrier(len(tellos))
		self.funcBarrier = Barrier(len(tellos) + 1)
		self.funcQueues = [Queue() for tello in tellos]

		def worker(i):
			queue = self.funcQueues[i]
			tello = self.tellos[i]

			while True:
				func = queue.get()
				self.funcBarrier.wait()
				func(i, tello)
				self.funcBarrier.wait()

		self.threads = []
		for i, tello in enumerate(tellos):
			thread = Thread(target=worker, daemon=True, args=(i,))
			thread.start()
			self.threads.append(thread)

	def sequential(self, func):
		for i, tello in enumerate(self.tellos):
			func(i, tello)

	def parallel(self, func):
		for queue in self.funcQueues:
			queue.put(func)
		
		self.funcBarrier.wait()
		self.funcBarrier.wait()

	def sync(self, timeout=None):
		return self.barrier.wait(timeout)

	def __getattr__(self, attr):
		def callAll(*args, **kwargs):
			self.parallel(lambda i, tello: getattr(tello, attr)(*args, **kwargs))

		return callAll

	def __iter__(self):
		return iter(self.tellos)

	def __len__(self):
		return len(self.tellos)
