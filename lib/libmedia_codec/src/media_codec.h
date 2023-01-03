#ifndef __RM_MEDIA_CODEC_H__
#define __RM_MEDIA_CODEC_H__


extern "C" {
#include <libavcodec/avcodec.h>
#include <libavutil/avutil.h>
#include <libavutil/mem.h>
#include <libswscale/swscale.h>
}

#include <errno.h>
#include <stdio.h>
#include <stdexcept>
#include <string>
#include <cstdlib>
#include <utility>
#include <opus/opus.h>
#include <pybind11/pybind11.h>

#ifndef PIX_FMT_BGR24
#define PIX_FMT_BGR24 AV_PIX_FMT_BGR24
#endif

#ifndef PIX_FMT_RGB24
#define PIX_FMT_RGB24 AV_PIX_FMT_RGB24
#endif

#ifndef CODEC_CAP_TRUNCATED
#define CODEC_CAP_TRUNCATED AV_CODEC_CAP_TRUNCATED
#endif

#ifndef CODEC_FLAG_TRUNCATED
#define CODEC_FLAG_TRUNCATED AV_CODEC_FLAG_TRUNCATED
#endif

#if (LIBAVCODEC_VERSION_MAJOR <= 54)
#  define av_frame_alloc avcodec_alloc_frame
#  define av_frame_free  avcodec_free_frame
#endif

using ubyte = unsigned char;
namespace py = pybind11;


class CodecException : public std::runtime_error {
public:
    CodecException(const char* s) : std::runtime_error(s) {}
};

class H264Decoder {
private:
    AVCodecContext        *context;
    AVFrame               *frame;
    AVCodec               *codec;
    AVCodecParserContext  *parser;
    AVPacket              *pkt;

public:
    H264Decoder() {
        avcodec_register_all();

        codec = avcodec_find_decoder(AV_CODEC_ID_H264);
        if (!codec)
            throw CodecException("H264Decoder: avcodec_find_decoder failed!");

        context = avcodec_alloc_context3(codec);
        if (!context)
            throw CodecException("H264Decoder: avcodec_alloc_context3 failed!");

        if(codec->capabilities & CODEC_CAP_TRUNCATED) {
            context->flags |= CODEC_FLAG_TRUNCATED;
        }

        int err = avcodec_open2(context, codec, nullptr);
        if (err < 0)
            throw CodecException("H264Decoder: avcodec_open2 failed!");

        parser = av_parser_init(AV_CODEC_ID_H264);
        if (!parser)
            throw CodecException("H264Decoder: av_parser_init failed!");

        frame = av_frame_alloc();
        if (!frame)
            throw CodecException("H264Decoder: av_frame_alloc failed!");

        pkt = new AVPacket;
        if (!pkt)
            throw CodecException("H264Decoder: alloc AVPacket failed!");
        av_init_packet(pkt);
    }

    ~H264Decoder() {
        av_parser_close(parser);
        avcodec_close(context);
        av_free(context);
        av_frame_free(&frame);
        delete pkt;
    }

    ssize_t parse(const unsigned char* in_data, ssize_t in_size) {
        auto nread = av_parser_parse2(parser, context, &pkt->data, &pkt->size,
                                      in_data, in_size,
                                      0, 0, AV_NOPTS_VALUE);
        return nread;
    }

    bool is_frame_available() const {
        return pkt->size > 0;
    }

    const AVFrame& decode_frame() {
        int got_picture = 0;
        int nread = avcodec_decode_video2(context, frame, &got_picture, pkt);
        if (nread < 0 || got_picture == 0)
            throw CodecException("H264Decoder: decode_frame, avcodec_decode_video2 failed!");
        return *frame;
    }
};


class FormatConverter {
private:
    SwsContext *context_;
    AVFrame *output_frame_;
    AVPixelFormat output_format_;

public:
    FormatConverter(enum AVPixelFormat output_format) {
        output_format_ = output_format;
        output_frame_ = av_frame_alloc();
        if (!output_frame_)
            throw CodecException("FormatConverter: av_frame_alloc failed!");
        context_ = nullptr;
    }

    ~FormatConverter() {
        sws_freeContext(context_);
        av_frame_free(&output_frame_);
    }

    int predict_size(int w, int h) {
        return avpicture_fill((AVPicture*)output_frame_, nullptr, output_format_, w, h);
    }

    const AVFrame& convert(const AVFrame &frame, unsigned char* out_bgr) {
        int w = frame.width;
        int h = frame.height;
        int pix_fmt = frame.format;
        context_ = sws_getCachedContext(context_,
                                        w, h, (AVPixelFormat)pix_fmt,
                                        w, h, output_format_, SWS_BILINEAR,
                                        nullptr, nullptr, nullptr);
        if (!context_)
            throw CodecException("FormatConverter: convert, sws_getCachedContext failed!");

        avpicture_fill((AVPicture*)output_frame_, out_bgr, output_format_, w, h);

        sws_scale(context_, frame.data, frame.linesize, 0, h,
                  output_frame_->data, output_frame_->linesize);
        output_frame_->width = w;
        output_frame_->height = h;
        return *output_frame_;
    }
};

void disable_logging() {
    av_log_set_level(AV_LOG_QUIET);
}

std::pair<int, int> width_height(const AVFrame& f) {
    return std::make_pair(f.width, f.height);
}

int row_size(const AVFrame& f) {
    return f.linesize[0];
}


class PyH264Decoder {
public:
    std::unique_ptr<H264Decoder> decoder;
    std::unique_ptr<FormatConverter> converter;

    py::tuple decode_frame_impl(const ubyte *data_in, ssize_t len, ssize_t &num_consumed, bool &is_frame_available) {
        py::gil_scoped_release decode_release;
        num_consumed = decoder->parse((ubyte*)data_in, len);

        if (is_frame_available = decoder->is_frame_available()) {
            const auto &frame = decoder->decode_frame();
            int w, h; std::tie(w,h) = width_height(frame);
            Py_ssize_t out_size = converter->predict_size(w,h);

            py::gil_scoped_acquire decode_acquire;
            py::object py_out_str = py::reinterpret_steal<py::object>(PYBIND11_BYTES_FROM_STRING_AND_SIZE(NULL, out_size));
            char* out_buffer = PYBIND11_BYTES_AS_STRING(py_out_str.ptr());

            py::gil_scoped_release convert_release;
            const auto &out_frame = converter->convert(frame, (ubyte*)out_buffer);

            py::gil_scoped_acquire convert_acquire;
            return py::make_tuple(py_out_str, w, h, row_size(out_frame));
        }
        else {
            py::gil_scoped_acquire decode_acquire;
            return py::make_tuple(py::none(), 0, 0, 0);
        }
    }

public:
    PyH264Decoder(std::string output_format, bool verbose) {
        decoder = std::unique_ptr<H264Decoder>(new H264Decoder());
        if (output_format == "RGB") {
            converter = std::unique_ptr<FormatConverter>(new FormatConverter(PIX_FMT_RGB24));
        }
        else if (output_format == "BGR") {
            converter = std::unique_ptr<FormatConverter>(new FormatConverter(PIX_FMT_BGR24));
        }
        else {
            converter = std::unique_ptr<FormatConverter>(new FormatConverter(PIX_FMT_BGR24));
        }
        if (verbose) {
            disable_logging();
        }
    }

    ~PyH264Decoder() = default;

    py::list decode(const py::str &input) {
        ssize_t len = PYBIND11_BYTES_SIZE(input.ptr());
        const ubyte* data_in = (const ubyte*)(PYBIND11_BYTES_AS_STRING(input.ptr()));

        py::list out;

        try {
            while (len > 0) {
                ssize_t num_consumed = 0;
                bool is_frame_available = false;

                try {
                    auto frame = decode_frame_impl(data_in, len, num_consumed, is_frame_available);
                    if (is_frame_available)
                        out.append(frame);
                }
                catch (const CodecException &e) {
                    if (num_consumed <= 0) throw e;
                }
                len -= num_consumed;
                data_in += num_consumed;
            }
        }
        catch (const CodecException &e) {}
        return out;
    }
};


class PyOpusDecoder {
public:
    PyOpusDecoder(int frame_size, int sample_rate, int channels):
            FRAME_SIZE(frame_size),SAMPLE_RATE(sample_rate),CHANNELS(channels) {
        int err;
        decoder_ = opus_decoder_create(SAMPLE_RATE, CHANNELS, &err);
        if (err < 0) {
            throw CodecException("PyOpusDecoder: opus_decoder_create failed!");
        }
        int16_raw_ = new opus_int16[FRAME_SIZE];
    }

    ~PyOpusDecoder() {
        opus_decoder_destroy(decoder_);
        delete [] int16_raw_;
    }

    py::bytes decode(const py::str & input) {
        ssize_t len = PYBIND11_BYTES_SIZE(input.ptr());
        const unsigned char* data_in = (const unsigned char*)(PYBIND11_BYTES_AS_STRING(input.ptr()));
        try {
            py::gil_scoped_release decoder_release;
            int frame_size = opus_decode(decoder_, data_in, len, int16_raw_, FRAME_SIZE, 0);
            if (frame_size < 0) {
                return py::bytes();
            }

            py::gil_scoped_acquire decoder_acquire;
            py::object py_out_str = py::reinterpret_steal<py::object>(
                    PYBIND11_BYTES_FROM_STRING_AND_SIZE(NULL, frame_size * sizeof(opus_int16)));
            char *out_buffer = PYBIND11_BYTES_AS_STRING(py_out_str.ptr());
            py::gil_scoped_release convert_release;

            for (int i = 0; i < frame_size; ++i) {
                out_buffer[i * 2] = int16_raw_[i] & 0xFF;
                out_buffer[i * 2 + 1] = (int16_raw_[i] >> 8) & 0xFF;
            }

            py::gil_scoped_acquire convert_acquire;
            return py_out_str;
        }
        catch (const CodecException &e) {
            throw e;
        }
    }

private:
    int FRAME_SIZE = 960;
    int SAMPLE_RATE = 48000;
    int CHANNELS = 1;
    OpusDecoder *decoder_;
    opus_int16 *int16_raw_;
};

#endif