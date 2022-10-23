#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import functools
import logging
import os
import subprocess
from multiprocessing import Pool
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from typing import List

import ffmpeg
from pydub import AudioSegment, silence


def time_format(ms):
    msec = ms % 1000
    sec = ms // 1000
    minutes = sec // 60
    sec %= 60
    hours = minutes // 60
    minutes %= 60
    return "%02d:%02d:%02d.%03d" % (hours, minutes, sec, msec)


BASENAME = "lecture"
FFMPEG_CMD = ["ffmpeg", "-hide_banner", "-loglevel", "error"]


def get_length(filename: str) -> float:
    result = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                             "format=duration", "-of",
                             "default=noprint_wrappers=1:nokey=1", filename],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT)
    return float(result.stdout)


def split_video(infile: str, output_dir: str, prefix: str, n_parts: int) -> List[str]:
    duration = round(get_length(infile) * 1000)
    split_args = FFMPEG_CMD + ["-i", infile]
    segments = []
    for i in range(n_parts):
        filename = os.path.join(output_dir, f"{prefix}_{i}{Path(infile).suffix}")
        split_args += [
            "-ss", time_format(round(duration * i) / n_parts),
            "-to", time_format(round(duration * (i + 1) / n_parts)),
            "-c", "copy",
            filename
        ]
        segments.append(filename)
    logging.info(f"Splitting {infile} into {n_parts} segments")
    subprocess.check_output(split_args)
    logging.info(f"Done splitting {infile}")
    logging.info(segments)
    return segments


def concatenate_videos(temp_dir, chunks: List[str], outfile: str):
    with NamedTemporaryFile("w", suffix='.txt', dir=temp_dir) as list_file:
        for file in chunks:
            print(f"file '{file}'", file=list_file)
        list_file.flush()
        logging.info(f'{len(chunks)} chunks written to {list_file.name}')

        logging.info(f'Concatenating chunks into {outfile}')

        concat_args = FFMPEG_CMD + [
            "-safe", "0",
            "-f", "concat",
            "-i", str(list_file.name),
            "-c", "copy",
            outfile
        ]
        subprocess.check_output(concat_args)


def trim_silence(infile: str, outfile: str, min_silence_len: int, silence_thresh: int, margin: int) -> bool:
    """
    Returns
    -------
    True trimming was successful and resulted in nonempty outfile
    """
    infile_video = infile
    infile_audio = str(Path(infile_video).with_suffix('.mp3'))

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

    if not parts:
        return False

    logging.info("Trimming audio")
    segments = AudioSegment._sync(*[audio[start:stop] for start, stop in parts])
    trimmed_audio = segments[0]._spawn([segment._data for segment in segments])
    logging.info("Done trimming audio")

    logging.info(f"Writing trimmed audio into {infile_audio} with duration {trimmed_audio.duration_seconds} s.")
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
    return True


def process_chunk(workdir: str, args: argparse.Namespace, total_segments: int, id_: int, segment: str):
    outfile = os.path.join(workdir, BASENAME + f"_cropped_{id_}" + Path(args.infile).suffix)
    logging.info(f"Processing chunk {id_ + 1}/{total_segments}: {segment} -> {outfile}")
    if not trim_silence(segment,
                        outfile,
                        args.min_silence_len,
                        args.silence_thresh,
                        args.margin):
        outfile = None
    logging.info(f"Done processing chunk {id_ + 1}/{total_segments}")
    return outfile


def main():
    parser = argparse.ArgumentParser(description='Trim silence from video.')
    parser.add_argument('-i', '-input', dest='infile', help='input file', required=True)
    parser.add_argument('-o', '-output', dest='outfile', help='output file', default="cropped.mp4")
    parser.add_argument('-s', dest='min_silence_len', type=int,
                        help='min_silence_len (ms)', default=300)
    parser.add_argument('-t', dest='silence_thresh', type=int,
                        help='silence threshold', default=-16)
    parser.add_argument('-m', dest='margin', type=int,
                        help='margin (ms)', default=100)
    parser.add_argument('-n', dest='n_segments', type=int,
                        help='number of chunks to split input file to be processed independently', default=10)
    parser.add_argument('-p', dest='pool_size', type=int,
                        help='number of chunks to be processed concurrently', default=1)
    parser.add_argument('-T', dest='temp_dir',
                        help='directory for temporary files')
    parser.add_argument('-d', dest='log_level', action='store_const', const=logging.DEBUG, help='print debugging info',
                        default=logging.WARNING)
    args = parser.parse_args()

    logging.basicConfig(format="%(asctime)s - %(message)s", level=args.log_level)

    with TemporaryDirectory(dir=args.temp_dir) as workdir:
        segments = split_video(args.infile, workdir, BASENAME, args.n_segments)
        cropped_segments = []
        with Pool(processes=args.pool_size) as pool:
            cropped_segments = pool.starmap(functools.partial(process_chunk, workdir, args, len(segments)), enumerate(segments))
        cropped_segments = [segment for segment in cropped_segments if segment is not None]
        concatenate_videos(args.temp_dir, cropped_segments, args.outfile)


if __name__ == '__main__':
    main()
