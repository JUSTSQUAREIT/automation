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
    not_yet_on_excel_dir = r'\not-yet-on-excel'
    invalid_file_name_dir = r'\invalid-file-name'
    invalid_file_type_dir = r'\invalid-file-type'
    invalid_file_size_dir = r'\invalid-file-size'

    image_path = path_root + client_name + image_dir
    uploaded_path = image_path + uploaded_dir
    not_yet_uploaded_path = image_path + not_yet_uploaded_dir
    not_yet_on_excel_path = image_path + not_yet_on_excel_dir
    invalid_file_name_path = image_path + invalid_file_name_dir
    invalid_file_type_path = image_path + invalid_file_type_dir
    invalid_file_size_path = image_path + invalid_file_size_dir

    # Data cleaning for image_files
    skus = []
    valid_image_files = []
    duplicated_skus = []
    invalid_file_names = []
    invalid_file_types = []
    invalid_file_sizes = []
    ignored_files = ['desktop.ini']

    # Check image format validity
    print("### CHECKING IMAGE FORMAT VALIDITY ###")
    print("Image format needs to be 'png', 'jpg', 'jpeg', or 'gif'")
    # Fetch image file names
    image_files = [f for f in listdir(
        not_yet_uploaded_path) if isfile(join(not_yet_uploaded_path, f))]
    total_image_count = len(image_files)

    for image in image_files:
        if image in ignored_files:
            continue
        extension = image.split('.')[1]
        if extension.lower() not in ['png', 'jpg', 'jpeg', 'gif']:
            invalid_file_types.append(image)

    print("\n")
    print("invalid_file_types: " + str(len(invalid_file_types)))
    print("invalid_file_types =")
    print(invalid_file_types)
    print("\n")

    # Move invalid files to invalid_file_type_dir
    move_files(invalid_file_types,
               "NEXT STEP: move invalid files to invalid_file_type_dir", not_yet_uploaded_path, invalid_file_type_path)

    # Check image size validity
    print("### CHECKING IMAGE SIZE VALIDITY ###")
    print("Image size needs to be less than 15MB")
    # Fetch image file names
    image_files = [f for f in listdir(
        not_yet_uploaded_path) if isfile(join(not_yet_uploaded_path, f))]

    for image in image_files:
        if image in ignored_files:
            continue
        if stat(not_yet_uploaded_path + '\\' + image).st_size > 15000000:
            invalid_file_sizes.append(image)

    print("\n")
    print("invalid_file_sizes: " + str(len(invalid_file_sizes)))
    print("invalid_file_sizes =")
    print(invalid_file_sizes)
    print("\n")

    # Move invalid files to invalid_file_size_dir
    move_files(invalid_file_sizes,
               "NEXT STEP: move invalid files to invalid_file_size_dir", not_yet_uploaded_path, invalid_file_size_path)

    # Check image name validity
    print("### CHECKING IMAGE NAME VALIDITY ###")
    print("Image name needs to be a 9 digit numerical only value")
    print("If there is a '-' appended to the 9 digits file name, they are treated as duplicates")
    print("Else, the rest are treated as invalid files")
    # Fetch image file names
    image_files = [f for f in listdir(
        not_yet_uploaded_path) if isfile(join(not_yet_uploaded_path, f))]

    for image in image_files:
        if image in ignored_files:
            continue
        filename = image.split('.')[0]
        sku = filename.split('-')
        # When '-' token does not exist in image filename string
        if len(sku) == 1:
            if sku[0].isdigit() and len(sku[0]) == 9:
                skus.append(sku[0])
                valid_image_files.append(image)
            else:
                invalid_file_names.append(image)
        # When '-' is in place for item variations
        elif len(sku) == 2:
            if sku[1].isdigit() and len(sku[1]) < 3:
                duplicated_skus.append(image)
            else:
                invalid_file_names.append(image)
        else:
            invalid_file_names.append(image)

    print("\n")
    print("invalid_file_names: " + str(len(invalid_file_names)))
    print("invalid_file_names =")
    print(invalid_file_names)
    print("\n")

    # Move invalid SKUs to invalid_file_name_dir
    move_files(invalid_file_names,
               "NEXT STEP: move invalid SKUs to invalid_file_name_dir", not_yet_uploaded_path, invalid_file_name_path)

    # Image files debrif
    image_files_debrief(total_image_count, skus, duplicated_skus,
                        invalid_file_names, invalid_file_types, invalid_file_sizes)

    print("### CHECKING PARSED SKUS VALIDITY & FETCH ITS CATALOG OBJECT ID ###")
    print("Check if these SKUs' corresponding items exist on Square DB")
    print("If it exists, then fetch its catalog object ID")
    print("\n")
    # Create an instance of the API Client
    # and initialize it with the credentials
    # for the Square account whose assets you want to manage
    client = Client(
        access_token='EAAAEHPWeUfUN-78ZpMUX4CSpzVC8v7YhaFYzeYn4K2ql8TXM4_8HTWBJrGS2QYU',
        environment='production',
    )

    # Get an instance of the Square API you want call
    api_catalog = client.catalog

    continue_or_exit(
        "NEXT STEP: call Square API api_catalog.search_catalog_items to check SKU validity and fetch its catalog object ID")
    # Call search_catalog_items method to get the Unique ID of the CatalogObject
    catalog_object_ids = []
    existing_skus = []
    existing_sku_files = []
    non_existing_skus = []
    non_existing_sku_files = []
    for sku in skus:
        print("Checking SKU {}...".format(sku))
        search_catalog_items_result = api_catalog.search_catalog_items(
            body={
                "text_filter": sku
            }
        )

        print("API request status: " +
              str(search_catalog_items_result.status_code))
        if search_catalog_items_result.is_success():
            # When SKU exists on Square
            if 'items' in search_catalog_items_result.body:
                existing_skus.append(sku)
                catalog_object_id = search_catalog_items_result.body['items'][0]['id']
                catalog_object_ids.append(catalog_object_id)
            # When SKU does not exist on Square
            else:
                non_existing_skus.append(sku)
        elif search_catalog_items_result.is_error():
            print(search_catalog_items_result.errors)
        print("\n")

    # Find files in directory that match with non_existing_skus
    for image in valid_image_files:
        if image in ignored_files:
            continue
        filename = image.split('.')[0]
        if filename in non_existing_skus:
            non_existing_sku_files.append(image)
        elif filename in existing_skus:
            existing_sku_files.append(image)

    # SKU debrief
    # print("\n")
    print("====================================================================================================")
    sku_debrief(existing_skus, existing_sku_files,
                non_existing_skus, non_existing_sku_files, skus)

    # Move non existing SKUs to not_yet_on_excel_dir
    move_files(non_existing_sku_files,
               "NEXT STEP: move non existing SKUs to not_yet_on_excel_dir", not_yet_uploaded_path, not_yet_on_excel_path)

    # Catalog Pbject IDs debrief
    catalog_object_ids_debrief(existing_skus, catalog_object_ids)

    continue_or_exit(
        "NEXT STEP: create catalog image with Catalog Objet IDs fetched")
    print("### CREATE CATALOG IMAGE WITH CATALOG OBJECT IDS FETCHED ###")
    for index, catalog_object_id in enumerate(catalog_object_ids):
        print("Creating catalog image for SKU: " + existing_skus[index])
        print("Corresponding image file name: " + existing_sku_files[index])
        print("Corresponding Catalog Object ID: " + catalog_object_id)
        file_to_upload_path = not_yet_uploaded_path + \
            '\\' + existing_sku_files[index]
        print("file_to_upload_path = " + file_to_upload_path)
        f_stream = open(file_to_upload_path, "rb")

        create_catalog_image_result = api_catalog.create_catalog_image(
            request={
                "idempotency_key": str(uuid.uuid1()),
                "object_id": catalog_object_ids[index],
                "image": {
                    "type": "IMAGE",
                    "id": "#2021",
                    "image_data": {
                        "name": existing_skus[index]
                    }
                }
            },
            image_file=f_stream
        )

        print("API request status: " +
              str(create_catalog_image_result.status_code))
        # if create_catalog_image_result.is_success():
        #     print(create_catalog_image_result.body)
        if create_catalog_image_result.is_error():
            print(create_catalog_image_result.errors)
        print("\n")

    print("====================================================================================================")
    # Move existing_sku_files to uploaded_dir
    move_files(existing_sku_files,
               "NEXT STEP: move existing_sku_files to uploaded_dir", not_yet_uploaded_path, uploaded_path)


def continue_or_exit(message):
    while True:
        if message:
            print(message)
        answer = input("Do You Want To Continue? [y/n]: ")
        if answer != 'y':
            print("Terminating program...")
            exit()
        else:
            print("Continue...\n")
            break


def os_rename(source, dest, filename):
    # try renaming the source path
    # to destination path
    # using os.rename() method

    try:
        rename(source, dest)
        print("Source path renamed to destination path successfully for file " + filename)

    # If Source is a file
    # but destination is a directory
    except IsADirectoryError as error:
        print("Source is a file but destination is a directory, for file " + filename)
        print(error)

    # If source is a directory
    # but destination is a file
    except NotADirectoryError as error:
        print("Source is a directory but destination is a file, for file " + filename)
        print(error)

    # For permission related errors
    except PermissionError as error:
        print("Operation not permitted, for file " + filename)
        print(error)

    # For OS errors
    except OSError as error:
        print("OS errors, for file " + filename)
        print(error)

    # For any other errors
    except Exception as error:
        print("Unknown errors, for file " + filename)
        print(error)


def move_files(files, message, source_root, dest_root):
    continue_or_exit(message)
    if len(files) != 0:
        for sku in files:
            source = source_root + '\\' + sku
            dest = dest_root + '\\' + sku
            os_rename(source, dest, sku)
        print("\n")
    else:
        print("File list is empty, no files to be moved here.")
        print("\n")
    print("====================================================================================================")


def image_files_debrief(total_image_count, skus, duplicated_skus, invalid_file_names, invalid_file_types, invalid_file_sizes):
    print("### IMAGE FILES DEBRIEF ###")
    print("total_image_count: " + str(total_image_count))
    print("skus: " + str(len(skus)))
    print("duplicated_skus: " + str(len(duplicated_skus)))
    print("invalid_file_names: " + str(len(invalid_file_names)))
    print("invalid_file_types: " + str(len(invalid_file_types)))
    print("invalid_file_sizes: " + str(len(invalid_file_sizes)))

    print(str(len(skus)) + " + " + str(len(duplicated_skus)) + " + " + str(len(invalid_file_names)) + " + " +
          str(len(invalid_file_types)) + " + " + str(len(invalid_file_sizes)) + " = " + str(total_image_count) + "?")
    print("\n")

    if len(skus) + len(duplicated_skus) + len(invalid_file_names) + len(invalid_file_types) + len(invalid_file_sizes) == total_image_count:
        print("Number of files added up to the correct number")
        print("Please go on to the next step")
    else:
        print("Number of files DID NOT add up to the correct number")
        print("Some files are not filtered or located correctly")
        print("Please double check the directories before moving on to the next step")
    print("\n")

    print("skus =")
    print(skus)
    print("\n")

    print("duplicated_skus =")
    print(duplicated_skus)
    print("\n")

    print("invalid_file_names =")
    print(invalid_file_names)
    print("\n")

    print("invalid_file_types =")
    print(invalid_file_types)
    print("\n")

    print("invalid_file_sizes =")
    print(invalid_file_sizes)
    print("\n")

    print("====================================================================================================")


def sku_debrief(existing_skus, existing_sku_files, non_existing_skus, non_existing_sku_files, skus):
    print("### SKU DEBRIEF ###")
    print("existing_skus: " + str(len(existing_skus)))
    print("non_existing_skus: " + str(len(non_existing_skus)))
    print(str(len(existing_skus)) + " + " + str(len(non_existing_skus)) +
          " = " + str(len(skus)) + "?")
    print("\n")

    if len(existing_skus) + len(non_existing_skus) == len(skus):
        print("Number of SKUs added up to the correct number")
        print("There are NO SKUs failed the API request")
        print("Please go on to the next step")
    else:
        print("Number of SKUs DID NOT add up to the correct number")
        print("There are SKUs failed the API request")
        print("Please double check the API responses before moving on to the next step")
    print("\n")

    print("existing_skus =")
    print(existing_skus)
    print("\n")

    print("non_existing_skus =")
    print(non_existing_skus)
    print("\n")

    print("existing_skus: " + str(len(existing_skus)))
    print("existing_sku_files: " + str(len(existing_sku_files)))
    print(str(len(existing_skus)) + " = " +
          str(len(existing_sku_files)) + "?")
    print("\n")

    if len(existing_skus) == len(existing_sku_files):
        print("Number of existing_skus IS EQUAL to number of existing_sku_files")
        print("The existing_skus file filter process was done CORRECTLY")
        print("Please go on to the next step")
    else:
        print(
            "Number of existing_skus IS NOT EQUAL to number of existing_sku_files")
        print("The existing_skus file filter process was done INCORRECTLY")
        print("Please double check the file filter logic before moving on to the next step")
    print("\n")

    print("existing_skus =")
    print(existing_skus)
    print("\n")

    print("existing_sku_files =")
    print(existing_sku_files)
    print("\n")

    print("non_existing_skus: " + str(len(non_existing_skus)))
    print("non_existing_sku_files: " + str(len(non_existing_sku_files)))
    print(str(len(non_existing_skus)) + " = " +
          str(len(non_existing_sku_files)) + "?")
    print("\n")

    if len(non_existing_skus) == len(non_existing_sku_files):
        print("Number of non_existing_skus IS EQUAL to number of non_existing_sku_files")
        print("The non_existing_skus file filter process was done CORRECTLY")
        print("Please go on to the next step")
    else:
        print(
            "Number of non_existing_skus IS NOT EQUAL to number of non_existing_sku_files")
        print("The non_existing_skus file filter process was done INCORRECTLY")
        print("Please double check the file filter logic before moving on to the next step")
    print("\n")

    print("non_existing_skus =")
    print(non_existing_skus)
    print("\n")

    print("non_existing_sku_files =")
    print(non_existing_sku_files)
    print("\n")

    print("====================================================================================================")


def catalog_object_ids_debrief(existing_skus, catalog_object_ids):
    print("### CATALOG OBJECT IDS DEBRIEF ###")
    print("existing_skus: " + str(len(existing_skus)))
    print("catalog_object_ids: " + str(len(catalog_object_ids)))
    print(str(len(existing_skus)) + " = " + str(len(catalog_object_ids)) + "?")
    print("\n")

    if len(existing_skus) == len(catalog_object_ids):
        print("Every SKU found its corresponding Catalog Object ID successfully")
        print("There are NO SKUs failed to find its corresponding Catalog Object ID")
        print("Please go on to the next step")
    else:
        print("Number of SKUs and number of Catalog Object ID DID NOT match up")
        print("There are SKUs failed to find its corresponding Catalog Object ID")
        print("Please double check the API responses before moving on to the next step")
    print("\n")

    print("catalog_object_ids =")
    print(catalog_object_ids)
    print("\n")

    print("====================================================================================================")


if __name__ == "__main__":
    main()
