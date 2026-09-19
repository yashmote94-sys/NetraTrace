import os
import io
import time

import cv2
import torch
import torch.nn as nn
import numpy as np
import streamlit as st

from PIL import Image, ImageEnhance
from torchvision import transforms
from torchvision.models import resnet18

from database import (
    get_patient,
    save_patient,
    generate_screening_id,
    save_screening,
)


# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

MODEL_DIR = os.path.join(
    BASE_DIR,
    "model"
)

VALIDATOR_MODEL_PATH = os.path.join(
    MODEL_DIR,
    "fundus_validator_resnet18_v2.pth"
)

# Updated V2 ordinal DR model.
DR_MODEL_PATH = os.path.join(
    MODEL_DIR,
    "best_resnet18_ordinal_v2.pth"
)


# ============================================================
# DEVICE
# ============================================================

DEVICE = torch.device(
    "cuda"
    if torch.cuda.is_available()
    else "cpu"
)


# ============================================================
# IMAGE SETTINGS
# ============================================================

IMAGE_SIZE = 224


# ============================================================
# FUNDUS VALIDATOR
# ============================================================

# Confirmed mapping:
#
# 0 = Fundus
# 1 = Non-Fundus

FUNDUS_CLASS = 0
NON_FUNDUS_CLASS = 1

FUNDUS_VALIDATION_THRESHOLD = 0.90


validator_transform = transforms.Compose([
    transforms.Resize(
        (IMAGE_SIZE, IMAGE_SIZE)
    ),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[
            0.485,
            0.456,
            0.406
        ],
        std=[
            0.229,
            0.224,
            0.225
        ]
    )
])


# ============================================================
# UPDATED V2 DR CLASSIFIER
# ============================================================

CLASS_NAMES = [
    "Grade 0 - No DR",
    "Grade 1 - Mild NPDR",
    "Grade 2 - Moderate NPDR",
    "Grade 3 - Severe NPDR",
    "Grade 4 - Proliferative DR",
]

DR_GRADE_DETAILS = {
    0: {"severity": "No DR", "priority": "LOW"},
    1: {"severity": "Mild NPDR", "priority": "LOW"},
    2: {"severity": "Moderate NPDR", "priority": "MEDIUM"},
    3: {"severity": "Severe NPDR", "priority": "HIGH"},
    4: {"severity": "Proliferative DR", "priority": "HIGH"},
}

IMAGE_SIZE = 224
TEMPERATURE = 0.9811

# Prototype / engineering safety thresholds from the V2 pipeline.
CONFIDENCE_THRESHOLD = 0.85
MARGIN_THRESHOLD = 0.10
MAX_GRADE_DIFFERENCE = 1
TTA_PROBABILITY_DIFFERENCE = 0.25
TTA_CONFIDENCE_THRESHOLD = 0.65

dr_transform = transforms.Compose([
    transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225],
    ),
])


# ============================================================
# V2 ORDINAL RESNET18
# ============================================================

class OrdinalResNet18(nn.Module):

    def __init__(self, num_classes=5):
        super().__init__()

        self.backbone = resnet18(weights=None)
        features = self.backbone.fc.in_features

        self.backbone.fc = nn.Identity()

        self.classifier = nn.Linear(
            features,
            num_classes,
        )

        self.ordinal_head = nn.Linear(
            features,
            num_classes - 1,
        )

    def forward(self, x):
        features = self.backbone(x)

        classification_logits = self.classifier(features)
        ordinal_logits = self.ordinal_head(features)

        return classification_logits, ordinal_logits


# ============================================================
# LOAD FUNDUS VALIDATOR
# ============================================================

@st.cache_resource
def load_fundus_validator():

    if not os.path.exists(VALIDATOR_MODEL_PATH):
        raise FileNotFoundError(
            "Fundus Validator model not found:\n"
            f"{VALIDATOR_MODEL_PATH}"
        )

    model = resnet18(weights=None)
    model.fc = nn.Linear(model.fc.in_features, 2)

    checkpoint = torch.load(
        VALIDATOR_MODEL_PATH,
        map_location=DEVICE,
        weights_only=False,
    )

    if (
        isinstance(checkpoint, dict)
        and "model_state_dict" in checkpoint
    ):
        checkpoint = checkpoint["model_state_dict"]
    elif (
        isinstance(checkpoint, dict)
        and "state_dict" in checkpoint
    ):
        checkpoint = checkpoint["state_dict"]

    model.load_state_dict(checkpoint, strict=True)
    model = model.to(DEVICE)
    model.eval()

    return model


# ============================================================
# LOAD NEW V2 DR MODEL
# ============================================================

@st.cache_resource
def load_dr_model():

    if not os.path.exists(DR_MODEL_PATH):
        raise FileNotFoundError(
            "V2 DR model not found:\n"
            f"{DR_MODEL_PATH}"
        )

    model = OrdinalResNet18(num_classes=5)

    checkpoint = torch.load(
        DR_MODEL_PATH,
        map_location=DEVICE,
        weights_only=False,
    )

    if (
        isinstance(checkpoint, dict)
        and "model_state_dict" in checkpoint
    ):
        state_dict = checkpoint["model_state_dict"]
    elif (
        isinstance(checkpoint, dict)
        and "state_dict" in checkpoint
    ):
        state_dict = checkpoint["state_dict"]
    else:
        state_dict = checkpoint

    model.load_state_dict(
        state_dict,
        strict=True,
    )

    model = model.to(DEVICE)
    model.eval()

    return model


# ============================================================
# FUNDUS VALIDATION
# ============================================================

def validate_fundus_image(image):

    try:

        image = image.convert("RGB")

        input_tensor = (
            validator_transform(image)
            .unsqueeze(0)
            .to(DEVICE)
        )

        model = load_fundus_validator()

        with torch.no_grad():
            output = model(input_tensor)
            probabilities = torch.softmax(output, dim=1)

        fundus_probability = float(
            probabilities[0, FUNDUS_CLASS].item()
        )

        non_fundus_probability = float(
            probabilities[0, NON_FUNDUS_CLASS].item()
        )

        passed = (
            fundus_probability >= FUNDUS_VALIDATION_THRESHOLD
            and fundus_probability > non_fundus_probability
        )

        if passed:
            return {
                "passed": True,
                "label": "Fundus",
                "confidence": fundus_probability * 100.0,
                "fundus_probability": fundus_probability * 100.0,
                "non_fundus_probability": non_fundus_probability * 100.0,
            }

        return {
            "passed": False,
            "label": "Non-Fundus",
            "confidence": non_fundus_probability * 100.0,
            "fundus_probability": fundus_probability * 100.0,
            "non_fundus_probability": non_fundus_probability * 100.0,
        }

    except Exception as e:

        return {
            "passed": False,
            "label": "Validation Error",
            "confidence": 0.0,
            "fundus_probability": 0.0,
            "non_fundus_probability": 0.0,
            "error": str(e),
        }


# ============================================================
# RETINAL REGION DETECTION / IMAGE QUALITY
# ============================================================

def detect_retinal_region(image):

    image_array = np.asarray(image.convert("RGB"))
    gray = cv2.cvtColor(image_array, cv2.COLOR_RGB2GRAY)

    height, width = gray.shape

    percentile_value = np.percentile(gray, 35)

    threshold = max(
        10,
        min(int(percentile_value * 1.35), 80),
    )

    _, binary = cv2.threshold(
        gray,
        threshold,
        255,
        cv2.THRESH_BINARY,
    )

    kernel = np.ones((9, 9), np.uint8)

    binary = cv2.morphologyEx(
        binary,
        cv2.MORPH_CLOSE,
        kernel,
    )

    binary = cv2.morphologyEx(
        binary,
        cv2.MORPH_OPEN,
        kernel,
    )

    contours, _ = cv2.findContours(
        binary,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE,
    )

    mask = np.zeros_like(gray, dtype=np.uint8)

    if contours:

        largest_contour = max(
            contours,
            key=cv2.contourArea,
        )

        contour_area = cv2.contourArea(
            largest_contour
        )

        image_area = width * height

        if contour_area >= image_area * 0.08:
            cv2.drawContours(
                mask,
                [largest_contour],
                -1,
                255,
                thickness=-1,
            )

    if np.count_nonzero(mask) < width * height * 0.05:

        center_x = width // 2
        center_y = height // 2

        radius = int(min(width, height) * 0.42)

        y_grid, x_grid = np.ogrid[:height, :width]

        circle = (
            (x_grid - center_x) ** 2
            + (y_grid - center_y) ** 2
            <= radius ** 2
        )

        mask[circle] = 255

    return mask


def calculate_quality_metrics(image):

    image_array = np.asarray(image.convert("RGB"))
    height, width = image_array.shape[:2]

    min_dimension = min(width, height)
    resolution_pass = min_dimension >= 300

    gray = cv2.cvtColor(
        image_array,
        cv2.COLOR_RGB2GRAY,
    )

    retinal_mask = detect_retinal_region(image)

    retinal_pixels = gray[retinal_mask > 0]

    if retinal_pixels.size < 1000:

        center_x = width // 2
        center_y = height // 2
        radius = int(min(width, height) * 0.40)

        y1 = max(0, center_y - radius)
        y2 = min(height, center_y + radius)
        x1 = max(0, center_x - radius)
        x2 = min(width, center_x + radius)

        retinal_region = gray[y1:y2, x1:x2]
        region_mask = np.ones(
            retinal_region.shape,
            dtype=bool,
        )

    else:

        ys, xs = np.where(retinal_mask > 0)

        x1 = max(0, int(xs.min()))
        x2 = min(width, int(xs.max()) + 1)
        y1 = max(0, int(ys.min()))
        y2 = min(height, int(ys.max()) + 1)

        retinal_region = gray[y1:y2, x1:x2]

        region_mask = (
            retinal_mask[y1:y2, x1:x2] > 0
        )

    laplacian = cv2.Laplacian(
        retinal_region,
        cv2.CV_64F,
    )

    laplacian_values = laplacian[region_mask]

    if laplacian_values.size == 0:
        laplacian_values = laplacian.reshape(-1)

    laplacian_score = float(
        np.var(laplacian_values)
    )

    sobel_x = cv2.Sobel(
        retinal_region,
        cv2.CV_64F,
        1,
        0,
        ksize=3,
    )

    sobel_y = cv2.Sobel(
        retinal_region,
        cv2.CV_64F,
        0,
        1,
        ksize=3,
    )

    sobel_magnitude = sobel_x ** 2 + sobel_y ** 2
    sobel_values = sobel_magnitude[region_mask]

    if sobel_values.size == 0:
        sobel_values = sobel_magnitude.reshape(-1)

    tenengrad_score = float(
        np.mean(sobel_values)
    )

    valid_pixels = retinal_region[region_mask]

    if valid_pixels.size == 0:
        valid_pixels = retinal_region.reshape(-1)

    contrast_score = float(
        np.std(valid_pixels)
    )

    brightness_score = float(
        np.mean(valid_pixels)
    )

    exposure_pass = (
        15.0 <= brightness_score <= 245.0
    )

    laplacian_component = min(
        laplacian_score / 20.0,
        1.0,
    )

    tenengrad_component = min(
        tenengrad_score / 250.0,
        1.0,
    )

    sharpness_component = (
        0.45 * laplacian_component
        + 0.55 * tenengrad_component
    )

    contrast_component = min(
        contrast_score / 40.0,
        1.0,
    )

    exposure_component = (
        1.0 if exposure_pass else 0.0
    )

    quality_score = (
        0.70 * sharpness_component
        + 0.20 * contrast_component
        + 0.10 * exposure_component
    )

    if not resolution_pass:
        passed = False
        status = "Poor Resolution"
    elif not exposure_pass:
        passed = False
        status = "Poor Exposure"
    elif contrast_score < 8.0:
        passed = False
        status = "Poor Contrast"
    elif quality_score < 0.08:
        passed = False
        status = "Blurry / Low Quality"
    else:
        passed = True
        status = "Acceptable"

    return {
        "passed": passed,
        "status": status,
        "quality_score": float(quality_score * 100.0),
        "laplacian_score": laplacian_score,
        "tenengrad_score": tenengrad_score,
        "contrast_score": contrast_score,
        "brightness_score": brightness_score,
        "width": width,
        "height": height,
        "resolution_pass": resolution_pass,
        "exposure_pass": exposure_pass,
    }


def calculate_blur_score(image):
    return calculate_quality_metrics(image)["laplacian_score"]


def check_image_quality(image):

    metrics = calculate_quality_metrics(image)

    return {
        "passed": metrics["passed"],
        "status": metrics["status"],
        "quality_score": metrics["quality_score"],
        "blur_score": metrics["laplacian_score"],
        "tenengrad_score": metrics["tenengrad_score"],
        "contrast_score": metrics["contrast_score"],
        "brightness_score": metrics["brightness_score"],
        "width": metrics["width"],
        "height": metrics["height"],
    }


# ============================================================
# MODEL PREDICTION
# ============================================================

def _prepare_dr_tensor(image):

    return (
        dr_transform(image.convert("RGB"))
        .unsqueeze(0)
        .to(DEVICE)
    )


def _probability_margin(probabilities):

    values = np.sort(
        np.asarray(probabilities)
    )

    if len(values) < 2:
        return float(values[-1])

    return float(values[-1] - values[-2])


def _predict_single_pass(model, image):

    tensor = _prepare_dr_tensor(image)

    with torch.no_grad():

        classification_logits, ordinal_logits = model(
            tensor
        )

        calibrated_logits = (
            classification_logits / TEMPERATURE
        )

        probabilities = (
            torch.softmax(
                calibrated_logits,
                dim=1,
            )[0]
            .detach()
            .cpu()
            .numpy()
        )

        ordinal_probabilities = (
            torch.sigmoid(
                ordinal_logits[0]
            )
            .detach()
            .cpu()
            .numpy()
        )

    predicted_class = int(
        np.argmax(probabilities)
    )

    confidence = float(
        probabilities[predicted_class]
    )

    margin = _probability_margin(
        probabilities
    )

    ordinal_grade = int(
        np.sum(ordinal_probabilities >= 0.5)
    )

    ordinal_grade = min(
        ordinal_grade,
        4,
    )

    return {
        "class": predicted_class,
        "label": CLASS_NAMES[predicted_class],
        "confidence": confidence,
        "margin": margin,
        "probabilities": probabilities,
        "ordinal_grade": ordinal_grade,
        "ordinal_probabilities": ordinal_probabilities,
    }


# ============================================================
# TEST-TIME AUGMENTATION
# ============================================================

def _predict_tta(model, image):

    image = image.convert("RGB")

    tta_images = [
        image,
        image.transpose(
            Image.Transpose.FLIP_LEFT_RIGHT
        ),
        ImageEnhance.Contrast(image).enhance(1.08),
        ImageEnhance.Brightness(image).enhance(1.05),
    ]

    probability_results = []
    individual_results = []

    with torch.no_grad():

        for variant in tta_images:

            result = _predict_single_pass(
                model,
                variant,
            )

            probability_results.append(
                result["probabilities"]
            )

            individual_results.append(
                result
            )

    mean_probabilities = np.mean(
        np.asarray(probability_results),
        axis=0,
    )

    predicted_class = int(
        np.argmax(mean_probabilities)
    )

    confidence = float(
        mean_probabilities[predicted_class]
    )

    margin = _probability_margin(
        mean_probabilities
    )

    original_probabilities = (
        individual_results[0]["probabilities"]
    )

    probability_change = float(
        np.max(
            np.abs(
                mean_probabilities
                - original_probabilities
            )
        )
    )

    return {
        "class": predicted_class,
        "label": CLASS_NAMES[predicted_class],
        "confidence": confidence,
        "margin": margin,
        "probabilities": mean_probabilities,
        "probability_change": probability_change,
        "original_class": individual_results[0]["class"],
        "individual_results": individual_results,
    }


# ============================================================
# SAFETY DECISION
# ============================================================

def _safety_decision(first_pass, tta_pass):

    classifier_grade = first_pass["class"]
    ordinal_grade = first_pass["ordinal_grade"]

    classifier_confidence = first_pass["confidence"]
    classifier_margin = first_pass["margin"]

    tta_grade = tta_pass["class"]
    tta_confidence = tta_pass["confidence"]
    tta_margin = tta_pass["margin"]

    probability_change = tta_pass[
        "probability_change"
    ]

    agreement = (
        classifier_grade == tta_grade
    )

    grade_difference = abs(
        classifier_grade - tta_grade
    )

    classifier_ordinal_difference = abs(
        classifier_grade - ordinal_grade
    )

    probability_stable = (
        probability_change
        < TTA_PROBABILITY_DIFFERENCE
    )

    classifier_strong = (
        classifier_confidence >= CONFIDENCE_THRESHOLD
        and classifier_margin >= MARGIN_THRESHOLD
    )

    tta_strong = (
        tta_confidence >= TTA_CONFIDENCE_THRESHOLD
        and tta_margin >= MARGIN_THRESHOLD
    )

    reasons = []

    if classifier_ordinal_difference > MAX_GRADE_DIFFERENCE:
        return {
            "status": "MANUAL REVIEW REQUIRED",
            "recommendation": (
                "Classifier and ordinal predictions differ "
                "substantially. Human review is recommended."
            ),
            "reasons": [
                "Classifier and ordinal predictions differ substantially."
            ],
            "agreement": agreement,
            "grade_difference": grade_difference,
            "probability_difference": probability_change,
            "probability_stable": probability_stable,
        }

    if probability_change >= TTA_PROBABILITY_DIFFERENCE:
        return {
            "status": "MANUAL REVIEW REQUIRED",
            "recommendation": (
                "The model probability distribution changed "
                "substantially during TTA. Human review is recommended."
            ),
            "reasons": [
                "Prediction changes substantially under TTA."
            ],
            "agreement": agreement,
            "grade_difference": grade_difference,
            "probability_difference": probability_change,
            "probability_stable": False,
        }

    if not agreement:

        if grade_difference > MAX_GRADE_DIFFERENCE:
            return {
                "status": "MANUAL REVIEW REQUIRED",
                "recommendation": (
                    "Original and TTA predictions differ by "
                    "more than one grade. Human review is recommended."
                ),
                "reasons": [
                    "Original and TTA predictions differ by more than one grade."
                ],
                "agreement": False,
                "grade_difference": grade_difference,
                "probability_difference": probability_change,
                "probability_stable": probability_stable,
            }

        reasons.append(
            "First-pass and TTA predictions disagree."
        )

    if not tta_strong:
        reasons.append(
            "TTA confidence or margin is below the prototype safety threshold."
        )

    if not classifier_strong:
        reasons.append(
            "Calibrated classifier confidence or margin is below the prototype safety threshold."
        )

    if grade_difference > MAX_GRADE_DIFFERENCE:
        reasons.append(
            "Predictions differ by more than one severity grade."
        )

    if not probability_stable:
        reasons.append(
            "Class probabilities changed substantially during TTA."
        )

    if reasons:

        return {
            "status": (
                "RECHECK REQUIRED"
                if grade_difference <= MAX_GRADE_DIFFERENCE
                else "MANUAL REVIEW REQUIRED"
            ),
            "recommendation": (
                "The first-pass grade is retained as the primary "
                "result. Repeat screening or human review is recommended."
            ),
            "reasons": reasons,
            "agreement": agreement,
            "grade_difference": grade_difference,
            "probability_difference": probability_change,
            "probability_stable": probability_stable,
        }

    return {
        "status": "AUTOMATED SCREENING RESULT",
        "recommendation": (
            "Classifier, ordinal prediction, confidence, margin "
            "and TTA checks passed."
        ),
        "reasons": [],
        "agreement": agreement,
        "grade_difference": grade_difference,
        "probability_difference": probability_change,
        "probability_stable": probability_stable,
    }


# ============================================================
# GRAD-CAM FOR ORDINAL RESNET18 V2
# ============================================================

def generate_gradcam(
    model,
    image,
    target_class=None,
):

    device = next(
        model.parameters()
    ).device

    image = image.convert("RGB")

    input_tensor = (
        dr_transform(image)
        .unsqueeze(0)
        .to(device)
    )

    target_layer = (
        model.backbone.layer4[-1]
    )

    activations = []
    gradients = []

    def forward_hook(
        module,
        input_data,
        output,
    ):
        activations.append(output)

    def backward_hook(
        module,
        grad_input,
        grad_output,
    ):
        gradients.append(
            grad_output[0]
        )

    forward_handle = (
        target_layer.register_forward_hook(
            forward_hook
        )
    )

    backward_handle = (
        target_layer.register_full_backward_hook(
            backward_hook
        )
    )

    try:

        model.zero_grad()

        classification_logits, _ = model(
            input_tensor
        )

        calibrated_logits = (
            classification_logits / TEMPERATURE
        )

        probabilities = torch.softmax(
            calibrated_logits,
            dim=1,
        )

        predicted_class = int(
            torch.argmax(
                probabilities,
                dim=1,
            ).item()
        )

        if target_class is None:
            cam_class = predicted_class
        else:
            cam_class = int(target_class)

            if cam_class < 0 or cam_class > 4:
                cam_class = predicted_class

        confidence = float(
            probabilities[
                0,
                cam_class,
            ].item()
            * 100.0
        )

        calibrated_logits[
            0,
            cam_class,
        ].backward()

    finally:

        forward_handle.remove()
        backward_handle.remove()

    if not activations:
        raise RuntimeError(
            "Grad-CAM activations were not captured."
        )

    if not gradients:
        raise RuntimeError(
            "Grad-CAM gradients were not captured."
        )

    activation = activations[0]
    gradient = gradients[0]

    weights = gradient.mean(
        dim=(2, 3),
        keepdim=True,
    )

    cam = torch.relu(
        (
            weights * activation
        ).sum(
            dim=1,
            keepdim=True,
        )
    )

    cam = (
        cam.squeeze()
        .detach()
        .cpu()
        .numpy()
    )

    cam_min = cam.min()
    cam_max = cam.max()

    if cam_max - cam_min > 1e-8:

        cam = (
            cam - cam_min
        ) / (
            cam_max - cam_min
        )

    else:
        cam = np.zeros_like(cam)

    cam_image = (
        Image.fromarray(
            np.uint8(cam * 255)
        )
        .resize(
            image.size,
            Image.Resampling.BILINEAR,
        )
    )

    cam_array = (
        np.asarray(cam_image)
        .astype(np.float32)
        / 255.0
    )

    heatmap = cv2.applyColorMap(
        np.uint8(cam_array * 255),
        cv2.COLORMAP_JET,
    )

    heatmap = cv2.cvtColor(
        heatmap,
        cv2.COLOR_BGR2RGB,
    )

    original_array = (
        np.asarray(image)
        .astype(np.float32)
    )

    overlay = (
        0.60 * original_array
        + 0.40 * heatmap.astype(np.float32)
    )

    overlay = np.clip(
        overlay,
        0,
        255,
    ).astype(np.uint8)

    probability_dict = {
        CLASS_NAMES[i]: float(
            probabilities[
                0,
                i,
            ].item() * 100.0
        )
        for i in range(5)
    }

    return {
        "predicted_class": predicted_class,
        "cam_class": cam_class,
        "predicted_label": CLASS_NAMES[predicted_class],
        "cam_label": CLASS_NAMES[cam_class],
        "confidence": confidence,
        "probabilities": probability_dict,
        "heatmap": Image.fromarray(heatmap),
        "overlay": Image.fromarray(overlay),
        "original": image.copy(),
        "cam": cam,
    }


# ============================================================
# COMPLETE V2 AI ANALYSIS
# ============================================================

def analyze_fundus_image(
    image,
    progress_callback=None,
):

    model = load_dr_model()

    image = image.convert("RGB")

    if progress_callback:
        progress_callback(
            "1/4",
            "Running first-pass V2 ResNet18 prediction",
            "The ordinal ResNet18 model is classifying the fundus image into DR Grade 0–4.",
        )

    first_pass = _predict_single_pass(
        model,
        image,
    )

    if progress_callback:
        progress_callback(
            "2/4",
            "Running TTA safety recheck",
            "The prediction is being checked across controlled image variations.",
        )

    tta_pass = _predict_tta(
        model,
        image,
    )

    if progress_callback:
        progress_callback(
            "3/4",
            "Running AI safety consistency check",
            "Classifier, ordinal prediction and TTA stability are being compared.",
        )

    decision = _safety_decision(
        first_pass,
        tta_pass,
    )

    final_grade = int(
        first_pass["class"]
    )

    grade_info = DR_GRADE_DETAILS[
        final_grade
    ]

    if progress_callback:
        progress_callback(
            "4/4",
            "Generating Grad-CAM explainability",
            f"Creating the attention map for the primary prediction: Grade {final_grade}.",
        )

    gradcam = generate_gradcam(
        model,
        image,
        target_class=final_grade,
    )

    return {
        "quality_status": "Acceptable",
        "input_width": image.width,
        "input_height": image.height,
        "dr_grade": final_grade,
        "severity": grade_info["severity"],
        "confidence": float(
            first_pass["confidence"] * 100.0
        ),
        "referral_priority": grade_info["priority"],

        "original": gradcam["original"],
        "heatmap": gradcam["heatmap"],
        "overlay": gradcam["overlay"],
        "cam": gradcam["cam"],

        "probabilities": {
            CLASS_NAMES[i]: float(
                first_pass["probabilities"][i] * 100.0
            )
            for i in range(5)
        },

        "tta_probabilities": {
            CLASS_NAMES[i]: float(
                tta_pass["probabilities"][i] * 100.0
            )
            for i in range(5)
        },

        "ai_status": decision["status"],
        "ai_recommendation": decision["recommendation"],
        "ai_reasons": decision["reasons"],
        "ai_agreement": decision["agreement"],
        "ai_grade_difference": decision["grade_difference"],
        "ai_probability_difference": decision["probability_difference"],
        "ai_probability_stable": decision["probability_stable"],

        "first_pass_grade": first_pass["class"],
        "first_pass_label": first_pass["label"],
        "first_pass_confidence": first_pass["confidence"] * 100.0,
        "first_pass_margin": first_pass["margin"],

        "ordinal_grade": first_pass["ordinal_grade"],
        "ordinal_probabilities": first_pass["ordinal_probabilities"],

        "tta_grade": tta_pass["class"],
        "tta_label": tta_pass["label"],
        "tta_confidence": tta_pass["confidence"] * 100.0,
        "tta_margin": tta_pass["margin"],
    }


# ============================================================
# SCREENING SELECTION
# ============================================================

def screening_selection():

    st.title(
        "🩺 New Screening"
    )

    st.caption(
        "Select whether you want to screen an existing "
        "patient or register a new patient."
    )

    st.markdown(
        "---"
    )

    col1, col2 = st.columns(
        2
    )

    # ========================================================
    # EXISTING PATIENT
    # ========================================================

    with col1:

        st.subheader(
            "👤 Existing Patient"
        )

        st.write(
            "Search and select an existing patient "
            "for a new screening."
        )

        if st.button(
            "🔎 Select Existing Patient",
            width="stretch"
        ):

            st.session_state[
                "current_screen"
            ] = "patients"

            st.rerun()

    # ========================================================
    # NEW PATIENT
    # ========================================================

    with col2:

        st.subheader(
            "➕ New Patient"
        )

        st.write(
            "Register a new patient and continue "
            "with fundus screening."
        )

        if st.button(
            "➕ Register New Patient",
            width="stretch"
        ):

            st.session_state[
                "patient_id"
            ] = ""

            st.session_state[
                "patient_name"
            ] = ""

            st.session_state[
                "patient_age"
            ] = 18

            st.session_state[
                "patient_gender"
            ] = "Male"

            st.session_state[
                "patient_phone"
            ] = ""

            st.session_state[
                "patient_email"
            ] = ""

            st.session_state[
                "patient_address"
            ] = ""

            st.session_state[
                "diabetes_status"
            ] = "Unknown"

            st.session_state[
                "screening_started"
            ] = True

            st.session_state[
                "current_screen"
            ] = "screening"

            st.rerun()

    st.markdown(
        "---"
    )

    if st.button(
        "🏠 Dashboard",
        width="stretch"
    ):

        st.session_state[
            "current_screen"
        ] = "dashboard"

        st.rerun()


# ============================================================
# MAIN SCREENING PAGE
# ============================================================

def show_screening():

    # ========================================================
    # SCREENING SELECTION
    # ========================================================

    if not st.session_state.get(
        "screening_started",
        False
    ):

        screening_selection()

        return

    st.title(
        "🩺 Fundus Screening"
    )

    st.caption(
        "Validate the retinal image and perform "
        "AI-assisted diabetic retinopathy screening."
    )

    # ========================================================
    # PATIENT INFORMATION
    # ========================================================

    st.subheader(
        "👤 Patient Information"
    )

    patient_id_default = (
        st.session_state.get(
            "patient_id",
            ""
        )
    )

    patient_name_default = (
        st.session_state.get(
            "patient_name",
            ""
        )
    )

    patient_age_default = (
        st.session_state.get(
            "patient_age",
            18
        )
    )

    patient_gender_default = (
        st.session_state.get(
            "patient_gender",
            "Male"
        )
    )

    patient_phone_default = (
        st.session_state.get(
            "patient_phone",
            ""
        )
    )

    patient_email_default = (
        st.session_state.get(
            "patient_email",
            ""
        )
    )

    patient_address_default = (
        st.session_state.get(
            "patient_address",
            ""
        )
    )

    diabetes_default = (
        st.session_state.get(
            "diabetes_status",
            "Unknown"
        )
    )

    existing_patient = None

    if patient_id_default:

        existing_patient = (
            get_patient(
                patient_id_default
            )
        )

    # ========================================================
    # PATIENT FORM
    # ========================================================

    with st.container(
        border=True
    ):

        col1, col2 = st.columns(
            2
        )

        with col1:

            patient_id = (
                st.text_input(
                    "Patient ID *",
                    value=patient_id_default,
                    placeholder="Example: NT-001",
                    disabled=(
                        existing_patient
                        is not None
                    )
                )
            )

            patient_name = (
                st.text_input(
                    "Patient Name *",
                    value=patient_name_default
                )
            )

            patient_age = (
                st.number_input(
                    "Age",
                    min_value=0,
                    max_value=120,
                    value=(
                        patient_age_default
                        if patient_age_default
                        is not None
                        else 18
                    )
                )
            )

            gender_options = [
                "Male",
                "Female",
                "Other"
            ]

            gender = (
                st.selectbox(
                    "Gender",
                    gender_options,
                    index=(
                        gender_options.index(
                            patient_gender_default
                        )
                        if patient_gender_default
                        in gender_options
                        else 0
                    )
                )
            )

        with col2:

            diabetes_options = [
                "Diabetic",
                "Non-Diabetic",
                "Unknown"
            ]

            diabetes_status = (
                st.selectbox(
                    "Diabetes Status",
                    diabetes_options,
                    index=(
                        diabetes_options.index(
                            diabetes_default
                        )
                        if diabetes_default
                        in diabetes_options
                        else 2
                    )
                )
            )

            phone = (
                st.text_input(
                    "Phone",
                    value=patient_phone_default
                )
            )

            email = (
                st.text_input(
                    "Email",
                    value=patient_email_default
                )
            )

            address = (
                st.text_area(
                    "Address",
                    value=patient_address_default
                )
            )

    # ========================================================
    # SCREENING INFORMATION
    # ========================================================

    st.markdown(
        "---"
    )

    st.subheader(
        "👁️ Screening Information"
    )

    col1, col2 = st.columns(
        2
    )

    with col1:

        screening_date = (
            st.date_input(
                "Screening Date"
            )
        )

    with col2:

        eye = (
            st.selectbox(
                "Eye",
                [
                    "Right Eye",
                    "Left Eye",
                    "Both Eyes"
                ]
            )
        )

    # ========================================================
    # IMAGE UPLOAD
    # ========================================================

    st.markdown(
        "---"
    )

    st.subheader(
        "📷 Fundus Image"
    )

    uploaded_file = (
        st.file_uploader(
            "Upload Fundus Image",
            type=[
                "jpg",
                "jpeg",
                "png"
            ],
            help=(
                "Upload a retinal fundus photograph "
                "for AI-assisted screening."
            )
        )
    )

    if uploaded_file is not None:

        uploaded_file.seek(
            0
        )

        preview_image = (
            Image.open(
                uploaded_file
            )
            .convert(
                "RGB"
            )
        )

        st.image(
            preview_image,
            caption=uploaded_file.name,
            width="stretch"
        )

        st.caption(
            f"Resolution: "
            f"{preview_image.width} × "
            f"{preview_image.height} pixels"
        )

    # ========================================================
    # VALIDATION INFORMATION
    # ========================================================

    st.markdown(
        "---"
    )

    st.subheader(
        "🔍 Image Validation"
    )

    st.info(
        "NetraTrace first verifies that the image is "
        "a retinal fundus image. It then evaluates "
        "image quality before running the DR classifier "
        "with a TTA-based safety recheck."
    )

    # ========================================================
    # ANALYZE BUTTON
    # ========================================================

    if st.button(
        "🔬 Validate & Analyze Image",
        type="primary",
        width="stretch"
    ):

        # ====================================================
        # BASIC VALIDATION
        # ====================================================

        if not patient_id.strip():

            st.error(
                "Patient ID is required."
            )

            return

        if not patient_name.strip():

            st.error(
                "Patient name is required."
            )

            return

        if uploaded_file is None:

            st.error(
                "Please upload a fundus image."
            )

            return

        # ====================================================
        # SAVE PATIENT
        # ====================================================

        save_patient(
            patient_id=(
                patient_id.strip()
            ),
            name=(
                patient_name.strip()
            ),
            age=patient_age,
            gender=gender,
            diabetes_status=(
                diabetes_status
            ),
            phone=(
                phone.strip()
            ),
            email=(
                email.strip()
            ),
            address=(
                address.strip()
            )
        )

        # ====================================================
        # SAVE SESSION PATIENT DATA
        # ====================================================

        st.session_state[
            "patient_id"
        ] = patient_id.strip()

        st.session_state[
            "patient_name"
        ] = patient_name.strip()

        st.session_state[
            "patient_age"
        ] = patient_age

        st.session_state[
            "patient_gender"
        ] = gender

        st.session_state[
            "patient_phone"
        ] = phone.strip()

        st.session_state[
            "patient_email"
        ] = email.strip()

        st.session_state[
            "patient_address"
        ] = address.strip()

        st.session_state[
            "diabetes_status"
        ] = diabetes_status

        st.session_state[
            "screening_eye"
        ] = eye

        st.session_state[
            "screening_date"
        ] = screening_date

        # ====================================================
        # READ IMAGE
        # ====================================================

        uploaded_file.seek(
            0
        )

        image_bytes = (
            uploaded_file.getvalue()
        )

        image = (
            Image.open(
                io.BytesIO(
                    image_bytes
                )
            )
            .convert(
                "RGB"
            )
        )

        st.session_state[
            "uploaded_image_bytes"
        ] = image_bytes

        st.session_state[
            "uploaded_image"
        ] = image

        st.session_state[
            "image_name"
        ] = uploaded_file.name

        # ====================================================
        # STEP 1 — FUNDUS VALIDATOR
        # ====================================================

        with st.spinner(
            "🔍 Checking whether the image is a retinal fundus image..."
        ):

            fundus_result = (
                validate_fundus_image(
                    image
                )
            )

        # ====================================================
        # FUNDUS VALIDATION FAILED
        # ====================================================

        if not fundus_result[
            "passed"
        ]:

            st.error(
                "❌ **Fundus Validation: Failed**\n\n"
                "The uploaded image does not appear to be "
                "a retinal fundus image. Please upload a "
                "valid fundus photograph."
            )

            st.write(
                f"**Fundus probability:** "
                f"{fundus_result['fundus_probability']:.1f}%"
            )

            st.write(
                f"**Non-fundus probability:** "
                f"{fundus_result['non_fundus_probability']:.1f}%"
            )

            st.session_state[
                "fundus_validation"
            ] = "Failed"

            st.session_state[
                "fundus_confidence"
            ] = fundus_result[
                "confidence"
            ]

            st.session_state[
                "quality_status"
            ] = "Non-Fundus"

            return

        # ====================================================
        # FUNDUS PASSED
        # ====================================================

        st.success(
            "✅ **Fundus Validation: Passed**\n\n"
            "Image accepted as a retinal fundus image."
        )

        st.write(
            f"**Fundus confidence:** "
            f"{fundus_result['fundus_probability']:.1f}%"
        )

        st.session_state[
            "fundus_validation"
        ] = "Passed"

        st.session_state[
            "fundus_confidence"
        ] = fundus_result[
            "confidence"
        ]

        # ====================================================
        # STEP 2 — IMAGE QUALITY
        # ====================================================

        with st.spinner(
            "🔎 Assessing retinal image quality..."
        ):

            quality_result = (
                check_image_quality(
                    image
                )
            )

        # ====================================================
        # QUALITY FAILED
        # ====================================================

        if not quality_result[
            "passed"
        ]:

            st.warning(
                "⚠️ **Image Quality: Poor**\n\n"
                "The uploaded fundus photograph does not "
                "meet the minimum image-quality requirements "
                "for reliable DR analysis. Please upload "
                "a clearer retinal photograph."
            )

            st.write(
                f"**Reason:** "
                f"{quality_result['status']}"
            )

            st.write(
                f"**Quality score:** "
                f"{quality_result['quality_score']:.1f}%"
            )

            st.write(
                f"**Sharpness:** "
                f"{quality_result['blur_score']:.1f}"
            )

            st.write(
                f"**Contrast:** "
                f"{quality_result['contrast_score']:.1f}"
            )

            st.session_state[
                "quality_status"
            ] = quality_result[
                "status"
            ]

            st.session_state[
                "blur_score"
            ] = quality_result[
                "blur_score"
            ]

            st.session_state[
                "image_quality_score"
            ] = quality_result[
                "quality_score"
            ]

            return

        # ====================================================
        # QUALITY PASSED
        # ====================================================

        st.success(
            "✅ **Image Quality: Acceptable**"
        )

        quality_col1, quality_col2, quality_col3 = (
            st.columns(3)
        )

        with quality_col1:

            st.metric(
                "Quality Score",
                f"{quality_result['quality_score']:.1f}%"
            )

        with quality_col2:

            st.metric(
                "Sharpness",
                f"{quality_result['blur_score']:.1f}"
            )

        with quality_col3:

            st.metric(
                "Contrast",
                f"{quality_result['contrast_score']:.1f}"
            )

        st.caption(
            "Quality assessment uses retinal-region sharpness, "
            "Tenengrad/Sobel detail, contrast and exposure."
        )

        st.session_state[
            "quality_status"
        ] = "Acceptable"

        st.session_state[
            "blur_score"
        ] = quality_result[
            "blur_score"
        ]

        st.session_state[
            "image_quality_score"
        ] = quality_result[
            "quality_score"
        ]

        # ====================================================
        # STEP 3 — AI ANALYSIS
        # ====================================================

        st.markdown("---")
        st.subheader("🧠 AI Analysis")

        ai_stage = st.empty()
        ai_detail = st.empty()

        def show_ai_progress(step, title, detail):
            ai_stage.info(
                f"🧠 **AI Analysis — {step}**\n\n"
                f"**{title}**"
            )
            ai_detail.caption(detail)

        show_ai_progress(
            "Starting",
            "Initializing the trained ResNet18 screening model",
            "Preparing the image and loading the model weights."
        )

        try:

            result = (
                analyze_fundus_image(
                    image,
                    progress_callback=show_ai_progress
                )
            )

        except Exception as e:

            ai_stage.error(
                "❌ **AI Analysis Failed**"
            )
            ai_detail.empty()

            st.error(
                "The DR AI model could not "
                "analyze this image."
            )

            st.exception(
                e
            )

            return

        # ====================================================
        # V2 MODEL DIAGNOSTIC PANEL
        # ====================================================
        # This panel is intentionally diagnostic only. It does not
        # alter the model prediction or final grade. It lets us
        # compare NetraTrace inference against the standalone V2
        # pipeline using the exact same uploaded image.
        with st.expander(
            "🔬 V2 Model Diagnostic — Prediction Verification",
            expanded=True
        ):
            first_probs = result.get("probabilities", {})
            tta_probs = result.get("tta_probabilities", {})
            ordinal_probs = result.get("ordinal_probabilities", [])

            st.write(
                f"**Uploaded image:** {result.get('input_width')} × {result.get('input_height')} pixels"
            )
            st.write(
                f"**Inference resize:** {IMAGE_SIZE} × {IMAGE_SIZE} pixels | "
                f"**Temperature:** {TEMPERATURE}"
            )

            st.markdown("### Primary classifier")
            d1, d2, d3 = st.columns(3)
            with d1:
                st.metric("Primary Grade", f"Grade {result.get('first_pass_grade')}")
            with d2:
                st.metric("Confidence", f"{float(result.get('first_pass_confidence', 0)):.2f}%")
            with d3:
                st.metric("Margin", f"{float(result.get('first_pass_margin', 0)):.4f}")

            st.write("**Classifier probabilities:**")
            for class_name in CLASS_NAMES:
                probability = float(first_probs.get(class_name, 0.0))
                st.write(f"{class_name}: **{probability:.4f}%**")

            st.markdown("### Ordinal head")
            st.write(
                f"**Ordinal prediction:** Grade {result.get('ordinal_grade', 'N/A')}"
            )
            if ordinal_probs is not None and len(ordinal_probs) > 0:
                st.write(
                    "**Ordinal threshold probabilities:** "
                    + ", ".join(
                        f"O{i}: {float(value):.4f}"
                        for i, value in enumerate(ordinal_probs)
                    )
                )

            st.markdown("### TTA verification")
            t1, t2, t3 = st.columns(3)
            with t1:
                st.metric("TTA Grade", f"Grade {result.get('tta_grade')}")
            with t2:
                st.metric("TTA Confidence", f"{float(result.get('tta_confidence', 0)):.2f}%")
            with t3:
                st.metric("Max Probability Shift", f"{float(result.get('ai_probability_difference', 0)) * 100.0:.2f}%")

            st.write("**TTA mean probabilities:**")
            for class_name in CLASS_NAMES:
                probability = float(tta_probs.get(class_name, 0.0))
                st.write(f"{class_name}: **{probability:.4f}%**")

            st.markdown("### Final mapping check")
            st.write(
                f"**Primary model grade:** Grade {result.get('first_pass_grade')}  \n"
                f"**Final stored/displayed grade:** Grade {result.get('dr_grade')}"
            )
            st.caption(
                "The final grade must equal the primary classifier grade. "
                "TTA and ordinal outputs are verification signals only."
            )

        # Keep the completed AI analysis visible before
        # moving to the Results screen.
        ai_stage.success(
            "✅ **AI Analysis Complete**"
        )
        ai_detail.success(
            f"Primary prediction: **Grade {result['dr_grade']} — "
            f"{result['severity']}** | "
            f"Confidence: **{result['confidence']:.1f}%** | "
            f"Safety status: **{result['ai_status']}**"
        )

        time.sleep(2.5)

        # ====================================================
        # SAVE BASIC AI RESULTS
        # ====================================================

        st.session_state[
            "dr_grade"
        ] = result[
            "dr_grade"
        ]

        st.session_state[
            "severity"
        ] = result[
            "severity"
        ]

        st.session_state[
            "confidence"
        ] = result[
            "confidence"
        ]

        st.session_state[
            "referral_priority"
        ] = result[
            "referral_priority"
        ]

        st.session_state[
            "ai_probabilities"
        ] = result[
            "probabilities"
        ]

        # ====================================================
        # SAVE SAFETY RESULTS
        # ====================================================

        st.session_state[
            "ai_status"
        ] = result.get(
            "ai_status",
            "AUTOMATED SCREENING RESULT"
        )

        st.session_state[
            "ai_recommendation"
        ] = result.get(
            "ai_recommendation",
            ""
        )

        st.session_state[
            "ai_reasons"
        ] = result.get(
            "ai_reasons",
            []
        )

        st.session_state[
            "ai_agreement"
        ] = result.get(
            "ai_agreement",
            True
        )

        st.session_state[
            "ai_grade_difference"
        ] = result.get(
            "ai_grade_difference",
            0
        )

        st.session_state[
            "ai_probability_difference"
        ] = result.get(
            "ai_probability_difference",
            0.0
        )

        st.session_state[
            "ai_probability_stable"
        ] = result.get(
            "ai_probability_stable",
            True
        )

        # ====================================================
        # FIRST PASS
        # ====================================================

        st.session_state[
            "first_pass_grade"
        ] = result.get(
            "first_pass_grade"
        )

        st.session_state[
            "first_pass_confidence"
        ] = result.get(
            "first_pass_confidence"
        )

        st.session_state[
            "first_pass_margin"
        ] = result.get(
            "first_pass_margin"
        )

        # ====================================================
        # TTA
        # ====================================================

        st.session_state[
            "tta_grade"
        ] = result.get(
            "tta_grade"
        )

        st.session_state[
            "tta_confidence"
        ] = result.get(
            "tta_confidence"
        )

        st.session_state[
            "tta_margin"
        ] = result.get(
            "tta_margin"
        )

        # ====================================================
        # GRAD-CAM
        # ====================================================

        st.session_state[
            "gradcam_original"
        ] = result[
            "original"
        ]

        st.session_state[
            "gradcam_heatmap"
        ] = result[
            "heatmap"
        ]

        st.session_state[
            "gradcam_overlay"
        ] = result[
            "overlay"
        ]

        # ====================================================
        # ANALYSIS MODE
        # ====================================================

        st.session_state[
            "analysis_mode"
        ] = "Real AI Model"

        # ====================================================
        # GENERATE SCREENING ID
        # ====================================================

        screening_id = (
            generate_screening_id()
        )

        # ====================================================
        # SAVE SCREENING
        # ====================================================

        save_screening(
            screening_id,
            patient_id.strip(),
            screening_date.isoformat(),
            eye,
            uploaded_file.name,
            result["dr_grade"],
            result["severity"],
            result["confidence"],
            result["referral_priority"],
            "Acceptable"
        )

        # ====================================================
        # SAVE SCREENING SESSION
        # ====================================================

        st.session_state[
            "screening_id"
        ] = screening_id

        st.session_state[
            "screening_result"
        ] = True

        st.session_state[
            "screening_saved"
        ] = True

        # ====================================================
        # SHOW AI RESULT
        # ====================================================

        ai_status = result.get(
            "ai_status",
            "AUTOMATED SCREENING RESULT"
        )

        if (
            ai_status
            ==
            "AUTOMATED SCREENING RESULT"
        ):

            st.success(
                "🧠 **AI Analysis Completed — Safety Checks Passed**"
            )

        elif (
            ai_status
            ==
            "RECHECK REQUIRED"
        ):

            st.warning(
                "⚠️ **AI Analysis Completed — Recheck Required**"
            )

        else:

            st.error(
                "⚠️ **AI Analysis Completed — Manual Review Required**"
            )

        # ====================================================
        # AI SAFETY SUMMARY
        # ====================================================

        with st.container(
            border=True
        ):

            st.subheader(
                "🛡️ AI Safety Check"
            )

            status_col1, status_col2, status_col3 = (
                st.columns(3)
            )

            with status_col1:

                st.metric(
                    "First Pass",
                    f"Grade {result['first_pass_grade']}"
                )

                st.caption(
                    f"{result['first_pass_confidence']:.1f}% confidence"
                )

            with status_col2:

                st.metric(
                    "TTA Recheck",
                    f"Grade {result['tta_grade']}"
                )

                st.caption(
                    f"{result['tta_confidence']:.1f}% confidence"
                )

            with status_col3:

                agreement_text = (
                    "Yes"
                    if result[
                        "ai_agreement"
                    ]
                    else "No"
                )

                st.metric(
                    "Agreement",
                    agreement_text
                )

            st.write(
                f"**Safety Status:** {ai_status}"
            )

            st.write(
                f"**Grade Difference:** "
                f"{result['ai_grade_difference']}"
            )

            st.write(
                f"**Probability Difference:** "
                f"{result['ai_probability_difference']:.3f}"
            )

            st.write(
                f"**Probability Stable:** "
                f"{'Yes' if result['ai_probability_stable'] else 'No'}"
            )

            st.write(
                f"**Recommendation:** "
                f"{result['ai_recommendation']}"
            )

            with st.expander(
                "🧪 Model Prediction Verification"
            ):
                st.write(
                    f"**First-pass raw class index:** "
                    f"{result['first_pass_grade']}"
                )
                st.write(
                    f"**First-pass mapped label:** "
                    f"{result['first_pass_label']}"
                )
                st.write(
                    f"**TTA raw class index:** "
                    f"{result['tta_grade']}"
                )
                st.write(
                    f"**TTA mapped label:** "
                    f"{result['tta_label']}"
                )
                st.caption(
                    "The first-pass class index is the primary "
                    "DR grade stored in the screening record. "
                    "TTA is used for verification only."
                )

            if result[
                "ai_reasons"
            ]:

                with st.expander(
                    "🔎 Safety Check Details"
                ):

                    for reason in (
                        result[
                            "ai_reasons"
                        ]
                    ):

                        st.write(
                            f"• {reason}"
                        )

        # ====================================================
        # FINAL DR RESULT
        # ====================================================

        st.subheader(
            "📊 Screening Result"
        )

        result_col1, result_col2, result_col3, result_col4 = (
            st.columns(4)
        )

        with result_col1:

            st.metric(
                "DR Grade",
                f"Grade {result['dr_grade']}"
            )

        with result_col2:

            st.metric(
                "Severity",
                result["severity"]
            )

        with result_col3:

            st.metric(
                "Confidence",
                f"{result['confidence']:.1f}%"
            )

        with result_col4:

            st.metric(
                "Referral Priority",
                result["referral_priority"]
            )

        # ====================================================
        # PROBABILITY DISTRIBUTION
        # ====================================================

        with st.expander(
            "📈 Class Probabilities"
        ):

            for class_name, probability in (
                result[
                    "probabilities"
                ].items()
            ):

                st.progress(
                    min(
                        max(
                            probability / 100.0,
                            0.0
                        ),
                        1.0
                    ),
                    text=(
                        f"{class_name}: "
                        f"{probability:.2f}%"
                    )
                )

        # ====================================================
        # GRAD-CAM PREVIEW
        # ====================================================

        with st.expander(
            "🔬 Grad-CAM Explainability"
        ):

            cam_col1, cam_col2 = (
                st.columns(2)
            )

            with cam_col1:

                st.image(
                    result["original"],
                    caption="Original Fundus Image",
                    width="stretch"
                )

            with cam_col2:

                st.image(
                    result["overlay"],
                    caption="Grad-CAM Attention Overlay",
                    width="stretch"
                )

            st.caption(
                "Grad-CAM shows image regions receiving "
                "higher model attention. It explains the "
                "model output and does not independently "
                "confirm clinical correctness."
            )

        # ====================================================
        # GO TO RESULTS
        # ====================================================
        # The completed AI analysis is intentionally kept visible
        # for a short moment before navigation.

        st.session_state[
            "current_screen"
        ] = "results"

        st.rerun()

    # ========================================================
    # BOTTOM ACTIONS
    # ========================================================

    st.markdown(
        "---"
    )

    col1, col2 = st.columns(
        2
    )

    # ========================================================
    # START OVER
    # ========================================================

    with col1:

        if st.button(
            "🔄 Start Over",
            width="stretch"
        ):

            st.session_state[
                "screening_started"
            ] = False

            st.session_state[
                "screening_id"
            ] = ""

            st.session_state[
                "uploaded_image"
            ] = None

            st.session_state[
                "uploaded_image_bytes"
            ] = None

            st.session_state[
                "fundus_validation"
            ] = None

            st.session_state[
                "fundus_confidence"
            ] = None

            st.session_state[
                "quality_status"
            ] = None

            st.session_state[
                "blur_score"
            ] = None

            st.session_state[
                "image_quality_score"
            ] = None

            st.session_state[
                "dr_grade"
            ] = None

            st.session_state[
                "severity"
            ] = None

            st.session_state[
                "confidence"
            ] = None

            st.session_state[
                "referral_priority"
            ] = None

            st.session_state[
                "gradcam_original"
            ] = None

            st.session_state[
                "gradcam_heatmap"
            ] = None

            st.session_state[
                "gradcam_overlay"
            ] = None

            st.session_state[
                "ai_probabilities"
            ] = {}

            st.session_state[
                "ai_status"
            ] = None

            st.session_state[
                "ai_recommendation"
            ] = None

            st.session_state[
                "ai_reasons"
            ] = []

            st.session_state[
                "ai_agreement"
            ] = None

            st.session_state[
                "ai_grade_difference"
            ] = None

            st.session_state[
                "ai_probability_difference"
            ] = None

            st.session_state[
                "ai_probability_stable"
            ] = None

            st.session_state[
                "first_pass_grade"
            ] = None

            st.session_state[
                "first_pass_confidence"
            ] = None

            st.session_state[
                "first_pass_margin"
            ] = None

            st.session_state[
                "tta_grade"
            ] = None

            st.session_state[
                "tta_confidence"
            ] = None

            st.session_state[
                "tta_margin"
            ] = None

            st.session_state[
                "current_screen"
            ] = "screening_selection"

            st.rerun()

    # ========================================================
    # DASHBOARD
    # ========================================================

    with col2:

        if st.button(
            "🏠 Dashboard",
            width="stretch"
        ):

            st.session_state[
                "current_screen"
            ] = "dashboard"

            st.rerun()