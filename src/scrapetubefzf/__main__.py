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
from pathlib import Path
from typing import Dict, List

from scrapetubefzf import PREVIEW_SCRIPT, CLEAR_SCRIPT, DOWNLOAD_SCRIPT
from scrapetubefzf.ueberzug import setup_ueberzug, cleanup_ueberzug


def search_youtube(query: str, limit: int) -> List[dict]:
    """Search YouTube and return video IDs."""
    videos = scrapetube.get_search(query)
    results = []

    for i, video in enumerate(videos):
        if i >= limit:
            break
        results.append(video)

    return results


def download_thumbnail(video_id: str, cache_dir: Path) -> None:
    """Download thumbnail for a video and save in cache directory."""
    thumbnail_path = cache_dir / f"{video_id}.jpg"

    if thumbnail_path.exists():
        return

    # Try different thumbnail qualities
    urls = [
        f"https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg",  # Highest quality (up to 1920x1080)
        f"https://i.ytimg.com/vi/{video_id}/sddefault.jpg",      # Standard definition (640x480)
        f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",      # High quality (480x360)
        f"https://i.ytimg.com/vi/{video_id}/mqdefault.jpg",      # Medium quality (320x180)
        f"https://i.ytimg.com/vi/{video_id}/default.jpg"         # Lowest quality (120x90)
    ]

    for url in urls:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                with open(thumbnail_path, 'wb') as f:
                    f.write(response.content)
                return
        except Exception as e:
            print(f"Warning: Failed to download {url}: {e}", file=sys.stderr)
            continue


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

        # Get view count and published time
        view_count = 'N/A views'
        published = ''
        view_count_text = video.get('viewCountText', {})
        if view_count_text and 'simpleText' in view_count_text:
            view_count = view_count_text['simpleText']

        published_time = video.get('publishedTimeText', {})
        if published_time and 'simpleText' in published_time:
            published = published_time['simpleText']

        # Get video duration
        length_text = video.get('lengthText', {})
        if length_text and 'simpleText' in length_text:
            duration = length_text['simpleText']

        video_map[video_id] = {
            'title': title,
            'channel': channel,
            'duration': duration,
            'published': published,
            'view_count': view_count
        }

    return video_map


def main():
    """Main function of scrapetubefzf."""
    # Parse arguments
    parser = argparse.ArgumentParser(description='Search YouTube and play videos with mpv')
    parser.add_argument('-d', action='store_true', help='Run mpv in detached mode (terminal can close)')
    parser.add_argument('-n', type=int, default=20, help='Number of search results to fetch (default: 20)')
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

    query = input("Search: ").strip()
    if not query:
        print("Error: Search query cannot be empty.")
        sys.exit(1)

    # Create cache directory for thumbnails and other transient files
    cache_dir = Path(tempfile.gettempdir()) / "scrapetubefzf"
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Search YouTube
    print("Fetching...", end=" ", flush=True)
    videos = search_youtube(query, limit=args.n)
    if not videos:
        print("No results found.")
        sys.exit(1)
    print(f"fetched {len(videos)} results.", flush=True)

    # Download video info
    video_map = get_video_info(videos)

    # Download thumbnails
    for i, video_id in enumerate(video_map, 1):
        print(f"\rDownloading thumbnails... ({i}/{len(videos)})", end="", flush=True)
        download_thumbnail(video_id, cache_dir)
    print()  # New line after progress

    # Prepare fzf input string
    fzf_str = ""
    for video_id, info in video_map.items():
        video_str = f"{video_id}\t\033[1m{info['title']}\033[0m\n{info['channel']} | {info['duration']} | {info['published']} | {info['view_count']}\0"
        fzf_str += video_str

    # Initialize ueberzug if available
    ueberzug_fifo = setup_ueberzug(cache_dir)

    # Set up environment for fzf
    fzf_env = os.environ.copy()
    fzf_env.update({
        'CACHE_DIR': str(cache_dir),  # Make cache_dir available to preview script
        'UEBERZUG_FIFO': str(ueberzug_fifo) if ueberzug_fifo else '',
    })

    fzf_result = subprocess.run(
        ['fzf', '--multi', '--reverse',
            '--read0', '--gap', '--ansi',
            '--delimiter', '\t', '--with-nth=2',  # Skip video ID in display
            '--prompt=Select videos: ',
            '--preview', f'{PREVIEW_SCRIPT} {{}}',
            '--bind', f'alt-d:execute({CLEAR_SCRIPT} && {DOWNLOAD_SCRIPT} {{+}})+abort',
            '--bind', 'resize:refresh-preview',
            '--header=Tab: multi-select | Enter: play | Alt+D: download'],
        input=fzf_str,
        text=True,
        capture_output=True,
        env=fzf_env
    )

    if ueberzug_fifo:
        subprocess.run([CLEAR_SCRIPT], env=fzf_env)
        cleanup_ueberzug(ueberzug_fifo)

    if fzf_result.returncode == 0:
        fzf_lines = fzf_result.stdout.strip().split('\n')
        selected_videos = [line.split('\t')[0] for i, line in enumerate(fzf_lines) if i % 2 == 0]

        if not selected_videos or selected_videos[0] == '':
            print("No selection made.")
            sys.exit(1)

        # Display selected videos
        print(f"\nSelected {len(selected_videos)} video(s):")
        for i, video_id in enumerate(selected_videos, 1):
            print(f"{i:>4d}. {video_map[video_id]['title']}")

        # Create an M3U playlist with titles (in order to preload titles in mpv)
        playlist_content = "#EXTM3U\n"
        for video_id in selected_videos:
            playlist_content += f"#EXTINF:-1,{video_map[video_id]['title']}\nhttps://www.youtube.com/watch?v={video_id}\n"

        # Write to a playlist file inside the cache directory
        with tempfile.NamedTemporaryFile('w', delete=False, suffix=".m3u", dir=str(cache_dir)) as f:
            f.write(playlist_content)
            playlist_path = f.name

        if args.d:
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
            print(f"\nLaunching mpv with {len(selected_videos)} video(s)...")
            subprocess.run(['mpv', f'--playlist={playlist_path}'])
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
