# kcwebm
Quick video to webm converter. Uses FFMPEG. Originally developed for Krautchan.

Simple python script.

# Krautchan.net

```
kcwebm.py -s 10 -x9 videofile
```

will produce "good" quality webms for Krautchan

```
kcwebm.py -s 10 -x8 videofile
```

will produce "fast" webms (short encoding time).

# 4chan

```
kcwebm.py -s 3 -a -x8 videofile
```

will be fine for 4chan.

# zshrc and bashrc

You can add the function in zshrc.aliases.addon to your
zshrc (or bashrc, untested) setup and then run kcwebmdl
and it will download and convert your youtube video (the
URL has to be in your CTRL+C clipboard) to the _WEBMDIR 
directory. If you execute "kcwebmdl 480" for example 
instead, it will convert that video to 480p. This also
always uses the libvpx-vp9 (VP9) codec.

Obviously you will have to edit _WEBMDIR to a directory
to a directory that suits you.

Also youtube-dl and xsel have to be installed.

# Full help output

Full ```--help``` output:

```
usage: kcwebm.py [-h] [-s SIZE | -b BITRATE] [-r RESIZE] [-x {8,9}] [-a] [-1]
                 [-c] [--cfac CFAC]
                 video

positional arguments:
  video                 The video file to be converted.

optional arguments:
  -h, --help            show this help message and exit
  -s SIZE, --size SIZE  Target size of the new video in MB (approximate).
  -b BITRATE, --bitrate BITRATE
                        Target bitrate in k of the video (approximate). This
                        implies --onepass.
  -r RESIZE, --resize RESIZE
                        Resize video to this height. Aspect ratio will be
                        kept.
  -x {8,9}, --vpxversion {8,9}
                        8 for VP8 (default), or 9 for VP9.
  -a, --noaudio         Disable audio completely.
  -1, --onepass         Disable two-pass encoding.
  -c, --commandonly     Output ffmpeg commands only.
  --cfac CFAC           Correction factor to account for headers, containers,
                        jitter. Must be between 0 and 0.3. Default is 0.05.
                        Increase if videos get too large.
```
