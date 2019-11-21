#!/usr/bin/env python3
"""A script to automate the upload of videos to YouTube.

The script depends on ffmpeg to combine multiple videos, if required.

"""
import os
import re
import subprocess
from urllib.parse import unquote

INPUT_TXT = "input.txt"
OUTPUT_FILE = "output.mkv"

IGNORE_EXTENSIONS = {".txt", ".jpg"}


def _video_number(filename):
    numbers = re.findall(r"\d+", unquote(filename).rsplit(".")[0])
    num = int(numbers[-1])
    return num


def generate_concatenated_video(video_dir):
    """Generate a concatenated video from all videos in a directory.

    *NOTE*: The function assumes that all the videos are in the same format. If
     the videos are not in the same format, this function cannot be used.

    """
    if os.path.exists(os.path.join(video_dir, OUTPUT_FILE)):
        print('Output video file "{}" already exists!'.format(OUTPUT_FILE))
        return
    videos = [
        name
        for name in os.listdir(video_dir)
        if not name.lower().endswith(".txt")
    ]
    if len(videos) == 1:
        video = videos[0]
        print('Renaming single video "{}" to "{}"'.format(video, OUTPUT_FILE))
        os.rename(
            os.path.join(video_dir, video),
            os.path.join(video_dir, OUTPUT_FILE),
        )
        return
    formats = {v.rsplit(".")[-1] for v in videos}
    assert len(formats) == 1, "All videos must be in the same format!"

    # Create INPUT_TXT file for ffmpeg to combine files
    with open(os.path.join(video_dir, "input.txt"), "w") as f:
        for name in sorted(videos, key=_video_number):
            if name.endswith(".txt"):
                continue
            print("file '{}'".format(name), file=f)

    command_fmt = "ffmpeg -f concat -safe 0 -i {filelist} -c copy {output}"
    command = command_fmt.format(
        filelist=INPUT_TXT, output=OUTPUT_FILE
    ).split()
    subprocess.check_call(command, cwd=video_dir)


def main(video_dir):
    generate_concatenated_video(video_dir)


if __name__ == "__main__":
    import sys

    video_dir = sys.argv[1]
    main(video_dir)
