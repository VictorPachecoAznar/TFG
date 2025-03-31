import os
import pydoc

def generate_docs(package_path):
    for root, dirs, files in os.walk(package_path):
        for file in files:
            if file.endswith(".py"):
                module_path = os.path.join(root, file)
                module_name = module_path.replace(os.sep, ".").replace(".py", "")
                pydoc.writedoc(module_name)

generate_docs("C:\dev\TFG\package")