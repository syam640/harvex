import os
import urllib.request
import json
import time
import sys

DATA_DIR = "app/ml/data/tomato_disease"
GITHUB_BASE = "https://api.github.com/repos/spMohanty/PlantVillage-Dataset/contents/raw/color"

CLASSES_TO_EXPAND = {
    "Tomato___Early_blight": 80,
    "Tomato___Septoria_leaf_spot": 80,
    "Tomato___Spider_mites Two-spotted_spider_mite": 70,
    "Tomato___Bacterial_spot": 70,
    "Tomato___Target_Spot": 70,
    "Tomato___Yellow_Leaf_Curl_Virus": 70,
    "Tomato___Leaf_Mold": 60,
    "Tomato___Late_blight": 60,
    "Tomato___Tomato_mosaic_virus": 60,
    "Tomato___healthy": 60,
}

def list_github_files(class_name):
    url = f"{GITHUB_BASE}/{class_name}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        data = json.loads(resp.read())
        return [item for item in data if item["name"].lower().endswith(('.jpg', '.jpeg', '.png'))]
    except Exception as e:
        print(f"  Error listing {class_name}: {e}")
        return []

def download_image(url, filepath):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        resp = urllib.request.urlopen(req, timeout=15)
        with open(filepath, 'wb') as f:
            f.write(resp.read())
        return True
    except Exception as e:
        return False

def main():
    total_downloaded = 0
    
    for class_name, target_extra in CLASSES_TO_EXPAND.items():
        class_dir = os.path.join(DATA_DIR, class_name)
        existing = len([f for f in os.listdir(class_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))])
        
        need = max(0, target_extra - existing)
        if need == 0:
            print(f"{class_name}: already {existing} images, skipping")
            continue
        
        print(f"{class_name}: {existing} existing, downloading {need} more...")
        
        files = list_github_files(class_name)
        if not files:
            print(f"  No files found on GitHub for {class_name}")
            continue
        
        downloaded = 0
        for item in files:
            if downloaded >= need:
                break
            filepath = os.path.join(class_dir, item["name"])
            if os.path.exists(filepath):
                continue
            if download_image(item["download_url"], filepath):
                downloaded += 1
                total_downloaded += 1
                if downloaded % 10 == 0:
                    print(f"  Downloaded {downloaded}/{need}")
            time.sleep(0.1)
        
        final = len([f for f in os.listdir(class_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))])
        print(f"  Total: {final} images")
    
    print(f"\nTotal new images downloaded: {total_downloaded}")
    
    print("\nFinal class distribution:")
    for cls in sorted(os.listdir(DATA_DIR)):
        cls_dir = os.path.join(DATA_DIR, cls)
        if os.path.isdir(cls_dir):
            count = len([f for f in os.listdir(cls_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))])
            print(f"  {cls}: {count}")

if __name__ == "__main__":
    main()
