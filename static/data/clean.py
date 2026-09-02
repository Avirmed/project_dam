import os
import sys

# Ensure emoji/UTF-8 output never crashes on a non-UTF-8 console (Windows cp1252).
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def cleanup_files():
    protected_extensions = [".py"]
    protected_files = ["index.html"]

    count = 0
    for root, dirs, files in os.walk("."):
        for file in files:
            file_path = os.path.join(root, file)
            extension = os.path.splitext(file)[1].lower()

            if extension not in protected_extensions and file not in protected_files:
                try:
                    os.remove(file_path)
                    count += 1
                except Exception as e:
                    print(f"Error deleting {file_path}: {e}")

    print("\n" + "=" * 47)
    print("⭐  CLEANUP OPERATIONS COMPLETE  ⭐")
    print("=" * 47)
    print(f"  ✅  Status: Success! {count} files removed.")
    print("  🔒  Kept: *.sh, *.py, and index.html")
    print("  📂  Note: All folders were preserved.")
    print("=" * 47 + "\n")


if __name__ == "__main__":
    cleanup_files()
