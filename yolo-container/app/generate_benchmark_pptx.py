from __future__ import annotations

import argparse
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
import xml.etree.ElementTree as ET


NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "cp": "http://schemas.openxmlformats.org/package/2006/metadata/core-properties",
    "dc": "http://purl.org/dc/elements/1.1/",
    "dcterms": "http://purl.org/dc/terms/",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
}


for prefix, uri in NS.items():
    ET.register_namespace(prefix, uri)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Maak een PowerPoint met benchmarktabel uit benchmark_metrics.json."
    )
    parser.add_argument(
        "--metrics",
        default="yolo-container/benchmark_metrics.json",
    )
    parser.add_argument(
        "--template",
        default="YOLO_MQTT_Benchmark_Local_vs_Tailscale.pptx",
    )
    parser.add_argument(
        "--output",
        default="yolo-container/benchmark_table.pptx",
    )
    return parser.parse_args()


def fmt_ms(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:.2f} ms"


def fmt_x(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:.2f}x"


def load_metrics(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def slide1_texts(metrics: dict) -> list[str]:
    common = metrics["common_images_per_metric"]
    evidence = metrics["evidence"]
    local_overview = metrics["scenarios"]["local"]["overview"]
    cloud_overview = metrics["scenarios"]["cloud"]["overview"]
    local_all = metrics["scenarios"]["local"]["all_messages"]
    cloud_all = metrics["scenarios"]["cloud"]["all_messages"]

    return [
        "YOLO MQTT Benchmark Tabel",
        "Lokaal vs cloud/Tailscale | 100 beelden | hoofdvergelijking = mediaan van per-image gemiddelden",
        "Metric",
        "Lokaal",
        "Cloud/Tailscale",
        "Unieke images",
        str(local_overview["unique_image_count"]),
        str(cloud_overview["unique_image_count"]),
        "Inferentie mediaan",
        fmt_ms(common["inference_ms"]["local"]["median"]),
        fmt_ms(common["inference_ms"]["cloud"]["median"]),
        "Pub -> sub mediaan",
        fmt_ms(common["publish_to_subscriber_ms"]["local"]["median"]),
        fmt_ms(common["publish_to_subscriber_ms"]["cloud"]["median"]),
        "ACK terug mediaan",
        fmt_ms(common["ack_return_ms"]["local"]["median"]),
        fmt_ms(common["ack_return_ms"]["cloud"]["median"]),
        "Roundtrip mediaan",
        fmt_ms(common["roundtrip_ms"]["local"]["median"]),
        fmt_ms(common["roundtrip_ms"]["cloud"]["median"]),
        "Inferentie gem.",
        fmt_ms(local_all["inference_ms"]["mean"]),
        fmt_ms(cloud_all["inference_ms"]["mean"]),
        "Pub -> sub gem.",
        fmt_ms(local_all["publish_to_subscriber_ms"]["mean"]),
        fmt_ms(cloud_all["publish_to_subscriber_ms"]["mean"]),
        "ACK terug gem.",
        fmt_ms(local_all["ack_return_ms"]["mean"]),
        fmt_ms(cloud_all["ack_return_ms"]["mean"]),
        "Roundtrip gem.",
        fmt_ms(local_all["roundtrip_ms"]["mean"]),
        fmt_ms(cloud_all["roundtrip_ms"]["mean"]),
        "Roundtrip ratio",
        "1.00x",
        fmt_x(evidence["roundtrip_ratio"]),
        (
            "Conclusie: inferentie blijft vrijwel gelijk; cloud/Tailscale voegt "
            f"{fmt_ms(evidence['roundtrip_delta_ms'])} extra roundtrip-latency toe."
        ),
    ]


def replace_slide_texts(xml_bytes: bytes, new_texts: list[str]) -> bytes:
    root = ET.fromstring(xml_bytes)
    nodes = root.findall(".//a:t", NS)
    if len(nodes) != len(new_texts):
        raise ValueError(
            f"Verwachtte {len(nodes)} tekstvelden in de slide, maar kreeg {len(new_texts)} waarden."
        )
    for node, text in zip(nodes, new_texts):
        node.text = text
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def update_presentation(xml_bytes: bytes) -> bytes:
    root = ET.fromstring(xml_bytes)
    sld_id_lst = root.find("p:sldIdLst", NS)
    if sld_id_lst is None:
        raise ValueError("Slide-lijst niet gevonden in presentation.xml")
    children = list(sld_id_lst)
    for child in children[1:]:
        sld_id_lst.remove(child)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def update_app_props(xml_bytes: bytes) -> bytes:
    root = ET.fromstring(xml_bytes)
    slides = root.find("{http://schemas.openxmlformats.org/officeDocument/2006/extended-properties}Slides")
    if slides is not None:
        slides.text = "1"
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def update_core_props(xml_bytes: bytes) -> bytes:
    root = ET.fromstring(xml_bytes)
    title = root.find("dc:title", NS)
    creator = root.find("dc:creator", NS)
    modified_by = root.find("{http://schemas.openxmlformats.org/package/2006/metadata/core-properties}lastModifiedBy")
    modified = root.find("dcterms:modified", NS)

    if title is not None:
        title.text = "YOLO MQTT Benchmark Tabel"
    if creator is not None:
        creator.text = "Codex"
    if modified_by is not None:
        modified_by.text = "Codex"
    if modified is not None:
        modified.text = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def build_pptx(template: Path, output: Path, metrics: dict) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    replacements = {
        "ppt/slides/slide1.xml": replace_slide_texts(
            template_zip.read("ppt/slides/slide1.xml"),
            slide1_texts(metrics),
        ),
        "ppt/presentation.xml": update_presentation(template_zip.read("ppt/presentation.xml")),
        "docProps/app.xml": update_app_props(template_zip.read("docProps/app.xml")),
        "docProps/core.xml": update_core_props(template_zip.read("docProps/core.xml")),
    }

    with zipfile.ZipFile(output, "w") as out_zip:
        for info in template_zip.infolist():
            data = replacements.get(info.filename, template_zip.read(info.filename))
            out_zip.writestr(info, data)


def main() -> None:
    args = parse_args()
    metrics = load_metrics(Path(args.metrics))
    template = Path(args.template)
    output = Path(args.output)

    if not template.exists():
        raise FileNotFoundError(f"Template niet gevonden: {template}")

    global template_zip
    with zipfile.ZipFile(template) as template_zip:
        build_pptx(template, output, metrics)

    print(f"PPTX gemaakt: {output}")


if __name__ == "__main__":
    main()
