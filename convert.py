#!/usr/bin/env python3
"""A script to automate the upload of videos to YouTube.

The script depends on ffmpeg to combine multiple videos, if required.

"""
import os
import re
import subprocess
from urllib.parse import unquote

from PIL import Image, ImageDraw, ImageFont
import yaml


INPUT_TXT = "input.txt"
OUTPUT_NAME = "output.mkv"
CONFIG_NAME = "config.yaml"
COVER_NAME = "cover.png"
HERE = os.path.dirname(os.path.abspath(__file__))
LOGO_FILE = os.path.join(HERE, "logo.jpg")
AUDIO_FILE = os.path.join(HERE, "audio.mp3")
IGNORE_EXTENSIONS = (".txt", ".jpg", ".png", ".yaml")
CODEC_MAP = {
    "h264": "libx264",
    # "hevc": "libx265"
}


def _video_number(filename):
    numbers = re.findall(r"\d+", unquote(filename).rsplit(".")[0])
    num = int(numbers[-1])
    return num


def _get_video_list(video_dir):
    videos = [
        name
        for name in os.listdir(video_dir)
        if not name.lower().endswith(IGNORE_EXTENSIONS)
    ]
    return videos


def generate_cover_image(video_dir, width, height):
    img = Image.new("RGB", (width, height), color=(255, 255, 255))

    with open(os.path.join(video_dir, CONFIG_NAME)) as f:
        config = yaml.load(f.read(), Loader=yaml.SafeLoader)

    if not {"title", "date", "venue"}.issubset(config.keys()):
        raise RuntimeError("Need title, date and venue in config")

    # Insert title, date and venue
    title_fnt = ImageFont.truetype("Ubuntu-R.ttf", 40)
    text_fnt = ImageFont.truetype("Ubuntu-R.ttf", 20)

    title, date, venue = config["title"], config["date"], config["venue"]

    t_w, t_h = title_fnt.getsize(title)
    d_w, d_h = text_fnt.getsize(date)
    v_w, v_h = text_fnt.getsize(venue)

    title_x = (width - t_w) / 2
    title_y = height / 2

    date_x = (width - d_w) / 2
    date_y = title_y + t_h + 10

    venue_y = date_y + d_h + 10
    venue_x = (width - v_w) / 2

    d = ImageDraw.Draw(img)
    d.text((title_x, title_y), title, font=title_fnt, fill=(110, 110, 110))
    d.text((date_x, date_y), date, font=text_fnt, fill=(110, 110, 110))
    d.text((venue_x, venue_y), venue, font=text_fnt, fill=(110, 110, 110))

    # Insert logo
    logo = Image.open(LOGO_FILE, "r")
    logo_w, logo_h = logo.size
    offset = ((width - logo_w - 10), (height - logo_h - 10))
    img.paste(logo, offset)

    path = os.path.join(video_dir, COVER_NAME)
    img.save(path)
    return path


def generate_annotation(video_dir):
    videos = _get_video_list(video_dir)
    command_fmt = (
        "ffprobe -v error -select_streams {stream}:0 -show_entries stream={params} "
        "-of default=noprint_wrappers=1:nokey=1 {video}"
    )
    params = "codec_name,width,height"
    command = command_fmt.format(stream="v", video=videos[0], params=params)
    video_encoding, width, height = (
        subprocess.check_output(command.split(), cwd=video_dir)
        .strip()
        .decode("utf8")
        .split()
    )
    if video_encoding not in CODEC_MAP:
        return False
    generate_cover_image(video_dir, int(width), int(height))

    params = "codec_name"
    command = command_fmt.format(stream="a", video=videos[0], params=params)
    audio_encoding = (
        subprocess.check_output(command.split(), cwd=video_dir)
        .strip()
        .decode("utf8")
    )

    cmd_fmt = (
        "ffmpeg -framerate 0.2 -pattern_type glob -i {cover} "
        "-i {audio} -c:a {a_codec} -shortest "
        "-c:v {v_codec} -r 30 -pix_fmt yuv420p {fname}.{ext}"
    )
    video_ext = videos[0].rsplit(".", 1)[-1]
    command = cmd_fmt.format(
        cover=COVER_NAME,
        audio=AUDIO_FILE,
        a_codec=audio_encoding,
        v_codec=CODEC_MAP[video_encoding],
        fname="annotation_0",
        ext=video_ext,
    )
    subprocess.check_output(command.split(), cwd=video_dir)
    return True


def generate_concatenated_video(video_dir):
    """Generate a concatenated video from all videos in a directory.

    *NOTE*: The function assumes that all the videos are in the same format. If
     the videos are not in the same format, this function cannot be used.

    """
    output_file = os.path.abspath(os.path.join(video_dir, OUTPUT_NAME))
    if os.path.exists(output_file):
        print('"{}" already exists!'.format(output_file))
        return
    videos = _get_video_list(video_dir)
    if len(videos) == 1:
        video = videos[0]
        print('Renaming single video "{}" to "{}"'.format(video, OUTPUT_NAME))
        os.rename(os.path.join(video_dir, video), output_file)
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
        filelist=INPUT_TXT, output=output_file
    ).split()
    subprocess.check_call(command, cwd=video_dir)


def main(video_dir):
    annotated = generate_annotation(video_dir)
    generate_concatenated_video(video_dir)
    if not annotated:
        print(
            "Did not generate an annotation video. Video format is not supported currently"
        )


if __name__ == "__main__":
    import sys

    assert os.path.exists(AUDIO_FILE)
    assert os.path.exists(LOGO_FILE)
    video_dir = sys.argv[1]
    main(video_dir)
