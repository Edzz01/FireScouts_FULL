import cv2
import numpy as np
import tensorflow as tf
import os

# ============================================================
# FireScout Standalone Fire/Smoke Detector
# ============================================================

MODEL_PATH = r"C:\FireScout_ROS\models\best.tflite"
IMAGE_PATH = r"C:\FireScout_ROS\test_fire.jpg"
OUTPUT_PATH = r"C:\FireScout_ROS\fire_detection_result.jpg"

# Detection settings
CONFIDENCE_THRESHOLD = 0.25
NMS_THRESHOLD = 0.45

CLASS_NAMES = {
    0: "fire",
    1: "smoke",
}


# ============================================================
# Load TFLite model
# ============================================================

print("Loading TFLite model...")

interpreter = tf.lite.Interpreter(
    model_path=MODEL_PATH
)

interpreter.allocate_tensors()

input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

input_index = input_details[0]["index"]
output_index = output_details[0]["index"]

input_shape = input_details[0]["shape"]

print("Model loaded.")
print("Input shape:", input_shape)
print("Output shape:", output_details[0]["shape"])


# ============================================================
# Load image
# ============================================================

print()
print("Loading image:")

image = cv2.imread(IMAGE_PATH)

if image is None:
    raise FileNotFoundError(
        f"Could not find image:\n{IMAGE_PATH}"
    )

original_image = image.copy()

original_height, original_width = image.shape[:2]

print(
    f"Original image size: "
    f"{original_width} x {original_height}"
)


# ============================================================
# Preprocess
# ============================================================

# Model expects 320 x 320
model_width = int(input_shape[3])
model_height = int(input_shape[2])

resized = cv2.resize(
    image,
    (model_width, model_height)
)

# BGR -> RGB
rgb = cv2.cvtColor(
    resized,
    cv2.COLOR_BGR2RGB
)

# Normalize 0-255 -> 0-1
input_data = rgb.astype(np.float32) / 255.0

# Model input is NCHW:
# [1, 3, 320, 320]
input_data = np.transpose(
    input_data,
    (2, 0, 1)
)

input_data = np.expand_dims(
    input_data,
    axis=0
)

input_data = np.ascontiguousarray(
    input_data,
    dtype=np.float32
)

print(
    f"Prepared input: {input_data.shape}"
)


# ============================================================
# Run inference
# ============================================================

interpreter.set_tensor(
    input_index,
    input_data
)

interpreter.invoke()

output = interpreter.get_tensor(
    output_index
)

print(
    f"Raw output shape: {output.shape}"
)


# ============================================================
# Decode YOLO output
# ============================================================

# Model output:
#
# [1, 6, 2100]
#
# Each prediction:
#
# x
# y
# width
# height
# fire confidence
# smoke confidence
#
# Transpose:
#
# [6, 2100] -> [2100, 6]

predictions = output[0].T

boxes = []
scores = []
class_ids = []


for prediction in predictions:

    x_center = float(prediction[0])
    y_center = float(prediction[1])
    width = float(prediction[2])
    height = float(prediction[3])

    class_scores = prediction[4:]

    class_id = int(
        np.argmax(class_scores)
    )

    confidence = float(
        class_scores[class_id]
    )

    # Ignore weak detections
    if confidence < CONFIDENCE_THRESHOLD:
        continue

    # --------------------------------------------------------
    # Coordinates are normalized 0-1
    # Convert to original image coordinates
    # --------------------------------------------------------

    x_center *= original_width
    y_center *= original_height

    width *= original_width
    height *= original_height

    x = int(x_center - width / 2)
    y = int(y_center - height / 2)

    w = int(width)
    h = int(height)

    # Clamp box to image
    x = max(0, x)
    y = max(0, y)

    w = min(
        w,
        original_width - x
    )

    h = min(
        h,
        original_height - y
    )

    if w <= 0 or h <= 0:
        continue

    boxes.append(
        [x, y, w, h]
    )

    scores.append(
        confidence
    )

    class_ids.append(
        class_id
    )


# ============================================================
# Non-Maximum Suppression
# ============================================================

print()
print(
    f"Predictions above "
    f"{CONFIDENCE_THRESHOLD:.2f}: {len(boxes)}"
)

final_detections = []

if len(boxes) > 0:

    # Run NMS separately for each class.
    #
    # This prevents a fire detection from suppressing
    # a smoke detection.

    for class_id in CLASS_NAMES:

        class_indices = [
            i
            for i, cid in enumerate(class_ids)
            if cid == class_id
        ]

        if not class_indices:
            continue

        class_boxes = [
            boxes[i]
            for i in class_indices
        ]

        class_scores = [
            scores[i]
            for i in class_indices
        ]

        indices = cv2.dnn.NMSBoxes(
            class_boxes,
            class_scores,
            CONFIDENCE_THRESHOLD,
            NMS_THRESHOLD
        )

        if len(indices) == 0:
            continue

        for index in np.array(indices).flatten():

            original_index = class_indices[
                int(index)
            ]

            final_detections.append(
                {
                    "class_id": class_ids[original_index],
                    "class_name": CLASS_NAMES[
                        class_ids[original_index]
                    ],
                    "confidence": scores[
                        original_index
                    ],
                    "box": boxes[
                        original_index
                    ],
                }
            )


# ============================================================
# Sort detections by confidence
# ============================================================

final_detections.sort(
    key=lambda d: d["confidence"],
    reverse=True
)


# ============================================================
# Print results
# ============================================================

print()
print("==============================")
print("FINAL DETECTIONS")
print("==============================")

if not final_detections:

    print("NO FIRE OR SMOKE DETECTED.")

else:

    for i, detection in enumerate(
        final_detections,
        start=1
    ):

        print(
            f"{i}. "
            f"{detection['class_name'].upper()} "
            f"| Confidence: "
            f"{detection['confidence'] * 100:.2f}% "
            f"| Box: "
            f"{detection['box']}"
        )


# ============================================================
# Draw detections
# ============================================================

result_image = original_image.copy()


for detection in final_detections:

    class_name = detection["class_name"]
    confidence = detection["confidence"]

    x, y, w, h = detection["box"]

    # Use OpenCV default color.
    # Different classes are visually distinguished
    # through their labels.

    cv2.rectangle(
        result_image,
        (x, y),
        (x + w, y + h),
        (0, 255, 0),
        2
    )

    label = (
        f"{class_name.upper()} "
        f"{confidence * 100:.1f}%"
    )

    text_y = max(
        y - 10,
        20
    )

    cv2.putText(
        result_image,
        label,
        (x, text_y),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 255, 0),
        2
    )


# ============================================================
# Overall status
# ============================================================

fire_detected = any(
    d["class_id"] == 0
    for d in final_detections
)

smoke_detected = any(
    d["class_id"] == 1
    for d in final_detections
)


print()
print("==============================")
print("FIRE SCOUT STATUS")
print("==============================")

if fire_detected:

    fire_scores = [
        d["confidence"]
        for d in final_detections
        if d["class_id"] == 0
    ]

    highest_fire = max(
        fire_scores
    )

    print(
        f"🔥 FIRE DETECTED "
        f"({highest_fire * 100:.2f}%)"
    )

elif smoke_detected:

    smoke_scores = [
        d["confidence"]
        for d in final_detections
        if d["class_id"] == 1
    ]

    highest_smoke = max(
        smoke_scores
    )

    print(
        f"SMOKE DETECTED "
        f"({highest_smoke * 100:.2f}%)"
    )

else:

    print("CLEAR")


# ============================================================
# Save result
# ============================================================

cv2.imwrite(
    OUTPUT_PATH,
    result_image
)

print()
print(
    f"Result saved to:\n{OUTPUT_PATH}"
)

print()
print("Detection test complete.")
