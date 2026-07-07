import os
import glob

folders = ["models", "routes"]


def create_init_files():
    for folder in folders:
        os.makedirs(folder, exist_ok=True)
        init_path = os.path.join(folder, "__init__.py")
        if not os.path.exists(init_path):
            with open(init_path, "w") as f:
                f.write("")
            print(f"✅ Created: {init_path}")


def generate_dynamic_imports(folder):
    module_files = glob.glob(os.path.join(folder, "*.py"))
    modules = [
        os.path.basename(f)[:-3]
        for f in module_files
        if os.path.isfile(f) and not f.endswith("__init__.py")
    ]

    init_path = os.path.join(folder, "__init__.py")
    with open(init_path, "w") as f:
        f.write(f"__all__ = {modules}\n\n")

        for module in modules:
            if folder == "routes":
                f.write(f"from .{module} import {module}_bp\n")
            else:
                f.write(f"from .{module} import *\n")

    print(f"✅ Updated imports in: {init_path}")


if __name__ == "__main__":
    create_init_files()
    for folder in folders:
        generate_dynamic_imports(folder)
    print("🚀 All __init__.py files are ready!")
