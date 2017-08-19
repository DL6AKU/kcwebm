#!/usr/bin/env python3

"""
Copyright (c) 2017 Bernd Lauert

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import argparse
import multiprocessing
import os
import sys
import subprocess
import shlex

FFMPEG_COMMANDS = {
    "get_duration": 'ffprobe -v quiet -of csv=p=0 -show_entries format=duration',
    "ffmpeg_cmd":          'ffmpeg -y -i @INVID@ -map 0:0 -map 0:1 @@SCALE@@ @CODEC@ @@RATE@@ -threads @CPUS@ @AUDIO@ -f webm @OUTVID@'
}

FFMPEG_OPTIONS = {
    "scale": "-filter:v scale=-1:@SCALE@",
    "rate_size": "-b:v @RATE@",
    "rate_maxsize": "",
    "codec_vp9": "-c:v libvpx-vp9 -cpu-used 8 @PASS@",
    "codec_vp8": "-c:v libvpx -cpu-used 16 @PASS@",
    "rate_bitrate": "-b:v @RATE@",
    "pass_vorbis": "-c:a libvorbis -b:a 64k -ac 2",
    "pass_opus": "-c:a libopus -b:a 64k -ac 2",
    "pass_noaudio": "-an",
}


def calc_rate(args, video):
    cmd = FFMPEG_COMMANDS["get_duration"]
    cmd += " {}".format(video)
    r = subprocess.run(cmd, stdout=subprocess.PIPE, shell=True)
    if r.returncode != 0:
        raise RuntimeError("Unable to get stream duration. Return code != 0")
    r = r.stdout.decode(sys.getdefaultencoding())
    length = float(r)
    if not length > 0:
        raise RuntimeError("Invalid length.")

    available_bits = args.size * 1024 * 1024 * 8

    # Correct for headers, container and jitter (5%)
    if args.cfac > 0.30 or args.cfac < 0.01:
        raise AttributeError("Valid --cfac values range from 0.01 to 0.30")
    available_bits -= available_bits * args.cfac

    audio_bits = 64 * 1024 * length
    if args.noaudio:
        video_bits = available_bits
    else:
        video_bits = available_bits - audio_bits
    video_bitrate = video_bits / length

    return int(video_bitrate / 1024)


def encode(cmd):
    r = subprocess.run(cmd, stdout=subprocess.PIPE, shell=True)
    if r.returncode != 0:
        raise RuntimeError("Unable to encode the video")


def get_encode_cmds(args):
    cmds = []
    if args.size:
        if not args.onepass:
            cmds.append(get_encode_cmd(args, 1))
            cmds.append(get_encode_cmd(args, 2))
            return cmds
    cmds.append(get_encode_cmd(args))
    return cmds


def get_input_file(args):
    return os.path.abspath(args.video).replace(" ", "\\ ")


def get_output_file(args):
    return os.path.splitext(get_input_file(args))[0] + ".webm"


def get_output_dir(args):
    return os.path.dirname(os.path.abspath(get_input_file(args)))


def get_encode_cmd(args, encode_pass=0):
    cmd = FFMPEG_COMMANDS["ffmpeg_cmd"]

    input_file = get_input_file(args)
    output_file = get_output_file(args)

    if args.vpxversion == 8:
        cmd = cmd.replace("@CODEC@", FFMPEG_OPTIONS["codec_vp8"])
    else:
        cmd = cmd.replace("@CODEC@", FFMPEG_OPTIONS["codec_vp9"])

    cmd = cmd.replace("@CPUS@", "{!s}".format(multiprocessing.cpu_count()))

    if args.resize:
        cmd = cmd.replace("@@SCALE@@", FFMPEG_OPTIONS["scale"])
        cmd = cmd.replace("@SCALE@", str(args.resize))
    else:
        cmd = cmd.replace("@@SCALE@@", "")

    if args.size:
        cmd = cmd.replace("@@RATE@@", FFMPEG_OPTIONS["rate_size"])
        cmd = cmd.replace("@RATE@", "{!s}k".format(calc_rate(args, input_file)))
    elif args.bitrate:
        cmd = cmd.replace("@@RATE@@", FFMPEG_OPTIONS["rate_bitrate"])
        cmd = cmd.replace("@RATE@", "{!s}k".format(args.bitrate))
    else:
        cmd = cmd.replace("@@RATE@@", "")

    if args.noaudio or encode_pass == 1:
        cmd = cmd.replace("@AUDIO@", FFMPEG_OPTIONS["pass_noaudio"])
    else:
        if args.vpxversion == 8:
            cmd = cmd.replace("@AUDIO@", FFMPEG_OPTIONS["pass_vorbis"])
        else:
            cmd = cmd.replace("@AUDIO@", FFMPEG_OPTIONS["pass_opus"])

    if encode_pass == 0:
        cmd = cmd.replace("@PASS@", "")
    elif encode_pass == 1:
        cmd = cmd.replace("@PASS@", "-pass 1")
        output_file = "/dev/null"
    else:
        cmd = cmd.replace("@PASS@", "-pass 2")

    cmd = cmd.replace("@INVID@", '{:s}'.format(input_file))
    cmd = cmd.replace("@OUTVID@", '{:s}'.format(output_file))

    return cmd


def main():
    parser = argparse.ArgumentParser()

    parser_group_size = parser.add_mutually_exclusive_group()
    parser_group_size.add_argument("-s", "--size", type=int, help="Target size of the new video in MB (approximate).")
    #parser_group_size.add_argument("-m", "--maxsize", type=int, help="Target size of the new video in MB (hard limit, 2 passes)")
    parser_group_size.add_argument("-b", "--bitrate", type=int, help="Target bitrate in k of the video (approximate). This implies --onepass.")
    #parser_group_size.add_argument("-c", "--crf", type=int, help="Target CRF of the video. 10 is default.")

    parser.add_argument("-r", "--resize", type=int, help="Resize video to this height. Aspect ratio will be kept.")
    parser.add_argument("-x", "--vpxversion", type=int, default="8", choices=[8, 9], help="8 for VP8 (default), or 9 for VP9.")
    parser.add_argument("-a", "--noaudio", action="store_true", help="Disable audio completely.")
    parser.add_argument("-1", "--onepass", action="store_true", help="Disable two-pass encoding.")
    parser.add_argument("-c", "--commandonly", action="store_true", help="Output ffmpeg commands only.")
    parser.add_argument("--cfac", type=float, default="0.05", help="Correction factor to account for headers, containers, jitter. Default is 0.05. Increase if videos get too large.")

    parser.add_argument("video", help="The video file to be converted.")

    args = parser.parse_args()

    if args.bitrate:
        args.onepass = True

    if not os.path.exists(args.video):
        print("File {} does not exist.".format(os.path.abspath(args.video)))
        sys.exit(1)

    encode_cmds = get_encode_cmds(args)
    for cmd in encode_cmds:
        if not args.commandonly:
            print("Running command: {:s}".format(cmd))
            encode(cmd)
        else:
            print(cmd)
    try:
        os.remove(get_output_dir(args) + "/ffmpeg2pass-0.log")
    except FileNotFoundError:
        pass

    sys.exit(0)


if __name__ == "__main__":
    main()
