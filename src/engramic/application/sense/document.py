# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

from __future__ import annotations

import asyncio
import base64
import copy
import hashlib
import json
import re
import uuid
from concurrent.futures import Future
from dataclasses import asdict
from datetime import datetime, timezone
from importlib.resources import files
from typing import TYPE_CHECKING, Any

import fitz

from engramic.application.sense.prompt_gen_full_summary import PromptGenFullSummary
from engramic.application.sense.prompt_gen_initial_summary import PromptGenInitialSummary
from engramic.application.sense.prompt_scan_page import PromptScanPage
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


class Document(Media):
    DPI = 72

    def __init__(self, parent_service: SenseService, document_id: str, sense_inital_summary: dict[str, Any]):
        self.id = document_id
        self.service = parent_service
        self.page_images: list[str] = []
        self.sense_initial_summary = sense_inital_summary

    def parse_media_resource(self, resource_path_in: str, file_name: str) -> None:
        resource_path: Traversable = files(resource_path_in).joinpath(file_name)
        self.file_name = file_name
        self.file_path = resource_path

        with resource_path.open('rb') as file_ptr:
            pdf_document: fitz.Document = fitz.open(stream=file_ptr.read(), filetype='pdf')

            total_pages = pdf_document.page_count

            if total_pages == 0:
                error = 'PDF loaded with zero page count.'
                raise RuntimeError(error)

            self.page_images = [''] * total_pages
            self.total_pages = total_pages
            self._convert_pages_to_images(pdf_document, 0, total_pages)

    def _convert_pages_to_images(self, pdf: fitz.Document, start_page: int, end_page: int) -> None:
        coroutines = [self._page_to_image(pdf, i) for i in range(start_page, end_page)]
        future = self.service.run_tasks(coroutines)

        future.add_done_callback(self._on_pages_converted)

    async def _page_to_image(self, pdf: fitz.Document, page_number: int) -> bool:
        page = pdf.load_page(page_number)
        zoom = Document.DPI / 72
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
        args = plugin['args']
        summary_images = self.page_images[:4]

        prompt = PromptGenInitialSummary(input_data={'file_path': self.file_path, 'file_name': self.file_name})

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
            prompt=prompt, images=summary_images, structured_schema=structured_response, args=args
        )

        initial_scan = json.loads(ret[0]['llm_response'])

        return initial_scan

    def _on_short_summary(self, future: Future[Any]) -> None:
        result = future.result()
        self.inital_scan = result

        self.total_pages = 4
        coroutines = [self._scan_page(i) for i in range(self.total_pages)]

        # Assume run_tasks returns a Future or an awaitable that wraps the coroutine execution
        future = self.service.run_tasks(coroutines)
        future.add_done_callback(self._on_pages_scanned)

    async def _scan_page(self, page_num: int) -> Any:
        plugin = self.service.sense_scan_page
        args = plugin['args']

        initial_scan_copy = copy.copy(self.inital_scan)
        initial_scan_copy.update({'page_number': page_num + 1})

        prompt_scan = PromptScanPage(input_data=initial_scan_copy)

        image = self.page_images[page_num]

        ret = await asyncio.to_thread(
            self.sense_initial_summary['func'].submit,
            prompt=prompt_scan,
            images=[image],
            structured_schema=None,
            args=args,
        )

        return ret[0]['llm_response']

    def _on_pages_scanned(self, future: Future[Any]) -> None:
        result = future.result()

        self.meta_id = str(uuid.uuid4())

        context: dict[str, str] = {}
        results: list[tuple[str, str]] = []
        summary_text = ''

        summary_text, results = self._extract_tags_and_summary(result['_scan_page'])

        scan = self.inital_scan
        context = copy.copy(self.inital_scan)
        del context['summary_initial']
        del context['toc']

        self.engrams: list[Engram] = []

        self._process_engrams(results, context, scan)

        future = self.service.run_task(self._generate_full_summary(summary_text))
        future.add_done_callback(self._on_generate_full_summary)

    def _extract_tags_and_summary(self, pages: list[str]) -> tuple[str, list[tuple[str, str]]]:
        summary_text = ''
        results = []
        pattern = re.compile(r'<(?P<tag>\w+)[^>]*>(.*?)</\1>', re.DOTALL)

        for page in pages:
            summary_text += page
            for match in pattern.finditer(page):
                tag = match.group('tag')
                content = match.group(2)
                results.append((tag, content.strip()))
        return summary_text, results

    def _process_engrams(self, results: list[tuple[str, str]], context: dict[str, str], scan: dict[str, str]) -> None:
        current_engram = None
        content = ''

        for result in results:
            tag = result[0]
            value = result[1]

            if (tag == 'title') and value.strip():
                context.update({'Domain': value})
                value = ''

            elif (tag == 'h1') and value.strip():
                context.update({'Main Topic: ': value})
                value = ''

            elif (tag == 'h3') and value.strip():
                context.update({'Sub Topic': value})
                value = ''

            elif (tag == 'page') and value.strip():
                context.update({'Page': str(value)})
                value = ''

            elif tag == 'engram' and content.strip():
                current_engram = Engram(
                    str(uuid.uuid4()),
                    [scan['file_path']],
                    [hashlib.md5(scan['file_path'].encode('utf-8')).hexdigest()],
                    content,
                    True,
                    copy.copy(context),
                    None,
                    [self.meta_id],
                    None,  # library
                    None,  # accuracy
                    None,  # relevancy
                    int(datetime.now(timezone.utc).timestamp()),
                )
                self.engrams.append(current_engram)
                content = value + '\n'
            else:
                content += value + '\n'

        current_engram = Engram(
            str(uuid.uuid4()),
            [scan['file_path']],
            [hashlib.md5(scan['file_path'].encode('utf-8')).hexdigest()],
            content,
            True,
            copy.copy(context),
            None,
            [self.meta_id],
            None,  # library
            None,  # accuracy
            None,  # relevancy
            int(datetime.now(timezone.utc).timestamp()),
        )

        self.engrams.append(current_engram)

    async def _generate_full_summary(self, summary: str) -> Any:
        plugin = self.service.sense_full_summary
        args = plugin['args']
        initial_scan_copy = copy.copy(self.inital_scan)
        initial_scan_copy.update({'full_text': summary})

        prompt = PromptGenFullSummary(input_data=initial_scan_copy)

        structure = {'summary_full': str, 'keywords': str}

        ret = self.service.sense_full_summary['func'].submit(
            prompt=prompt, images=None, structured_schema=structure, args=args
        )

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

        observation = Observation(str(uuid.uuid4()), meta, self.engrams, datetime.now(timezone.utc).timestamp())

        self.service.send_message_async(Service.Topic.OBSERVATION_COMPLETE, asdict(observation))
