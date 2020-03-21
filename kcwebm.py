#!/usr/bin/env python3

"""
Copyright (c) 2017-2020 Bernd Lauert

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
    "ffmpeg_cmd": 'ffmpeg -y -i @INVID@ -map 0:0 -map 0:1 @@SCALEORFRAMERATE@@ @@SCALE@@ @@FRAMERATE@@ @CODEC@ @@RATE@@ -threads @CPUS@ @AUDIO@ -f webm @OUTVID@'
}

AUDIO_BITRATE_VORBIS = 32
AUDIO_BITRATE_OPUS = 32
AUDIO_CHANNELS = 1

FFMPEG_OPTIONS = {
    "scale_or_framerate": "-filter:v",
    "scale": "scale=-1:@SCALE@",
    "framerate": "-framerate @FRAMERATE@",
    "rate_size": "-b:v @RATE@ -maxrate @RATE@ -minrate @RATE@ -bufsize 500k",
    "rate_maxsize": "",
    "codec_vp9": "-c:v libvpx-vp9 -cpu-used @CPUS@ @PASS@",
    "codec_vp8": "-c:v libvpx -cpu-used @CPUS@ @PASS@",
    "rate_bitrate": "-maxrate @RATE@ -minrate @RATE@ -b:v @RATE@ -bufsize 500k",
    "pass_vorbis": "-c:a libvorbis -b:a {:d}k -ac {:d}".format(AUDIO_BITRATE_VORBIS, AUDIO_CHANNELS),
    "pass_opus": "-c:a libopus -b:a {:d}k -ac {:d}".format(AUDIO_BITRATE_OPUS, AUDIO_CHANNELS),
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
    available_bits -= available_bits * args.cfac
    
    if args.vpxversion == 8:
        audio_bits = AUDIO_BITRATE_VORBIS * 1024 * length
    else:
        audio_bits = AUDIO_BITRATE_OPUS * 1024 * length

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
    return os.path.abspath(args.video)


def get_output_file(args):
    return os.path.splitext(get_input_file(args))[0] + ".webm"


def get_output_dir(args):
    return os.path.dirname(os.path.abspath(get_input_file(args)))


def get_encode_cmd(args, encode_pass=0):
    cmd = FFMPEG_COMMANDS["ffmpeg_cmd"]

    input_file = shlex.quote(get_input_file(args))
    output_file = shlex.quote(get_output_file(args))

    if output_file == input_file:
        output_file = output_file.replace(".webm", ".kcwebm.webm")

    if args.vpxversion == 8:
        cmd = cmd.replace("@CODEC@", FFMPEG_OPTIONS["codec_vp8"])
    else:
        cmd = cmd.replace("@CODEC@", FFMPEG_OPTIONS["codec_vp9"])

    cmd = cmd.replace("@CPUS@", "{!s}".format(multiprocessing.cpu_count()))

    if args.resize or args.framerate:
        cmd = cmd.replace("@@SCALEORFRAMERATE@@", FFMPEG_OPTIONS["scale_or_framerate"])
        if args.resize:
            cmd = cmd.replace("@@SCALE@@", FFMPEG_OPTIONS["scale"])
            cmd = cmd.replace("@SCALE@", str(args.resize))
        else:
            cmd = cmd.replace("@@SCALE@@", "")
    else:
        cmd = cmd.replace("@@SCALEORFRAMERATE@@", "")
        cmd = cmd.replace("@@SCALE@@", "")

    if args.framerate:
        cmd = cmd.replace("@@FRAMERATE@@", FFMPEG_OPTIONS["framerate"])
        cmd = cmd.replace("@FRAMERATE@", str(args.framerate))
    else:
        cmd = cmd.replace("@@FRAMERATE@@", "")

    if args.size:
        cmd = cmd.replace("@@RATE@@", FFMPEG_OPTIONS["rate_size"])
        cmd = cmd.replace("@RATE@", "{!s}000".format(calc_rate(args, input_file)))
    elif args.bitrate:
        cmd = cmd.replace("@@RATE@@", FFMPEG_OPTIONS["rate_bitrate"])
        cmd = cmd.replace("@RATE@", "{!s}000".format(args.bitrate))
    else:
        cmd = cmd.replace("@@RATE@@", "")

    if args.noaudio or encode_pass == 1:
        cmd = cmd.replace("@AUDIO@", FFMPEG_OPTIONS["pass_noaudio"])
        cmd = cmd.replace("-map 0:0", "")
        cmd = cmd.replace("-map 0:1", "")
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
    parser_group_size.add_argument("-s", "--size", type=float, help="Target size of the new video in MB (approximate).")
    #parser_group_size.add_argument("-m", "--maxsize", type=int, help="Target size of the new video in MB (hard limit, 2 passes)")
    parser_group_size.add_argument("-b", "--bitrate", type=int, help="Target bitrate in k of the video (approximate). This implies --onepass.")
    #parser_group_size.add_argument("-c", "--crf", type=int, help="Target CRF of the video. 10 is default.")

    parser.add_argument("-r", "--resize", type=int, help="Resize video to this height. Aspect ratio will be kept.")
    parser.add_argument("-x", "--vpxversion", type=int, default="8", choices=[8, 9], help="8 for VP8 (default), or 9 for VP9.")
    parser.add_argument("-a", "--noaudio", action="store_true", help="Disable audio completely.")
    parser.add_argument("-1", "--onepass", action="store_true", help="Disable two-pass encoding.")
    parser.add_argument("-c", "--commandonly", action="store_true", help="Output ffmpeg commands only.")
    parser.add_argument("-f", "--framerate", type=int, help="Specify framerate.")
    parser.add_argument("--cfac", type=float, default="0.05", help="Correction factor to account for headers, containers, jitter. Must be between 0 and 0.3. Default is 0.05. Increase if videos get too large.")

    parser.add_argument("video", help="The video file to be converted.")

    args = parser.parse_args()

    # Check Arguments for sanity:
    ## If bitrate mode is set, we only do one pass
    if args.bitrate:
        args.onepass = True
    ## Make sure cfac is a sane value
    assert 0 <= args.cfac <= 0.3

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
