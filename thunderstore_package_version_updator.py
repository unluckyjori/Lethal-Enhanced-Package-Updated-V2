import argparse
import json
import time
import requests
from packaging import version


class ThunderStorePackage:
    def __init__(self, namespace, name, previous_version):
        self.namespace = namespace
        self.name = name
        self.updated_version = None
        self.previous_version = previous_version

    def __repr__(self):
        return f"ThunderStorePackage(namespace={self.namespace}, name={self.name}, version={self.updated_version})"


expected_package_list_file_name = "package_list.txt"
updated_package_list_file_name = "updated_package_list.txt"
error_return_key_from_thunderstore = "ERROR"

important_keys = ["Core", "Cosmetics", "Cosmos", "Extras"]

core_list = []
cosmetics_list = []
cosmos_list = []
extras_list = []

sections = {
    "Core": core_list,
    "Cosmetics": cosmetics_list,
    "Cosmos": cosmos_list,
    "Extras": extras_list
}

spaces_per_package_indent = 10


def parse_package_file(input_file_name=expected_package_list_file_name):
    with open(input_file_name, "r") as file:
        data = file.read().replace("\n", "").replace(" ", "")
        file.close()
        validate_important_keys_in_package_file(data)
        populate_maps(data)


def populate_list(list, packages):
    for package in packages:
        namespace, name, version = package.split("-")
        list.append(
            ThunderStorePackage(namespace.replace(" ", "").replace("\t", ""),
                                name.replace(" ", "").replace("\t", ""),
                                version))


def populate_maps(data):
    for key, list in sections.items():
        start = data.find(key) + len(key)
        end = data.find("Cosmetics") if key == "Core" else data.find("Cosmos") if key == "Cosmetics" else data.find(
            "Extras") if key == "Cosmos" else None
        packages = data[start:end].replace('"', "").split(",") if end else data[start:].replace('"', "").split(",")
        populate_list(list, packages)


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


def update_package_version(package, server_delay):
    package.version = get_thunderstore_package_latest_version(package.namespace, package.name)
    time.sleep(server_delay)


def print_package_update_status(package):
    if error_return_key_from_thunderstore not in package.version:
        package_info = f"{package.namespace}-{package.name}"
        if version.parse(package.version) > version.parse(package.previous_version):
            # print updated message
            print(f"{package_info:<40} - ✅ Updated! - {package.previous_version} -> {package.version}")
        else:
            # print not updated message
            print(f"{package_info:<40} - {package.name} - {package.version}")
    else:
        # print error message
        print(f"{package.namespace} - {package.name} - ❌ Error: {package.version}")


def update_all_packages(server_delay=0):
    for section_key, section_list in sections.items():
        print(f"Updating packages in section: {section_key}")
        for package in section_list:
            update_package_version(package, server_delay)
            print_package_update_status(package)


def write_packages_to_file(output_file_name=updated_package_list_file_name):
    with open(output_file_name, "w") as file:
        for key, list in sections.items():
            file.write(key + "\n")
            for package in list:
                line = "{}{}{}".format(" " * spaces_per_package_indent,
                                       f'"{package.namespace}-{package.name}-{package.version}"',
                                       "," if package != list[-1] else "")
                file.write(line + "\n")
            file.write("\n\n")
    file.close()
    print(f"Updated package list written to file: {output_file_name}")


def parse_arguments():
    parser = argparse.ArgumentParser(description='Update packages.')
    parser.add_argument('--server_delay', type=int, default=0,
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
