import os
import zipfile

def zip_project():
    source_dir = r"c:\Users\chowd\Documents\varun\Fai project Final (2)\Fai project Final"
    target_zip = r"c:\Users\chowd\Documents\Fai_Project_Ready_To_Share.zip"
    
    # Items to exclude from the zip to make it clean and small
    exclusions = [
        "node_modules",
        "__pycache__",
        ".pytest_cache",
        ".venv",
        "venv",
        "env",
        ".env",
        "dist",
        "lifeos_data.json",  # Don't share personal data
        ".git"
    ]
    
    with zipfile.ZipFile(target_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(source_dir):
            # Modify dirs in-place to skip excluded directories
            dirs[:] = [d for d in dirs if d not in exclusions]
            
            for file in files:
                if file in exclusions:
                    continue
                
                # Only include standard files (no backup DBs etc.)
                if file.endswith('.bak'):
                    continue
                    
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, source_dir)
                zipf.write(file_path, arcname)
                
    print(f"Success! Clean zip file created at: {target_zip}")

if __name__ == '__main__':
    zip_project()
