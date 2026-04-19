import csv
import json
import os
import time
from pathlib import Path

import paho.mqtt.client as mqtt


OUTPUT_FILE = Path(
    os.getenv(
        "OUTPUT_FILE",
        "results_local.csv",
    )
)

MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "waste/detections")
MQTT_ACK_TOPIC = os.getenv("MQTT_ACK_TOPIC", "waste/acks")

CSV_HEADERS = [
    "received_at",
    "run_id",
    "message_id",
    "image_name",
    "publisher_timestamp_sent",
    "publisher_publish_started_at",
    "detections_count",
    "top_class",
    "top_confidence",
    "inference_ms",
    "payload_size_bytes",
    "ack_published_at",
]


def ensure_csv_exists():
    if not OUTPUT_FILE.exists():
        with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
            writer.writeheader()


def append_row(row: dict):
    with open(OUTPUT_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        writer.writerow(row)


def on_message(client, userdata, msg):
    received_at = time.time()
    payload = json.loads(msg.payload.decode())

    detections = payload.get("detections", [])
    detections_count = payload.get("detections_count", len(detections))

    top_class = ""
    top_confidence = ""

    if detections:
        top_detection = max(detections, key=lambda d: d.get("confidence", 0))
        top_class = top_detection.get("class_name", "")
        top_confidence = top_detection.get("confidence", "")

    row = {
        "received_at": round(received_at, 6),
        "run_id": payload.get("run_id", ""),
        "message_id": payload.get("message_id", ""),
        "image_name": payload.get("image_name", ""),
        "publisher_timestamp_sent": payload.get("timestamp_sent", ""),
        "publisher_publish_started_at": payload.get("publish_started_at", ""),
        "detections_count": detections_count,
        "top_class": top_class,
        "top_confidence": top_confidence,
        "inference_ms": payload.get("inference_ms", ""),
        "payload_size_bytes": payload.get("payload_size_bytes", ""),
        "ack_published_at": "",
    }

    ack_published_at = time.time()
    ack_payload = {
        "run_id": payload.get("run_id", ""),
        "message_id": payload.get("message_id", ""),
        "subscriber_received_at": received_at,
        "ack_received_at": received_at,
        "ack_published_at": ack_published_at,
    }
    client.publish(MQTT_ACK_TOPIC, json.dumps(ack_payload))

    row["ack_published_at"] = round(ack_published_at, 6)
    append_row(row)

    print("----- MESSAGE RECEIVED -----")
    print(f"Topic: {msg.topic}")
    print(f"Run ID: {row['run_id']}")
    print(f"Message ID: {row['message_id']}")
    print(f"Image: {row['image_name']}")
    print(f"Detections: {row['detections_count']}")
    print(f"Top class: {row['top_class']}")
    print(f"Top confidence: {row['top_confidence']}")
    print(f"Inference ms: {row['inference_ms']}")
    print(f"Payload size bytes: {row['payload_size_bytes']}")
    print(f"Saved to: {OUTPUT_FILE}")


ensure_csv_exists()

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_message = on_message
print(f"Connecting to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}")
print(f"Subscribing to topic: {MQTT_TOPIC}")
client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.subscribe(MQTT_TOPIC)
client.loop_forever()
