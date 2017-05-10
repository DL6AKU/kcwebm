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


Full ```--help``` output:

```
usage: kcwebm.py [-h] [-s SIZE] [-r RESIZE] [-x {8,9}] [-a] [--cfac CFAC]
                 video

positional arguments:
  video                 The video file to be converted.

optional arguments:
  -h, --help            show this help message and exit
  -s SIZE, --size SIZE  Target size of the new video in MB (approximate).
  -r RESIZE, --resize RESIZE
                        Resize video to this height. Aspect ratio will be
                        kept.
  -x {8,9}, --vpxversion {8,9}
                        8 for VP8 (default), or 9 for VP9.
  -a, --noaudio         Disable audio completely.
  --cfac CFAC           Correction factor to account for headers, containers,
                        jitter. Default is 0.05. Increase if videos get too
                        large.
```
