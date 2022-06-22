from square.client import Client
from os import listdir, rename, stat
from os.path import isfile, join
import re
import uuid
import sys
import glob

def main():
    # Set local path
    path_root = r'G:\My Drive\clients'
    client_name = r'\yesnaturalgoods'
    image_dir = r'\images'
    uploaded_dir = r'\uploaded'
    not_yet_uploaded_dir = r'\not-yet-uploaded'
    
    image_path = path_root + client_name + image_dir
    uploaded_path = image_path + uploaded_dir
    not_yet_uploaded_path = image_path + not_yet_uploaded_dir

    # Data cleaning for image_files
    uploaded_files = []
    not_yet_uploaded_files = []
    duplicated_files = []
    ignored_files = ['desktop.ini']

    # Fetch uploaded files
    print("### FETCH UPLOADED FILES ###")
    # Fetch image file names
    raw_uploaded_files = [f for f in listdir(uploaded_path) if isfile(join(uploaded_path, f))]
    for image in raw_uploaded_files:
        uploaded_files.append(image.lower())
    uploaded_file_count = len(uploaded_files)

    print("\n")
    print("uploaded_file_count: " + str(uploaded_file_count))
    print("uploaded_files =")
    print(uploaded_files)
    print("\n")

    # Fetch not yet uploaded files
    print("### FETCH NOT YET UPLOADED FILES ###")
    # Fetch image file names
    not_yet_uploaded_files = [f for f in listdir(not_yet_uploaded_path) if isfile(join(not_yet_uploaded_path, f))]
    not_yet_uploaded_file_count = len(not_yet_uploaded_files)

    print("\n")
    print("not_yet_uploaded_file_count: " + str(not_yet_uploaded_file_count))
    print("not_yet_uploaded_files =")
    print(not_yet_uploaded_files)
    print("\n")

    # Find duplicated files
    print("### FIND DUPLICATED FILES ###")
    # Iterate through not yet uploaded files list
    for image in not_yet_uploaded_files:
        if image.lower() in uploaded_files and image not in ignored_files:
            duplicated_files.append(image)

    duplicated_file_count = len(duplicated_files)

    print("\n")
    print("duplicated_file_count: " + str(duplicated_file_count))
    print("duplicated_files =")
    print(duplicated_files)
    print("\n")


if __name__ == "__main__":
    main()
