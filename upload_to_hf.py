import os
from huggingface_hub import HfApi
from pathlib import Path

def upload_to_huggingface():
    # Initialize the Hugging Face API
    api = HfApi()
    
    # Your Space ID
    repo_id = "lmoussadek/Nutrition-Chatbot"
    
    # List of files to upload (add more as needed)
    files_to_upload = [
        "app.py",
        "requirements.txt",
        "README.md",
        ".gitignore",
        "translations.json"
    ]
    
    # Upload each file
    for file in files_to_upload:
        if os.path.exists(file):
            print(f"Uploading {file}...")
            api.upload_file(
                path_or_fileobj=file,
                path_in_repo=file,
                repo_id=repo_id,
                repo_type="space"
            )
            print(f"Successfully uploaded {file}")
        else:
            print(f"Warning: {file} not found")

if __name__ == "__main__":
    print("Starting upload to Hugging Face Space...")
    upload_to_huggingface()
    print("Upload complete!") 