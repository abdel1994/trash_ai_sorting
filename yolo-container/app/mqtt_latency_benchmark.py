import argparse
import csv
import json
import queue
import statistics
import time
import uuid
from pathlib import Path

import paho.mqtt.client as mqtt


CSV_HEADERS = [
    "label",
    "run_id",
    "message_id",
    "broker_host",
    "broker_port",
    "topic",
    "qos",
    "payload_size_bytes",
    "rtt_ms",
]


def build_payload(run_id: str, message_id: int, payload_size_bytes: int) -> bytes:
    payload = {
        "run_id": run_id,
        "message_id": message_id,
        "sent_at_unix": time.time(),
        "padding": "",
    }

    while True:
        encoded = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        missing_bytes = payload_size_bytes - len(encoded)
        if missing_bytes <= 0:
            return encoded
        payload["padding"] += "x" * missing_bytes


def write_rows(output_file: Path, rows: list[dict]) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    file_exists = output_file.exists()

    with open(output_file, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        if not file_exists:
            writer.writeheader()
        writer.writerows(rows)


def percentile(values: list[float], percent: float) -> float:
    if not values:
        return 0.0

    sorted_values = sorted(values)
    index = round((len(sorted_values) - 1) * percent)
    return sorted_values[index]


def print_summary(rows: list[dict]) -> None:
    rtts = [float(row["rtt_ms"]) for row in rows]

    print("")
    print("MQTT latency benchmark")
    print(f"messages: {len(rows)}")
    print(f"min_ms:   {min(rtts):.2f}")
    print(f"avg_ms:   {statistics.mean(rtts):.2f}")
    print(f"median_ms:{statistics.median(rtts):.2f}")
    print(f"p95_ms:   {percentile(rtts, 0.95):.2f}")
    print(f"max_ms:   {max(rtts):.2f}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Measure MQTT round-trip latency by publishing locally and subscribing locally through the same broker."
    )
    parser.add_argument("--broker-host", default="localhost")
    parser.add_argument("--broker-port", type=int, default=1883)
    parser.add_argument("--topic", default="benchmark/mqtt-latency")
    parser.add_argument("--messages", type=int, default=100)
    parser.add_argument("--warmup", type=int, default=5)
    parser.add_argument("--payload-bytes", type=int, default=512)
    parser.add_argument("--qos", type=int, choices=[0, 1, 2], default=0)
    parser.add_argument("--timeout-seconds", type=float, default=5.0)
    parser.add_argument("--label", default="mqtt-latency")
    parser.add_argument("--output-file", default="results_mqtt_latency.csv")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    run_id = f"{args.label}_{int(time.time())}_{uuid.uuid4().hex[:8]}"
    topic = f"{args.topic}/{run_id}"
    output_file = Path(args.output_file)

    received_messages: queue.Queue[tuple[int, int]] = queue.Queue()
    subscribed = queue.Queue(maxsize=1)

    def on_message(client, userdata, msg):
        received_at_ns = time.perf_counter_ns()
        payload = json.loads(msg.payload.decode("utf-8"))
        received_messages.put((payload["message_id"], received_at_ns))

    def on_subscribe(client, userdata, mid, reason_code_list, properties):
        subscribed.put(True)

    subscriber = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=f"{run_id}_subscriber",
    )
    publisher = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=f"{run_id}_publisher",
    )

    subscriber.on_message = on_message
    subscriber.on_subscribe = on_subscribe

    print(f"Connecting subscriber to {args.broker_host}:{args.broker_port}")
    subscriber.connect(args.broker_host, args.broker_port, 60)
    subscriber.loop_start()
    subscriber.subscribe(topic, qos=args.qos)
    subscribed.get(timeout=args.timeout_seconds)

    print(f"Connecting publisher to {args.broker_host}:{args.broker_port}")
    publisher.connect(args.broker_host, args.broker_port, 60)
    publisher.loop_start()

    rows = []

    try:
        total_messages = args.warmup + args.messages

        for message_id in range(1, total_messages + 1):
            payload = build_payload(run_id, message_id, args.payload_bytes)

            sent_at_ns = time.perf_counter_ns()
            publish_info = publisher.publish(topic, payload, qos=args.qos)
            publish_info.wait_for_publish(timeout=args.timeout_seconds)

            received_message_id, received_at_ns = received_messages.get(
                timeout=args.timeout_seconds
            )

            if received_message_id != message_id:
                raise RuntimeError(
                    f"Expected message_id={message_id}, received message_id={received_message_id}"
                )

            if message_id <= args.warmup:
                continue

            rtt_ms = (received_at_ns - sent_at_ns) / 1_000_000
            measured_message_id = message_id - args.warmup

            rows.append(
                {
                    "label": args.label,
                    "run_id": run_id,
                    "message_id": measured_message_id,
                    "broker_host": args.broker_host,
                    "broker_port": args.broker_port,
                    "topic": topic,
                    "qos": args.qos,
                    "payload_size_bytes": len(payload),
                    "rtt_ms": round(rtt_ms, 3),
                }
            )

            print(
                f"message_id={measured_message_id} "
                f"payload_bytes={len(payload)} rtt_ms={rtt_ms:.2f}"
            )

    finally:
        publisher.loop_stop()
        publisher.disconnect()
        subscriber.loop_stop()
        subscriber.disconnect()

    write_rows(output_file, rows)
    print_summary(rows)
    print(f"saved_to: {output_file}")


if __name__ == "__main__":
    main()
