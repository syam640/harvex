"""
HARVEX Disease Model Builder
Single source of truth for model architecture.
Used by both training and inference to prevent architecture drift.
"""

import torch
import torch.nn as nn
from torchvision import models


def build_disease_model(num_classes: int, weights=None):
    """Build a MobileNetV2 model for disease classification.
    
    This is the SINGLE authoritative model construction function.
    Training and inference MUST both use this function.
    
    Architecture:
    - Backbone: MobileNetV2 (pretrained on ImageNet if weights provided)
    - Classifier: Dropout(0.3) -> Linear(1280, num_classes)
    - Input: 224x224 RGB image, normalized with ImageNet stats
    
    Args:
        num_classes: Number of output classes
        weights: MobileNet_V2_Weights enum or None (random init)
    
    Returns:
        torch.nn.Module ready for training or inference
    """
    model = models.mobilenet_v2(weights=weights)
    model.classifier[1] = nn.Sequential(
        nn.Dropout(0.3),
        nn.Linear(model.last_channel, num_classes)
    )
    return model


def get_model_state_dict_keys(num_classes: int):
    """Return the expected state_dict keys for the classifier.
    Used to verify checkpoint compatibility."""
    model = build_disease_model(num_classes)
    return set(k for k in model.state_dict().keys() if "classifier" in k)
