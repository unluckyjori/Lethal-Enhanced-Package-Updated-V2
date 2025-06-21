import json
import os
import subprocess
import sys
import time
import uuid
import zipfile
import hashlib
import base64
from typing import Dict, List, Optional

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


def parse_mod_string(mod_str: str) -> Optional[ThunderStorePackage]:
    mod_str = mod_str.strip().strip('"')
    parts = mod_str.split("-")
    if len(parts) < 3:
        return None
    namespace, name = parts[0], parts[1]
    version_str = "-".join(parts[2:])
    return ThunderStorePackage(namespace, name, version_str)


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
    first_section = True
    for section, packages in sections_map.items():
        if not first_section:
            print()
        print(f"Updating packages in section: {section}")
        for pkg in packages:
            prev_version = pkg.version
            update_package_version(pkg, delay)
            print_package_update_status(pkg, prev_version)
        first_section = False
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
    settings = load_settings()
    try:
        delay = int(settings.get("server_delay", 1))
    except (ValueError, TypeError):
        delay = 1
    update_all_packages(delay, PACKAGE_LIST_FILE)
    print()


def distribute_lists():
    packages = parse_updated_package_list()
    update_dependencies(packages)
    print()


def add_mod() -> None:
    mod_str = input(
        "Enter full mod string (e.g. ScienceBird-Universal_Radar-1.0.6): "
    ).strip()
    mod_str = mod_str.strip().strip('"')
    if not mod_str:
        print("No mod provided.\n")
        return
    section_input = input(
        "Section (core/cosmos/cosmetic/extra): "
    ).strip().lower()
    section = SECTION_ALIASES.get(section_input)
    if not section:
        print("Invalid section.\n")
        return

    pkg_obj = parse_mod_string(mod_str)
    if pkg_obj is None:
        print("Invalid mod string format.\n")
        return

    sections_map = parse_package_list_for_update(PACKAGE_LIST_FILE)
    sections_map.setdefault(section, [])
    sections_map[section].append(pkg_obj)
    write_packages_to_file(sections_map, PACKAGE_LIST_FILE)

    folder = SECTION_TO_FOLDER.get(section)
    manifest_path = os.path.join(folder, "manifest.json")
    if os.path.isfile(manifest_path):
        with open(manifest_path, "r") as mf:
            data = json.load(mf)
        deps = data.get("dependencies", [])
        deps.append(mod_str)
        data["dependencies"] = deps
        with open(manifest_path, "w") as mf:
            json.dump(data, mf, indent=4)
            mf.write("\n")
        print(f"Added {mod_str} to {manifest_path}\n")
    else:
        print(f"Manifest not found for section {section}.\n")


def remove_mod() -> None:
    mod_str = input(
        "Enter full mod string (e.g. ScienceBird-Universal_Radar-1.0.6): "
    ).strip()
    mod_str = mod_str.strip().strip('"')
    if not mod_str:
        print("No mod provided.\n")
        return
    section_input = input(
        "Section (core/cosmos/cosmetic/extra): "
    ).strip().lower()
    section = SECTION_ALIASES.get(section_input)
    if not section:
        print("Invalid section.\n")
        return

    pkg_obj = parse_mod_string(mod_str)
    if pkg_obj is None:
        print("Invalid mod string format.\n")
        return

    sections_map = parse_package_list_for_update(PACKAGE_LIST_FILE)
    packages = sections_map.get(section, [])
    new_packages = [
        p for p in packages
        if not (
            p.namespace == pkg_obj.namespace
            and p.name == pkg_obj.name
            and p.version == pkg_obj.version
        )
    ]
    if len(new_packages) == len(packages):
        print("Mod not found in package list.\n")
        return

    sections_map[section] = new_packages
    write_packages_to_file(sections_map, PACKAGE_LIST_FILE)

    folder = SECTION_TO_FOLDER.get(section)
    manifest_path = os.path.join(folder, "manifest.json")
    if os.path.isfile(manifest_path):
        with open(manifest_path, "r") as mf:
            data = json.load(mf)
        deps = data.get("dependencies", [])
        new_deps = []
        removed = False
        for dep in deps:
            if dep.strip().strip('"') == mod_str:
                removed = True
                continue
            new_deps.append(dep)
        if removed:
            data["dependencies"] = new_deps
            with open(manifest_path, "w") as mf:
                json.dump(data, mf, indent=4)
                mf.write("\n")
            print(f"Removed {mod_str} from {manifest_path}\n")
    else:
        print(f"Manifest not found for section {section}.\n")


def load_settings(path: str = "settings.json") -> Dict[str, str]:
    if os.path.isfile(path):
        with open(path, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                pass
    return {}


def save_settings(settings: Dict[str, str], path: str = "settings.json") -> None:
    with open(path, "w") as f:
        json.dump(settings, f, indent=4)
        f.write("\n")


def settings_menu():
    prompt = (
        "Settings:\n"
        "1: Modify token\n"
        "2: Modify server delay\n"
        "3: Back\n\n"
    )
    while True:
        choice = input(prompt).strip()
        print()
        if choice == "1":
            token = input("Enter API token: ").strip()
            settings = load_settings()
            settings["token"] = token
            save_settings(settings)
            print("Token saved.\n")
        elif choice == "2":
            try:
                delay = int(input("Enter server delay in seconds: ").strip())
            except ValueError:
                print("Invalid delay.\n")
                continue
            settings = load_settings()
            settings["server_delay"] = delay
            save_settings(settings)
            print("Server delay saved.\n")
        elif choice == "3":
            break
        else:
            print("Invalid choice, try again.\n")


def update_manifest_versions(new_version: str) -> None:
    for folder in SECTION_TO_FOLDER.values():
        manifest_path = os.path.join(folder, "manifest.json")
        if not os.path.isfile(manifest_path):
            continue
        with open(manifest_path, "r") as mf:
            data = json.load(mf)
        data["version_number"] = new_version
        with open(manifest_path, "w") as mf:
            json.dump(data, mf, indent=4)
            mf.write("\n")


def zip_folders(output_dir: str = "packages") -> List[str]:
    os.makedirs(output_dir, exist_ok=True)
    zipped = []
    for folder in SECTION_TO_FOLDER.values():
        zip_path = os.path.join(output_dir, f"{folder}.zip")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, _, files in os.walk(folder):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, folder)
                    zf.write(file_path, arcname)
        zipped.append(zip_path)
    return zipped


def upload_packages(token: str, packages_dir: str = "packages") -> None:
    meta_url = "https://thunderstore.io/api/experimental/submission/submit/"

    for name in os.listdir(packages_dir):
        if not name.lower().endswith(".zip"):
            continue

        path = os.path.join(packages_dir, name)

        with zipfile.ZipFile(path, "r") as zf:
            with zf.open("manifest.json") as mf:
                manifest = json.load(mf)
            try:
                with zf.open("README.md") as rf:
                    readme = rf.read().decode("utf-8")
            except KeyError:
                readme = manifest.get("description", "")

        summary = readme.splitlines()[0] if readme else manifest.get("description", "")

        file_size = os.path.getsize(path)
        init_payload = {"filename": name, "file_size_bytes": file_size}
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        init_url = "https://thunderstore.io/api/experimental/usermedia/initiate-upload/"
        init_resp = requests.post(init_url, headers=headers, json=init_payload)
        if init_resp.status_code != 200:
            print(f"Failed to initiate upload for {name}: {init_resp.text}")
            continue

        init_data = init_resp.json()
        upload_uuid = init_data.get("usermedia", {}).get("uuid") or init_data.get("uuid")
        upload_urls = init_data.get("upload_urls") or init_data.get("usermedia", {}).get("upload_urls", [])
        parts = []

        with open(path, "rb") as fh:
            for part in upload_urls:
                part_num = part.get("part_number")
                offset = part.get("offset", 0)
                length = part.get("length")
                url = part.get("url")
                if url is None or length is None or part_num is None:
                    continue
                fh.seek(offset)
                data = fh.read(length)
                md5 = base64.b64encode(hashlib.md5(data).digest()).decode()
                put_headers = {"Content-MD5": md5}
                resp = requests.put(url, headers=put_headers, data=data)
                etag = resp.headers.get("ETag")
                if resp.status_code >= 300 or not etag:
                    print(f"Failed to upload part {part_num} for {name}: {resp.text}")
                    break
                parts.append({"ETag": etag, "PartNumber": part_num})

        finish_url = f"https://thunderstore.io/api/experimental/usermedia/{upload_uuid}/finish-upload/"
        finish_payload = {"parts": parts}
        finish_resp = requests.post(finish_url, headers=headers, json=finish_payload)
        if finish_resp.status_code != 200:
            print(f"Failed to finalize upload for {name}: {finish_resp.text}")
            continue

        metadata = {
            "upload_uuid": upload_uuid,
            "author_name": "lethal_coder",
            "communities": ["lethal-company"],
            "community_categories": {"lethal-company": ["modpacks"]},
            "has_nsfw_content": False,
            "package_name": manifest.get("name"),
            "version_number": manifest.get("version_number"),
            "platform": "windows",
            "package_type": "modpack",
            "package_summary": summary,
            "package_description": readme,
            "license": "MIT",
        }

        meta_resp = requests.post(meta_url, headers=headers, json=metadata)
        if meta_resp.status_code != 200:
            print(f"Failed to submit metadata for {name}: {meta_resp.text}")
            continue

        submission_id = meta_resp.json().get("submission_id")
        if not submission_id:
            print(f"No submission id for {name}")
            continue

        poll_headers = {"Authorization": f"Bearer {token}"}
        poll_url = f"https://thunderstore.io/api/experimental/submission/poll-async/{submission_id}/"

        while True:
            poll_resp = requests.get(poll_url, headers=poll_headers)
            if poll_resp.status_code != 200:
                print(f"Error polling {name}: {poll_resp.text}")
                break
            data = poll_resp.json()
            status = data.get("status")
            if status in {"Success", "Failed"}:
                print(f"{name} upload {status}")
                break
            time.sleep(5)


def run_upload():
    new_version = input("Enter new version number: ").strip()
    print()
    if not new_version:
        print("No version provided.\n")
        return
    update_manifest_versions(new_version)
    zip_folders()
    settings = load_settings()
    token = settings.get("token") or os.environ.get("THUNDERSTORE_TOKEN")
    if not token:
        print(
            "API token not found. Set it via settings or THUNDERSTORE_TOKEN env variable.\n"
        )
        return
    confirm = input("Proceed with upload? (y/n): ").strip().lower()
    print()
    if confirm != "y":
        print("Upload cancelled.\n")
        return
    upload_packages(token)
    print()


def run_all():
    run_update_mods()
    distribute_lists()
    new_version = input("Enter new version number: ").strip()
    print()
    if not new_version:
        print("No version provided.\n")
        return
    update_manifest_versions(new_version)
    zip_folders()
    settings = load_settings()
    token = settings.get("token") or os.environ.get("THUNDERSTORE_TOKEN")
    if not token:
        print(
            "API token not found. Set it via settings or THUNDERSTORE_TOKEN env variable.\n"
        )
        return
    confirm = input("Proceed with upload? (y/n): ").strip().lower()
    print()
    if confirm != "y":
        print("Upload cancelled.\n")
        return
    upload_packages(token)
    print()


def menu():
    prompt = (
        "What action do you want to perform?\n"
        "1: Update mods\n"
        "2: Distribute\n"
        "3: Add mod\n"
        "4: Remove mod\n"
        "5: Upload\n"
        "6: Settings\n"
        "7: All\n"
        "8: Exit\n\n"
    )
    while True:
        choice = input(prompt).strip()
        print()
        if choice == "1":
            run_update_mods()
        elif choice == "2":
            distribute_lists()
        elif choice == "3":
            add_mod()
        elif choice == "4":
            remove_mod()
        elif choice == "5":
            run_upload()
        elif choice == "6":
            settings_menu()
        elif choice == "7":
            run_all()
        elif choice == "8":
            print("Exiting...")
            break
        else:
            print("Invalid choice, try again.\n")


if __name__ == "__main__":
    menu()
