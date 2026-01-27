"""XML processing for legislative documents."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from xml.etree import ElementTree as ET


@dataclass
class XMLSection:
    """A section extracted from XML."""

    identifier: str
    title: str | None = None
    text: str = ""
    level: int = 0
    children: list[XMLSection] = field(default_factory=list)


@dataclass
class XMLProcessingResult:
    """Result of XML processing."""

    original_path: Path
    markdown_path: Path | None = None
    sections: list[XMLSection] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    text_content: str = ""


class XMLProcessor:
    """Process XML documents (USLM for bills/code, etc.)."""

    # USLM namespace
    USLM_NS = {"uslm": "http://schemas.gpo.gov/xml/uslm"}

    def __init__(self, output_dir: Path | None = None):
        """Initialize XML processor.

        Args:
            output_dir: Directory for output files.
        """
        self.output_dir = output_dir or Path("data/processed/markdown")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def process(
        self,
        xml_path: Path | str,
        xml_type: str = "auto",
    ) -> XMLProcessingResult:
        """Process an XML file.

        Args:
            xml_path: Path to XML file.
            xml_type: Type of XML (uslm, federal_register, auto).

        Returns:
            XMLProcessingResult with extracted content.
        """
        xml_path = Path(xml_path)

        if not xml_path.exists():
            raise FileNotFoundError(f"XML file not found: {xml_path}")

        result = XMLProcessingResult(original_path=xml_path)

        # Parse XML
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
        except ET.ParseError as e:
            raise ValueError(f"Invalid XML: {e}")

        # Auto-detect type
        if xml_type == "auto":
            xml_type = self._detect_xml_type(root)

        # Process based on type
        if xml_type == "uslm":
            result = self._process_uslm(result, root)
        elif xml_type == "federal_register":
            result = self._process_federal_register(result, root)
        else:
            result = self._process_generic(result, root)

        # Save markdown
        if result.text_content:
            md_path = self.output_dir / f"{xml_path.stem}.md"
            md_path.write_text(result.text_content, encoding="utf-8")
            result.markdown_path = md_path

        return result

    def _detect_xml_type(self, root: ET.Element) -> str:
        """Detect XML type from root element."""
        tag = root.tag.lower()

        if "uslm" in tag or root.tag.startswith("{http://schemas.gpo.gov"):
            return "uslm"
        elif "frdoc" in tag or "prorule" in tag:
            return "federal_register"
        else:
            return "generic"

    def _process_uslm(self, result: XMLProcessingResult, root: ET.Element) -> XMLProcessingResult:
        """Process USLM (US Legislative Markup) XML."""
        # Extract metadata
        meta = root.find(".//uslm:meta", self.USLM_NS) or root.find(".//meta")
        if meta is not None:
            for child in meta:
                tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                result.metadata[tag] = child.text

        # Extract sections
        markdown_parts = []

        # Title
        title_elem = root.find(".//uslm:title", self.USLM_NS) or root.find(".//title")
        if title_elem is not None:
            title_text = self._get_element_text(title_elem)
            if title_text:
                markdown_parts.append(f"# {title_text}\n")

        # Process sections recursively
        for section in root.iter():
            tag = section.tag.split("}")[-1] if "}" in section.tag else section.tag

            if tag == "section":
                sec = self._extract_uslm_section(section)
                result.sections.append(sec)
                markdown_parts.append(self._section_to_markdown(sec))

            elif tag in ("chapter", "subchapter", "part"):
                # Heading elements
                heading = section.find(".//heading") or section.find(
                    ".//uslm:heading", self.USLM_NS
                )
                if heading is not None:
                    level = {"chapter": 2, "subchapter": 3, "part": 3}.get(tag, 2)
                    text = self._get_element_text(heading)
                    if text:
                        markdown_parts.append(f"{'#' * level} {text}\n")

        result.text_content = "\n".join(markdown_parts)
        return result

    def _extract_uslm_section(self, section: ET.Element) -> XMLSection:
        """Extract a USLM section."""
        # Get section number
        num_elem = section.find(".//num") or section.find(".//uslm:num", self.USLM_NS)
        identifier = num_elem.text if num_elem is not None else ""

        # Get heading
        heading = section.find(".//heading") or section.find(".//uslm:heading", self.USLM_NS)
        title = self._get_element_text(heading) if heading is not None else None

        # Get text content
        content_elem = section.find(".//content") or section.find(".//uslm:content", self.USLM_NS)
        if content_elem is not None:
            text = self._get_element_text(content_elem)
        else:
            # Get all text from section
            text = self._get_element_text(section)

        return XMLSection(
            identifier=identifier,
            title=title,
            text=text,
            level=0,
        )

    def _process_federal_register(
        self, result: XMLProcessingResult, root: ET.Element
    ) -> XMLProcessingResult:
        """Process Federal Register XML."""
        markdown_parts = []

        # Extract document info
        for elem in root.iter():
            tag = elem.tag.lower()

            if tag == "agency":
                result.metadata["agency"] = elem.text
            elif tag == "subagy":
                result.metadata["subagency"] = elem.text
            elif tag == "subject":
                text = elem.text or ""
                markdown_parts.append(f"# {text}\n")
                result.metadata["subject"] = text
            elif tag == "summary":
                text = self._get_element_text(elem)
                markdown_parts.append(f"## Summary\n\n{text}\n")
            elif tag in ("suplinf", "supplementary"):
                text = self._get_element_text(elem)
                markdown_parts.append(f"## Supplementary Information\n\n{text}\n")

        result.text_content = "\n".join(markdown_parts)
        return result

    def _process_generic(
        self,
        result: XMLProcessingResult,
        root: ET.Element,
    ) -> XMLProcessingResult:
        """Process generic XML to markdown."""
        markdown_parts = []

        def process_element(elem: ET.Element, level: int = 0):
            tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag

            # Skip metadata-like elements
            if tag in ("meta", "head", "header"):
                return

            text = elem.text.strip() if elem.text else ""
            tail = elem.tail.strip() if elem.tail else ""

            # Handle common elements
            if tag in ("title", "h1"):
                if text:
                    markdown_parts.append(f"# {text}\n")
            elif tag in ("h2", "section"):
                if text:
                    markdown_parts.append(f"## {text}\n")
            elif tag in ("h3", "subsection"):
                if text:
                    markdown_parts.append(f"### {text}\n")
            elif tag in ("p", "para", "paragraph"):
                full_text = self._get_element_text(elem)
                if full_text:
                    markdown_parts.append(f"{full_text}\n")
            elif text:
                markdown_parts.append(f"{text}\n")

            # Process children
            for child in elem:
                process_element(child, level + 1)

            if tail:
                markdown_parts.append(tail)

        process_element(root)
        result.text_content = "\n".join(markdown_parts)
        return result

    def _get_element_text(self, elem: ET.Element) -> str:
        """Get all text from an element and its children."""
        return "".join(elem.itertext()).strip()

    def _section_to_markdown(self, section: XMLSection) -> str:
        """Convert an XMLSection to markdown."""
        parts = []

        # Section header
        header = f"### {section.identifier}"
        if section.title:
            header += f" - {section.title}"
        parts.append(header + "\n")

        # Section text
        if section.text:
            parts.append(section.text + "\n")

        # Child sections
        for child in section.children:
            parts.append(self._section_to_markdown(child))

        return "\n".join(parts)
