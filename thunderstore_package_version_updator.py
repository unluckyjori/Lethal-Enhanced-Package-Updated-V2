import argparse
import time

import requests
import json


class ThunderStorePackage:
    def __init__(self, namespace, name):
        self.namespace = namespace
        self.name = name
        self.version = None

    def __repr__(self):
        return f"ThunderStorePackage(namespace={self.namespace}, name={self.name}, version={self.version})"


expected_package_list_file_name = "package_list.txt"
updated_package_list_file_name = "updated_package_list.txt"
longest_package_name = 0

important_keys = ["Core", "Cosmetics", "Cosmos", "Extras"]

core_map = {}
cosmetics_map = {}
cosmos_map = {}
extras_map = {}

sections = {
    "Core": core_map,
    "Cosmetics": cosmetics_map,
    "Cosmos": cosmos_map,
    "Extras": extras_map
}

spaces_per_package_indent = 10


def parse_package_file(input_file_name=expected_package_list_file_name):
    with open(input_file_name, "r") as file:
        data = file.read().replace("\n", "").replace(" ", "")
        file.close()
        validate_important_keys_in_package_file(data)
        populate_maps(data)


def populate_map(map, packages):
    global longest_package_name
    for package in packages:
        # get the namespace and package name and store its length
        longest_package_name = len(package) if len(package) > longest_package_name else longest_package_name
        namespace, name, version = package.split("-")
        if namespace not in map:
            map[namespace] = []
        map[namespace].append(
            ThunderStorePackage(namespace.replace(" ", "").replace("\t", ""), name.replace(" ", "").replace("\t", "")))


def populate_maps(data):
    for key, map in sections.items():
        start = data.find(key) + len(key)
        end = data.find("Cosmetics") if key == "Core" else data.find("Cosmos") if key == "Cosmetics" else data.find(
            "Extras") if key == "Cosmos" else None
        packages = data[start:end].replace('"', "").split(",") if end else data[start:].replace('"', "").split(",")
        populate_map(map, packages)


def validate_important_keys_in_package_file(data):
    for key in important_keys:
        if key not in data:
            raise Exception(f"Key '{key}' not found in package file!")
    print("All important keys found in package file! Keys: {}\n".format(important_keys))


def get_thunderstore_package_latest_version(namespace, name):
    url = f"https://thunderstore.io/api/experimental/package/{namespace}/{name}/"
    response = requests.get(url)
    if response.status_code == 200:
        return json.loads(response.text)["latest"]["version_number"]
    return "ERROR - namespace / package name doesn't exist?"


def update_all_packages(server_delay=1):
    for section_key, section_map in sections.items():
        print(f"Updating packages in section: {section_key}")
        for packages in section_map.values():
            for package in packages:
                # align the output
                package_info = f"{package.namespace}-{package.name}".ljust(longest_package_name + 2)
                print(package_info, end="")
                package.version = get_thunderstore_package_latest_version(package.namespace, package.name)
                print("{}".format(
                    f"✅ - {package.version}" if "ERROR" not in package.version else f"❌ - {package.version}",
                    end="\n"))
                # add delay to not spam the server
                time.sleep(server_delay)


def write_packages_to_file(output_file_name=updated_package_list_file_name):
    with open(output_file_name, "w") as file:
        for key, map in sections.items():
            length_of_map = calculate_total_items_in_map(map)
            write_count = 0
            file.write(key + "\n")
            for namespace, packages in map.items():
                for package in packages:
                    write_count += 1
                    # if there is a single item in the package
                    line = "{}{}{}".format(" " * spaces_per_package_indent,
                                           f'"{package.namespace}-{package.name}-{package.version}"',
                                           "," if write_count != length_of_map else "")
                    file.write(line + "\n")
            file.write("\n\n")
    file.close()
    print(f"Updated package list written to file: {output_file_name}")


def calculate_total_items_in_map(map):
    total = 0
    for key, value in map.items():
        if len(value) > 0:
            total += len(value)
    return total


def parse_arguments():
    parser = argparse.ArgumentParser(description='Update packages.')
    parser.add_argument('--server_delay', type=int, default=1,
                        help='Delay between server requests in seconds')
    parser.add_argument('--output_file_name', type=str, default='updated_package_list.txt',
                        help='Name of the output file')
    parser.add_argument('--input_file_name', type=str, default='package_list.txt',
                        help='Name of the input file')
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_arguments()
    server_delay = args.server_delay
    output_file_name = args.output_file_name
    input_file_name = args.input_file_name

    # print the data in the file
    parse_package_file(input_file_name)
    update_all_packages(server_delay)
    write_packages_to_file(output_file_name)
    input("Script finished! Press any key to exit.")
