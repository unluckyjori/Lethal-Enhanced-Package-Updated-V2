import json
import os
import subprocess
import sys
import time
from typing import Dict, List

import requests
from packaging import version

PACKAGE_LIST_FILE = "package_list.txt"

SECTION_TO_FOLDER = {
    "Core": "core",
    "Cosmetics": "cosmetic",
    "Cosmos": "cosmos",
    "Extras": "extra",
}

SECTION_ALIASES = {k.lower(): k for k in SECTION_TO_FOLDER}


class ThunderStorePackage:
    def __init__(self, namespace: str, name: str, version_str: str):
        self.namespace = namespace
        self.name = name
        self.version = version_str

    def __repr__(self) -> str:
        return (
            f"ThunderStorePackage(namespace={self.namespace}, "
            f"name={self.name}, version={self.version})"
        )


def parse_package_list_for_update(path: str = PACKAGE_LIST_FILE) -> Dict[str, List[ThunderStorePackage]]:
    result: Dict[str, List[ThunderStorePackage]] = {k: [] for k in SECTION_TO_FOLDER}
    current_section = None
    if not os.path.isfile(path):
        print(f"Package list not found: {path}")
        return result
    with open(path, "r") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            key_lower = line.rstrip(":").lower()
            if key_lower in SECTION_ALIASES:
                current_section = SECTION_ALIASES[key_lower]
                result.setdefault(current_section, [])
            else:
                if current_section is None:
                    continue
                pkg = line.strip(',').strip('"')
                if not pkg:
                    continue
                parts = pkg.split("-")
                if len(parts) < 3:
                    continue
                namespace, name = parts[0], parts[1]
                version_str = "-".join(parts[2:])
                result[current_section].append(
                    ThunderStorePackage(namespace, name, version_str)
                )
    return result


def write_packages_to_file(sections_map: Dict[str, List[ThunderStorePackage]], path: str = PACKAGE_LIST_FILE) -> None:
    with open(path, "w") as file:
        for section, packages in sections_map.items():
            file.write(f"{section}\n")
            for idx, pkg in enumerate(packages):
                comma = "," if idx < len(packages) - 1 else ""
                line = (
                    f"{' ' * 10}\"{pkg.namespace}-{pkg.name}-{pkg.version}\"{comma}"
                )
                file.write(line + "\n")
            file.write("\n\n")


def get_thunderstore_package_latest_version(namespace: str, name: str) -> str:
    url = f"https://thunderstore.io/api/experimental/package/{namespace}/{name}/"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()["latest"]["version_number"]
    return "ERROR"


def update_package_version(pkg: ThunderStorePackage, delay: int) -> None:
    pkg.version = get_thunderstore_package_latest_version(pkg.namespace, pkg.name)
    time.sleep(delay)


def print_package_update_status(pkg: ThunderStorePackage, previous_version: str) -> None:
    if pkg.version != "ERROR":
        pkg_info = f"{pkg.namespace}-{pkg.name}"
        if version.parse(pkg.version) > version.parse(previous_version):
            print(f"{pkg_info:<40} - \u2705 Updated! - {previous_version} -> {pkg.version}")
        else:
            print(f"{pkg_info:<40} - {pkg.name} - {pkg.version}")
    else:
        print(f"{pkg.namespace} - {pkg.name} - \u274C Error")


def update_all_packages(delay: int = 0, path: str = PACKAGE_LIST_FILE) -> None:
    sections_map = parse_package_list_for_update(path)
    for section, packages in sections_map.items():
        print(f"Updating packages in section: {section}")
        for pkg in packages:
            prev_version = pkg.version
            update_package_version(pkg, delay)
            print_package_update_status(pkg, prev_version)
    write_packages_to_file(sections_map, path)


def parse_updated_package_list(path=PACKAGE_LIST_FILE):
    result = {k: [] for k in SECTION_TO_FOLDER}
    current = None
    if not os.path.isfile(path):
        print(f"Package list not found: {path}")
        return result
    with open(path, "r") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            key_lower = line.rstrip(":").lower()
            if key_lower in SECTION_ALIASES:
                current = SECTION_ALIASES[key_lower]
                # ensure list exists
                result.setdefault(current, [])
            else:
                if current is None:
                    continue
                pkg = line.strip(',').strip('"')
                if pkg:
                    result[current].append(pkg)
    return result


def update_dependencies(section_packages):
    for section, packages in section_packages.items():
        folder = SECTION_TO_FOLDER.get(section)
        if not folder:
            continue
        manifest_path = os.path.join(folder, "manifest.json")
        if not os.path.isfile(manifest_path):
            print(f"Manifest not found for section {section}: {manifest_path}")
            continue
        with open(manifest_path, "r") as mf:
            data = json.load(mf)
        data["dependencies"] = packages
        with open(manifest_path, "w") as mf:
            json.dump(data, mf, indent=4)
            mf.write("\n")
        print(f"Updated dependencies for {section} -> {manifest_path}")


def run_update_mods():
    try:
        delay = int(input("Delay between server requests in seconds (0 for none): ").strip() or "0")
    except ValueError:
        delay = 0
    update_all_packages(delay, PACKAGE_LIST_FILE)


def distribute_lists():
    packages = parse_updated_package_list()
    update_dependencies(packages)


def menu():
    prompt = (
        "What action do you want to perform?\n"
        "1: Update mods\n"
        "2: Distribute the list to each folder\n"
        "3: Both\n"
        "4: Exit\n"
    )
    while True:
        choice = input(prompt).strip()
        if choice == "1":
            run_update_mods()
        elif choice == "2":
            distribute_lists()
        elif choice == "3":
            run_update_mods()
            distribute_lists()
        elif choice == "4":
            print("Exiting...")
            break
        else:
            print("Invalid choice, try again.\n")


if __name__ == "__main__":
    menu()
