# FireScout — AI-Powered Autonomous Fire-Fighting Robot

FireScout is an autonomous fire-fighting robot project that combines **Artificial Intelligence, ROS 2, Arduino Mega, sensors, servo-based aiming, and an automated fire-extinguisher mechanism**.

The system is designed to detect a potential fire using both **AI-based visual detection** and **environmental sensors**, determine an appropriate response, navigate toward the detected fire, aim the extinguisher using two servo motors, and activate the extinguisher using a third servo motor.

---

## 🚒 System Overview

FireScout uses a layered control architecture:

```text
                    ┌─────────────────────┐
                    │     Camera / AI     │
                    │   Fire Detection    │
                    └──────────┬──────────┘
                               │
                 /fire/detected
                 /fire/class
                 /fire/confidence
                 /fire/center_x
                 /fire/center_y
                               │
                               ▼
                    ┌─────────────────────┐
                    │   Fire Response    │
                    │     Coordinator     │
                    └──────────┬──────────┘
                               │
                         /robot/action
                               │
              ┌────────────────┴────────────────┐
              ▼                                 ▼
     ┌─────────────────┐              ┌─────────────────┐
     │ Robot Controller│              │ Aim Controller  │
     └────────┬────────┘              └────────┬────────┘
              │                                │
          /cmd_vel                    /aim/servo_x
              │                       /aim/servo_y
              │                                │
              ▼                                ▼
     ┌─────────────────┐              ┌─────────────────┐
     │ Arduino Bridge  │              │  X/Y Servos     │
     │ / Motor Control │              │  Aiming System  │
     └────────┬────────┘              └─────────────────┘
              │
              ▼
        Arduino Mega
              │
       ┌──────┴────────┐
       │               │
    L298N          Sensors
       │
   DC Motors

                    ┌─────────────────────┐
                    │ Extinguisher        │
                    │ Controller          │
                    └──────────┬──────────┘
                               │
                     /extinguisher/servo
                               │
                               ▼
                       Extinguisher Servo
```

---

# ✨ Main Features

* 🔥 AI-based fire detection
* 📷 Camera-based fire localization
* 🎯 Automatic X/Y aiming system
* 🤖 Autonomous robot movement
* 🌡️ Temperature monitoring
* 💨 Gas/smoke monitoring using MQ-2
* 🚗 Differential-drive motor control
* 🧯 Automatic extinguisher activation
* 🧠 ROS 2 node-based architecture
* 🔌 Arduino Mega hardware interface
* 🌐 ROS-compatible communication architecture
* 🛡️ Multiple conditions required before extinguisher activation

---

# 🧠 Software Architecture

FireScout is built using **ROS 2 Jazzy**.

The major ROS nodes are:

| Node                      | Purpose                                                      |
| ------------------------- | ------------------------------------------------------------ |
| `fire_detector`           | AI-based camera fire detection                               |
| `fire_decision`           | Determines fire status from temperature and gas              |
| `fire_response`           | Combines AI and sensor information to determine robot action |
| `robot_controller`        | Converts robot actions into movement commands                |
| `arduino_bridge`          | Interface between ROS and Arduino/motor system               |
| `aim_controller`          | Controls X/Y fire-extinguisher aiming                        |
| `extinguisher_controller` | Controls automatic extinguisher activation                   |
| `sensor_node`             | Sensor interface                                             |
| `sensor_simulator`        | Provides simulated sensor data during development            |
| `motor_controller`        | Motor-control layer                                          |
| `robot_state`             | Robot state management                                       |
| `robot_status`            | Robot status information                                     |
| `web_bridge`              | Web/ROS communication interface                              |

---

# 🔥 AI Fire Detection

The `fire_detector` node uses a TensorFlow Lite model to detect fire from the camera.

The current detector uses a:

```text
Input:  1 × 3 × 320 × 320
Output: 1 × 6 × 2100
```

The detector publishes:

```text
/fire/detected
/fire/class
/fire/confidence
/fire/center_x
/fire/center_y
```

The center coordinates are used by the aiming system.

For a 320 × 320 image:

```text
Image center X = 160
Image center Y = 160
```

---

# 🎯 Automatic Aiming System

The `aim_controller` receives:

```text
/fire/detected
/fire/class
/fire/confidence
/fire/center_x
/fire/center_y
```

It calculates the difference between the detected fire position and the center of the camera frame.

It then controls:

```text
/aim/servo_x
/aim/servo_y
```

The system uses:

* X-axis servo
* Y-axis servo
* 2° movement step
* 20-pixel dead zone
* Minimum confidence of 0.50

When the fire is sufficiently centered:

```text
AIM_LOCKED
```

is generated.

---

# 🧯 Automatic Extinguisher

The `extinguisher_controller` controls the third servo.

The extinguisher is **not activated simply because AI detects fire**.

Activation requires:

```text
FIRE_CONFIRMED
        +
AIM_LOCKED
```

The default servo positions are:

```text
Released = 0°
Activated = 90°
```

The default activation duration is:

```text
3 seconds
```

After activation, the servo automatically returns to the release position.

---

# 🤖 Fire Response Logic

The `fire_response` node combines AI and sensor information.

### AI fire condition

```text
AI detects fire
AND
class = fire
AND
confidence >= 0.50
```

### Strong sensor fire condition

```text
Temperature >= 40°C
AND
Gas >= 600
```

### Warning condition

```text
Temperature >= 35°C
OR
Gas >= 500
```

The resulting actions are:

| Condition                 | Robot Action     |
| ------------------------- | ---------------- |
| AI + sensors confirm fire | `FIRE_CONFIRMED` |
| AI detects fire           | `APPROACH_FIRE`  |
| Sensors indicate fire     | `SEARCH_FIRE`    |
| Elevated sensor values    | `CAUTION`        |
| No danger detected        | `SEARCH`         |

---

# 🚗 Robot Controller

The `robot_controller` receives:

```text
/robot/action
```

and publishes:

```text
/cmd_vel
```

The robot uses differential-drive movement.

Example:

```text
SEARCH
→ Rotate/search

APPROACH_FIRE
→ Move forward

SEARCH_FIRE
→ Slow search

CAUTION
→ Slow movement

FIRE_CONFIRMED
→ Stop
```

Stopping the robot before extinguishing is an important safety condition.

---

# 🔌 Arduino Mega

The physical robot uses an **Arduino Mega** as the low-level hardware controller.

The Arduino is intended to control:

* DC motors
* L298N motor driver
* X-axis aiming servo
* Y-axis aiming servo
* Extinguisher servo
* Ultrasonic sensors
* MQ-2 gas sensor
* Other physical sensors

The ROS side communicates with the Arduino through the Arduino bridge.

---

# ⚙️ Motor System

The robot uses an L298N motor driver.

The motors are configured as differential drive:

```text
Left motors  → Left channel
Right motors → Right channel
```

Two motors are connected to each side.

ROS sends:

```text
/cmd_vel
```

The Arduino bridge converts the movement command into left/right motor commands.

---

# 🌡️ Environmental Sensors

The system includes environmental sensing for additional fire confirmation.

Current ROS topics include:

```text
/sensor/temperature
/sensor/gas
/sensor/distance
```

The MQ-2 gas sensor provides the gas/smoke measurement.

The sensor information is combined with AI detection instead of relying on only one detection method.

---

# 📡 ROS 2 Topics

Current major topics include:

```text
/aim/servo_x
/aim/servo_y
/aim/status

/cmd_vel

/extinguisher/servo
/extinguisher/status

/fire/center_x
/fire/center_y
/fire/class
/fire/confidence
/fire/detected
/fire/response
/fire/status

/robot/action

/sensor/distance
/sensor/gas
/sensor/temperature
```

---

# 🛠️ Development Environment

The ROS 2 development environment was developed and tested on Windows using:

```text
Windows 11
ROS 2 Jazzy
Python 3.12
Pixi environment
Cyclone DDS
colcon
```

The ROS workspace is:

```text
C:\FireScout_ROS
```

The ROS 2 installation is located under:

```text
C:\pixi_ws\ros2-windows
```

The development environment uses:

```text
RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
```

---

# 📁 Project Structure

The main ROS package is:

```text
FireScout_FULL/
└── src/
    └── firescout_robot/
        ├── firescout_robot/
        │   ├── fire_detector.py
        │   ├── fire_decision.py
        │   ├── fire_response.py
        │   ├── robot_controller.py
        │   ├── arduino_bridge.py
        │   ├── aim_controller.py
        │   ├── extinguisher_controller.py
        │   ├── sensor_node.py
        │   ├── sensor_simulator.py
        │   ├── motor_controller.py
        │   ├── robot_state.py
        │   ├── robot_status.py
        │   └── web_bridge.py
        │
        ├── resource/
        ├── package.xml
        ├── setup.py
        └── setup.cfg
```

The exact repository structure may change as development continues.

---

# 🧪 Development and Simulation

The project currently supports development using simulated components.

For example:

```text
sensor_simulator
```

can provide sensor values without requiring the physical sensors.

The `arduino_bridge` has also been developed initially as a simulated hardware interface.

This allows ROS logic to be developed before deployment to the physical Raspberry Pi/Arduino robot.

---

# 🥧 Planned Raspberry Pi Deployment

The final robot is intended to use a **Raspberry Pi 5** as the main computer.

The planned architecture is:

```text
                 Raspberry Pi 5
                       │
                    ROS 2
                       │
       ┌───────────────┼────────────────┐
       │               │                │
   AI Camera       Decision        Navigation
       │               │                │
       └───────────────┼────────────────┘
                       │
                Arduino Bridge
                       │
                  USB / Serial
                       │
                 Arduino Mega
                       │
       ┌───────────────┼─────────────────┐
       │               │                 │
    Motors          Sensors          Servos
```

The Raspberry Pi handles the high-level processing while the Arduino Mega handles low-level hardware control.

---

# ⚠️ Hardware Safety Notes

The physical system should use appropriate regulated power supplies.

The DC motors are rated approximately:

```text
3–6 V
```

Therefore, they should **not be directly supplied with an unsuitable 12 V motor voltage**.

The following components may also require an external regulated 5 V supply:

* X/Y servos
* Extinguisher servo
* HC-SR04 sensors
* Other 5 V peripherals

The Arduino, external sensor/servo supply, motor driver, and other components must share a suitable **common ground** where required.

Always verify the L298N logic-supply/`5VEN` configuration before powering the circuit.

---

# 🚧 Current Development Status

### Completed / Working

* ROS 2 workspace
* ROS 2 package
* Fire detector node
* TensorFlow Lite model loading
* AI detection topics
* Fire decision node
* Fire response coordinator
* Robot controller
* Arduino bridge simulation
* X/Y aiming controller
* Extinguisher controller
* ROS topic architecture
* ROS node architecture
* Motor command architecture
* Simulation/testing environment

### In Development

* Physical Arduino Mega communication
* Physical motor control
* Physical servo control
* Physical sensor integration
* Raspberry Pi 5 deployment
* Camera deployment on Raspberry Pi
* Final autonomous behavior
* Web interface integration
* Full hardware testing

---

# 🚀 Future Improvements

Potential future improvements include:

* Real Arduino serial communication
* Raspberry Pi 5 deployment
* ROS 2 launch files
* Automatic startup of all nodes
* Navigation and obstacle avoidance
* Improved fire localization
* Better fire-distance estimation
* PID-based servo aiming
* Fire-size/intensity estimation
* Improved AI model
* Physical extinguisher integration
* Web dashboard
* Robot telemetry
* Emergency-stop system
* Hardware watchdog
* Battery monitoring

---

# 📜 Project Goal

The ultimate goal of FireScout is to create a robotic platform capable of:

```text
Detect Fire
     ↓
Confirm Fire
     ↓
Locate Fire
     ↓
Navigate Toward Fire
     ↓
Stop Safely
     ↓
Aim Extinguisher
     ↓
Lock Target
     ↓
Activate Extinguisher
     ↓
Monitor Result
```

The project demonstrates the integration of **robotics, embedded systems, computer vision, artificial intelligence, ROS 2, sensors, motor control, and autonomous decision-making**.

---

## 👨‍💻 Project

**FireScout**

AI-Powered Autonomous Fire-Fighting Robot

Repository:

`https://github.com/Edzz01/FireScouts_FULL`
