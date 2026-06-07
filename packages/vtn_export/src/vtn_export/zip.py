from __future__ import annotations

import json
import re
import zipfile
from io import BytesIO
from typing import Any

from vtn_storage.blob import BlobStore

from vtn_export.markdown import render_note_markdown
from vtn_export.metadata import build_metadata


def build_export_zip(context: dict[str, Any], blob_store: BlobStore) -> bytes:
    image_names = {str(clip["id"]): _image_name(clip) for clip in context["clips"]}
    output = BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("note.md", render_note_markdown(context, image_names))
        archive.writestr(
            "metadata.json",
            json.dumps(build_metadata(context, image_names), indent=2),
        )
        for clip in context["clips"]:
            archive.writestr(image_names[str(clip["id"])], blob_store.get(clip["scene_blob_path"]))
    return output.getvalue()


def _image_name(clip: dict[str, Any]) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", str(clip["title"]).lower()).strip("-") or "clip"
    return f"images/{int(clip['order_index']) + 1:04d}-{slug}.png"
