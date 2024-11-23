"""Script for recursively counting the number of folders in a specified directory."""

import os

def count_folders_in_folder_recursive(folder_path):
    """Counts the number of folders in a directory recursively.

    Args:
        folder_path (str): The path to the directory to count folders in.

    Returns:
        int or str: The total number of folders found, or an error message if an exception occurs.
    """
    try:
        folder_count = 0
        # Walk through the directory tree and count the subdirectories
        for root, dirs, files in os.walk(folder_path):
            folder_count += len(dirs)
        return folder_count
    except FileNotFoundError:
        return "The specified folder was not found."
    except Exception as e:
        return f"An error occurred: {e}"

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Recursively count the number of folders in a folder."
    )
    parser.add_argument(
        "folder_path",
        type=str,
        help="Path to the folder to count subfolders in."
    )

    args = parser.parse_args()

    folder_count = count_folders_in_folder_recursive(args.folder_path)
    print(f"Number of folders in the folder (including subdirectories): {folder_count}")