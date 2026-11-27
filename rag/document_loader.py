from pathlib import Path
import re

import yaml
from langchain_core.documents import Document


def load_documents(data_dir):

    data_dir = Path(data_dir)
    txt_files = sorted(data_dir.rglob("*.txt"))

    docs = []

    for file_path in txt_files:

        raw_text = file_path.read_text(encoding="utf-8")

        matches = list(
            re.finditer(r"^\s*\\?---\s*$", raw_text, flags=re.MULTILINE)
        )

        if len(matches) >= 2:

            first_separator = matches[0]
            second_separator = matches[1]

            metadata_text = raw_text[
                first_separator.end():second_separator.start()
            ].strip()

            content = raw_text[second_separator.end():].strip()

            metadata = yaml.safe_load(metadata_text) or {}

        else:
            metadata = {}
            content = raw_text.strip()

        # Rename department_id to domain
        if "department_id" in metadata:
            metadata["domain"] = metadata.pop("department_id")

        # Add source
        metadata["source"] = file_path.name

        doc = Document(
            page_content=content,
            metadata=metadata
        )

        docs.append(doc)

    

    return docs