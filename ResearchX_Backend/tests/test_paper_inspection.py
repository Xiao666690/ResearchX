import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock

import fitz

from core.backend.services.paper_inspection import extract_page_text, inspect_pdf


def sample_pdf(*, scanned: bool = False, invoice: bool = False) -> bytes:
    document = fitz.open()
    page = document.new_page()
    lines = (
        ["INVOICE", "Purchase order and invoice for office supplies", "Invoice number 12345"]
        if invoice else [
            "A Study of Reliable Research Retrieval",
            "Abstract",
            "This paper studies evidence retrieval for scientific research. " * 3,
            "1 Introduction",
            "We present a reproducible method for evaluating document retrieval.",
            "2 Methods",
            "We compare two systems on a fixed collection of research documents.",
            "References",
        ]
    )
    for index, line in enumerate(lines):
        page.insert_text((50, 70 + index * 45), line, fontsize=14)
    if scanned:
        image = page.get_pixmap(matrix=fitz.Matrix(2, 2)).tobytes("png")
        document.close()
        document = fitz.open()
        page = document.new_page()
        page.insert_image(page.rect, stream=image)
    data = document.tobytes()
    document.close()
    return data


class PaperInspectionTests(unittest.TestCase):
    def test_text_pdf_paper(self):
        assessment = inspect_pdf(sample_pdf())
        self.assertEqual(assessment["verdict"], "likely_paper")
        self.assertFalse(assessment["scanned"])
        self.assertIn("摘要", assessment["signals"])

    def test_scanned_pdf_uses_ocr_and_yields_indexable_text(self):
        pdf = sample_pdf(scanned=True)
        assessment = inspect_pdf(pdf)
        self.assertEqual(assessment["verdict"], "likely_paper")
        self.assertEqual(assessment["ocr_pages"], [1])
        with fitz.open(stream=pdf, filetype="pdf") as document:
            text, used_ocr = extract_page_text(document[0])
        self.assertTrue(used_ocr)
        self.assertIn("Abstract", text)

    def test_obvious_non_paper(self):
        self.assertEqual(inspect_pdf(sample_pdf(invoice=True))["verdict"], "not_paper")

    def test_invalid_pdf(self):
        with self.assertRaises(ValueError):
            inspect_pdf(b"not a pdf")

    def test_scanned_pdf_produces_searchable_chunks(self):
        from core.agent.dataprocessAgent import DataProcessAgent

        class AgentWithoutModel(DataProcessAgent):
            def summarize_paper(self, filename):
                return {
                    "Abstract": "OCR indexed paper",
                    "Primary Classification": "Computer Science",
                    "Secondary Classification": "Information Retrieval",
                    "Research Direction Tags": [],
                }

        with TemporaryDirectory() as directory:
            path = Path(directory) / "scan.pdf"
            path.write_bytes(sample_pdf(scanned=True))
            chroma = Mock()
            result = AgentWithoutModel(None, chroma).add_newpaper(str(path), "library-1")
            self.assertGreater(result["documentVector"], 0)
            indexed_text = chroma.add_paper_to_layer1.call_args.args[0]
            self.assertTrue(any("Abstract" in chunk for chunk in indexed_text))


if __name__ == "__main__":
    unittest.main()
