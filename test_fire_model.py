import cv2
import numpy as np
import tensorflow as tf

MODEL_PATH = r"C:\FireScout_ROS\models\best.tflite"
IMAGE_PATH = r"C:\FireScout_ROS\test_fire.jpg"

# ---------------------------------------------------------
# Load model
# ---------------------------------------------------------

interpreter = tf.lite.Interpreter(model_path=MODEL_PATH)
interpreter.allocate_tensors()

input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

print("Model loaded.")
print("Input:", input_details[0]["shape"])
print("Output:", output_details[0]["shape"])

# ---------------------------------------------------------
# Load image
# ---------------------------------------------------------

image = cv2.imread(IMAGE_PATH)

if image is None:
    raise FileNotFoundError(
        f"Could not find image: {IMAGE_PATH}"
    )

original = image.copy()

# ---------------------------------------------------------
# Prepare image
# ---------------------------------------------------------

image = cv2.resize(image, (320, 320))

# OpenCV = BGR
# YOLO/TFLite model expects normalized float32
image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

image = image.astype(np.float32) / 255.0

# Model input is NCHW:
# [1, 3, 320, 320]
image = np.transpose(image, (2, 0, 1))

image = np.expand_dims(image, axis=0)

# ---------------------------------------------------------
# Run inference
# ---------------------------------------------------------

interpreter.set_tensor(
    input_details[0]["index"],
    image
)

interpreter.invoke()

output = interpreter.get_tensor(
    output_details[0]["index"]
)

print("Raw output shape:", output.shape)
print(
    "Raw output range:",
    output.min(),
    "to",
    output.max()
)

# ---------------------------------------------------------
# Convert:
# [1, 6, 2100]
# ->
# [2100, 6]
# ---------------------------------------------------------

predictions = output[0].T

print("Number of predictions:", len(predictions))

# ---------------------------------------------------------
# Print strongest predictions
# ---------------------------------------------------------

# Find the largest value in each prediction.
scores = predictions[:, 4:].max(axis=1)

# Sort strongest first.
indices = np.argsort(scores)[::-1]

print()
print("Top 20 predictions:")
print("--------------------")

for rank, index in enumerate(indices[:20], start=1):

    prediction = predictions[index]

    print(
        f"{rank:02d}: "
        f"x={prediction[0]:.4f}, "
        f"y={prediction[1]:.4f}, "
        f"w={prediction[2]:.4f}, "
        f"h={prediction[3]:.4f}, "
        f"class0={prediction[4]:.6f}, "
        f"class1={prediction[5]:.6f}"
    )

print()
print("Highest class-0 score:", predictions[:, 4].max())
print("Highest class-1 score:", predictions[:, 5].max())

# ---------------------------------------------------------
# Determine strongest class
# ---------------------------------------------------------

class0_index = np.argmax(predictions[:, 4])
class1_index = np.argmax(predictions[:, 5])

class0_score = predictions[class0_index, 4]
class1_score = predictions[class1_index, 5]

print()
print("Strongest class-0 prediction:")
print(predictions[class0_index])

print()
print("Strongest class-1 prediction:")
print(predictions[class1_index])

# ---------------------------------------------------------
# Simple detection test
# ---------------------------------------------------------

CONFIDENCE_THRESHOLD = 0.25

if class0_score >= CONFIDENCE_THRESHOLD:
    print(
        f"\nCLASS 0 DETECTED "
        f"(confidence={class0_score:.3f})"
    )

if class1_score >= CONFIDENCE_THRESHOLD:
    print(
        f"\nCLASS 1 DETECTED "
        f"(confidence={class1_score:.3f})"
    )

if (
    class0_score < CONFIDENCE_THRESHOLD
    and class1_score < CONFIDENCE_THRESHOLD
):
    print(
        f"\nNO DETECTION ABOVE "
        f"{CONFIDENCE_THRESHOLD:.2f}"
    )