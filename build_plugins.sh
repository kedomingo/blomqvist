#!/bin/bash

# Root directory
PLUGIN_DIR="src/plugins"
ZIP_DIR="zips"

# Create the zips directory if it doesn't exist
mkdir -p "$ZIP_DIR"

# Function to get the next version number
get_next_version() {
    local dir_name=$1
    local zip_dir="$ZIP_DIR/$dir_name"

    # Find the highest version in existing zip files
    if [[ -d "$zip_dir" ]]; then
        latest_version=$(ls "$zip_dir" | grep -Eo "$dir_name-[0-9]+\.[0-9]+\.zip" | sed -E "s/$dir_name-([0-9]+\.[0-9]+)\.zip/\1/" | sort -V | tail -n 1)
    fi

    # Default to version 1.0 if no zip exists
    if [[ -z "$latest_version" ]]; then
        echo "1.0"
    else
        # Increment the patch version by 0.01
        new_version=$(echo "$latest_version" | awk -F. '{printf "%d.%02d", $1, $2+1}')
        echo "$new_version"
    fi
}

# Loop through each subdirectory in the plugins directory
for dir in "$PLUGIN_DIR"/*/; do
    # Extract the directory name (e.g., 'a' or 'b')
    dir_name=$(basename "$dir")

    # Create the corresponding directory in zips (e.g., /zips/a)
    mkdir -p "$ZIP_DIR/$dir_name"

    # Copy contents from the plugin directory, excluding 'resources' and 'main.py'
    rsync -av --exclude='resources' --exclude='main.py' "$dir" "$ZIP_DIR/$dir_name" --quiet

    # Get the next version number
    next_version=$(get_next_version "$dir_name")

    curr_dir=$(pwd)

    (cd "$dir.." && zip -r "$dir_name.zip" "$dir_name" --quiet)

    cd "$curr_dir"

    mv "$dir""../$dir_name.zip" "$ZIP_DIR/$dir_name/$dir_name-$next_version.zip"

    if [[ $dir_name =~ ^repository\.kedomingo ]]; then
        rm repository.kedomingo*.zip
        cp "$ZIP_DIR/$dir_name/$dir_name-$next_version.zip" .
        cp "$ZIP_DIR/$dir_name/$dir_name-$next_version.zip" "$dir_name.zip"
    fi

done

echo "Build complete"