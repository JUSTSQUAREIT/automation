from square.client import Client

# Create an instance of the API Client
# and initialize it with the credentials
# for the Square account whose assets you want to manage

client = Client(
    access_token='EAAAEHPWeUfUN-78ZpMUX4CSpzVC8v7YhaFYzeYn4K2ql8TXM4_8HTWBJrGS2QYU',
    environment='production',
)

# Get an instance of the Square API you want call
api_locations = client.locations

# Call list_locations method to get all locations in this Square account
result = api_locations.list_locations()
# Call the success method to see if the call succeeded
if result.is_success():
        # The body property is a list of locations
    locations = result.body['locations']
    # Iterate over the list
    for location in locations:
        # Each location is represented as a dictionary
        for key, value in location.items():
            print("{} : {}".format(key, value))
        print("\n")
# Call the error method to see if the call failed
elif result.is_error():
    print('Error calling LocationsApi.listlocations')
    errors = result.errors
    # An error is returned as a list of errors
    for error in errors:
        # Each error is represented as a dictionary
        for key, value in error.items():
            print("{} : {}".format(key, value))
        print("\n")
