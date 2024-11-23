"""Script for recursively counting the number of files in a folder."""

import os

def count_files_in_folder_recursive(folder_path, ext):
    """Counts the number of files in a folder recursively, optionally filtering by extension.

    Args:
        folder_path (str): Path to the folder to count files in.
        ext (str): Optional extension to filter files (e.g., '.txt'). If None, counts all files.

    Returns:
        int or str: Number of files counted or an error message if an exception occurs.
    """
    try:
        file_count = 0
        # Walk through the directory tree and count the files
        for root, dirs, files in os.walk(folder_path):
            if ext:
                # Count files that end with the specified extension
                file_count += len([file for file in files if file.endswith(ext)])
            else:
                # Count all files
                file_count += len(files)
        return file_count
    except FileNotFoundError:
        return "The specified folder was not found."
    except Exception as e:
        return f"An error occurred: {e}"

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Recursively count the number of files in a folder.")
    parser.add_argument("folder_path", type=str, help="Path to the folder to count files in.")
    parser.add_argument("--ext", type=str, default=None, help="Optional extension of the files to count.")

    args = parser.parse_args()

    file_count = count_files_in_folder_recursive(args.folder_path, args.ext)
    print(f"Number of files ({args.ext if args.ext else 'all'}) in the folder (including subdirectories): {file_count}")