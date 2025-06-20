import json
import os
import subprocess
import sys

UPDATED_LIST_FILE = "updated_package_list.txt"

SECTION_TO_FOLDER = {
    "Core": "core",
    "Cosmetics": "cosmetic",
    "Cosmos": "cosmos",
    "Extras": "extra",
}

SECTION_ALIASES = {k.lower(): k for k in SECTION_TO_FOLDER}


def parse_updated_package_list(path=UPDATED_LIST_FILE):
    result = {k: [] for k in SECTION_TO_FOLDER}
    current = None
    if not os.path.isfile(path):
        print(f"Updated package list not found: {path}")
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
    subprocess.run([sys.executable, "thunderstore_package_version_updator.py"])


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
