import queue
import socket
import threading

class VideoConnection(object):

   def __init__(self):
       self._sock = None
       self._sock_queue = queue.Queue(32)
       self._sock_recv = None
       self._recv_count = 0
       self._receiving = False

   def __del__(self):
       if self._sock:
           self._sock.close()

   def connect(self, camera_ip: str="0.0.0.0", camera_port: int=11111):
       try:
           self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
           self._sock.bind((camera_ip, camera_port))
           print("OVER")
       except Exception as e:
           print("StreamConnection: connect addr {0}:{1}, exception {2}".format(camera_ip, camera_port, e))
           return False
       self._sock_recv = threading.Thread(target=self._recv_task)
       self._sock_recv.start()
       print("StreamConnection {0} successfully!".format(camera_ip))
       return True

   def disconnect(self):
       self._receiving = False
       self._sock_queue.put(None)
       if self._sock_recv:
           self._sock_recv.join()
       self._sock.close()
       self._sock_queue.queue.clear()
       self._recv_count = 0
       print("StreamConnection: disconnected")

   def _recv_task(self):
       self._receiving = True
       print("StreamConnection: _recv_task, Start to receiving Data...")
       while self._receiving:
           try:
               if self._sock is None:
                   break
               data, addr = self._sock.recvfrom(4096)
               if not self._receiving:
                   break
               self._recv_count += 1
               if self._sock_queue.full():
                   print("StreamConnection: _recv_task, sock_data_queue is full.")
                   self._sock_queue.get()
               else:
                   self._sock_queue.put(data)
           except socket.timeout:
               print("StreamConnection: _recv_task， recv data timeout!")
               continue
           except Exception as e:
               print("StreamConnection: recv, exceptions:{0}".format(e))
               self._receiving = False
               return

   def read_buf(self, timeout=2):
       try:
           buf = self._sock_queue.get(timeout=timeout)
           return buf
       except Exception as e:
           print("StreamConnection: read_buf, exception {0}".format(e))
           return None