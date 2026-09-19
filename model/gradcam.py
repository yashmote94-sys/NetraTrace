import torch
import torch.nn as nn
import numpy as np

from PIL import Image
from torchvision import transforms
from torchvision.models import resnet18

import cv2


# ============================================================
# SETTINGS
# ============================================================

CLASS_NAMES = [
    "Grade 0 - No DR",
    "Grade 1 - Mild NPDR",
    "Grade 2 - Moderate NPDR",
    "Grade 3 - Severe NPDR",
    "Grade 4 - Proliferative DR",
]

IMAGE_SIZE = 224


# ============================================================
# IMAGE TRANSFORM
# ============================================================

transform = transforms.Compose([
    transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225],
    ),
])


# ============================================================
# LOAD MODEL
# ============================================================

def load_model(model_path, device=None):

    if device is None:
        device = torch.device(
            "cuda" if torch.cuda.is_available() else "cpu"
        )

    model = resnet18(weights=None)

    # NetraTrace / APTOS: 5 DR classes
    model.fc = nn.Linear(
        model.fc.in_features,
        5,
    )

    checkpoint = torch.load(
        model_path,
        map_location=device,
    )

    # Uploaded model is a direct state_dict
    model.load_state_dict(checkpoint)

    model = model.to(device)
    model.eval()

    return model, device


# ============================================================
# GRAD-CAM
# ============================================================

def generate_gradcam(
    model,
    image,
    device=None,
):

    if device is None:
        device = next(model.parameters()).device

    # --------------------------------------------------------
    # PREPARE IMAGE
    # --------------------------------------------------------

    if not isinstance(image, Image.Image):
        image = Image.open(image)

    image = image.convert("RGB")

    original_image = image.copy()

    input_tensor = transform(image).unsqueeze(0)
    input_tensor = input_tensor.to(device)

    # --------------------------------------------------------
    # HOOK LAST RESNET CONVOLUTIONAL LAYER
    # --------------------------------------------------------

    target_layer = model.layer4[-1]

    activations = []
    gradients = []

    def forward_hook(module, input_data, output):
        activations.append(output)

    def backward_hook(module, grad_input, grad_output):
        gradients.append(grad_output[0])

    forward_handle = target_layer.register_forward_hook(
        forward_hook
    )

    backward_handle = target_layer.register_full_backward_hook(
        backward_hook
    )

    # --------------------------------------------------------
    # PREDICTION
    # --------------------------------------------------------

    model.zero_grad()

    output = model(input_tensor)

    probabilities = torch.softmax(
        output,
        dim=1,
    )

    predicted_class = torch.argmax(
        probabilities,
        dim=1,
    ).item()

    confidence = (
        probabilities[
            0,
            predicted_class,
        ].item()
        * 100.0
    )

    # --------------------------------------------------------
    # BACKPROPAGATE PREDICTED CLASS
    # --------------------------------------------------------

    output[0, predicted_class].backward()

    # Remove hooks
    forward_handle.remove()
    backward_handle.remove()

    # --------------------------------------------------------
    # GET ACTIVATIONS AND GRADIENTS
    # --------------------------------------------------------

    if not activations or not gradients:
        raise RuntimeError(
            "Grad-CAM could not capture model activations "
            "or gradients."
        )

    activation = activations[0]
    gradient = gradients[0]

    # --------------------------------------------------------
    # GLOBAL AVERAGE POOLING
    # --------------------------------------------------------

    weights = gradient.mean(
        dim=(2, 3),
        keepdim=True,
    )

    # --------------------------------------------------------
    # WEIGHTED ACTIVATION MAP
    # --------------------------------------------------------

    cam = (
        weights * activation
    ).sum(
        dim=1,
        keepdim=True,
    )

    # ReLU
    cam = torch.relu(cam)

    # Convert to NumPy
    cam = (
        cam.squeeze()
        .detach()
        .cpu()
        .numpy()
    )

    # --------------------------------------------------------
    # NORMALIZE CAM
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # RESIZE CAM TO ORIGINAL IMAGE
    # --------------------------------------------------------

    cam_image = Image.fromarray(
        np.uint8(cam * 255)
    )

    cam_image = cam_image.resize(
        original_image.size,
        Image.Resampling.BILINEAR,
    )

    cam_array = (
        np.asarray(cam_image)
        .astype(np.float32)
        / 255.0
    )

    # --------------------------------------------------------
    # CREATE HEATMAP
    # --------------------------------------------------------

    heatmap = cv2.applyColorMap(
        np.uint8(cam_array * 255),
        cv2.COLORMAP_JET,
    )

    heatmap = cv2.cvtColor(
        heatmap,
        cv2.COLOR_BGR2RGB,
    )

    # --------------------------------------------------------
    # ORIGINAL IMAGE ARRAY
    # --------------------------------------------------------

    original_array = np.asarray(
        original_image
    ).astype(np.float32)

    # --------------------------------------------------------
    # CREATE OVERLAY
    # --------------------------------------------------------

    overlay = (
        0.60 * original_array
        +
        0.40 * heatmap.astype(np.float32)
    )

    overlay = np.clip(
        overlay,
        0,
        255,
    ).astype(np.uint8)

    overlay_image = Image.fromarray(
        overlay
    )

    # --------------------------------------------------------
    # PROBABILITIES
    # --------------------------------------------------------

    probability_dict = {
        CLASS_NAMES[i]: float(
            probabilities[0, i].item() * 100.0
        )
        for i in range(5)
    }

    # --------------------------------------------------------
    # RETURN
    # --------------------------------------------------------

    return {
        "predicted_class": predicted_class,
        "predicted_label": CLASS_NAMES[predicted_class],
        "confidence": confidence,
        "probabilities": probability_dict,
        "heatmap": Image.fromarray(heatmap),
        "overlay": overlay_image,
        "original": original_image,
        "cam": cam,
    }