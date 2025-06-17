import os
package_dir = "apb_spatial_computer_vision"
docs_dir = os.path.dirname(__file__)
api_dir=os.path.join(docs_dir,'api')
os.makedirs(api_dir,exist_ok=True)

modules = [f[:-3] for f in os.listdir(package_dir) if f.endswith(".py") and f != "__init__.py"]


for module in modules:
    with open(os.path.join(api_dir, f"{module}.md"), "w") as f:
        f.write("# API Reference\n\n")
        f.write(f"## {module}\n\n")
        f.write(f"::: {package_dir}.{module}\n\n")

