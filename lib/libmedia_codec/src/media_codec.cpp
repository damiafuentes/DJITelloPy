#include "media_codec.h"
#include <pybind11/pybind11.h>

namespace py = pybind11;
PYBIND11_MODULE(libmedia_codec, m) {
    m.doc()="RoboMaster Media Codec library for H264 and Opus stream using pybind11";
#ifdef VERSION_INFO
    m.attr("__version__") = VERSION_INFO;
#else
    m.attr("__version__") = "dev";
#endif

    py::class_<PyOpusDecoder> ad(m, "OpusDecoder");
    ad.doc() = "Class for Opus Decoder";
    ad.def(py::init<int, int, int>(),py::arg("frame_size") = 960,
           py::arg("sample_rate") = 48000, py::arg("channels") = 1);
    ad.def("decode", &PyOpusDecoder::decode, "Opus decode function",py::arg("input"));

    py::class_<PyH264Decoder> vd(m,"H264Decoder");
    vd.doc() = "Class for H264 Decoder";
    vd.def(py::init<std::string, bool>(), py::arg("output_format") = "BGR", py::arg("verbose") = true);
    vd.def("decode", &PyH264Decoder::decode, "H264 decode function",py::arg("input"));

}
