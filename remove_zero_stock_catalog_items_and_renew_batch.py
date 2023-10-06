#!/usr/bin/env python3
"""
Module Docstring
"""

__author__ = "JUSTSQUAREIT Canada Co."
__version__ = "0.1.0"
__license__ = "MIT"

import uuid
import argparse
from logzero import logger
from square.client import Client


ACCESS_TOKEN = "EAAAEHPWeUfUN-78ZpMUX4CSpzVC8v7YhaFYzeYn4K2ql8TXM4_8HTWBJrGS2QYU"
ENVIRONMENT = "production"
LOCATION_ID = "LB5F8WYCHXM5V"


def main(args):
    """ Main entry point of the app """
    logger.info("hello world")
    logger.info(args.args)

    square_api_client = create_square_api_client()

    stock_out_catalog_item_names = search_stock_out_catalog_items(
        square_api_client)
    logger.info(len(stock_out_catalog_item_names))

    stock_out_catalog_items_with_batches = search_stock_out_catalog_items_with_batches(
        square_api_client, stock_out_catalog_item_names)
    logger.info(stock_out_catalog_items_with_batches)
    logger.info(len(stock_out_catalog_items_with_batches))

    # we assume stock out catalog items ALL have 0 inventory
    # instead of negative inventory for now.
    # add_oversold_inventory_to_next_batch(
    #     square_api_client, stock_out_catalog_items_with_batches)

    # upsert_second_batch_catalog_item_names(
    #     square_api_client, stock_out_catalog_items_with_batches)

    # batch_delete_stock_out_catalog_items(
    #     square_api_client, stock_out_catalog_items_with_batches)


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


def search_stock_out_catalog_items(client):
    """Search 0 stock catalog items

    Invoke the search_catalog_items endpoint in the Catalog API to retrieve catalog items that are sold out.

    Args:
        client (square.client): Instance of the Square API Client.

    Returns:
        zero_stock_catalog_item_names (list of str): List of names of catalog items that are sold out.
    """

    zero_stock_catalog_item_names = []
    result = client.catalog.search_catalog_items(
        body={
            "stock_levels": [
                "OUT"
            ],
            "enabled_location_ids": [
                LOCATION_ID
            ],
            "product_types": [
                "REGULAR"
            ]
        }
    )

    if result.is_success():
        cursor = result.cursor

        for item in result.body['items']:
            # print(f"ID: {cust['id']}: ", end="")
            # logger.info(item['item_data']['name'])
            zero_stock_catalog_item_names.append(item['item_data']['name'])

        while cursor:
            result = client.catalog.search_catalog_items(
                body={
                    "stock_levels": [
                        "OUT"
                    ],
                    "enabled_location_ids": [
                        "LB5F8WYCHXM5V"
                    ],
                    "cursor": cursor,
                    "product_types": [
                        "REGULAR"
                    ]
                }
            )

            cursor = result.cursor

            for item in result.body['items']:
                # print(f"ID: {cust['id']}: ", end="")
                # logger.info(item['item_data']['name'])
                zero_stock_catalog_item_names.append(item['item_data']['name'])

    elif result.is_error():
        for error in result.errors:
            logger.error(error['category'])
            logger.error(error['code'])
            logger.error(error['detail'])

    return zero_stock_catalog_item_names


def search_stock_out_catalog_items_with_batches(client, zero_stock_catalog_item_names):
    """Search 0 stock catalog items with batches

    Invoke the search_catalog_objects endpoint in the Catalog API to check if zero_stock_catalog_item_names have upcoming batches in place. If so, store their first batch object IDs as the dict keys, and store their second batch object IDs as the dict values.

    Args:
        client (square.client): Instance of the Square API Client.
        zero_stock_catalog_item_names (list of str): List of names of catalog items that are sold out.

    Returns:
        zero_stock_catalog_items_with_batches (dict of (int, int)): The return value. First batch object IDs as the dict keys, and second batch object IDs as the dict values.
    """

    zero_stock_catalog_items_with_batches = {}
    for zero_stock_catalog_item_name in zero_stock_catalog_item_names:
        result = client.catalog.search_catalog_objects(
            body={
                "object_types": [
                    "ITEM"
                ],
                "include_deleted_objects": False,
                "include_related_objects": False,
                "query": {
                    "prefix_query": {
                        "attribute_name": "name",
                        "attribute_prefix": zero_stock_catalog_item_name
                    }
                }
            }
        )

        if result.is_success():
            # print(f"ID: {cust['id']}: ", end="")
            if len(result.body['objects']) > 1:
                for item in result.body['objects']:
                    logger.info(item['item_data']['name'])
                logger.info("==========")
                zero_stock_catalog_items_with_batches[result.body['objects']
                                                      [0]['id']] = result.body['objects'][1]['id']

        elif result.is_error():
            for error in result.errors:
                logger.error(error['category'])
                logger.error(error['code'])
                logger.error(error['detail'])

    return zero_stock_catalog_items_with_batches


def add_oversold_inventory_to_next_batch(client, zero_stock_catalog_items_with_batches):
    """Add oversold inventory to next batch if any

    Invoke the retrieve_catalog_object endpoint in the Catalog API to get the second batch object. And then remove the expiry dates from the item name. Finally, invoke the upsert_catalog_object endpoint with the modified object to update the item name.

    Args:
        client (square.client): Instance of the Square API Client.
        zero_stock_catalog_items_with_batches (dict of (int, int)): First batch object IDs as the dict keys, and second batch object IDs as the dict values.
    """
    return


def upsert_second_batch_catalog_item_names(client, zero_stock_catalog_items_with_batches):
    """Remove expiry date from second batch catalog item names

    Invoke the retrieve_catalog_object endpoint in the Catalog API to get the second batch object. And then remove the expiry dates from the item name. Finally, invoke the upsert_catalog_object endpoint with the modified object to update the item name.

    Args:
        client (square.client): Instance of the Square API Client.
        zero_stock_catalog_items_with_batches (dict of (int, int)): First batch object IDs as the dict keys, and second batch object IDs as the dict values.
    """

    for second_batch_object_id in zero_stock_catalog_items_with_batches.values():
        result = client.catalog.retrieve_catalog_object(
            object_id=second_batch_object_id,
            include_related_objects=False
        )

        if result.is_success():
            logger.info(result.body['object']['item_data']['name'])
            result.body['object']['item_data']['name'] = result.body['object']['item_data']['name'][:-8]
            logger.info(result.body['object']['item_data']['name'])

            result = client.catalog.upsert_catalog_object(
                body={
                    "idempotency_key": str(uuid.uuid1()),
                    "object": result.body['object']
                }
            )

            if result.is_success():
                logger.info(result.status_code)

            elif result.is_error():
                for error in result.errors:
                    logger.error(error['category'])
                    logger.error(error['code'])
                    logger.error(error['detail'])

        elif result.is_error():
            for error in result.errors:
                logger.error(error['category'])
                logger.error(error['code'])
                logger.error(error['detail'])


def batch_delete_stock_out_catalog_items(client, zero_stock_catalog_items_with_batches):
    """Delete zero stock catalog items

    Invoke the batch_delete_catalog_objects endpoint in the Catalog API to delete the zero stock catalog items.

    Args:
        client (square.client): Instance of the Square API Client.
        zero_stock_catalog_items_with_batches (dict of (int, int)): First batch object IDs as the dict keys, and second batch object IDs as the dict values.
    """

    continue_or_exit(message)

    result = client.catalog.batch_delete_catalog_objects(
        body={
            "object_ids": list(zero_stock_catalog_items_with_batches.keys())
        }
    )

    if result.is_success():
        logger.info(result.status_code)

    elif result.is_error():
        for error in result.errors:
            logger.error(error['category'])
            logger.error(error['code'])
            logger.error(error['detail'])


def continue_or_exit(message):
    while True:
        if message:
            logger.info(message)
        answer = input("Do You Want To Continue? [y/n]: ")
        if answer != 'y':
            logger.info("Terminating program...")
            exit()
        else:
            logger.info("Continue...\n")
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
