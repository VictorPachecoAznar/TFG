import yaml
import os

MKDOCS_YML = "mkdocs.yml"
API_DIR = "docs/api"

def generate_api_nav():
    md_files = sorted(f for f in os.listdir(API_DIR) if f.endswith(".md"))
    api_nav = []

    for f in md_files:
        title = os.path.splitext(f)[0].replace("_", " ").capitalize()
        api_nav.append({title: f"api/{f}"})

    return api_nav

def update_nav():
    with open(MKDOCS_YML, "r") as f:
        config = yaml.safe_load(f)

    config["nav"] = [entry for entry in config["nav"] if "API" not in entry]

    config["nav"].append({"API": generate_api_nav()})

    with open(MKDOCS_YML, "w") as f:
        yaml.dump(config, f, sort_keys=False)

if __name__ == "__main__":
    update_nav()