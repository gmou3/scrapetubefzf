#!/usr/bin/env python
"""Main module for scrapetubefzf."""

import scrapetube
import subprocess
import sys
import json
import os
import tempfile
import requests
import argparse
from pathlib import Path


def search_youtube(query, limit):
    """Search YouTube and return video results."""
    videos = scrapetube.get_search(query)
    results = []

    for i, video in enumerate(videos):
        if i >= limit:
            break
        results.append(video)

    return results


def download_thumbnail(video_id, cache_dir):
    """Download thumbnail for a video and return the path."""
    thumbnail_path = cache_dir / f"{video_id}.jpg"

    if thumbnail_path.exists():
        return str(thumbnail_path)

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
                return str(thumbnail_path)
        except:
            continue

    return None


def format_for_fzf(videos, cache_dir):
    """Format video data for fzf display and download thumbnails."""
    lines = ""
    thumbnail_map = {}

    for i, video in enumerate(videos, 1):
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

        # Download thumbnail
        print(f"\rDownloading thumbnails... ({i}/{len(videos)})", end="", flush=True)
        thumbnail_path = download_thumbnail(video_id, cache_dir)
        thumbnail_map[video_id] = thumbnail_path

        # Format: Title | Channel | Views | Time | ID
        line = f"\033[1m{title}\033[0m\t\n{channel} | {view_count} | {published} | {video_id}\0"
        lines += line

    print()  # New line after progress
    return lines, thumbnail_map


def main():
    """Main entry point for the application."""
    # Parse arguments
    parser = argparse.ArgumentParser(description='Search YouTube and play videos with mpv')
    parser.add_argument('-d', action='store_true', help='Run mpv in detached mode (terminal closes immediately)')
    parser.add_argument('-n', type=int, default=20, help='Number of search results to fetch (default: 20)')
    args = parser.parse_args()

    # Validate number of results
    if args.n <= 0:
        print("Error: -n must be a positive integer.")
        sys.exit(1)

    query = input("Search: ").strip()

    if not query:
        print("Error: Search query cannot be empty.")
        sys.exit(1)

    print("Fetching...", end=" ", flush=True)

    # Create cache directory for thumbnails and other transient files
    cache_dir = Path(tempfile.gettempdir()) / "scrapetubefzf"
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Search YouTube
    videos = search_youtube(query, limit=args.n)

    if not videos:
        print("No results found.")
        sys.exit(1)

    print(f"fetched {len(videos)} results.", flush=True)

    # Format for fzf and download thumbnails
    lines, thumbnail_map = format_for_fzf(videos, cache_dir)

    # Create preview script
    preview_script = cache_dir / "preview.sh"
    with open(preview_script, 'w') as f:
        f.write('#!/bin/bash\n')
        f.write('VIDEO_ID=$(echo "$1" | awk -F " | " \'{last=$NF} END{print last}\')\n')
        f.write(f'THUMB_PATH="{cache_dir}/$VIDEO_ID.jpg"\n')
        f.write('if [ -f "$THUMB_PATH" ]; then\n')
        f.write('  if [ -n "$UEBERZUG_FIFO" ]; then\n')
        f.write('    echo \'{"action": "add", "identifier": "fzf", "x": \'$FZF_PREVIEW_LEFT\', "y": \'$FZF_PREVIEW_TOP\', "max_width": \'$FZF_PREVIEW_COLUMNS\', "max_height": \'$FZF_PREVIEW_LINES\', "path": "\'$THUMB_PATH\'"}\' >> "$UEBERZUG_FIFO"\n')
        f.write('  elif command -v chafa >/dev/null 2>&1; then\n')
        f.write('    chafa -s "$((FZF_PREVIEW_COLUMNS))x$((FZF_PREVIEW_LINES))" "$THUMB_PATH"\n')
        f.write('  elif command -v catimg >/dev/null 2>&1; then\n')
        f.write('    catimg -w "$((FZF_PREVIEW_COLUMNS))" "$THUMB_PATH"\n')
        f.write('  else\n')
        f.write('    echo "Thumbnail available at: $THUMB_PATH"\n')
        f.write('    echo "Install ueberzug, chafa, or catimg to view thumbnails in terminal"\n')
        f.write('  fi\n')
        f.write('fi\n')

    os.chmod(preview_script, 0o755)

    clear_script = cache_dir / "clear.sh"
    with open(clear_script, 'w') as f:
        f.write('#!/bin/bash\n')
        f.write('echo \'{"action": "remove", "identifier": "fzf"}\' >> "$UEBERZUG_FIFO"\n')

    os.chmod(clear_script, 0o755)

    # Create download script for Alt+D binding
    download_script = cache_dir / "download.sh"
    with open(download_script, 'w') as f:
        f.write('#!/bin/bash\n')
        f.write('IFS=$\'\\n\'\n')
        f.write('SELECTED=($@)\n')
        f.write('i=0\n')
        f.write('for LINE in "${SELECTED[@]}"; do\n')
        f.write('   if (( i % 2 )); then\n')
        f.write('       VIDEO_ID=$(echo "$LINE" | awk -F " | " \'{print $NF}\')\n')
        f.write('       URL="https://www.youtube.com/watch?v=$VIDEO_ID"\n')
        f.write('       echo "Downloading: $URL"\n')
        f.write('       yt-dlp "$URL"\n')
        f.write('   fi\n')
        f.write('   ((i++))\n')
        f.write('done\n')
        f.write('echo ""\n')
        f.write('read -p "Press Enter to continue..."\n')

    os.chmod(download_script, 0o755)

    # Initialize ueberzug if available
    ueberzug_fifo = None
    ueberzug_process = None
    tail_process = None

    # Check if ueberzug is available
    if subprocess.run(['bash', '-c', 'command -v ueberzug || command -v ueberzugpp'],
                     capture_output=True).returncode == 0:
        # Create temporary FIFO for ueberzug
        ueberzug_fifo = cache_dir / f"scrapetubefzf-ueberzug.{os.getpid()}"
        try:
            if not ueberzug_fifo.exists():
                os.mkfifo(ueberzug_fifo)

            # Check if ueberzugpp is available, otherwise use ueberzug
            if subprocess.run(['bash', '-c', 'command -v ueberzugpp'],
                            capture_output=True).returncode == 0:
                ueberzug_cmd = 'ueberzugpp'
            else:
                ueberzug_cmd = 'ueberzug'

            # Start ueberzug process
            ueberzug_process = subprocess.Popen(
                [ueberzug_cmd, 'layer', '--silent'],
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            # Start tail to pipe FIFO to ueberzug
            tail_process = subprocess.Popen(
                ['tail', '-f', str(ueberzug_fifo)],
                stdout=ueberzug_process.stdin,
                stderr=subprocess.DEVNULL
            )

        except Exception as e:
            print(f"Failed to initialize ueberzug: {e}", file=sys.stderr)
            ueberzug_fifo = None
            if ueberzug_process:
                ueberzug_process.terminate()
                ueberzug_process = None
            if tail_process:
                tail_process.terminate()
                tail_process = None

    # Pipe to fzf with multi-select enabled and side panel preview
    fzf_env = os.environ.copy()
    if ueberzug_fifo:
        fzf_env['UEBERZUG_FIFO'] = str(ueberzug_fifo)
    try:
        result = subprocess.run(
            ['fzf', '--multi', '--reverse',
             '--read0', '--gap', '--ansi',
             '--prompt=Select videos: ',
             '--preview', f'{preview_script} {{}}',
             '--bind', f'alt-d:execute({clear_script} && {download_script} {{+}})+abort',
             '--bind', 'resize:refresh-preview',
             '--header=Tab: multi-select | Enter: play | Alt+D: download'],
            input=lines,
            text=True,
            capture_output=True,
            env=fzf_env
        )
        subprocess.run([clear_script], env=fzf_env)
        if result.returncode == 0:
            selected_lines = result.stdout.replace("\t\n", " | ").strip().split('\n')

            if not selected_lines or selected_lines[0] == '':
                print("No selection made.")
                sys.exit(1)

            # Extract video IDs and build URLs
            video_urls = []
            video_titles = []
            print(f"\nSelected {len(selected_lines)} video(s):")
            for i, line in enumerate(selected_lines, 1):
                video_id = line.split(' | ')[-1]
                video_url = f"https://www.youtube.com/watch?v={video_id}"
                video_urls.append(video_url)
                video_titles.append(line.split(' | ')[0])
                print(f"{i:>4d}. {line}")

            # Create an M3U playlist with titles (in order to preload titles in mpv)
            playlist_content = "#EXTM3U\n"
            for title, url in zip(video_titles, video_urls):
                playlist_content += f"#EXTINF:-1,{title}\n{url}\n"

            # Write to a temporary playlist file inside the cache directory
            with tempfile.NamedTemporaryFile('w', delete=False, suffix=".m3u", dir=str(cache_dir)) as f:
                f.write(playlist_content)
                playlist_path = f.name

            # Play with mpv
            try:
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
                    print(f"\nLaunching mpv with {len(video_urls)} video(s)...")
                    subprocess.run(['mpv'] + [f'--playlist={playlist_path}'])
            except FileNotFoundError:
                print("\nError: mpv not found. Please install mpv first.")
                print("Installation: https://mpv.io/installation/")
                sys.exit(1)
        else:
            print("No selection made.")
            sys.exit(1)

    except FileNotFoundError:
        print("Error: fzf not found. Please install fzf first.")
        print("Installation: https://github.com/junegunn/fzf#installation")
        sys.exit(1)
    finally:
        # Clean up ueberzug
        if tail_process:
            try:
                tail_process.terminate()
                tail_process.wait(timeout=1)
            except:
                tail_process.kill()
        if ueberzug_process:
            try:
                ueberzug_process.terminate()
                ueberzug_process.wait(timeout=1)
            except:
                ueberzug_process.kill()
        if ueberzug_fifo and os.path.exists(ueberzug_fifo):
            try:
                os.remove(ueberzug_fifo)
            except:
                pass


if __name__ == "__main__":
    main()
