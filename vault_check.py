import filecmp
import os
import subprocess
import difflib
from datetime import datetime
from urllib.parse import quote

# The remote branch to be compared against
BRANCH_NAME = "main"
# Path to local vault
LOCAL_PATH = r"C:\Users\trjji\Documents\Obsidian Vault"
# URL to clone remote repo
REMOTE_URL = "https://github.com/Nexeor/Notes.git"
# Path to cloned repo
REMOTE_PATH = "./temp_clone"
# List of dirs to ignore
IGNORE_DIRS = [".git", ".obsidian"]
# Path to ouput dir
OUTPUT_DIR_PATH = "./results"


def get_remote():
    subprocess.run(
        ["git", "clone", "-b", BRANCH_NAME, "--single-branch", REMOTE_URL, REMOTE_PATH]
    )


def print_dir_tree():
    for dirpath, dirnames, filenames in os.walk(REMOTE_PATH):
        # Modify dirnames in place so os.walk doesn't traverse hidden dirs
        dirnames[:] = [dir for dir in dirnames if dir not in IGNORE_DIRS]

        # Calculate depth and print dir
        depth = dirpath.replace(REMOTE_PATH, "").count(os.sep)
        print(f"{"\t" * depth}{os.path.normpath(dirpath)}")

        # Print files in dir
        for name in filenames:
            print(f"{"\t" * (depth + 1)}{name}")


# Compare the modified directory to the remote copy
# No Change:
# 1) Exists in base_dir and comp_dir
# 2) Exists in same place,
# 3) Contains same content
# OR
# 1) Only exists in base_dir
# Upload from mod:
# 1) Exists in comp_dir but not in base_dir
# Choose between:
# 1) Exists in comp_dir and base_dir
# 2) Exists in same place
# 3) Contain's different content
# OR
# 2) Exists in differnt place
def compare_dirs(base_dir, comp_dir):
    diff = {
        "DNE": {"unique_base": [], "unique_local": []},
        "DIFF": [],
        "DUPLICATE": {},
    }
    base_files = {}
    comp_files = {}

    # Go through base (Git) and compare to comp (local)
    for dirpath, dirnames, filenames in os.walk(base_dir):
        # Modify dirnames in place so os.walk doesn't traverse hidden dirs
        dirnames[:] = [dir for dir in dirnames if dir not in IGNORE_DIRS]

        # Get absolute path to both dirs
        abs_base_dir_path = os.path.normpath(os.path.abspath(dirpath))
        abs_comp_dir_path = os.path.abspath(
            os.path.join(comp_dir, os.path.basename(dirpath))
        )
        # Ensure dir references (., ..) are not included in path
        if os.path.basename(dirpath) == os.path.basename(base_dir):
            abs_comp_dir_path = os.path.abspath(comp_dir)
        print(f"Base dir: {abs_base_dir_path}")
        print(f"Comp dir: {abs_comp_dir_path}")

        # Iterate over files in base dir and check against comp dir
        for filename in filenames:
            base_file_path = os.path.join(abs_base_dir_path, filename)
            comp_file_path = os.path.join(abs_comp_dir_path, filename)
            print("\tBase File:", base_file_path)
            print("\tComp File:", comp_file_path)

            # Add files to base_files for tracking duplicates and diff filepaths
            if not base_files.get(filename):
                base_files[filename] = [base_file_path]
            else:
                base_files[filename].append(base_file_path)

            # Check if comp with same path exits
            if not os.path.exists(comp_file_path):
                diff["DNE"]["unique_base"].append(base_file_path)
                print(f"\tISSUE: Comp file DNE\n")
            # Check if files with same path have same contents
            elif not filecmp.cmp(base_file_path, comp_file_path, shallow=False):
                with open(base_file_path) as base:
                    base_content = base.readlines()
                with open(comp_file_path) as comp:
                    comp_content = comp.readlines()

                diff_log = list(
                    difflib.unified_diff(
                        base_content, comp_content, base_file_path, comp_file_path
                    )
                )
                diff["DIFF"].append(diff_log)
                print(f"\tISSUE: File contents differ\n")
            else:
                print(f"\tMATCH\n")

    # Go through comp dirs and compare to base dirs
    for dirpath, dirnames, filenames in os.walk(comp_dir):
        # Modify dirnames in place so os.walk doesn't traverse hidden dirs
        dirnames[:] = [dir for dir in dirnames if dir not in IGNORE_DIRS]

        # Get absolute path to both dirs
        abs_comp_dir_path = os.path.abspath(os.path.abspath(dirpath))
        abs_base_dir_path = os.path.abspath(
            os.path.join(base_dir, os.path.basename(dirpath))
        )
        print(f"Base dir: {abs_base_dir_path}")
        print(f"Comp dir: {abs_comp_dir_path}")

        for filename in filenames:
            comp_file_path = os.path.join(abs_comp_dir_path, filename)
            base_file_path = os.path.join(abs_base_dir_path, filename)
            print("\tBase File:", base_file_path)
            print("\tComp File:", comp_file_path)

            # Add files to comp_files for tracking duplicates and diff filepaths
            if not comp_files.get(filename):
                comp_files[filename] = [comp_file_path]
            else:
                comp_files[filename].append(comp_file_path)

            # Check if base file with same path exists
            if not os.path.exists(base_file_path):
                diff["DNE"]["unique_local"].append(comp_file_path)
                print(f"\tISSUE: Base file DNE\n")
            else:
                print(f"\tMATCH\n")

    # Go over all base files and check for duplicates
    for base_file in base_files:
        # File appears twice in base
        if base_files[base_file] and len(base_files[base_file]) > 1:
            diff["DUPLICATE"].setdefault(base_file, base_files[base_file])

        # File appears in both base and comp
        if base_file in comp_files and len(comp_files[base_file]) > 0:
            base_paths = set(base_files[base_file])
            print(base_paths)
            comp_paths = set(comp_files[base_file])
            print(comp_paths)

            # Same file appears in base and comp with different paths
            if base_paths != comp_paths:
                diff["DUPLICATE"].setdefault(base_file, []).extend(
                    comp_files[base_file]
                )

    # Go over comp files and check for duplicates
    for comp_file in comp_files:
        if comp_files[comp_file] and len(comp_files[comp_file]) > 1:
            diff["DUPLICATE"].setdefault(comp_file, []).extend(comp_files[comp_file])

    if not diff:
        print(f"No differences between base and local")

    return diff


def print_diff(diffs):
    # Create unique file for DNE
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    with open(
        f"{OUTPUT_DIR_PATH}/missing/MISSING-{timestamp}.txt", "w", encoding="utf-8"
    ) as file:
        file.write("MISSING FILES:\nUNIQUE TO GIT:\n")
        for path in diffs["DNE"]["unique_base"]:
            file.write(make_link(path))

        file.write("UNIQUE TO LOCAL:\n")
        for path in diffs["DNE"]["unique_local"]:
            file.write(make_link(path))

    with open(f"{OUTPUT_DIR_PATH}/diff/DIFF-{timestamp}.txt", "w") as file:
        for diff in diffs["DIFF"]:
            file.writelines(diff)

    with open(
        f"{OUTPUT_DIR_PATH}/duplicate/DUPLICATE-{timestamp}.txt", "w", encoding="utf-8"
    ) as file:
        for dup in diffs["DUPLICATE"]:
            file.write(f"{dup}\n")
            for path in diffs["DUPLICATE"][dup]:
                file.write(make_link(path))


def make_link(path):
    encoded_path = quote(path.replace("\\", "/"))
    return f"\t{path}\n\t→ [Open](" + f"file:///{encoded_path})\n\n"


def main():
    diff = compare_dirs(REMOTE_PATH, LOCAL_PATH)
    print_diff(diff)


# Compare base_dir and new_dir and identify differences
if __name__ == "__main__":
    main()
