"""
HARVEX Disease Model Training Script v3
Uses the unified model builder to prevent architecture drift.

Produces:
- disease_model.pth (checkpoint)
- disease_model_info.json (metadata with full evaluation)
- confusion_matrix.csv
- classification_report.txt

Dataset: PlantVillage (tomato subset)
Architecture: MobileNetV2 + Dropout(0.3) + Linear(1280, num_classes)
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset, random_split
from torchvision import transforms, models
from PIL import Image
import os
import json
import csv
import numpy as np
from sklearn.metrics import classification_report, confusion_matrix
from disease_model_builder import build_disease_model
import warnings
warnings.filterwarnings('ignore')


DATA_DIR = "app/ml/data/tomato_disease"
MODEL_DIR = "app/ml/models"
os.makedirs(MODEL_DIR, exist_ok=True)

IMG_SIZE = 224
BATCH_SIZE = 32
EPOCHS = 15
LR = 0.001
WEIGHT_DECAY = 1e-4
SEED = 42
DEVICE = torch.device("cpu")

torch.manual_seed(SEED)
np.random.seed(SEED)


# Canonical class ordering — must match inference
CANONICAL_CLASSES = [
    "Tomato___Bacterial_spot",
    "Tomato___Early_blight",
    "Tomato___Late_blight",
    "Tomato___Leaf_Mold",
    "Tomato___Septoria_leaf_spot",
    "Tomato___Spider_mites Two-spotted_spider_mite",
    "Tomato___Target_Spot",
    "Tomato___Tomato_Yellow_Leaf_Curl_Virus",
    "Tomato___Tomato_mosaic_virus",
    "Tomato___healthy",
]


class PlantDataset(Dataset):
    def __init__(self, root_dir, transform=None):
        self.root_dir = root_dir
        self.transform = transform
        self.samples = []
        # Use canonical class ordering, not filesystem order
        self.classes = [c for c in CANONICAL_CLASSES if os.path.isdir(os.path.join(root_dir, c))]
        self.class_to_idx = {cls: idx for idx, cls in enumerate(self.classes)}

        for cls in self.classes:
            cls_dir = os.path.join(root_dir, cls)
            for fname in os.listdir(cls_dir):
                if fname.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp')):
                    self.samples.append((os.path.join(cls_dir, fname), self.class_to_idx[cls]))

        print(f"Loaded {len(self.samples)} images across {len(self.classes)} classes")
        for cls in self.classes:
            count = sum(1 for s in self.samples if s[1] == self.class_to_idx[cls])
            print(f"  {cls}: {count}")

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        img_path, label = self.samples[idx]
        img = Image.open(img_path).convert('RGB')
        if self.transform:
            img = self.transform(img)
        return img, label


def main():
    print(f"Device: {DEVICE}")
    print(f"Data dir: {DATA_DIR}")
    print(f"Canonical classes: {CANONICAL_CLASSES}")

    # Transforms — training uses augmentation, val/test use clean transforms
    train_transform = transforms.Compose([
        transforms.Resize((IMG_SIZE, IMG_SIZE)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomVerticalFlip(),
        transforms.RandomRotation(15),
        transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2),
        transforms.RandomAffine(degrees=0, translate=(0.1, 0.1)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])

    val_transform = transforms.Compose([
        transforms.Resize((IMG_SIZE, IMG_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])

    # Load dataset with canonical class ordering
    dataset = PlantDataset(DATA_DIR, transform=train_transform)
    num_classes = len(dataset.classes)
    assert num_classes == len(CANONICAL_CLASSES), f"Expected {len(CANONICAL_CLASSES)} classes, found {num_classes}"

    # Stratified split: 70% train, 15% val, 15% test
    labels = [s[1] for s in dataset.samples]
    train_size = int(0.70 * len(dataset))
    val_size = int(0.15 * len(dataset))
    test_size = len(dataset) - train_size - val_size

    train_ds, val_ds, test_ds = random_split(
        dataset, [train_size, val_size, test_size],
        generator=torch.Generator().manual_seed(SEED)
    )

    # Set appropriate transforms for each split
    train_ds.dataset.transform = train_transform
    val_ds.dataset.transform = val_transform
    test_ds.dataset.transform = val_transform

    print(f"\nSplit: train={len(train_ds)}, val={len(val_ds)}, test={len(test_ds)}")

    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_ds, batch_size=BATCH_SIZE, shuffle=False, num_workers=0)
    test_loader = DataLoader(test_ds, batch_size=BATCH_SIZE, shuffle=False, num_workers=0)

    # Build model using unified builder
    model = build_disease_model(num_classes, weights=models.MobileNet_V2_Weights.DEFAULT)
    model = model.to(DEVICE)

    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=LR, weight_decay=WEIGHT_DECAY)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', patience=3, factor=0.5)

    # Training loop
    print(f"\nTraining for {EPOCHS} epochs...")
    best_val_acc = 0
    for epoch in range(EPOCHS):
        model.train()
        running_loss = 0
        correct = 0
        total = 0

        for images, labels in train_loader:
            images, labels = images.to(DEVICE), labels.to(DEVICE)
            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()

            running_loss += loss.item()
            _, predicted = outputs.max(1)
            total += labels.size(0)
            correct += predicted.eq(labels).sum().item()

        train_acc = 100. * correct / total
        train_loss = running_loss / len(train_loader)

        model.eval()
        val_loss = 0
        val_correct = 0
        val_total = 0

        with torch.no_grad():
            for images, labels in val_loader:
                images, labels = images.to(DEVICE), labels.to(DEVICE)
                outputs = model(images)
                loss = criterion(outputs, labels)
                val_loss += loss.item()
                _, predicted = outputs.max(1)
                val_total += labels.size(0)
                val_correct += predicted.eq(labels).sum().item()

        val_acc = 100. * val_correct / val_total
        val_loss /= len(val_loader)
        scheduler.step(val_loss)

        print(f"Epoch {epoch+1}/{EPOCHS}: train_acc={train_acc:.1f}% val_acc={val_acc:.1f}% loss={train_loss:.4f}")

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            torch.save(model.state_dict(), os.path.join(MODEL_DIR, "disease_model.pth"))
            print(f"  -> Saved best model (val_acc={val_acc:.1f}%)")

    print(f"\nBest validation accuracy: {best_val_acc:.1f}%")

    # Load best model for final evaluation
    model.load_state_dict(torch.load(os.path.join(MODEL_DIR, "disease_model.pth"), weights_only=True))
    model.eval()

    # Test set evaluation
    all_preds = []
    all_labels = []
    test_correct = 0
    test_total = 0

    with torch.no_grad():
        for images, labels in test_loader:
            images, labels = images.to(DEVICE), labels.to(DEVICE)
            outputs = model(images)
            _, predicted = outputs.max(1)
            test_total += labels.size(0)
            test_correct += predicted.eq(labels).sum().item()
            all_preds.extend(predicted.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())

    test_acc = 100. * test_correct / test_total
    print(f"\nTest accuracy: {test_acc:.1f}%")

    class_names = dataset.classes
    report = classification_report(all_labels, all_preds, target_names=class_names, zero_division=0)
    print(f"\nClassification Report:\n{report}")

    cm = confusion_matrix(all_labels, all_preds)
    print(f"\nConfusion Matrix:\n{cm}")

    # Save confusion matrix to CSV
    cm_path = os.path.join(MODEL_DIR, "confusion_matrix.csv")
    with open(cm_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([""] + class_names)
        for i, row in enumerate(cm):
            writer.writerow([class_names[i]] + list(row))
    print(f"Confusion matrix saved to {cm_path}")

    # Save classification report to text
    report_path = os.path.join(MODEL_DIR, "classification_report.txt")
    with open(report_path, 'w') as f:
        f.write(report)
    print(f"Classification report saved to {report_path}")

    # Build per-class metrics
    per_class = {}
    report_dict = classification_report(all_labels, all_preds, target_names=class_names, zero_division=0, output_dict=True)
    for cls_name in class_names:
        if cls_name in report_dict:
            per_class[cls_name] = {
                "precision": round(report_dict[cls_name]["precision"], 4),
                "recall": round(report_dict[cls_name]["recall"], 4),
                "f1": round(report_dict[cls_name]["f1-score"], 4),
            }

    # Save model info
    model_info = {
        "model_version": "disease_pth_v3_20260907",
        "model_type": "MobileNetV2",
        "architecture": "MobileNetV2 + Dropout(0.3) + Linear(1280, num_classes)",
        "framework": "PyTorch",
        "num_classes": num_classes,
        "classes": class_names,
        "img_size": IMG_SIZE,
        "normalization": {"mean": [0.485, 0.456, 0.406], "std": [0.229, 0.224, 0.225]},
        "test_accuracy": round(test_acc, 2),
        "best_val_accuracy": round(best_val_acc, 2),
        "macro_avg": {
            "precision": round(report_dict["macro avg"]["precision"], 4),
            "recall": round(report_dict["macro avg"]["recall"], 4),
            "f1": round(report_dict["macro avg"]["f1-score"], 4),
        },
        "per_class_metrics": per_class,
        "train_samples": len(train_ds),
        "val_samples": len(val_ds),
        "test_samples": len(test_ds),
        "total_samples": len(dataset),
        "epochs": EPOCHS,
        "seed": SEED,
        "dataset": "PlantVillage (tomato subset)",
        "dataset_source": "https://github.com/spMohanty/PlantVillage-Dataset",
        "dataset_license": "CC0 (Public Domain)",
        "training_date": "2026-09-07",
        "class_ordering": "canonical (not filesystem)",
    }

    with open(os.path.join(MODEL_DIR, "disease_model_info.json"), 'w') as f:
        json.dump(model_info, f, indent=2)

    print(f"\nModel saved to {MODEL_DIR}/disease_model.pth")
    print(f"Info saved to {MODEL_DIR}/disease_model_info.json")
    print("Done!")


if __name__ == '__main__':
    main()
