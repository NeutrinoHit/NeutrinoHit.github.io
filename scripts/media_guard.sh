#!/bin/sh
# neutrinohit-media-guard: films live in the media projects (neutrinohit-map/docs/media-library.md).
# A deliberate exception for one commit: NH_ALLOW_VIDEO=1 git commit ...
[ "$NH_ALLOW_VIDEO" = 1 ] && exit 0
bad=$(git -c core.quotepath=off diff --cached --name-only --diff-filter=AM | while IFS= read -r f; do
  case "$f" in
    (*.[mM][pP]4|*.[mM]4[vV]|*.[mM][oO][vV]|*.[wW][eE][bB][mM]|*.[mM][kK][vV]|*.[aA][vV][iI]) echo "  $f"; continue ;;
  esac
  size=$(git cat-file -s ":$f" 2>/dev/null || echo 0)
  [ "$size" -gt 26214400 ] && echo "  $f ($((size / 1048576)) MB)"
done)
if [ -n "$bad" ]; then
  echo "Commit refused: video files or files over 25 MB:" >&2
  echo "$bad" >&2
  echo "Films go to a media project: neutrinohit-map/scripts/nh_media.py prepare." >&2
  echo "A deliberate exception: NH_ALLOW_VIDEO=1 git commit ..." >&2
  exit 1
fi
exit 0
