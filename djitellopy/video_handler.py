import queue
import threading
import libmedia_codec

import numpy as np

from djitellopy.video_connection import VideoConnection

class VideoHandler(object):

    def __init__(self, camera_ip: str="0.0.0.0", camera_port: int=11111):

        # Init variables
        self._video_frame_count = 0
        self._video_streaming = False

        # Create the video queue
        self._video_frame_queue = queue.Queue(64)

        # Create the video decoder
        self._video_decoder = libmedia_codec.H264Decoder()

        # Turn on the video converter
        self._video_stream_conn = VideoConnection()
        self._video_stream_conn.connect(camera_ip, camera_port)
        self._video_decoder_thread = threading.Thread(target=self._video_decoder_task)
        self._video_decoder_thread.start()
        self._x = 0

    def _h264_decode(self, data):
        res_frame_list = []
        frames = self._video_decoder.decode(data)
        for frame_data in frames:
            (frame, width, height, ls) = frame_data
            if frame:
                frame = np.fromstring(frame, dtype=np.ubyte, count=len(frame), sep='')
                frame = (frame.reshape((height, width, 3)))
                res_frame_list.append(frame)
        return res_frame_list

    def _video_decoder_task(self):
        self._video_streaming = True
        print("_video_decoder_task, started!")
        while self._video_streaming:
            data = b''
            buf = self._video_stream_conn.read_buf()
            if not self._video_streaming:
                break
            if buf:
                data += buf
                frames = self._h264_decode(data)
                for frame in frames:
                    try:
                        self._video_frame_count += 1
                        if self._video_frame_count % 30 == 1:
                            print("video_decoder_task, get frame {0}.".format(self._video_frame_count))
                        self._video_frame_queue.put(frame, timeout=2)
                    except Exception as e:
                        print("_video_decoder_task, decoder queue is full, e {}.".format(e))
                        continue
        print("_video_decoder_task, quit.")

    def read_video_frame(self, timeout=3, strategy="newest"):
        if strategy == "pipeline":
            return self._video_frame_queue.get(timeout=timeout)
        elif strategy == "newest":
            while self._video_frame_queue.qsize() > 1:
                self._video_frame_queue.get(timeout=timeout)
            return self._video_frame_queue.get(timeout=timeout)
        else:
            print("read_video_frame, unsupported strategy:{0}".format(strategy))
            return None