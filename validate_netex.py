#!/usr/bin/env python3
"""Validate a NeTEx XML document against the BISON NeTEx-NL XSD."""

import argparse
import sys
import tempfile
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

try:
    from lxml import etree
except ImportError:
    sys.exit("Missing dependency: install it with 'python -m pip install lxml'.")


SCHEMA_BASE_URL = "https://raw.githubusercontent.com/BISONNL/NeTEx-NL/master/xsd/"
SCHEMA_FILES = (
    "netex-nl-geen-constraints.xsd",
    "netex-nl.xsd",
    "netex-nl-basic.xsd",
    "netex-nl-enums.xsd",
    "netex-nl-data.xsd",
    "gml-bison.xsd",
)


def download_schema(directory: Path) -> Path:
    for filename in SCHEMA_FILES:
        with urlopen(SCHEMA_BASE_URL + filename, timeout=30) as response:
            (directory / filename).write_bytes(response.read())
    return directory / SCHEMA_FILES[0]


def validate(xml_path: Path, schema_path: Path) -> int:
    schema_parser = etree.XMLParser(resolve_entities=True, no_network=True)
    xml_parser = etree.XMLParser(resolve_entities=False, no_network=True)
    schema = etree.XMLSchema(etree.parse(str(schema_path), schema_parser))
    document = etree.parse(str(xml_path), xml_parser)
    if schema.validate(document):
        print(f"Valid: {xml_path}")
        return 0
    print(f"Invalid: {xml_path}", file=sys.stderr)
    for error in schema.error_log:
        print(f"  line {error.line}, column {error.column}: {error.message}", file=sys.stderr)
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("xml", type=Path, help="NeTEx XML file to validate")
    parser.add_argument(
        "--schema", type=Path,
        help="local BISON entry-point XSD, with its referenced XSDs alongside it",
    )
    args = parser.parse_args()
    try:
        if args.schema:
            return validate(args.xml, args.schema)
        with tempfile.TemporaryDirectory(prefix="netex-nl-xsd-") as directory:
            return validate(args.xml, download_schema(Path(directory)))
    except (OSError, URLError, etree.XMLSyntaxError, etree.XMLSchemaParseError) as error:
        print(f"Validation could not be completed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())