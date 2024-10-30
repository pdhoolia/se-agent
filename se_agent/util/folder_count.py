import os

def count_folders_in_folder_recursive(folder_path):
    try:
        folder_count = 0
        # os.walk generates the directory names in a directory tree by walking top-down
        for root, dirs, files in os.walk(folder_path):
            folder_count += len(dirs)
        return folder_count
    except FileNotFoundError:
        return "The specified folder was not found."
    except Exception as e:
        return f"An error occurred: {e}"

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Recursively count the number of folders in a folder.")
    parser.add_argument("folder_path", type=str, help="Path to the folder to count subfolders in.")

    args = parser.parse_args()

    folder_count = count_folders_in_folder_recursive(args.folder_path)
    print(f"Number of folders in the folder (including subdirectories): {folder_count}")
