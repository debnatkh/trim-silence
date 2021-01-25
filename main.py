#!/usr/bin/python
# -*- coding: utf-8 -*-
import logging
import os
import pathlib
import shutil
import tempfile
import argparse
import ffmpeg
from pydub import AudioSegment, silence


def time_format(ms):
    msec = ms % 1000
    sec = ms // 1000
    minutes = sec // 60
    sec %= 60
    hours = minutes // 60
    minutes %= 60
    return "%02d:%02d:%02d.%d" % (hours, minutes, sec, msec)


basename = "lecture"


def trim_silence(infile, outfile, min_silence_len, silence_thresh, margin):
    workdir = tempfile.mkdtemp()
    shutil.copy(os.path.join(workdir, infile), os.path.join(workdir, basename + pathlib.Path(infile).suffix))

    infile_video = os.path.join(workdir, basename + pathlib.Path(infile).suffix)
    infile_audio = os.path.join(workdir, basename + ".mp3")

    logging.info(f"Extracting audio from \"{infile_video}\" to \"{infile_audio}\"")
    ffmpeg \
        .input(infile_video) \
        .output(infile_audio) \
        .run(quiet=True)
    logging.info("Done extracting audio")

    audio = AudioSegment.from_mp3(infile_audio)

    logging.info("Detecting nonsilent parts")
    parts = silence.detect_nonsilent(audio, min_silence_len=min_silence_len,
                                     silence_thresh=audio.dBFS + silence_thresh)
    parts = [(start - margin, stop + margin) for (start, stop) in parts]
    logging.info(
        f"Detected {len(parts)} nonsilent parts, total duration: {sum((stop - start) for start, stop in parts)} ms")
    logging.info(parts)

    logging.info("Trimming audio")
    trimmed_audio = AudioSegment.empty()
    for start, stop in parts:
        trimmed_audio += audio[start:stop]
    logging.info("Done trimming audio")

    logging.info(f"Writing trimmed audio into {infile_audio} with duration {trimmed_audio.duration_seconds}")
    trimmed_audio.export(infile_audio)

    parts = [(start / 1000, stop / 1000) for (start, stop) in parts]

    in_file = ffmpeg.input(infile_video)

    joined = ffmpeg.concat(
        ffmpeg.concat(
            *[in_file.trim(start=start, end=stop).setpts('PTS-STARTPTS')
              for start, stop in parts]),
        ffmpeg.input(infile_audio),
        v=1,
        a=1).node
    ffmpeg.output(joined[0], joined[1], outfile).run(quiet=True, overwrite_output=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Trim silence from video.')
    parser.add_argument('-i', '-input', dest='infile', help='input file', required=True)
    parser.add_argument('-o', '-output', dest='outfile', help='output file', default="cropped.mp4")
    parser.add_argument('-s', dest='min_silence_len', type=int,
                        help='min_silence_len (ms)', default=300)
    parser.add_argument('-t', dest='silence_thresh', type=int,
                        help='silence threshold', default=-16)
    parser.add_argument('-m', dest='margin', type=int,
                        help='margin (ms)', default=100)

    parser.add_argument('-d', dest='log_level', action='store_const', const=logging.DEBUG, help='print debugging info',
                        default=logging.WARNING)
    args = parser.parse_args()

    logging.basicConfig(format="%(asctime)s - %(message)s", level=args.log_level)

    trim_silence(args.infile, args.outfile, args.min_silence_len, args.silence_thresh, args.margin)
