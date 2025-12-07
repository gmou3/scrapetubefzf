# scrapetubefzf

Search `YouTube` from the terminal, choose videos using `fzf` (with thumbnail previews), and play with `mpv` or download with `yt-dlp`.

![Screenshot](screenshots/screenshot.png)

## Installation

Clone the repository:
```bash
git clone https://github.com/gmou3/scrapetubefzf.git
cd scrapetubefzf
```

Build package and create symlink in `~/.local/bin/`:
```bash
make install
```

### Uninstall

Remove package, symlink, and clean up build artifacts:
```bash
make uninstall
```

## Usage

```
usage: scrapetubefzf [-h] [-n N] [-d] [query ...]

Search YouTube from the terminal, choose videos using fzf (with thumbnail previews), and play with mpv or download with yt-dlp.

positional arguments:
  query       search query

options:
  -h, --help  show this help message and exit
  -n N        number of search results to fetch (default: 20)
  -d          run mpv in detached mode (terminal can close)
```

**Tip**: within fzf, use the left and right arrow keys to switch between video and channel results.

## Requirements

- [Python](https://www.python.org/) 3.8+
- [fzf](https://github.com/junegunn/fzf) 0.56.0+
- [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- [mpv](https://mpv.io/)
- One of the following for thumbnails:
  - [ueberzug](https://github.com/ueber-devel/ueberzug) or [ueberzugpp](https://github.com/jstkdng/ueberzugpp) (recommended)
  - [chafa](https://hpjansson.org/chafa/)
  - [catimg](https://github.com/posva/catimg)


