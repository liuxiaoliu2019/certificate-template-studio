#!/usr/bin/env bash
set -euo pipefail

source_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
destination="${HOME}/.codex/skills/certificate-template-studio"
force=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --destination)
      [[ $# -ge 2 ]] || { echo "--destination requires a path" >&2; exit 2; }
      destination="$2"
      shift 2
      ;;
    --force)
      force=1
      shift
      ;;
    *)
      echo "Unknown option: $1" >&2
      exit 2
      ;;
  esac
done

if command -v python3 >/dev/null 2>&1; then
  python_cmd="python3"
elif command -v python >/dev/null 2>&1; then
  python_cmd="python"
else
  echo "Python 3.10 or newer is required." >&2
  exit 1
fi

destination="$($python_cmd -c 'import os,sys; print(os.path.abspath(sys.argv[1]))' "$destination")"
if [[ "$(basename "$destination")" != "certificate-template-studio" ]]; then
  echo "The destination directory name must be certificate-template-studio." >&2
  exit 2
fi

"$python_cmd" "$source_root/scripts/quick_validate.py" "$source_root"

if [[ "$source_root" == "$destination" ]]; then
  echo "The skill is already installed and valid: $destination"
  exit 0
fi

backup=""
if [[ -d "$destination" ]] && [[ -n "$(find "$destination" -mindepth 1 -maxdepth 1 -print -quit)" ]]; then
  if [[ $force -ne 1 ]]; then
    echo "The destination is not empty. Use --force to back it up before updating." >&2
    exit 1
  fi
  backup="${destination}.backup-$(date +%Y%m%d-%H%M%S)"
  [[ ! -e "$backup" ]] || { echo "Backup target already exists: $backup" >&2; exit 1; }
  mv "$destination" "$backup"
fi

mkdir -p "$destination"

top_files=(SKILL.md README.md README.en.md LICENSE LICENSE-ASSETS.md NOTICE.md requirements-dev.txt)
runtime_dirs=(agents assets examples prompts references schemas scripts)

for file in "${top_files[@]}"; do
  cp "$source_root/$file" "$destination/$file"
done
for directory in "${runtime_dirs[@]}"; do
  cp -R "$source_root/$directory" "$destination/$directory"
done

"$python_cmd" "$destination/scripts/quick_validate.py" "$destination"

echo "Installed: $destination"
if [[ -n "$backup" ]]; then
  echo "Previous installation backup: $backup"
fi
