from .tello import Tello
from threading import Thread, Barrier
from queue import Queue
from typing import List


class TelloSwarm:
	"""Swarm library for controlling multiple Tellos simultaneously
	"""

	funcQueues: List[Queue]

	@staticmethod
	def fromFile(path: str):
		"""Create TelloSwarm from file. The file should contain one IP address per line.

		Arguments:
			path: path to the file
		"""
		with open(path, "r") as fd:
			ips = fd.readlines()

		return TelloSwarm.fromIps(ips)

	@staticmethod
	def fromIps(ips: list):
		"""Create TelloSwarm from a list of IP addresses.

		Arguments:
			ips: list of IP Addresses
		"""
		if len(ips) == 0:
			raise Exception("No ips provided")

		tellos = []
		for ip in ips:
			tellos.append(Tello(ip.strip()))

		return TelloSwarm(tellos)

	def __init__(self, tellos: list):
		"""Initialize a TelloSwarm instance

		Arguments:
			tellos: list of [Tello][tello] instances
		"""
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
		"""Call `func` for each tello sequentially. The function retrieves
		two arguments: The index `i` of the current drone and `tello` the
		current [Tello][tello] instance.

		```python
		swarm.parallel(lambda i, tello: tello.land())
		```
		"""

		for i, tello in enumerate(self.tellos):
			func(i, tello)

	def parallel(self, func):
		"""Call `func` for each tello in parallel. The function retrieves
		two arguments: The index `i` of the current drone and `tello` the
		current [Tello][tello] instance.

		You can use `swarm.sync()` for syncing between threads.

		```python
		swarm.parallel(lambda i, tello: tello.move_up(50 + i * 10))
		```
		"""

		for queue in self.funcQueues:
			queue.put(func)
		
		self.funcBarrier.wait()
		self.funcBarrier.wait()

	def sync(self, timeout: float = None):
		"""Sync parallel tello threads. The code continues when all threads
		have called `swarm.sync`.

		```python
		def doStuff(i, tello):
			tello.move_up(50 + i * 10)
			swarm.sync()

			if i == 2:
				tello.flip_back()
			# make all other drones wait for one to complete its flip
			swarm.sync()

		swarm.parallel(doStuff)
		```
		"""
		return self.barrier.wait(timeout)

	def __getattr__(self, attr):
		"""Call a standard tello function in parallel on all tellos.

		```python
		swarm.command()
		swarm.takeoff()
		swarm.move_up(50)
		```
		"""
		def callAll(*args, **kwargs):
			self.parallel(lambda i, tello: getattr(tello, attr)(*args, **kwargs))

		return callAll

	def __iter__(self):
		"""Iterate over all drones in the swarm.

		```python
		for tello in swarm:
			print(tello.get_battery())
		```
		"""
		return iter(self.tellos)

	def __len__(self):
		"""Return the amount of tellos in the swarm

		```python
		print("Tello count: ", len(swarm))
		```
		"""
		return len(self.tellos)
