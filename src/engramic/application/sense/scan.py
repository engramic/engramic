# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

from __future__ import annotations

import asyncio
import base64
import copy
import hashlib
import json
import logging
import re
import uuid
from concurrent.futures import Future
from dataclasses import asdict
from datetime import datetime, timezone
from importlib.resources import files
from pathlib import Path
from typing import TYPE_CHECKING, Any

import fitz

from engramic.application.sense.prompt_gen_full_summary import PromptGenFullSummary
from engramic.application.sense.prompt_gen_meta import PromptGenMeta
from engramic.application.sense.prompt_scan_page import PromptScanPage
from engramic.core.document import Document
from engramic.core.engram import Engram
from engramic.core.index import Index
from engramic.core.interface.media import Media
from engramic.core.meta import Meta
from engramic.core.observation import Observation
from engramic.infrastructure.system.service import Service

if TYPE_CHECKING:
    from concurrent.futures import Future
    from importlib.abc import Traversable

    from engramic.application.sense.sense_service import SenseService


class Scan(Media):
    """
    Coordinates the semantic analysis of a submitted document, converting it into engrams and metadata
    by orchestrating image extraction, LLM-driven summarization, and structured information parsing.

    This class performs the following operations:
    - Loads a PDF document and converts each page into Base64-encoded images.
    - Generates an initial summary using a few preview pages.
    - Scans each page with an LLM plugin to extract semantic content.
    - Parses scan results into Engrams and assembles a full summary.
    - Constructs a Meta object and emits an observation to the system.

    Attributes:
        id (str): Unique identifier for the scan session.
        service (SenseService): Reference to the parent service orchestrating the scan.
        page_images (list[str]): Base64-encoded representations of PDF pages.
        sense_initial_summary (Plugin): Plugin used to generate an initial summary from early pages.

    Constants:
        DPI (int): Resolution used for image extraction.
        DPI_DIVISOR (int): Used to calculate zoom level for rendering.
        TEST_PAGE_LIMIT (int): Max number of pages scanned during test runs.
        MAX_CHUNK_SIZE (int): Max text length before recursive engram chunking.
        SHORT_SUMMARY_PAGE_COUNT (int): Number of pages used to generate initial summary.
        SECTION, H1, H3 (int): Enum-like values to manage tag-based engram splitting depth.

    Methods:
        parse_media_resource(document): Loads and validates a PDF, then initiates conversion.
        _convert_pages_to_images(pdf, start_page, end_page): Converts PDF pages to images asynchronously.
        _page_to_image(pdf, page_number): Converts and encodes a single PDF page to Base64.
        _on_pages_converted(future): Handles post-conversion logic, triggering initial summary.
        _generate_short_summary(): Sends preview pages to the LLM for initial semantic scan.
        _on_short_summary(future): Kicks off page-by-page scanning after initial summary.
        _scan_page(page_num): Sends a single page to the LLM plugin and extracts structured data.
        _on_pages_scanned(future): Extracts structured context and initiates full summary.
        _process_engrams(text_in, context, depth): Recursively splits and constructs Engrams from HTML text.
        _generate_full_summary(summary): Uses full document content to generate final semantic summary.
        _on_generate_full_summary(future): Wraps summary and Engrams into a Meta and emits final Observation.
    """

    DPI = 72
    DPI_DIVISOR = 72
    TEST_PAGE_LIMIT = 100
    MAX_CHUNK_SIZE = 1200
    SHORT_SUMMARY_PAGE_COUNT = 4
    MAX_DEPTH = 3
    SECTION = 0
    H1 = 1
    H3 = 2

    def __init__(self, parent_service: SenseService, scan_id: str):
        self.id = scan_id
        self.service = parent_service
        self.page_images: list[str] = []
        self.sense_initial_summary = self.service.sense_initial_summary

    def parse_media_resource(self, document: Document) -> None:
        file_path: Traversable | Path
        if document.root_directory == Document.Root.RESOURCE:
            file_path = files(document.file_path).joinpath(document.file_name)
        elif document.root_directory == Document.Root.DATA:
            file_path = Path(document.file_path) / document.file_name

        self.document = document
        self.source_id = document.id

        try:
            with file_path.open('rb') as file_ptr:
                pdf_document: fitz.Document = fitz.open(stream=file_ptr.read(), filetype='pdf')

                total_pages = pdf_document.page_count

                if total_pages == 0:
                    error = 'PDF loaded with zero page count.'
                    raise RuntimeError(error)

                self.page_images = [''] * total_pages
                self.total_pages = total_pages
                self._convert_pages_to_images(pdf_document, 0, total_pages)
        except FileNotFoundError as e:
            error = f'File {document.file_name} failed to open. {e}'
            logging.exception(error)
        except RuntimeError as e:
            error = f'File {document.file_name} failed to open. {e}'
            logging.exception(error)

    def _convert_pages_to_images(self, pdf: fitz.Document, start_page: int, end_page: int) -> None:
        coroutines = [self._page_to_image(pdf, i) for i in range(start_page, end_page)]
        future = self.service.run_tasks(coroutines)
        future.add_done_callback(self._on_pages_converted)

    async def _page_to_image(self, pdf: fitz.Document, page_number: int) -> bool:
        page = pdf.load_page(page_number)
        zoom = Scan.DPI / Scan.DPI_DIVISOR
        matrix = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=matrix)

        # Convert the pixmap to PNG bytes in memory
        img_bytes = pix.tobytes('png')

        # Encode to Base64
        encoded_img = base64.b64encode(img_bytes).decode('utf-8')

        # Store the Base64 string in image_array
        self.page_images[page_number] = encoded_img

        return True

    def _on_pages_converted(self, future: Future[Any]) -> None:
        ret_functions = future.result()
        del ret_functions
        summary_future = self.service.run_task(self._generate_short_summary())
        summary_future.add_done_callback(self._on_short_summary)

    async def _generate_short_summary(self) -> Any:
        plugin = self.sense_initial_summary
        summary_images = self.page_images[: Scan.SHORT_SUMMARY_PAGE_COUNT]

        prompt = PromptGenMeta(input_data={'file_path': self.document.file_path, 'file_name': self.document.file_name})

        structured_response = {
            'file_path': str,
            'file_name': str,
            'subject': str,
            'audience': str,
            'document_title': str,
            'document_format': str,
            'document_type': str,
            'toc': str,
            'summary_initial': str,
            'author': str,
            'date': str,
            'version': str,
        }

        ret = self.sense_initial_summary['func'].submit(
            prompt=prompt,
            images=summary_images,
            structured_schema=structured_response,
            args=self.service.host.mock_update_args(plugin),
        )

        self.service.host.update_mock_data(plugin, ret)

        initial_scan = json.loads(ret[0]['llm_response'])

        return initial_scan

    def _on_short_summary(self, future: Future[Any]) -> None:
        result = future.result()
        self.inital_scan = result

        self.total_pages = min(Scan.TEST_PAGE_LIMIT, self.total_pages)
        coroutines = [self._scan_page(i) for i in range(self.total_pages)]
        future = self.service.run_tasks(coroutines)

        future.add_done_callback(self._on_pages_scanned)

    async def _scan_page(self, page_num: int) -> Any:
        plugin = self.service.sense_scan_page

        initial_scan_copy = copy.copy(self.inital_scan)
        initial_scan_copy.update({'page_number': page_num + 1})

        prompt_scan = PromptScanPage(input_data=initial_scan_copy)

        image = self.page_images[page_num]

        ret = await asyncio.to_thread(
            self.sense_initial_summary['func'].submit,
            prompt=prompt_scan,
            images=[image],
            structured_schema=None,
            args=self.service.host.mock_update_args(plugin),
        )

        self.service.host.update_mock_data(plugin, ret)
        return ret[0]['llm_response']

    def _on_pages_scanned(self, future: Future[Any]) -> None:
        result = future.result()

        self.meta_id = str(uuid.uuid4())

        context: dict[str, str] = {}

        context = copy.copy(self.inital_scan)
        del context['summary_initial']
        del context['toc']

        self.engrams: list[Engram] = []

        assembled = ''
        for page in result['_scan_page']:
            assembled += page

        # matches1 = re.findall(r'<h1[^>]*>(.*?)</h1>', assembled, re.DOTALL | re.IGNORECASE)
        # matches2 = re.findall(r'<h3[^>]*>(.*?)</h3>', assembled, re.DOTALL | re.IGNORECASE)

        self._process_engrams(assembled, context)

        future = self.service.run_task(self._generate_full_summary(assembled))
        future.add_done_callback(self._on_generate_full_summary)

    def _process_engrams(self, text_in: str, context: dict[str, str], depth: int = 0) -> None:
        if len(text_in) > Scan.MAX_CHUNK_SIZE and depth < Scan.MAX_DEPTH:
            tag = ''
            if depth == Scan.SECTION:
                tag = 'section'
            if depth == Scan.H1:
                tag = 'h1'
            if depth == Scan.H3:
                tag = 'h3'

            depth += 1

            pattern = rf'(?=<{tag}[^>]*>)'
            parts = re.split(pattern, text_in, flags=re.IGNORECASE)
            clean_parts = [part.strip() for part in parts if part.strip()]

            for part in clean_parts:
                match = re.search(rf'<{tag}[^>]*>(.*?)</{tag}>', text_in, re.DOTALL | re.IGNORECASE)
                context_copy = context
                if match:
                    tag_str = match.group(1).strip()
                    context.update({tag: tag_str})
                    context_copy = copy.copy(context)

                self._process_engrams(part, context_copy, depth)

        else:
            engram = Engram(
                str(uuid.uuid4()),
                [self.inital_scan['file_path']],
                [self.document.get_source_id()],
                text_in,
                True,
                context,
                None,
                [self.meta_id],
                None,  # library
                None,  # accuracy
                None,  # relevancy
                int(datetime.now(timezone.utc).timestamp()),
            )

            self.engrams.append(engram)

    async def _generate_full_summary(self, summary: str) -> Any:
        plugin = self.service.sense_full_summary

        initial_scan_copy = copy.copy(self.inital_scan)
        initial_scan_copy.update({'full_text': summary})

        prompt = PromptGenFullSummary(input_data=initial_scan_copy)

        structure = {'summary_full': str, 'keywords': str}

        ret = self.service.sense_full_summary['func'].submit(
            prompt=prompt, images=None, structured_schema=structure, args=self.service.host.mock_update_args(plugin)
        )

        self.service.host.update_mock_data(plugin, ret)

        llm_response = ret[0]['llm_response']

        return llm_response

    def _on_generate_full_summary(self, future: Future[Any]) -> None:
        results = json.loads(future.result())

        meta = Meta(
            self.meta_id,
            [self.inital_scan['file_path']],
            [hashlib.md5(self.inital_scan['file_path'].encode('utf-8')).hexdigest()],
            results['keywords'].split(','),
            self.inital_scan['summary_initial'],
            Index(results['summary_full']),
        )

        observation = Observation(
            str(uuid.uuid4()), self.document.id, meta, self.engrams, datetime.now(timezone.utc).timestamp()
        )

        self.service.host.update_mock_data_output(self.service, asdict(observation))

        self.service.send_message_async(Service.Topic.OBSERVATION_COMPLETE, asdict(observation))
