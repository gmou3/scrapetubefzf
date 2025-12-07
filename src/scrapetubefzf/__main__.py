#!/usr/bin/env python
"""Main module for scrapetubefzf."""

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

from scrapetubefzf import PREVIEW_SCRIPT, CLEAR_SCRIPT, DOWNLOAD_SCRIPT
from scrapetubefzf.ueberzug import setup_ueberzug, cleanup_ueberzug


def search_youtube(query: str, limit: int, type: str, results: list) -> List[dict]:
    """Search YouTube and return result IDs."""
    results_iterator = scrapetube.get_search(query, results_type=type)

    for i, result in enumerate(results_iterator):
        if i >= limit:
            break
        results.append(result)


def download_url(url: str, save_path: Path) -> None:
    """Download a file from a URL and save it to the specified path."""
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            with open(save_path, 'wb') as f:
                f.write(response.content)
    except Exception as e:
        print(f"Warning: Failed to download {url}: {e}", file=sys.stderr)


def download_video_thumbnails(video_map: Dict[str, Dict[str, str]], cache_dir: Path) -> None:
    """Download video thumbnails and save in cache directory."""
    for video_id in video_map:
        thumbnail_path = cache_dir / f"{video_id}.jpg"

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


def download_channel_thumbnails(channel_map: Dict[str, Dict[str, str]], cache_dir: Path) -> None:
    """Download channel thumbnails and save in cache directory."""
    for channel_id, info in channel_map.items():
        thumbnail_path = cache_dir / f"{channel_id}.jpg"

        if thumbnail_path.exists():
            continue

        url = info.get("thumbnail", "")
        if not url:
            continue
        url = url.lstrip('/')
        if not url.startswith("https://"):
            url = "https://" + url

        download_url(url, thumbnail_path)


def get_video_info(videos: List[dict]) -> Dict[str, Dict[str, str]]:
    """Get video info and return it as a dictionary."""
    video_map = {}

    for video in videos:
        video_id = video.get('videoId', 'N/A')
        title = video.get('title', {}).get('runs', [{}])[0].get('text', 'No title')

        # Get channel name
        channel = 'Unknown'
        owner_text = video.get('ownerText', {})
        if owner_text and 'runs' in owner_text:
            channel = owner_text['runs'][0].get('text', 'Unknown')

        # Get video duration
        duration = '--:--'
        length_text = video.get('lengthText', {})
        if length_text and 'simpleText' in length_text:
            duration = length_text['simpleText']

        # Get published time
        published = 'Unknown'
        published_time = video.get('publishedTimeText', {})
        if published_time and 'simpleText' in published_time:
            published = published_time['simpleText']

        # Get view count
        view_count = 'N/A views'
        view_count_text = video.get('viewCountText', {})
        if view_count_text and 'simpleText' in view_count_text:
            view_count = view_count_text['simpleText']

        video_map[video_id] = {
            'title': title,
            'channel': channel,
            'duration': duration,
            'published': published,
            'view_count': view_count
        }

    return video_map


def get_channel_info(channels: List[dict]) -> Dict[str, Dict[str, str]]:
    """Get channel info and return it as a dictionary."""
    channel_map = {}

    for channel in channels:
        channel_id = channel.get('channelId', 'N/A')

        # Channel name
        title = 'Unknown'
        title_text = channel.get('title', {})
        if title_text and 'simpleText' in title_text:
            title = title_text['simpleText']
        elif title_text and 'runs' in title_text:
            title = title_text['runs'][0].get('text', title)

        # Get channel description
        description = ''
        desc_text = channel.get('descriptionSnippet', {})
        if desc_text and 'runs' in desc_text:
            description = ''.join([run.get('text', '') for run in desc_text['runs']])

        # Get subscriber count
        subscribers = 'N/A'
        sub_text = channel.get('subscriberCountText', {})
        if sub_text and 'simpleText' in sub_text:
            subscribers = sub_text['simpleText']

        # Get video count
        video_count = 'N/A'
        video_count_text = channel.get('videoCountText', {})
        if video_count_text and 'simpleText' in video_count_text:
            video_count = video_count_text['simpleText']

        # Get thumbnails URLs
        thumbnails = []
        thumbnail_data = channel.get('thumbnail', {}).get('thumbnails', [])
        if thumbnail_data:
            thumbnails = [thumb.get('url', '') for thumb in thumbnail_data]

        channel_map[channel_id] = {
            'title': title,
            'description': description,
            'subscribers': subscribers,
            'video_count': video_count,
            'thumbnail': thumbnails[-1]
        }

    return channel_map


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
    for cmd in ['fzf', 'mpv']:
        if not shutil.which(cmd):
            print(f"Error: {cmd} not found. Please install {cmd} first.")
            if cmd == 'fzf':
                print("Installation: https://github.com/junegunn/fzf#installation")
            elif cmd == 'mpv':
                print("Installation: https://mpv.io/installation/")
            sys.exit(1)

    if args.query:
        query = " ".join(args.query).strip()
    else:
        query = input("Search: ").strip()
    if not query:
        print("Error: Search query cannot be empty.")
        sys.exit(1)

    # Create cache directory for thumbnails and other transient files
    cache_dir = Path(tempfile.gettempdir()) / "scrapetubefzf"
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Search YouTube
    print("Fetching...", end=" ", flush=True)
    videos, channels = [], []
    thread_v = threading.Thread(target=search_youtube, args=(query, args.n, "video", videos))
    thread_c = threading.Thread(target=search_youtube, args=(query, args.n, "channel", channels))
    thread_v.start()
    thread_c.start()
    thread_v.join()
    thread_c.join()

    if not videos:
        print("No results found.")
        sys.exit(1)
    print(f"fetched {len(videos)} results.", flush=True)

    # Download result info (and thumbnails in the background)
    video_map = get_video_info(videos)
    thread_v = threading.Thread(
        target=download_video_thumbnails,
        args=(video_map, cache_dir),
        daemon=True
    )
    thread_v.start()
    channel_map = get_channel_info(channels)
    thread_c = threading.Thread(
        target=download_channel_thumbnails,
        args=(channel_map, cache_dir),
        daemon=True
    )
    thread_c.start()
    results_map = {**video_map, **channel_map}

    # Prepare fzf input files
    fzf_video_str = ""
    for video_id, info in video_map.items():
        video_str = f"{video_id}\t\033[1m{info['title']}\033[0m\n{info['channel']} | {info['duration']} | {info['published']} | {info['view_count']}\0"
        fzf_video_str += video_str
    with open(cache_dir / "videos", "w") as f:
        f.write(fzf_video_str)

    fzf_channel_str = ""
    for channel_id, info in channel_map.items():
        channel_str = f"{channel_id}\t\033[1m{info['title']}\033[0m\n{info['subscribers']} | {info['video_count']}"
        if info['description']:
            channel_str += f" | {info['description']}\0"
        else:
            channel_str += "\0"
        fzf_channel_str += channel_str
    with open(cache_dir / "channels", "w") as f:
        f.write(fzf_channel_str)

    # Initialize ueberzug if available
    ueberzug_fifo = setup_ueberzug(cache_dir)

    # Set up environment for fzf
    fzf_env = os.environ.copy()
    fzf_env.update({
        'CACHE_DIR': str(cache_dir),
        'UEBERZUG_FIFO': str(ueberzug_fifo) if ueberzug_fifo else '',
        'MAIN_PID': str(os.getpid())
    })

    fzf_result = subprocess.run(
        ['fzf', '--multi', '--reverse',
            '--read0', '--gap', '--ansi',
            '--delimiter', '\t', '--with-nth=2',  # Skip ID in display
            '--prompt=Select: ',
            '--preview', f'{CLEAR_SCRIPT} && {PREVIEW_SCRIPT} {{}}',
            '--bind', f'left:reload(cat "{cache_dir}/videos")',
            '--bind', f'right:reload(cat "{cache_dir}/channels")',
            '--bind', f'alt-d:execute({CLEAR_SCRIPT} && {DOWNLOAD_SCRIPT} {{+}})+abort',
            '--bind', 'resize:refresh-preview',
            '--header=Tab: multi-select | Enter: play | Alt+D: download'],
        input=fzf_video_str,
        text=True,
        capture_output=True,
        env=fzf_env
    )

    if ueberzug_fifo:
        subprocess.run([CLEAR_SCRIPT], env=fzf_env)
        cleanup_ueberzug(ueberzug_fifo)

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
            print(f"    {results_map[selections[0]]['title']}")
            selections_str += f"{results_map[selections[0]]['title']}"
        else:
            for i, result_id in enumerate(selections, 1):
                print(f"{i:>4d}. {results_map[result_id]['title']}")
                selections_str += f"{i:>4d}. {results_map[result_id]['title']}\n"

        # Create an M3U playlist with titles (in order to preload titles in mpv)
        playlist_content = "#EXTM3U\n"
        for result_id in selections:
            if result_id in video_map:
                playlist_content += f"#EXTINF:-1,{results_map[result_id]['title']}\nhttps://www.youtube.com/watch?v={result_id}\n"
            if result_id in channel_map:
                playlist_content += f"#EXTINF:-1,{results_map[result_id]['title']}\nhttps://www.youtube.com/channel/{result_id}\n"

        # Write to a playlist file inside the cache directory
        with tempfile.NamedTemporaryFile('w', delete=False, suffix=".m3u", dir=str(cache_dir)) as f:
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
    elif os.path.exists(f"{cache_dir}/alt-d.{os.getpid()}"):  # Alt-D
        os.remove(f"{cache_dir}/alt-d.{os.getpid()}")
    elif fzf_result.returncode == 130:  # ESC or Ctrl-C
        print("No selection made.")
    else:
        if fzf_result.stderr:
            print(f"{fzf_result.stderr.strip()}")
        sys.exit(1)


if __name__ == "__main__":
    main()
