import os
import re

def rename_files(target_directory):
    # Regex pattern: matches a '.' NOT followed by 'json'
    pattern = r"\.(?!json)"
    
    for root, dirs, files in os.walk(target_directory):
        # Filter out hidden directories from the walk
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        
        for filename in files:
            # Skip hidden files
            if filename.startswith('.'):
                continue
                
            if re.search(pattern, filename):
                new_name = re.sub(pattern, "-", filename)
                
                old_path = os.path.join(root, filename)
                new_path = os.path.join(root, new_name)
                
                try:
                    # Check if destination already exists to avoid overwriting
                    if os.path.exists(new_path):
                        print(f"Skipping {filename}: {new_name} already exists.")
                        continue
                        
                    os.rename(old_path, new_path)
                    print(f"Renamed: {filename} -> {new_name}")
                except OSError as e:
                    print(f"Error renaming {filename}: {e}")

if __name__ == "__main__":
    # Ensure you provide the absolute or relative path
    path_to_folder = "./library"
    rename_files(path_to_folder)