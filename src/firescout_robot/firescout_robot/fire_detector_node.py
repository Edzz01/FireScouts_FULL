import cv2
import numpy as np
import tensorflow as tf

import rclpy
from rclpy.node import Node

from std_msgs.msg import Bool, Float32, String


MODEL_PATH = r"C:\FireScout_ROS\models\best.tflite"

INPUT_SIZE = 320
CONF_THRESHOLD = 0.25
IOU_THRESHOLD = 0.45


CLASS_NAMES = {
    0: "fire",
    1: "smoke",
}


class FireDetectorNode(Node):

    def __init__(self):
        super().__init__("fire_detector")

        self.get_logger().info("Loading FireScout TFLite model...")

        self.interpreter = tf.lite.Interpreter(
            model_path=MODEL_PATH
        )

        self.interpreter.allocate_tensors()

        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()

        self.get_logger().info(
            f"Model input: {self.input_details[0]['shape']}"
        )

        self.get_logger().info(
            f"Model output: {self.output_details[0]['shape']}"
        )

        # ROS publishers

        self.fire_pub = self.create_publisher(
            Bool,
            "fire/detected",
            10
        )

        self.class_pub = self.create_publisher(
            String,
            "fire/class",
            10
        )

        self.confidence_pub = self.create_publisher(
            Float32,
            "fire/confidence",
            10
        )
        self.center_x_pub = self.create_publisher(
            Float32,
            "fire/center_x",
            10
        )

        self.center_y_pub = self.create_publisher(
            Float32,
            "fire/center_y",
            10
        )

        # Open computer camera

        self.camera = cv2.VideoCapture(0)

        if not self.camera.isOpened():
            self.get_logger().error(
                "Could not open camera."
            )
            raise RuntimeError(
                "Could not open camera."
            )

        self.get_logger().info(
            "Camera opened successfully."
        )

        # Run detection approximately 10 times per second.

        self.timer = self.create_timer(
            0.1,
            self.process_frame
        )

        self.get_logger().info(
            "FireScout AI detector started."
        )

    def preprocess(self, frame):

        resized = cv2.resize(
            frame,
            (INPUT_SIZE, INPUT_SIZE)
        )

        rgb = cv2.cvtColor(
            resized,
            cv2.COLOR_BGR2RGB
        )

        image = rgb.astype(
            np.float32
        ) / 255.0

        # Model expects NCHW:
        # [1, 3, 320, 320]

        image = np.transpose(
            image,
            (2, 0, 1)
        )

        image = np.expand_dims(
            image,
            axis=0
        )

        return image.astype(
            self.input_details[0]["dtype"]
        )

    def calculate_iou(self, box1, box2):

        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])

        intersection = max(
            0,
            x2 - x1
        ) * max(
            0,
            y2 - y1
        )

        area1 = max(
            0,
            box1[2] - box1[0]
        ) * max(
            0,
            box1[3] - box1[1]
        )

        area2 = max(
            0,
            box2[2] - box2[0]
        ) * max(
            0,
            box2[3] - box2[1]
        )

        union = area1 + area2 - intersection

        if union <= 0:
            return 0.0

        return intersection / union

    def nms(
        self,
        boxes,
        scores,
        class_ids
    ):

        keep = []

        if not boxes:
            return keep

        for class_id in set(class_ids):

            indices = [
                i
                for i, cid in enumerate(class_ids)
                if cid == class_id
            ]

            indices.sort(
                key=lambda i: scores[i],
                reverse=True
            )

            while indices:

                current = indices.pop(0)

                keep.append(current)

                remaining = []

                for i in indices:

                    iou = self.calculate_iou(
                        boxes[current],
                        boxes[i]
                    )

                    if iou < IOU_THRESHOLD:
                        remaining.append(i)

                indices = remaining

        return keep

    def detect(self, frame):

        input_tensor = self.preprocess(
            frame
        )

        self.interpreter.set_tensor(
            self.input_details[0]["index"],
            input_tensor
        )

        self.interpreter.invoke()

        output = self.interpreter.get_tensor(
            self.output_details[0]["index"]
        )

        # [1, 6, 2100]
        predictions = output[0].transpose(
            1,
            0
        )

        height, width = frame.shape[:2]

        boxes = []
        scores = []
        class_ids = []

        for prediction in predictions:

            x_center = float(
                prediction[0]
            )

            y_center = float(
                prediction[1]
            )

            box_width = float(
                prediction[2]
            )

            box_height = float(
                prediction[3]
            )

            class_scores = prediction[4:]

            class_id = int(
                np.argmax(class_scores)
            )

            confidence = float(
                class_scores[class_id]
            )

            if confidence < CONF_THRESHOLD:
                continue

            # Convert YOLO coordinates.

            x1 = (
                x_center - box_width / 2
            )

            y1 = (
                y_center - box_height / 2
            )

            x2 = (
                x_center + box_width / 2
            )

            y2 = (
                y_center + box_height / 2
            )

            # Model output is based on 320x320.

            x1 = int(
                x1 * width
            )

            y1 = int(
                y1 * height
            )

            x2 = int(
                x2 * width
            )

            y2 = int(
                y2 * height
            )

            x1 = max(
                0,
                min(width - 1, x1)
            )

            y1 = max(
                0,
                min(height - 1, y1)
            )

            x2 = max(
                0,
                min(width - 1, x2)
            )

            y2 = max(
                0,
                min(height - 1, y2)
            )

            if x2 <= x1 or y2 <= y1:
                continue

            boxes.append(
                [x1, y1, x2, y2]
            )

            scores.append(
                confidence
            )

            class_ids.append(
                class_id
            )

        keep = self.nms(
            boxes,
            scores,
            class_ids
        )

        detections = []

        for i in keep:

            detections.append({
                "box": boxes[i],
                "confidence": scores[i],
                "class_id": class_ids[i],
                "class_name": CLASS_NAMES[
                    class_ids[i]
                ]
            })

        return detections

    def process_frame(self):

        ret, frame = self.camera.read()

        if not ret:
            self.get_logger().warning(
                "Could not read camera frame."
            )
            return

        detections = self.detect(
            frame
        )

        fire_detected = False
        highest_confidence = 0.0
        detected_class = "none"
        best_box = None

        for detection in detections:

            class_name = detection[
                "class_name"
            ]

            confidence = detection[
                "confidence"
            ]

            x1, y1, x2, y2 = detection[
                "box"
            ]

            label = (
                f"{class_name.upper()} "
                f"{confidence:.2f}"
            )

            cv2.rectangle(
                frame,
                (x1, y1),
                (x2, y2),
                (0, 0, 255),
                2
            )

            cv2.putText(
                frame,
                label,
                (x1, max(30, y1 - 10)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 0, 255),
                2
            )

            if confidence > highest_confidence:

                highest_confidence = confidence

                detected_class = class_name

                best_box = detection["box"]

            if class_name == "fire":

                fire_detected = True

        # Publish fire status.

        fire_msg = Bool()

        fire_msg.data = fire_detected

        self.fire_pub.publish(
            fire_msg
        )

        # Publish class.

        class_msg = String()

        class_msg.data = detected_class

        self.class_pub.publish(
            class_msg
        )

        # Publish confidence.

        confidence_msg = Float32()

        confidence_msg.data = (
            highest_confidence
        )

        self.confidence_pub.publish(
            confidence_msg
        )

        # Publish center position of strongest FIRE detection

        center_x_msg = Float32()
        center_y_msg = Float32()

        if best_box is not None and detected_class == "fire":

            x1, y1, x2, y2 = best_box

            center_x = (x1 + x2) / 2.0
            center_y = (y1 + y2) / 2.0

            center_x_msg.data = center_x
            center_y_msg.data = center_y

        else:

            center_x_msg.data = -1.0
            center_y_msg.data = -1.0

        self.center_x_pub.publish(center_x_msg)
        self.center_y_pub.publish(center_y_msg)

        # Display camera.

        cv2.imshow(
            "FireScout AI",
            frame
        )

        key = cv2.waitKey(1)

        if key == ord("q"):

            self.get_logger().info(
                "Stopping FireScout AI detector."
            )

            rclpy.shutdown()

    def destroy_node(self):

        if hasattr(self, "camera"):
            self.camera.release()

        cv2.destroyAllWindows()

        super().destroy_node()


def main(args=None):

    rclpy.init(
        args=args
    )

    node = FireDetectorNode()

    try:

        rclpy.spin(
            node
        )

    except KeyboardInterrupt:

        pass

    finally:

        node.destroy_node()

        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()