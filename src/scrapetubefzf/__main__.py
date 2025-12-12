#!/usr/bin/env python
"""
Main module for scrapetubefzf.

Functions:
- download_url: Download a file from a URL and save it to the specified path.
- download_video_thumbnails: Download video thumbnails and save in cache directory.
- download_channel_thumbnails: Download channel thumbnails and save in cache directory.
- get_video_info: Get video info and save it in a dictionary.
- get_channel_info: Get channel info and save it in a dictionary.
- run_fzf: Run fzf with the appropriate environment and options.
- main: Main function of scrapetubefzf.
"""

import scrapetube
import subprocess
import sys
import os
import tempfile
import requests
import argparse
import readline
import shutil
import threading
from pathlib import Path
from typing import Dict, List

from scrapetubefzf import PREVIEW_SCRIPT, CLEAR_SCRIPT, DOWNLOAD_SCRIPT, CACHE_DIR, VIDEOS_FILE, CHANNELS_FILE
from scrapetubefzf.ueberzug import setup_ueberzug, cleanup_ueberzug


def download_url(url: str, save_path: Path) -> None:
    """Download a file from a URL and save it to the specified path."""
    try:
        tmp_path = save_path.with_suffix(".tmp")

        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            with open(tmp_path, 'wb') as f:
                f.write(response.content)

        try:
            # Atomic move: PREVIEW_SCRIPT will not see partial data
            os.replace(tmp_path, save_path)
        except OSError as e:
            pass

    except Exception as e:
        log_path = os.path.join(CACHE_DIR, "download.log")
        with open(log_path, "a") as f:
            f.write(f"Warning: Failed to download {url}: {e}\n")


def download_video_thumbnails(video_map: Dict[str, Dict[str, str]]) -> None:
    """Download video thumbnails and save in cache directory."""
    for video_id in video_map:
        thumbnail_path = CACHE_DIR / f"{video_id}.jpg"

        if thumbnail_path.exists():
            continue

        # Try different thumbnail qualities
        urls = [
            f"https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg",  # Highest quality (up to 1920x1080)
            f"https://i.ytimg.com/vi/{video_id}/sddefault.jpg",      # Standard definition (640x480)
            f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",      # High quality (480x360)
            f"https://i.ytimg.com/vi/{video_id}/mqdefault.jpg",      # Medium quality (320x180)
            f"https://i.ytimg.com/vi/{video_id}/default.jpg"         # Lowest quality (120x90)
        ]

        for url in urls:
            download_url(url, thumbnail_path)
            if thumbnail_path.exists():
                break


def download_channel_thumbnails(channel_map: Dict[str, Dict[str, str]]) -> None:
    """Download channel thumbnails and save in cache directory."""
    for channel_id, info in channel_map.items():
        thumbnail_path = CACHE_DIR / f"{channel_id}.jpg"

        if thumbnail_path.exists():
            continue

        url = info.get('thumbnail', '')
        if not url:
            continue
        url = url.lstrip('/')
        if not url.startswith("https://"):
            url = "https://" + url

        download_url(url, thumbnail_path)


def get_video_info(query: str, limit: int, titles_map: Dict[str, str]) -> None:
    """Get video info and save it in a dictionary."""
    f = open(VIDEOS_FILE, "a")

    video_map = {}
    for video in scrapetube.get_search(query, limit):
        video_id = video.get('videoId', 'N/A')
        title = video.get('title', {}).get('runs', [{}])[0].get('text', 'No title')
        channel = video.get('ownerText', {}).get('runs', [{}])[0].get('text', 'Unknown')
        duration = video.get('lengthText', {}).get('simpleText', '--:--')
        published = video.get('publishedTimeText', {}).get('simpleText', 'Unknown')
        view_count = video.get('viewCountText', {}).get('simpleText', 'N/A')

        # Update dictionaries
        video_map[video_id] = {
            'title': title,
            'channel': channel,
            'duration': duration,
            'published': published,
            'view_count': view_count
        }
        titles_map[video_id] = title

        # Write to videos file
        video_str = f"{video_id}\t\033[1m{title}\033[0m\n{channel} | {duration} | {published} | {view_count}\0"
        f.write(video_str)
        f.flush()

    threading.Thread(target=download_video_thumbnails, args=(video_map,), daemon=True).start()
    f.close()


def get_channel_info(query: str, limit: int, titles_map: Dict[str, str]) -> None:
    """Get channel info and save it in a dictionary."""
    f = open(CHANNELS_FILE, "a")

    channel_map = {}
    for channel in scrapetube.get_search(query, limit, results_type="channel"):
        channel_id = channel.get('channelId', 'N/A')
        title = channel.get('title', {}).get('simpleText', 'Unknown')
        description = ''.join([run.get('text', '') for run in channel.get('descriptionSnippet', {}).get('runs', [{}])])
        subscribers = channel.get('subscriberCountText', {}).get('simpleText', 'N/A')
        video_count = channel.get('videoCountText', {}).get('simpleText', 'N/A')
        thumbnails = [thumb.get('url', '') for thumb in channel.get('thumbnail', {}).get('thumbnails', [])]

        # Update dictionaries
        channel_map[channel_id] = {
            'title': title,
            'description': description,
            'subscribers': subscribers,
            'video_count': video_count,
            'thumbnail': thumbnails[-1]
        }
        titles_map[channel_id] = title

        # Write to channels file
        channel_str = f"{channel_id}\t\033[1m{title}\033[0m\n{subscribers} | {video_count}"
        if description:
            channel_str += f" | {description}\0"
        else:
            channel_str += "\0"
        f.write(channel_str)
        f.flush()

    threading.Thread(target=download_channel_thumbnails, args=(channel_map,), daemon=True).start()
    f.close()


def run_fzf(n: int) -> subprocess.CompletedProcess:
    # Initialize ueberzug if available
    ueberzug_fifo = setup_ueberzug(CACHE_DIR)
    my_tail = f"tail -fz -s 0.2 -n {n}"

    # Set up environment for fzf
    fzf_env = os.environ.copy()
    fzf_env.update({
        'FZF_DEFAULT_COMMAND': f'{my_tail} "{VIDEOS_FILE}"',
        'CACHE_DIR': str(CACHE_DIR),
        'UEBERZUG_FIFO': str(ueberzug_fifo) if ueberzug_fifo else '',
        'MAIN_PID': str(os.getpid())
    })

    fzf_result = subprocess.run(
        ['fzf', '--multi', '--reverse',
            '--read0', '--gap', '--ansi',
            '--delimiter', '\t', '--with-nth=2',  # Skip ID in display
            '--prompt=Select: ', '--info=hidden',
            '--header=Tab: multi-select | Enter: play | Alt-d: download | →: channels',
            '--preview', f'{CLEAR_SCRIPT} && {PREVIEW_SCRIPT} {{}}',
            '--bind', 'resize:refresh-preview',
            '--bind', f'left:reload({my_tail} "{VIDEOS_FILE}")+change-header(Tab: multi-select | Enter: play | Alt-d: download | →: channels)',
            '--bind', f'right:reload({my_tail} "{CHANNELS_FILE}")+change-header(Tab: multi-select | Enter: play | Alt-d: download | ←: videos)',
            '--bind', f'alt-d:execute({CLEAR_SCRIPT} && {DOWNLOAD_SCRIPT} {{+}})+abort'],
        text=True,
        capture_output=True,
        env=fzf_env
    )

    if ueberzug_fifo:
        subprocess.run([CLEAR_SCRIPT], env=fzf_env)
        cleanup_ueberzug(ueberzug_fifo)

    return fzf_result


def main():
    """Main function of scrapetubefzf."""
    # Parse arguments
    parser = argparse.ArgumentParser(
        description=(
            "Search YouTube from the terminal, choose videos using fzf (with thumbnail previews), "
            "and play with mpv or download with yt-dlp."
        )
    )
    parser.add_argument('-n', type=int, default=20, help='number of search results to fetch (default: 20)')
    parser.add_argument('-d', action='store_true', help='run mpv in detached mode (terminal can close)')
    parser.add_argument('query', nargs='*', help='search query')
    args = parser.parse_args()

    # Validate number of results
    if args.n <= 0:
        print("Error: -n must be a positive integer.")
        sys.exit(1)

    # Ensure required commands exist
    for cmd, url in {
        'fzf':'https://github.com/junegunn/fzf#installation',
        'yt-dlp':'https://github.com/yt-dlp/yt-dlp/wiki/Installation',
        'mpv':'https://mpv.io/installation/'
    }.items():
        if not shutil.which(cmd):
            print(f"Error: {cmd} not found. Installation: {url}")
            sys.exit(1)

    if args.query:
        query = " ".join(args.query).strip()
    else:
        try:
            query = input("Search: ").strip()
        except KeyboardInterrupt:
            print("\nExiting...")
            sys.exit(1)
    if not query:
        print("Search query empty.")
        sys.exit(1)

    # Search YouTube (download result info and thumbnails in the background)
    titles_map = {}
    thread_v = threading.Thread(target=get_video_info, args=(query, args.n, titles_map), daemon=True)
    thread_c = threading.Thread(target=get_channel_info, args=(query, args.n, titles_map), daemon=True)
    thread_v.start()
    thread_c.start()

    fzf_result = run_fzf(args.n)

    if fzf_result.returncode == 0:
        fzf_lines = fzf_result.stdout.strip().split('\n')
        selections = [line.split('\t')[0] for i, line in enumerate(fzf_lines) if i % 2 == 0]

        if not selections or selections[0] == '':
            print("No selection made.")
            sys.exit(1)

        # Display selections
        selections_str = ""
        print(f"Selected {len(selections)} result{'s' if len(selections) != 1 else ''}:")
        if len(selections) == 1:
            print(f"    {titles_map[selections[0]]}")
            selections_str += f"{titles_map[selections[0]]}"
        else:
            for i, result_id in enumerate(selections, 1):
                print(f"{i:>4d}. {titles_map[result_id]}")
                selections_str += f"{i:>4d}. {titles_map[result_id]}\n"

        # Create an M3U playlist with titles (in order to preload titles in mpv)
        playlist_content = "#EXTM3U\n"
        for result_id in selections:
            if len(result_id) == 11:  # video
                playlist_content += f"#EXTINF:-1,{titles_map[result_id]}\nhttps://www.youtube.com/watch?v={result_id}\n"
            else:  # channel
                playlist_content += f"#EXTINF:-1,{titles_map[result_id]}\nhttps://www.youtube.com/channel/{result_id}\n"

        # Write to a playlist file inside the cache directory
        with tempfile.NamedTemporaryFile('w', delete=False, suffix=".m3u", dir=str(CACHE_DIR)) as f:
            f.write(playlist_content)
            playlist_path = f.name

        if args.d:
            # Send notification with notify-send (if available)
            try:
                subprocess.run(
                    ["notify-send", "scrapetubefzf (Playing):", selections_str],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            except FileNotFoundError:
                pass
            # Run mpv detached - terminal can close
            subprocess.Popen(
                ['mpv', '--no-terminal', f'--playlist={playlist_path}'],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
        else:
            # Run mpv normally - terminal waits
            print(f"Launching mpv with {len(selections)} selection{'s' if len(selections) != 1 else ''}...")
            subprocess.run(['mpv', f'--playlist={playlist_path}'])
    elif os.path.exists(f"{CACHE_DIR}/alt-d.{os.getpid()}"):  # Alt-D
        os.remove(f"{CACHE_DIR}/alt-d.{os.getpid()}")
    elif fzf_result.returncode == 130:  # ESC or Ctrl-C
        print("No selection made.")
    else:
        if fzf_result.stderr:
            print(f"{fzf_result.stderr.strip()}")
        sys.exit(1)


if __name__ == "__main__":
    main()
