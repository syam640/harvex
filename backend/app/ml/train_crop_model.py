import urllib.request
import io
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import joblib
import os
import json
from datetime import datetime

DATASET_URL = "https://raw.githubusercontent.com/nileshiq/Crop-Recommendation/main/Crop_Recommendation.csv"

FEATURE_COLUMNS = ['Nitrogen', 'Phosphorus', 'Potassium', 'Temperature', 'Humidity', 'pH_Value', 'Rainfall']
MODEL_FEATURE_ORDER = ['N', 'P', 'K', 'temperature', 'humidity', 'ph', 'rainfall']

def load_dataset():
    print("Downloading crop recommendation dataset...")
    req = urllib.request.Request(DATASET_URL, headers={'User-Agent': 'Mozilla/5.0'})
    resp = urllib.request.urlopen(req, timeout=30)
    data = resp.read()
    df = pd.read_csv(io.BytesIO(data))
    print(f"Dataset loaded: {df.shape[0]} samples, {df.shape[1]} columns")
    print(f"Crops: {sorted(df['Crop'].unique())}")
    return df

def train_crop_model():
    df = load_dataset()

    X = df[FEATURE_COLUMNS].to_numpy(dtype=float)
    y = df['Crop'].to_numpy()

    label_map = dict(zip(FEATURE_COLUMNS, MODEL_FEATURE_ORDER))

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    print(f"Train: {len(X_train)} samples, Test: {len(X_test)} samples")

    print("Training RandomForest classifier...")
    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=None,
        min_samples_split=2,
        min_samples_leaf=1,
        random_state=42,
        n_jobs=-1
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)

    cv_scores = cross_val_score(model, X, y, cv=5, scoring='accuracy')

    report = classification_report(y_test, y_pred, output_dict=True)
    cm = confusion_matrix(y_test, y_pred, labels=model.classes_)

    print(f"\n=== Model Evaluation ===")
    print(f"Test Accuracy: {accuracy:.4f}")
    print(f"CV Mean Accuracy: {cv_scores.mean():.4f} (+/- {cv_scores.std():.4f})")

    model_info = {
        'model_version': f'crop_rf_v1_{datetime.now().strftime("%Y%m%d")}',
        'feature_columns': MODEL_FEATURE_ORDER,
        'source_columns': FEATURE_COLUMNS,
        'label_map': label_map,
        'accuracy': float(accuracy),
        'cv_mean_accuracy': float(cv_scores.mean()),
        'cv_std_accuracy': float(cv_scores.std()),
        'classes': list(model.classes_),
        'num_classes': len(model.classes_),
        'training_samples': len(X_train),
        'test_samples': len(X_test),
        'total_samples': len(X),
        'dataset_url': DATASET_URL,
        'training_date': datetime.now().isoformat(),
        'classification_report': {
            k: v for k, v in report.items()
            if k in model.classes_ or k in ['accuracy', 'macro avg', 'weighted avg']
        },
        'feature_importances': dict(zip(MODEL_FEATURE_ORDER, [float(x) for x in model.feature_importances_]))
    }

    output_dir = 'app/ml/models'
    os.makedirs(output_dir, exist_ok=True)

    joblib.dump(model, f'{output_dir}/crop_model.joblib')
    joblib.dump(model_info, f'{output_dir}/crop_model_info.joblib')

    with open(f'{output_dir}/crop_model_metrics.json', 'w') as f:
        json.dump(model_info, f, indent=2, default=str)

    print(f"\n=== Saved ===")
    print(f"Model: {output_dir}/crop_model.joblib")
    print(f"Info: {output_dir}/crop_model_info.joblib")
    print(f"Metrics: {output_dir}/crop_model_metrics.json")
    print(f"Classes ({len(model.classes_)}): {model.classes_}")

    print(f"\nTop 5 feature importances:")
    importances = sorted(
        zip(MODEL_FEATURE_ORDER, model.feature_importances_),
        key=lambda x: x[1], reverse=True
    )
    for feat, imp in importances[:5]:
        print(f"  {feat}: {imp:.4f}")

    return model, model_info

if __name__ == "__main__":
    train_crop_model()
