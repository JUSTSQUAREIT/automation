#!/usr/bin/env python3
"""
This module is used to duplicate Square catalog items given a list of catalog items to be duplicated in the form provided by our XLSX template. The template can be found at https://docs.google.com/spreadsheets/d/1oMseNFOLteIpVL2eSEGm63dybO1htEgK/
"""

__author__ = "JUSTSQUAREIT Canada Co."
__version__ = "0.1.0"
__license__ = "MIT"

import argparse
import time
import requests
import pandas as pd
import uuid
from io import BytesIO
from logzero import logger, logfile
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from square.client import Client

ACCESS_TOKEN = "EAAAEHPWeUfUN-78ZpMUX4CSpzVC8v7YhaFYzeYn4K2ql8TXM4_8HTWBJrGS2QYU"
ENVIRONMENT = "production"
PURCHASE_ORDER_FOLDER_ID = "1szFbrksMcW8wCSvv2hKcSpn11EcpKXGm"
EXPIRY_DATE_CUSTOM_ATTRIBUTE_KEY = "Square:63c5f5f1-430e-4079-9879-80898e6cf310"
LOCATION_ID = "LB5F8WYCHXM5V"
EXPIRY_DATE_CUSTOM_ATTRIBUTE_DEFINITION_ID = "EMOUBMKM6N2GVRH67JGW375T"


def main(args):
    """ Main entry point of the app """

    logfile("/tmp/logfile-" + time.strftime("%Y%m%d-%H%M%S") + ".log")

    gauth = GoogleAuth()
    # gauth.LocalWebserverAuth()
    drive = GoogleDrive(gauth)
    square_api_client = create_square_api_client()
    df = retrieve_target_xlsx_df(gauth, drive, args.args)
    duplicate_catalog_items, modify_catalog_items = search_catalog_items(
        df, square_api_client)
    cleansed_catalog_items = cleanse_catalog_items(
        df, duplicate_catalog_items, modify_catalog_items)
    logger.info(len(cleansed_catalog_items))
    # logger.info(list(cleansed_catalog_items.values()))
    continue_or_exit("Catalog items are ready to be duplicated.")
    batch_upsert_catalog_objects(square_api_client, cleansed_catalog_items)


def create_square_api_client():
    """Create an instance of the API Client

    And initialize it with the credentials for the Square account whose assets you want to manage.

    Returns:
        client (square.client): Instance of the Square API Client.
    """

    client = Client(
        access_token=ACCESS_TOKEN,
        environment=ENVIRONMENT,
    )
    return client


def retrieve_target_xlsx_df(gauth, drive, purchase_order_id):
    """Retrieve target XLSX data frame

    Request target XLSX using Google Drive API
    and read the file in using Pandas as a data frame

    Args:
        gauth (GoogleAuth): Instance of Google Auth.
        drive (GoogleDrive): Instance of Google Drive client.
        purchase_order_id (str): Purchase order ID taken from standard input.

    Returns:
        df (pandas.DataFrame): Data frame of target XLSX.
    """

    purchase_order_file_list = drive.ListFile(
        {'q': f"'{PURCHASE_ORDER_FOLDER_ID}' in parents and trashed=false"}).GetList()

    for file in purchase_order_file_list:
        if (purchase_order_id in file['title']):
            spreadsheetId = file['id']
            logger.info(spreadsheetId)
            logger.info(file['title'])

    url = f"https://docs.google.com/spreadsheets/export?id={spreadsheetId}&exportFormat=xlsx"

    res = requests.get(url, headers={
        "Authorization": "Bearer " + gauth.attr['credentials'].access_token})
    return pd.read_excel(BytesIO(res.content))


def search_catalog_items(df, client):
    """Search catalog items to be duplicated using SKUs from df

    Search catalog items to be duplicated using SKUs from df as inputs.
    If there are more than 1 batch of the same item, meaning the item
    needs to be duplicated, hence added into the duplicate_catalog_items list.
    If there is only 1 batch of the item, add the item into the
    duplicate_catalog_items list to be duplicated if it is in stock. Otherwise,
    do not add it into the catalog_itmes list. 

    Args:
        df (pandas.DataFrame): Data frame of target XLSX.
        client (square.client): Instance of the Square API Client.

    Returns:
        duplicate_catalog_items (dict of (str, dict)): With SKU as keys and catalog item JSON responses ready to be duplicated as values.
        modify_catalog_items (dict of (str, dict)): With SKU as keys and catalog item JSON responses ready to be duplicated as values.
    """

    duplicate_catalog_items = {}
    modify_catalog_items = {}
    invalid_skus = []

    for _, row in df.iterrows():
        logger.info(str(int(row.SKU)))

        result = client.catalog.search_catalog_items(
            body={
                "text_filter": str(int(row.SKU)),
                "enabled_location_ids": [
                    LOCATION_ID
                ],
                "product_types": [
                    "REGULAR"
                ]
            }
        )

        if result.is_success():
            if 'items' in result.body:
                if len(result.body['items']) > 1:
                    # when there are more than 1 item returned in the result
                    duplicate_catalog_items.update(
                        {str(int(row.SKU)): result.body['items'][0]})
                    # duplication_needed.append(str(int(row.SKU)))
                else:
                    inventory_count = retrieve_inventory_count(
                        client, result.body['items'][0]['item_data']['variations'][0]['id'])

                    logger.info("==============================")
                    logger.info("inventory_count")
                    logger.info(inventory_count)
                    logger.info("==============================")

                    if inventory_count == 0:
                        # no need to duplicate this item
                        modify_catalog_items.update(
                            {str(int(row.SKU)): result.body['items'][0]})
                        # no_duplication_needed.append(str(int(row.SKU)))
                    elif inventory_count < 0:
                        # if inventory count is below 0, throw an error
                        logger.error(
                            f"{str(int(row.SKU))} has an inventory count of {inventory_count}")
                        logger.error(
                            "Inventory count is below 0, please fix.")
                        modify_catalog_items.update(
                            {str(int(row.SKU)): result.body['items'][0]})
                        # no_duplication_needed.append(str(int(row.SKU)))
                    else:
                        # if inventory count is greater than 0,
                        # then item still needs to be duplicated
                        duplicate_catalog_items.update(
                            {str(int(row.SKU)): result.body['items'][0]})
                        # duplication_needed.append(str(int(row.SKU)))
            else:
                invalid_skus.append(str(int(row.SKU)))
        elif result.is_error():
            for error in result.errors:
                logger.error(error['category'])
                logger.error(error['code'])
                logger.error(error['detail'])
            exit()

    if invalid_skus:
        logger.error(
            "The following SKUs are invalid (do not exist in Square Item Catalog):")
        logger.error(invalid_skus)
        logger.error("Terminating the program before duplication...")
        exit()

    logger.info("==============================")
    logger.info("len(df.SKU.tolist())")
    logger.info(len(df.SKU.tolist()))
    logger.info(df.SKU.tolist())
    logger.info("==============================")
    logger.info("len(duplicate_catalog_items)")
    logger.info(len(duplicate_catalog_items))
    logger.info(duplicate_catalog_items.keys())
    logger.info("==============================")
    logger.info("len(modify_catalog_items)")
    logger.info(len(modify_catalog_items))
    logger.info(modify_catalog_items.keys())
    logger.info("==============================")

    return duplicate_catalog_items, modify_catalog_items


def retrieve_inventory_count(client, item_variation_id):
    """Retrieve inventory count given item variation ID

    Args:
        client (square.client): Instance of the Square API Client.
        item_variation_id (str): Item variation ID

    Returns:
        inventory_count (int): Inventory count of the item variation.
    """

    result = client.inventory.retrieve_inventory_count(
        catalog_object_id=item_variation_id,
        location_ids=LOCATION_ID
    )

    if result.is_success():
        # logger.info(result.body)
        if 'counts' in result.body:
            return int(result.body['counts'][0]['quantity'])
        else:
            logger.error(
                "'counts' does not exist in result.body, unable to retrieve quantity.")
            logger.error("Terminating the program before duplication...")
            exit()

    elif result.is_error():
        for error in result.errors:
            logger.error(error['category'])
            logger.error(error['code'])
            logger.error(error['detail'])
        exit()


def cleanse_catalog_items(df, duplicate_catalog_items, modify_catalog_items):
    """Cleanse catalog items before batch duplication

    - Update existing IDs to "#uuid"
    - Update name by appending expiry date
    - Update expiry date in custom attributes
    - Update price

    Args:
        df (pandas.DataFrame): Data frame of target XLSX.
        duplicate_catalog_items (dict of (str, dict)): With SKU as keys and catalog item JSON responses ready to be duplicated as values.
        modify_catalog_items (dict of (str, dict)): With SKU as keys and catalog item JSON responses ready to be duplicated as values.

    Returns:
        cleansed_catalog_items (dict of (str, dict)): With SKU as keys and cleansed catalog item JSON responses ready to be duplicated/modified as values.
    """

    if len(df.index) != len(duplicate_catalog_items) + len(modify_catalog_items):
        logger.error("Item counts from Excel and Catalog are different.")
        logger.error("Item counts do not add up, please check manually.")
        logger.error("Terminating the program before duplication...")
        exit()

    duplicate_catalog_items_flag = False
    modify_catalog_items_flag = True

    # index = 0
    if duplicate_catalog_items_flag:
        for sku, catalog_item in duplicate_catalog_items.items():
            # while str(df.iloc[index]['SKU'].astype(int)) in no_duplication_needed:
            #     index += 1

            # logger.info(str(df.iloc[index]['SKU'].astype(int)))
            logger.info(sku)
            current_df_row = df[df['SKU'] == int(sku)]

            # sku = catalog_item['item_data']['variations'][0]['item_variation_data']['sku']

            # check if the current iterated SKU in df
            # is the same as SKU in catalog_item
            # if str(df.iloc[index]['SKU'].astype(int)) != sku:
            #     logger.error(
            #         f"Current iterated SKUs are not the same at index {index}, please check manually.")
            #     logger.error("str(df.iloc[index]['SKU'].astype(int))")
            #     logger.error(str(df.iloc[index]['SKU'].astype(int)))
            #     logger.error("sku")
            #     logger.error(sku)
            #     logger.error("Terminating the program before duplication...")
            #     exit()

            # change IDs to #uuid to create new item
            # instead of upserting existing item
            catalog_item['id'] = "#" + str(uuid.uuid1())

            # looping through variations in case the item
            # has multiple variations
            for variation in catalog_item['item_data']['variations']:
                variation['id'] = "#" + str(uuid.uuid1())
                del variation['item_variation_data']['item_id']

                if 'stockable_conversion' in variation['item_variation_data']:
                    variation['item_variation_data']['stockable_conversion'][
                        'stockable_item_variation_id'] = catalog_item['item_data']['variations'][0]['id']

            expiry_date_string = str(current_df_row['Expiry Date'].iloc[0])
            # update item name
            name = catalog_item['item_data']['name']
            catalog_item['item_data']['name'] = name + expiry_date_string

            # update item expiry date
            if 'custom_attribute_values' in catalog_item:
                # when there are more than 1 variation
                # custom_attribute_values is isolated out
                # placed right under catalog_item
                catalog_item['custom_attribute_values'][EXPIRY_DATE_CUSTOM_ATTRIBUTE_KEY]['number_value'] = expiry_date_string
            elif 'custom_attribute_values' in catalog_item['item_data']['variations'][0]:
                # when there is only 1 variation
                # custom_attribute_values is placed under variations
                catalog_item['item_data']['variations'][0]['custom_attribute_values'][
                    EXPIRY_DATE_CUSTOM_ATTRIBUTE_KEY]['number_value'] = expiry_date_string
            else:
                logger.error(
                    "No custom attributes have been set up yet for this item before. Creating an custom attribute object to insert into the catalog item object")

                variation_count = retrieve_variation_count(catalog_item)
                if variation_count == 1:
                    catalog_item['item_data']['variations'][0].update(
                        create_expiry_date_custom_attribute_object(expiry_date_string))
                else:
                    logger.info(
                        f"{sku} has more than 1 variation.")
                    catalog_item.update(
                        create_expiry_date_custom_attribute_object(expiry_date_string))

            # update item price
            logger.info(str(current_df_row['Price'].iloc[0]))
            price_string = str(current_df_row['Price'].iloc[0])
            price_string_split = price_string.split('.')
            if len(price_string_split) == 2:
                # when there is decimal in place
                if len(price_string_split[1]) == 2:
                    price = int(price_string.replace('.', ''))
                elif len(price_string_split[1]) == 1:
                    price = int(price_string.replace('.', '') + "0")
                else:
                    logger.error(
                        "Price numbers after the decimal place are incorrect.")
                    logger.error(
                        "Terminating the program before duplication...")
                    exit()
            elif len(price_string_split) == 1:
                # when there is no decimal in place
                price = int(price_string.replace('.', '') + "00")
            else:
                # when there are more than 1 decimal
                logger.error(
                    "There are more than 1 decimal detected, please fix.")
                logger.error("Terminating the program before duplication...")
                exit()

            catalog_item['item_data']['variations'][0]['item_variation_data']['price_money']['amount'] = price

            # logger.info(catalog_item)

            # index += 1

    if modify_catalog_items_flag:
        for sku, catalog_item in modify_catalog_items.items():
            logger.info(sku)
            current_df_row = df[df['SKU'] == int(sku)]
            expiry_date_string = str(current_df_row['Expiry Date'].iloc[0])
            logger.error(type(expiry_date_string))

            # update item expiry date
            if 'custom_attribute_values' in catalog_item:
                # when there are more than 1 variation
                # custom_attribute_values is isolated out
                # placed right under catalog_item
                catalog_item['custom_attribute_values'][EXPIRY_DATE_CUSTOM_ATTRIBUTE_KEY]['number_value'] = expiry_date_string
            elif 'custom_attribute_values' in catalog_item['item_data']['variations'][0]:
                # when there is only 1 variation
                # custom_attribute_values is placed under variations
                catalog_item['item_data']['variations'][0]['custom_attribute_values'][
                    EXPIRY_DATE_CUSTOM_ATTRIBUTE_KEY]['number_value'] = expiry_date_string
            else:
                logger.error(
                    "No custom attributes have been set up yet for this item before. Creating an custom attribute object to insert into the catalog item object")

                variation_count = retrieve_variation_count(catalog_item)
                if variation_count == 1:
                    catalog_item['item_data']['variations'][0].update(
                        create_expiry_date_custom_attribute_object(expiry_date_string))
                else:
                    logger.info(
                        f"{sku} has more than 1 variation.")
                    catalog_item.update(
                        create_expiry_date_custom_attribute_object(expiry_date_string))

            # update item price
            logger.info(str(current_df_row['Price'].iloc[0]))
            price_string = str(current_df_row['Price'].iloc[0])
            price_string_split = price_string.split('.')
            if len(price_string_split) == 2:
                # when there is decimal in place
                if len(price_string_split[1]) == 2:
                    price = int(price_string.replace('.', ''))
                elif len(price_string_split[1]) == 1:
                    price = int(price_string.replace('.', '') + "0")
                else:
                    logger.error(
                        "Price numbers after the decimal place are incorrect.")
                    logger.error(
                        "Terminating the program before duplication...")
                    exit()
            elif len(price_string_split) == 1:
                # when there is no decimal in place
                price = int(price_string.replace('.', '') + "00")
            else:
                # when there are more than 1 decimal
                logger.error(
                    "There are more than 1 decimal detected, please fix.")
                logger.error("Terminating the program before duplication...")
                exit()

            catalog_item['item_data']['variations'][0]['item_variation_data']['price_money']['amount'] = price

            logger.info(catalog_item)

    if duplicate_catalog_items_flag and modify_catalog_items_flag:
        duplicate_catalog_items.update(modify_catalog_items)
        return duplicate_catalog_items
    elif modify_catalog_items_flag and not duplicate_catalog_items_flag:
        return modify_catalog_items
    else:
        return duplicate_catalog_items


def retrieve_variation_count(catalog_item):
    """Retrieve variation count given catalog item object

    Args:
        catalog_items (list of catalog_items): List of catalog item JSON responses.

    Returns:
        variation_count (int): Variation count of the catalog item.
    """

    return len(catalog_item['item_data']['variations'])


def create_expiry_date_custom_attribute_object(expiry_date):
    """Create expiry date custom attribute object given the expiry date

    Args:
        expiry_date (str): Expiry date in the form of YYYYMMDD.

    Returns:
        expiry_date_custom_attribute (dict): Dictionary of custom attribute values.
    """

    return {"custom_attribute_values": {
        EXPIRY_DATE_CUSTOM_ATTRIBUTE_KEY: {
            "name": "expiry-date",
            "custom_attribute_definition_id": EXPIRY_DATE_CUSTOM_ATTRIBUTE_DEFINITION_ID,
            "type": "NUMBER",
            "number_value": expiry_date,
            "key": EXPIRY_DATE_CUSTOM_ATTRIBUTE_KEY
        }
    }}


def batch_upsert_catalog_objects(client, cleansed_catalog_items):
    """Batch upsert/create catalog objects given the cleansed catalog items

    Args:
        client (square.client): Instance of the Square API Client.
        cleansed_catalog_items (list of catalog_items): List of catalog item JSON responses that are cleansed.
    """

    result = client.catalog.batch_upsert_catalog_objects(
        body={
            "idempotency_key": str(uuid.uuid1()),
            "batches": [
                {
                    "objects": list(cleansed_catalog_items.values())
                }
            ]
        }
    )

    if result.is_success():
        logger.info(result.status_code)

    elif result.is_error():
        logger.error(result.errors)
        for error in result.errors:
            logger.error(error['category'])
            logger.error(error['code'])
            logger.error(error['detail'])
        exit()


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


if __name__ == "__main__":
    """ This is executed when run from the command line """

    parser = argparse.ArgumentParser()

    # Required positional argument
    parser.add_argument("args", help="Required positional argument")

    # Optional argument flag which defaults to False
    parser.add_argument("-f", "--flag", action="store_true", default=False)

    # Optional argument which requires a parameter (eg. -d test)
    parser.add_argument("-n", "--name", action="store", dest="name")

    # Optional verbosity counter (eg. -v, -vv, -vvv, etc.)
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Verbosity (-v, -vv, etc)")

    # Specify output of "--version"
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s (version {version})".format(version=__version__))

    args = parser.parse_args()
    main(args)
