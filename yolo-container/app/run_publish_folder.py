import csv
from html import escape
import json
import os
import time
from pathlib import Path

import paho.mqtt.client as mqtt
from PIL import Image
from ultralytics import YOLO


MQTT_BROKER = os.getenv("MQTT_BROKER", "host.docker.internal")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "waste/detections")
MQTT_ACK_TOPIC = os.getenv("MQTT_ACK_TOPIC", "waste/acks")

MODEL_PATH = os.getenv("MODEL_PATH", "/app/models/best.pt")
IMAGE_DIR = os.getenv("IMAGE_DIR", "/app/test-images")
RUN_ID = os.getenv("RUN_ID", f"run_{int(time.time())}")
ACK_TIMEOUT_SECONDS = float(os.getenv("ACK_TIMEOUT_SECONDS", "5"))

OUTPUT_FILE = Path(os.getenv("OUTPUT_FILE", "/app/results_roundtrip.csv"))
ANNOTATED_OUTPUT_DIR = Path(os.getenv("ANNOTATED_OUTPUT_DIR", "/app/results_images"))
HTML_REPORT_FILE = Path(os.getenv("HTML_REPORT_FILE", "/app/results_report.html"))

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png"}

pending_acks = {}
ack_results = {}

CSV_HEADERS = [
    "run_id",
    "message_id",
    "image_name",
    "detections_count",
    "top_class",
    "top_confidence",
    "inference_started_at",
    "inference_finished_at",
    "inference_ms",
    "payload_size_bytes",
    "publish_started_at",
    "publish_confirmed_at",
    "subscriber_received_at",
    "subscriber_ack_published_at",
    "publisher_ack_received_at",
    "publish_to_subscriber_ms",
    "subscriber_ack_processing_ms",
    "ack_return_ms",
    "roundtrip_ms",
]


def env_flag(name: str, default: str = "true") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


SAVE_ANNOTATED_IMAGES = env_flag("SAVE_ANNOTATED_IMAGES", "true")
WRITE_HTML_REPORT = env_flag("WRITE_HTML_REPORT", "true")


def ensure_csv_exists():
    if not OUTPUT_FILE.exists():
        OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
            writer.writeheader()


def append_row(row: dict):
    with open(OUTPUT_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        writer.writerow(row)


def on_message(client, userdata, msg):
    payload = json.loads(msg.payload.decode())

    if msg.topic == MQTT_ACK_TOPIC:
        message_id = payload.get("message_id")
        if message_id in pending_acks:
            ack_results[message_id] = {
                "publisher_ack_received_at": time.time(),
                "subscriber_received_at": payload.get("subscriber_received_at")
                or payload.get("ack_received_at"),
                "subscriber_ack_published_at": payload.get("ack_published_at"),
            }


def build_payload(
    run_id: str,
    message_id: int,
    image_name: str,
    detections: list,
    inference_ms: float,
    publish_started_at: float,
) -> dict:
    payload = {
        "run_id": run_id,
        "message_id": message_id,
        "timestamp_sent": time.time(),
        "publish_started_at": publish_started_at,
        "source": "yolo-container",
        "image_name": image_name,
        "inference_ms": round(inference_ms, 2),
        "detections_count": len(detections),
        "detections": detections,
    }
    payload["payload_size_bytes"] = len(json.dumps(payload).encode("utf-8"))
    return payload


def extract_detections(result, class_names: dict) -> list:
    detections = []

    if result.boxes is None:
        return detections

    for box in result.boxes:
        cls_id = int(box.cls[0].item())
        confidence = float(box.conf[0].item())
        xyxy = box.xyxy[0].tolist()

        detections.append(
            {
                "class_id": cls_id,
                "class_name": class_names.get(cls_id, str(cls_id)),
                "confidence": round(confidence, 4),
                "bbox": [round(v, 2) for v in xyxy],
            }
        )

    return detections


def get_top_detection(detections: list):
    if not detections:
        return "", ""
    top_detection = max(detections, key=lambda d: d.get("confidence", 0))
    return top_detection.get("class_name", ""), top_detection.get("confidence", "")


def save_annotated_image(result, image_path: Path, output_dir: Path, message_id: int) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{message_id:04d}_{image_path.stem}_annotated.jpg"

    annotated_bgr = result.plot()
    annotated_rgb = annotated_bgr[:, :, ::-1]
    Image.fromarray(annotated_rgb).save(output_path, quality=90)

    return output_path


def write_html_report(report_file: Path, rows: list[dict]) -> None:
    report_file.parent.mkdir(parents=True, exist_ok=True)

    cards = []
    for row in rows:
        annotated_image_path = row.get("annotated_image_path", "")
        if annotated_image_path:
            image_src = os.path.relpath(annotated_image_path, report_file.parent)
            image_src = image_src.replace("\\", "/")
            image_markup = f'<img src="{escape(image_src)}" alt="{escape(row["image_name"])}">'
        else:
            image_markup = "<p>No annotated image saved.</p>"

        top_class = row.get("top_class") or "none"
        top_confidence = row.get("top_confidence") or ""
        roundtrip_ms = row.get("roundtrip_ms") or "timeout"

        cards.append(
            f"""
            <article>
              <h2>{escape(str(row["message_id"]))}. {escape(row["image_name"])}</h2>
              {image_markup}
              <p>
                detections: {escape(str(row["detections_count"]))}<br>
                top: {escape(str(top_class))} {escape(str(top_confidence))}<br>
                inference_ms: {escape(str(row["inference_ms"]))}<br>
                roundtrip_ms: {escape(str(roundtrip_ms))}
              </p>
            </article>
            """
        )

    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>YOLO MQTT benchmark report</title>
  <style>
    body {{
      margin: 0;
      font-family: Arial, sans-serif;
      background: #f6f7f9;
      color: #171717;
    }}
    main {{
      max-width: 1200px;
      margin: 0 auto;
      padding: 24px;
    }}
    h1 {{
      margin: 0 0 20px;
      font-size: 28px;
    }}
    section {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 16px;
    }}
    article {{
      background: #ffffff;
      border: 1px solid #d7dce2;
      border-radius: 8px;
      overflow: hidden;
    }}
    h2 {{
      margin: 12px;
      font-size: 16px;
    }}
    img {{
      display: block;
      width: 100%;
      height: auto;
    }}
    p {{
      margin: 12px;
      line-height: 1.45;
    }}
  </style>
</head>
<body>
  <main>
    <h1>YOLO MQTT benchmark report</h1>
    <section>
      {''.join(cards)}
    </section>
  </main>
</body>
</html>
"""

    report_file.write_text(html, encoding="utf-8")


def wait_for_ack(message_id: int, timeout_seconds: float):
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if message_id in ack_results:
            return ack_results.pop(message_id)
        time.sleep(0.01)
    return None


def main():
    ensure_csv_exists()

    image_dir = Path(IMAGE_DIR)

    if not image_dir.exists():
        raise FileNotFoundError(f"Image directory not found: {image_dir}")

    image_files = sorted(
        [p for p in image_dir.iterdir() if p.suffix.lower() in SUPPORTED_EXTENSIONS]
    )

    if not image_files:
        raise FileNotFoundError(f"No supported images found in: {image_dir}")

    print(f"Found {len(image_files)} images in: {image_dir}")
    if SAVE_ANNOTATED_IMAGES:
        print(f"Annotated images will be saved to: {ANNOTATED_OUTPUT_DIR}")
    if WRITE_HTML_REPORT:
        print(f"HTML report will be saved to: {HTML_REPORT_FILE}")

    print(f"Loading model from: {MODEL_PATH}")
    model = YOLO(MODEL_PATH)

    print(f"Connecting to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}")
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.subscribe(MQTT_ACK_TOPIC)
    client.loop_start()

    report_rows = []

    try:
        for message_id, image_path in enumerate(image_files, start=1):
            print(f"Processing image {message_id}/{len(image_files)}: {image_path.name}")

            inference_started_at = time.time()
            results = model.predict(
                source=str(image_path),
                verbose=False,
                save=False,
            )
            inference_finished_at = time.time()

            inference_ms = (inference_finished_at - inference_started_at) * 1000
            result = results[0]

            detections = extract_detections(result, model.names)
            annotated_image_path = ""

            if SAVE_ANNOTATED_IMAGES:
                annotated_image_path = save_annotated_image(
                    result=result,
                    image_path=image_path,
                    output_dir=ANNOTATED_OUTPUT_DIR,
                    message_id=message_id,
                )

            publish_started_at = time.time()
            payload = build_payload(
                run_id=RUN_ID,
                message_id=message_id,
                image_name=image_path.name,
                detections=detections,
                inference_ms=inference_ms,
                publish_started_at=publish_started_at,
            )

            payload_json = json.dumps(payload)

            pending_acks[message_id] = publish_started_at

            message_info = client.publish(MQTT_TOPIC, payload_json)
            message_info.wait_for_publish()
            publish_confirmed_at = time.time()

            ack_result = wait_for_ack(message_id, ACK_TIMEOUT_SECONDS)

            top_class, top_confidence = get_top_detection(detections)

            subscriber_received_at = ""
            subscriber_ack_published_at = ""
            publisher_ack_received_at = ""
            publish_to_subscriber_ms = ""
            subscriber_ack_processing_ms = ""
            ack_return_ms = ""
            roundtrip_ms = ""

            if ack_result is not None:
                subscriber_received_at = ack_result.get("subscriber_received_at") or ""
                subscriber_ack_published_at = (
                    ack_result.get("subscriber_ack_published_at") or ""
                )
                publisher_ack_received_at = ack_result["publisher_ack_received_at"]
                roundtrip_ms = round(
                    (publisher_ack_received_at - publish_started_at) * 1000,
                    2,
                )

                if subscriber_received_at:
                    publish_to_subscriber_ms = round(
                        (float(subscriber_received_at) - publish_started_at) * 1000,
                        2,
                    )

                if subscriber_received_at and subscriber_ack_published_at:
                    subscriber_ack_processing_ms = round(
                        (
                            float(subscriber_ack_published_at)
                            - float(subscriber_received_at)
                        )
                        * 1000,
                        2,
                    )

                if subscriber_ack_published_at:
                    ack_return_ms = round(
                        (
                            publisher_ack_received_at
                            - float(subscriber_ack_published_at)
                        )
                        * 1000,
                        2,
                    )

            row = {
                "run_id": RUN_ID,
                "message_id": message_id,
                "image_name": image_path.name,
                "detections_count": len(detections),
                "top_class": top_class,
                "top_confidence": top_confidence,
                "inference_started_at": round(inference_started_at, 6),
                "inference_finished_at": round(inference_finished_at, 6),
                "inference_ms": round(inference_ms, 2),
                "payload_size_bytes": payload.get("payload_size_bytes", ""),
                "publish_started_at": round(publish_started_at, 6),
                "publish_confirmed_at": round(publish_confirmed_at, 6),
                "subscriber_received_at": (
                    round(float(subscriber_received_at), 6)
                    if subscriber_received_at
                    else ""
                ),
                "subscriber_ack_published_at": (
                    round(float(subscriber_ack_published_at), 6)
                    if subscriber_ack_published_at
                    else ""
                ),
                "publisher_ack_received_at": (
                    round(float(publisher_ack_received_at), 6)
                    if publisher_ack_received_at
                    else ""
                ),
                "publish_to_subscriber_ms": publish_to_subscriber_ms,
                "subscriber_ack_processing_ms": subscriber_ack_processing_ms,
                "ack_return_ms": ack_return_ms,
                "roundtrip_ms": roundtrip_ms,
            }

            append_row(row)
            report_row = {**row, "annotated_image_path": annotated_image_path}
            report_rows.append(report_row)

            print(
                f"Published message_id={message_id} image={image_path.name} "
                f"detections={len(detections)} top_class={top_class or 'none'} "
                f"publish_to_subscriber_ms={publish_to_subscriber_ms or 'timeout'} "
                f"ack_return_ms={ack_return_ms or 'timeout'} "
                f"roundtrip_ms={roundtrip_ms or 'timeout'}"
            )
            if annotated_image_path:
                print(f"Annotated image: {annotated_image_path}")

            pending_acks.pop(message_id, None)

    finally:
        client.loop_stop()
        client.disconnect()

    if WRITE_HTML_REPORT:
        write_html_report(HTML_REPORT_FILE, report_rows)
        print(f"HTML report saved to: {HTML_REPORT_FILE}")


if __name__ == "__main__":
    main()
