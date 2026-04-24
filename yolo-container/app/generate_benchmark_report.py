from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from html import escape
from pathlib import Path


NUMERIC_KEYS = {
    "message_id",
    "detections_count",
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
    "received_at",
    "publisher_timestamp_sent",
    "publisher_publish_started_at",
    "ack_published_at",
}

SCENARIO_LABELS = {
    "local": "Lokaal",
    "cloud": "Cloud via Tailscale",
}

METRIC_LABELS = {
    "inference_ms": "Inferentie",
    "publish_to_subscriber_ms": "Publisher naar subscriber",
    "ack_return_ms": "Ack terug naar publisher",
    "roundtrip_ms": "Totale roundtrip",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Genereer een vergelijkend benchmarkrapport uit YOLO MQTT CSV-bestanden."
    )
    parser.add_argument(
        "--local-roundtrip",
        default="yolo-container/results_roundtrip_local_steps.csv",
    )
    parser.add_argument(
        "--cloud-roundtrip",
        default="yolo-container/results_roundtrip_cloud_tailscale_steps.csv",
    )
    parser.add_argument(
        "--local-subscriber",
        default="yolo-container/results_subscriber_local_steps.csv",
    )
    parser.add_argument(
        "--cloud-subscriber",
        default="yolo-container/results_subscriber_cloud_tailscale_steps.csv",
    )
    parser.add_argument(
        "--html-out",
        default="yolo-container/benchmark_report.html",
    )
    parser.add_argument(
        "--markdown-out",
        default="yolo-container/benchmark_summary.md",
    )
    parser.add_argument(
        "--table-out",
        default="yolo-container/benchmark_table.md",
    )
    parser.add_argument(
        "--json-out",
        default="yolo-container/benchmark_metrics.json",
    )
    parser.add_argument(
        "--svg-out",
        default="yolo-container/benchmark_comparison.svg",
    )
    return parser.parse_args()


def load_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = []
        for row in csv.DictReader(handle):
            parsed = {}
            for key, value in row.items():
                if value == "":
                    parsed[key] = None
                elif key in NUMERIC_KEYS:
                    parsed[key] = float(value)
                else:
                    parsed[key] = value
            rows.append(parsed)
    return rows


def percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    if len(values) == 1:
        return values[0]
    ordered = sorted(values)
    idx = (len(ordered) - 1) * p
    lower = math.floor(idx)
    upper = math.ceil(idx)
    if lower == upper:
        return ordered[lower]
    fraction = idx - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def summarize(values: list[float]) -> dict:
    return {
        "count": len(values),
        "mean": statistics.fmean(values) if values else None,
        "median": statistics.median(values) if values else None,
        "p95": percentile(values, 0.95),
        "minimum": min(values) if values else None,
        "maximum": max(values) if values else None,
    }


def round_value(value: float | None, digits: int = 2) -> float | None:
    if value is None:
        return None
    return round(value, digits)


def summarize_rows(rows: list[dict], metric_keys: list[str]) -> dict:
    metrics = {}
    for key in metric_keys:
        values = [row[key] for row in rows if row.get(key) is not None]
        metrics[key] = summarize(values)
    return metrics


def image_metric_map(rows: list[dict], metric_key: str) -> dict[str, float]:
    grouped: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        image_name = row.get("image_name")
        value = row.get(metric_key)
        if image_name and value is not None:
            grouped[image_name].append(value)
    return {
        image_name: statistics.fmean(values)
        for image_name, values in grouped.items()
        if values
    }


def common_image_summary(
    local_rows: list[dict], cloud_rows: list[dict], metric_keys: list[str]
) -> dict:
    per_metric = {}
    for key in metric_keys:
        local_map = image_metric_map(local_rows, key)
        cloud_map = image_metric_map(cloud_rows, key)
        common_images = sorted(set(local_map) & set(cloud_map))
        local_values = [local_map[image] for image in common_images]
        cloud_values = [cloud_map[image] for image in common_images]
        per_metric[key] = {
            "common_image_count": len(common_images),
            "local": summarize(local_values),
            "cloud": summarize(cloud_values),
        }
    return per_metric


def subscriber_one_way(rows: list[dict]) -> list[float]:
    values = []
    for row in rows:
        received_at = row.get("received_at")
        publish_started = row.get("publisher_publish_started_at")
        if received_at is not None and publish_started is not None:
            values.append((received_at - publish_started) * 1000)
    return values


def format_ms(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:.2f} ms"


def format_number(value: float | None) -> str:
    if value is None:
        return "-"
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.2f}"


def dataset_overview(roundtrip_rows: list[dict], subscriber_rows: list[dict]) -> dict:
    unique_images = sorted(
        {
            row["image_name"]
            for row in roundtrip_rows
            if row.get("image_name")
        }
    )
    timeouts = sum(1 for row in roundtrip_rows if row.get("roundtrip_ms") is None)
    repetitions = (
        len(roundtrip_rows) / len(unique_images)
        if unique_images
        else 0
    )
    subscriber_latency = subscriber_one_way(subscriber_rows)
    return {
        "message_count": len(roundtrip_rows),
        "unique_image_count": len(unique_images),
        "average_repetitions_per_image": repetitions,
        "timeout_count": timeouts,
        "subscriber_one_way_ms": summarize(subscriber_latency),
    }


def build_metrics(args: argparse.Namespace) -> dict:
    metric_keys = [
        "inference_ms",
        "publish_to_subscriber_ms",
        "ack_return_ms",
        "roundtrip_ms",
    ]

    local_roundtrip = load_csv(Path(args.local_roundtrip))
    cloud_roundtrip = load_csv(Path(args.cloud_roundtrip))
    local_subscriber = load_csv(Path(args.local_subscriber))
    cloud_subscriber = load_csv(Path(args.cloud_subscriber))

    local = {
        "overview": dataset_overview(local_roundtrip, local_subscriber),
        "all_messages": summarize_rows(local_roundtrip, metric_keys),
    }
    cloud = {
        "overview": dataset_overview(cloud_roundtrip, cloud_subscriber),
        "all_messages": summarize_rows(cloud_roundtrip, metric_keys),
    }

    per_image = common_image_summary(local_roundtrip, cloud_roundtrip, metric_keys)

    roundtrip_local = per_image["roundtrip_ms"]["local"]["median"]
    roundtrip_cloud = per_image["roundtrip_ms"]["cloud"]["median"]
    inference_local = per_image["inference_ms"]["local"]["median"]
    inference_cloud = per_image["inference_ms"]["cloud"]["median"]
    publish_local = per_image["publish_to_subscriber_ms"]["local"]["median"]
    publish_cloud = per_image["publish_to_subscriber_ms"]["cloud"]["median"]
    ack_local = per_image["ack_return_ms"]["local"]["median"]
    ack_cloud = per_image["ack_return_ms"]["cloud"]["median"]

    evidence = {
        "roundtrip_ratio": roundtrip_cloud / roundtrip_local if roundtrip_local else None,
        "roundtrip_delta_ms": (
            roundtrip_cloud - roundtrip_local
            if roundtrip_local is not None and roundtrip_cloud is not None
            else None
        ),
        "inference_delta_ms": (
            inference_cloud - inference_local
            if inference_local is not None and inference_cloud is not None
            else None
        ),
        "publish_delta_ms": (
            publish_cloud - publish_local
            if publish_local is not None and publish_cloud is not None
            else None
        ),
        "ack_delta_ms": (
            ack_cloud - ack_local
            if ack_local is not None and ack_cloud is not None
            else None
        ),
    }

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "local_roundtrip": args.local_roundtrip,
            "cloud_roundtrip": args.cloud_roundtrip,
            "local_subscriber": args.local_subscriber,
            "cloud_subscriber": args.cloud_subscriber,
        },
        "scenarios": {
            "local": local,
            "cloud": cloud,
        },
        "common_images_per_metric": per_image,
        "evidence": evidence,
    }


def compact_metrics(metrics: dict) -> dict:
    compact = json.loads(json.dumps(metrics))
    for scenario in compact["scenarios"].values():
        scenario["overview"]["average_repetitions_per_image"] = round_value(
            scenario["overview"]["average_repetitions_per_image"], 2
        )
        for section in ("subscriber_one_way_ms",):
            for key, value in scenario["overview"][section].items():
                if isinstance(value, float):
                    scenario["overview"][section][key] = round_value(value)
        for metric in scenario["all_messages"].values():
            for key, value in metric.items():
                if isinstance(value, float):
                    metric[key] = round_value(value)
    for metric_data in compact["common_images_per_metric"].values():
        for scope in ("local", "cloud"):
            for key, value in metric_data[scope].items():
                if isinstance(value, float):
                    metric_data[scope][key] = round_value(value)
    for key, value in compact["evidence"].items():
        if isinstance(value, float):
            compact["evidence"][key] = round_value(value)
    return compact


def comparison_rows(metrics: dict) -> list[dict]:
    rows = []
    for key, label in METRIC_LABELS.items():
        local_metric = metrics["common_images_per_metric"][key]["local"]
        cloud_metric = metrics["common_images_per_metric"][key]["cloud"]
        local_median = local_metric["median"]
        cloud_median = cloud_metric["median"]
        rows.append(
            {
                "label": label,
                "local_median": local_median,
                "cloud_median": cloud_median,
                "delta": cloud_median - local_median if None not in (cloud_median, local_median) else None,
                "ratio": cloud_median / local_median if local_median else None,
                "local_p95": local_metric["p95"],
                "cloud_p95": cloud_metric["p95"],
            }
        )
    return rows


def render_markdown(metrics: dict) -> str:
    common_images = metrics["common_images_per_metric"]["roundtrip_ms"]["common_image_count"]
    local_overview = metrics["scenarios"]["local"]["overview"]
    cloud_overview = metrics["scenarios"]["cloud"]["overview"]
    evidence = metrics["evidence"]
    rows = comparison_rows(metrics)
    local_all = metrics["scenarios"]["local"]["all_messages"]
    cloud_all = metrics["scenarios"]["cloud"]["all_messages"]

    lines = [
        "# YOLO MQTT benchmark samenvatting",
        "",
        "## Kernconclusie",
        "",
        (
            f"- Over {common_images} gelijke images is de mediane roundtrip lokaal "
            f"{format_ms(rows[3]['local_median'])} en via cloud/Tailscale "
            f"{format_ms(rows[3]['cloud_median'])}."
        ),
        (
            f"- Cloud/Tailscale voegt ongeveer {format_ms(evidence['roundtrip_delta_ms'])} toe "
            f"en is circa {format_number(evidence['roundtrip_ratio'])}x langzamer dan lokaal."
        ),
        (
            f"- De mediane inferentie blijft vrijwel gelijk: "
            f"{format_ms(rows[0]['local_median'])} lokaal versus "
            f"{format_ms(rows[0]['cloud_median'])} via cloud/Tailscale."
        ),
        (
            f"- Het verschil zit dus vooral in netwerktransport: publisher naar subscriber "
            f"stijgt van {format_ms(rows[1]['local_median'])} naar "
            f"{format_ms(rows[1]['cloud_median'])}."
        ),
        "",
        "## Methode",
        "",
        "- Ja, er is met gemiddelden gewerkt, maar niet alleen met gemiddelden.",
        "- Omdat lokaal elke image 2 keer voorkomt en cloud/Tailscale 4 keer, berekent dit rapport eerst per image een gemiddelde.",
        "- Daarna vergelijkt het rapport de mediaan van die per-image gemiddelden. Dat maakt de vergelijking eerlijker.",
        "- In de JSON staan daarnaast ook gewone gemiddelden en medianen over alle losse berichten.",
        "",
        "## Meetopzet",
        "",
        f"- Lokale dataset: {local_overview['message_count']} berichten over {local_overview['unique_image_count']} unieke images.",
        f"- Cloud/Tailscale dataset: {cloud_overview['message_count']} berichten over {cloud_overview['unique_image_count']} unieke images.",
        "- Hoofdvergelijking gebruikt per-image gemiddelden op de overlap van dezelfde images, zodat het verschil in herhalingen de uitkomst niet scheeftrekt.",
        "",
        "## Hoofdvergelijking",
        "",
        "| Metric | Lokaal mediaan | Cloud/Tailscale mediaan | Verschil | Verhouding |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]

    for row in rows:
        lines.append(
            f"| {row['label']} | {format_ms(row['local_median'])} | "
            f"{format_ms(row['cloud_median'])} | {format_ms(row['delta'])} | "
            f"{format_number(row['ratio'])}x |"
        )

    lines.extend(
        [
            "",
            "## Gemiddelden over alle berichten",
            "",
            "| Metric | Lokaal gemiddelde | Cloud/Tailscale gemiddelde |",
            "| --- | ---: | ---: |",
        ]
    )

    for key, label in METRIC_LABELS.items():
        lines.append(
            f"| {label} | {format_ms(local_all[key]['mean'])} | {format_ms(cloud_all[key]['mean'])} |"
        )

    lines.extend(
        [
            "",
            "## Bewijszin voor presentatie",
            "",
            (
                f"Bij een vergelijking over {common_images} dezelfde testimages blijft de YOLO-inferentie "
                f"nagenoeg gelijk, maar de MQTT-communicatie via cloud/Tailscale verhoogt de mediane "
                f"roundtrip van {format_ms(rows[3]['local_median'])} naar {format_ms(rows[3]['cloud_median'])}. "
                f"Dat is een extra netwerkvertraging van ongeveer {format_ms(evidence['roundtrip_delta_ms'])}."
            ),
            "",
        ]
    )

    return "\n".join(lines)


def render_table_markdown(metrics: dict) -> str:
    rows = comparison_rows(metrics)
    local_all = metrics["scenarios"]["local"]["all_messages"]
    cloud_all = metrics["scenarios"]["cloud"]["all_messages"]

    lines = [
        "# Benchmark Tabel",
        "",
        "## Hoofdvergelijking",
        "",
        "| Metric | Lokaal mediaan | Cloud/Tailscale mediaan | Verschil | Verhouding |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]

    for row in rows:
        lines.append(
            f"| {row['label']} | {format_ms(row['local_median'])} | "
            f"{format_ms(row['cloud_median'])} | {format_ms(row['delta'])} | "
            f"{format_number(row['ratio'])}x |"
        )

    lines.extend(
        [
            "",
            "## Gemiddelden over alle berichten",
            "",
            "| Metric | Lokaal gemiddelde | Cloud/Tailscale gemiddelde |",
            "| --- | ---: | ---: |",
        ]
    )

    for key, label in METRIC_LABELS.items():
        lines.append(
            f"| {label} | {format_ms(local_all[key]['mean'])} | {format_ms(cloud_all[key]['mean'])} |"
        )

    return "\n".join(lines)


def render_stat_table(metrics: dict) -> str:
    rows = comparison_rows(metrics)
    table_rows = []
    for row in rows:
        table_rows.append(
            f"""
            <tr>
              <th>{escape(row['label'])}</th>
              <td>{escape(format_ms(row['local_median']))}</td>
              <td>{escape(format_ms(row['cloud_median']))}</td>
              <td>{escape(format_ms(row['delta']))}</td>
              <td>{escape(format_number(row['ratio']))}x</td>
              <td>{escape(format_ms(row['local_p95']))}</td>
              <td>{escape(format_ms(row['cloud_p95']))}</td>
            </tr>
            """
        )
    return "".join(table_rows)


def render_bar_cards(metrics: dict) -> str:
    rows = comparison_rows(metrics)
    max_value = max(
        max(filter(None, [row["local_median"], row["cloud_median"]]))
        for row in rows
    )
    cards = []
    for row in rows:
        local_width = (row["local_median"] / max_value) * 100 if row["local_median"] else 0
        cloud_width = (row["cloud_median"] / max_value) * 100 if row["cloud_median"] else 0
        cards.append(
            f"""
            <article class="metric-card">
              <h3>{escape(row['label'])}</h3>
              <div class="metric-row">
                <span>Lokaal</span>
                <strong>{escape(format_ms(row['local_median']))}</strong>
              </div>
              <div class="bar-track"><div class="bar local" style="width:{local_width:.2f}%"></div></div>
              <div class="metric-row">
                <span>Cloud/Tailscale</span>
                <strong>{escape(format_ms(row['cloud_median']))}</strong>
              </div>
              <div class="bar-track"><div class="bar cloud" style="width:{cloud_width:.2f}%"></div></div>
            </article>
            """
        )
    return "".join(cards)


def render_html(metrics: dict) -> str:
    common_images = metrics["common_images_per_metric"]["roundtrip_ms"]["common_image_count"]
    local_overview = metrics["scenarios"]["local"]["overview"]
    cloud_overview = metrics["scenarios"]["cloud"]["overview"]
    evidence = metrics["evidence"]
    local_all = metrics["scenarios"]["local"]["all_messages"]
    cloud_all = metrics["scenarios"]["cloud"]["all_messages"]
    rows = comparison_rows(metrics)

    hero_cards = "".join(
        [
            f"""
            <article class="stat-card">
              <span>Roundtrip lokaal</span>
              <strong>{escape(format_ms(metrics["common_images_per_metric"]["roundtrip_ms"]["local"]["median"]))}</strong>
            </article>
            """,
            f"""
            <article class="stat-card">
              <span>Roundtrip cloud/Tailscale</span>
              <strong>{escape(format_ms(metrics["common_images_per_metric"]["roundtrip_ms"]["cloud"]["median"]))}</strong>
            </article>
            """,
            f"""
            <article class="stat-card">
              <span>Extra vertraging</span>
              <strong>{escape(format_ms(evidence["roundtrip_delta_ms"]))}</strong>
            </article>
            """,
            f"""
            <article class="stat-card">
              <span>Verhouding</span>
              <strong>{escape(format_number(evidence["roundtrip_ratio"]))}x</strong>
            </article>
            """,
        ]
    )

    generated_at = datetime.fromisoformat(metrics["generated_at"]).astimezone().strftime(
        "%Y-%m-%d %H:%M:%S %Z"
    )

    return f"""<!doctype html>
<html lang="nl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>YOLO MQTT benchmark</title>
  <style>
    :root {{
      --bg: #f7f7f7;
      --panel: #ffffff;
      --ink: #1f2937;
      --muted: #6b7280;
      --line: #e5e7eb;
      --accent: #0f766e;
    }}
    * {{
      box-sizing: border-box;
    }}
    body {{
      margin: 0;
      font-family: Arial, sans-serif;
      color: var(--ink);
      background: var(--bg);
    }}
    main {{
      max-width: 980px;
      margin: 0 auto;
      padding: 32px 20px 48px;
    }}
    h1 {{
      margin: 0 0 10px;
      font-size: 34px;
    }}
    p {{
      line-height: 1.5;
      color: var(--muted);
    }}
    .intro,
    .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 20px;
      margin-bottom: 16px;
    }}
    .stats {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 12px;
      margin: 18px 0;
    }}
    .stat-card {{
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 14px;
      background: #fbfbfb;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 14px;
    }}
    th, td {{
      padding: 10px 8px;
      border-bottom: 1px solid var(--line);
      text-align: left;
    }}
    th {{
      background: #f9fafb;
    }}
    h2 {{
      margin: 0 0 12px;
      font-size: 22px;
    }}
    ul {{
      margin: 0;
      padding-left: 18px;
      line-height: 1.6;
    }}
    .small {{
      color: var(--muted);
      font-size: 13px;
    }}
  </style>
</head>
<body>
  <main>
    <section class="intro">
      <h1>YOLO MQTT benchmark</h1>
      <p>
        Vergelijking tussen lokaal en cloud/Tailscale op basis van dezelfde {common_images} testimages.
        Dit rapport gebruikt per image eerst een gemiddelde en vergelijkt daarna de mediaan van die image-gemiddelden.
      </p>
      <div class="stats">
        {hero_cards}
      </div>
    </section>

    <section class="panel">
      <h2>Kernconclusie</h2>
      <ul>
        <li>De mediane roundtrip stijgt van {escape(format_ms(metrics["common_images_per_metric"]["roundtrip_ms"]["local"]["median"]))} naar {escape(format_ms(metrics["common_images_per_metric"]["roundtrip_ms"]["cloud"]["median"]))}.</li>
        <li>Dat is {escape(format_ms(evidence["roundtrip_delta_ms"]))} extra vertraging en ongeveer {escape(format_number(evidence["roundtrip_ratio"]))}x langzamer.</li>
        <li>De inferentie blijft bijna gelijk: {escape(format_ms(metrics["common_images_per_metric"]["inference_ms"]["local"]["median"]))} lokaal versus {escape(format_ms(metrics["common_images_per_metric"]["inference_ms"]["cloud"]["median"]))} in de cloud.</li>
      </ul>
    </section>

    <section class="panel">
      <h2>Hoofdvergelijking</h2>
      <table>
        <thead>
          <tr>
            <th>Metric</th>
            <th>Lokaal mediaan</th>
            <th>Cloud/Tailscale mediaan</th>
            <th>Verschil</th>
            <th>Verhouding</th>
          </tr>
        </thead>
        <tbody>
          {"".join(
              f"<tr><td>{escape(row['label'])}</td><td>{escape(format_ms(row['local_median']))}</td><td>{escape(format_ms(row['cloud_median']))}</td><td>{escape(format_ms(row['delta']))}</td><td>{escape(format_number(row['ratio']))}x</td></tr>"
              for row in rows
          )}
        </tbody>
      </table>
    </section>

    <section class="panel">
      <h2>Gemiddelden over alle berichten</h2>
      <table>
        <thead>
          <tr>
            <th>Metric</th>
            <th>Lokaal gemiddelde</th>
            <th>Cloud/Tailscale gemiddelde</th>
          </tr>
        </thead>
        <tbody>
          {"".join(
              f"<tr><td>{escape(label)}</td><td>{escape(format_ms(local_all[key]['mean']))}</td><td>{escape(format_ms(cloud_all[key]['mean']))}</td></tr>"
              for key, label in METRIC_LABELS.items()
          )}
        </tbody>
      </table>
    </section>

    <section class="panel">
      <h2>Meetopzet</h2>
      <ul>
        <li>Lokaal: {local_overview["message_count"]} berichten over {local_overview["unique_image_count"]} unieke images.</li>
        <li>Cloud/Tailscale: {cloud_overview["message_count"]} berichten over {cloud_overview["unique_image_count"]} unieke images.</li>
        <li>Lokaal heeft gemiddeld {format_number(local_overview["average_repetitions_per_image"])} runs per image, cloud/Tailscale {format_number(cloud_overview["average_repetitions_per_image"])}.</li>
        <li>Daarom is de hoofdvergelijking gebaseerd op per-image gemiddelden.</li>
      </ul>
      <p class="small">Gegenereerd op {escape(generated_at)}</p>
      <p class="small">
        Bronbestanden: {escape(metrics["inputs"]["local_roundtrip"])},
        {escape(metrics["inputs"]["cloud_roundtrip"])},
        {escape(metrics["inputs"]["local_subscriber"])} en
        {escape(metrics["inputs"]["cloud_subscriber"])}.
      </p>
    </section>
  </main>
</body>
</html>
"""


def render_svg(metrics: dict) -> str:
    rows = comparison_rows(metrics)
    max_value = max(
        max(filter(None, [row["local_median"], row["cloud_median"]]))
        for row in rows
    )

    width = 1180
    height = 560
    margin_left = 270
    margin_right = 80
    bar_area = width - margin_left - margin_right
    top = 120
    group_gap = 92
    bar_height = 24
    bar_gap = 12

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="YOLO MQTT benchmark vergelijking">',
        '<defs>',
        '<linearGradient id="bg" x1="0" x2="1" y1="0" y2="1">',
        '<stop offset="0%" stop-color="#f8f3ec" />',
        '<stop offset="100%" stop-color="#efe4d7" />',
        "</linearGradient>",
        '<linearGradient id="local" x1="0" x2="1" y1="0" y2="0">',
        '<stop offset="0%" stop-color="#2f6fed" />',
        '<stop offset="100%" stop-color="#78a4ff" />',
        "</linearGradient>",
        '<linearGradient id="cloud" x1="0" x2="1" y1="0" y2="0">',
        '<stop offset="0%" stop-color="#d97706" />',
        '<stop offset="100%" stop-color="#f2b267" />',
        "</linearGradient>",
        "</defs>",
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="url(#bg)" rx="28" />',
        '<text x="70" y="68" font-family="Segoe UI, Helvetica Neue, sans-serif" font-size="34" font-weight="700" fill="#1c1917">YOLO MQTT benchmark: lokaal vs cloud/Tailscale</text>',
        '<text x="70" y="96" font-family="Segoe UI, Helvetica Neue, sans-serif" font-size="16" fill="#6b5f55">Medianen op per-image gemiddelden over dezelfde 100 testimages</text>',
        '<rect x="70" y="505" width="18" height="18" rx="6" fill="url(#local)" />',
        '<text x="98" y="519" font-family="Segoe UI, Helvetica Neue, sans-serif" font-size="14" fill="#1c1917">Lokaal</text>',
        '<rect x="170" y="505" width="18" height="18" rx="6" fill="url(#cloud)" />',
        '<text x="198" y="519" font-family="Segoe UI, Helvetica Neue, sans-serif" font-size="14" fill="#1c1917">Cloud via Tailscale</text>',
    ]

    for tick in range(0, 26, 5):
        x = margin_left + (tick / max_value) * bar_area
        parts.append(
            f'<line x1="{x:.1f}" y1="112" x2="{x:.1f}" y2="470" stroke="#d8ccbd" stroke-width="1" stroke-dasharray="4 6" />'
        )
        parts.append(
            f'<text x="{x:.1f}" y="108" text-anchor="middle" font-family="Segoe UI, Helvetica Neue, sans-serif" font-size="12" fill="#6b5f55">{tick} ms</text>'
        )

    for index, row in enumerate(rows):
        group_y = top + index * group_gap
        local_width = (row["local_median"] / max_value) * bar_area if row["local_median"] else 0
        cloud_width = (row["cloud_median"] / max_value) * bar_area if row["cloud_median"] else 0
        local_y = group_y
        cloud_y = group_y + bar_height + bar_gap

        parts.append(
            f'<text x="70" y="{group_y + 18}" font-family="Segoe UI, Helvetica Neue, sans-serif" font-size="18" font-weight="700" fill="#1c1917">{escape(row["label"])}</text>'
        )

        parts.append(
            f'<rect x="{margin_left}" y="{local_y}" width="{local_width:.1f}" height="{bar_height}" rx="12" fill="url(#local)" />'
        )
        parts.append(
            f'<text x="{margin_left + local_width + 10:.1f}" y="{local_y + 17}" font-family="Segoe UI, Helvetica Neue, sans-serif" font-size="13" fill="#1c1917">{format_ms(row["local_median"])}</text>'
        )

        parts.append(
            f'<rect x="{margin_left}" y="{cloud_y}" width="{cloud_width:.1f}" height="{bar_height}" rx="12" fill="url(#cloud)" />'
        )
        parts.append(
            f'<text x="{margin_left + cloud_width + 10:.1f}" y="{cloud_y + 17}" font-family="Segoe UI, Helvetica Neue, sans-serif" font-size="13" fill="#1c1917">{format_ms(row["cloud_median"])}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


def main() -> None:
    args = parse_args()
    metrics = compact_metrics(build_metrics(args))

    html_out = Path(args.html_out)
    markdown_out = Path(args.markdown_out)
    table_out = Path(args.table_out)
    json_out = Path(args.json_out)
    svg_out = Path(args.svg_out)

    html_out.write_text(render_html(metrics), encoding="utf-8")
    markdown_out.write_text(render_markdown(metrics), encoding="utf-8")
    table_out.write_text(render_table_markdown(metrics), encoding="utf-8")
    json_out.write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    svg_out.write_text(render_svg(metrics), encoding="utf-8")

    print(f"HTML report: {html_out}")
    print(f"Markdown summary: {markdown_out}")
    print(f"Markdown table: {table_out}")
    print(f"JSON metrics: {json_out}")
    print(f"SVG chart: {svg_out}")


if __name__ == "__main__":
    main()
