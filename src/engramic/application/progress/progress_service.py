# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

"""
Tracks and manages progress of various components through the Engramic system.

This module provides tracking capabilities for lessons, prompts, documents, observations,
engrams, and indices as they move through the processing pipeline, and reports completion
percentages to interested components.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from engramic.infrastructure.system.service import Service

if TYPE_CHECKING:
    from engramic.core.host import Host


class ProgressService(Service):
    """
    Monitors and reports progress of various components through the system pipeline.

    Tracks the creation and completion status of multiple object types (lessons, prompts,
    documents, observations, engrams, indices) in parent-child hierarchies, calculates
    completion percentages, and notifies the system when objects are fully processed.

    Attributes:
        progress_array (dict[str, ProgressArray]): Maps object IDs to their progress tracking data.
        lookup_array (dict[str, str]): Quick reverse lookup from child-id to parent-id.
        tracking_array (dict[str, BubbleReturn]): Stores progress aggregation data by tracking ID.

    Methods:
        on_lesson_created(msg): Handles lesson creation events.
        on_prompt_created(msg): Handles prompt creation events.
        on_document_created(msg): Handles document creation events.
        on_observation_created(msg): Handles observation creation events.
        on_engrams_created(msg): Handles engrams creation events.
        on_indices_created(msg): Handles indices creation events.
    """

    @dataclass(slots=True)
    class ProgressArray:
        """
        Stores progress tracking data for a single object in the system.

        Attributes:
            item_type (str): Type of the object being tracked (lesson, prompt, document, etc).
            tracking_id (str | None): Identifier used to track a processing chain.
            children_is_complete_array (dict[str, bool]): Maps child IDs to completion status.
            target_id (str | None): ID of the target object (usually a document).
        """

        item_type: str
        tracking_id: str | None = None
        children_is_complete_array: dict[str, bool] = field(default_factory=dict)
        target_id: str | None = None

    @dataclass(slots=True)
    class BubbleReturn:
        """
        Stores aggregated progress data during bubble-up operations.

        Used to track completion metrics as progress propagates up the object hierarchy.

        Attributes:
            total_indices (int): Total number of indices to be processed.
            completed_indices (int): Number of indices already processed.
            is_complete (bool): Whether the entire processing chain is complete.
            root_node (str): ID of the root node in the processing hierarchy.
            target_id (str | None): ID of the target object.
        """

        total_indices: int = 0
        completed_indices: int = 0
        is_complete: bool = False
        root_node: str = ''
        target_id: str | None = None

    # --------------------------------------------------------------------- #
    # life-cycle                                                            #
    # --------------------------------------------------------------------- #
    def __init__(self, host: Host) -> None:
        """
        Initializes the ProgressService.

        Args:
            host (Host): The host environment providing access to system resources.
        """
        super().__init__(host)
        self.progress_array: dict[str, ProgressService.ProgressArray] = {}
        # quick reverse lookup: child-id → parent-id
        self.lookup_array: dict[str, str] = {}
        self.tracking_array: dict[str, ProgressService.BubbleReturn] = {}

    def start(self) -> None:
        """
        Starts the progress service by subscribing to relevant system events.

        Subscribes to creation events for lessons, prompts, documents, observations,
        engrams, and indices to begin tracking their progress through the system.
        """
        self.subscribe(Service.Topic.LESSON_CREATED, self.on_lesson_created)
        self.subscribe(Service.Topic.PROMPT_CREATED, self.on_prompt_created)
        self.subscribe(Service.Topic.DOCUMENT_CREATED, self.on_document_created)
        self.subscribe(Service.Topic.OBSERVATION_CREATED, self.on_observation_created)
        self.subscribe(Service.Topic.ENGRAMS_CREATED, self.on_engrams_created)
        self.subscribe(Service.Topic.INDICES_CREATED, self.on_indices_created)
        self.subscribe(Service.Topic.INDICES_INSERTED, self._on_indices_inserted)

        super().start()

    # --------------------------------------------------------------------- #
    # message handlers                                                      #
    # --------------------------------------------------------------------- #
    def on_lesson_created(self, msg: dict[str, Any]) -> None:
        """
        Handles the creation of a new lesson in the system.

        Sets up progress tracking for the lesson and connects it to its parent if one exists.

        Args:
            msg (dict[str, Any]): Message containing lesson creation details.
        """
        lesson_id = msg['id']
        parent_id = msg.get('parent_id', '')
        tracking_id = msg['tracking_id']
        doc_id = msg['doc_id']

        self.progress_array.setdefault(lesson_id, ProgressService.ProgressArray('lesson'))

        parent_id = None
        if 'parent_id' in msg:
            parent_id = msg['parent_id']

        if parent_id:
            self.progress_array[parent_id].children_is_complete_array[lesson_id] = False
            self.progress_array[parent_id].tracking_id = tracking_id
            self.lookup_array[lesson_id] = parent_id

        else:
            self.progress_array[lesson_id].tracking_id = tracking_id
            self.progress_array[lesson_id].target_id = doc_id
            self.send_message_async(
                Service.Topic.PROGRESS_UPDATED,
                {
                    'progress_type': 'lesson',
                    'id': lesson_id,
                    'target_id': doc_id,
                    'percent_complete': 0.05,
                    'tracking_id': tracking_id,
                },
            )

    def on_prompt_created(self, msg: dict[str, Any]) -> None:
        """
        Handles the creation of a new prompt in the system.

        Sets up progress tracking for the prompt and connects it to its parent if one exists.

        Args:
            msg (dict[str, Any): Message containing prompt creation details.
        """
        prompt_id = msg['id']
        parent_id = msg.get('parent_id', '')
        tracking_id = msg['tracking_id']

        self.progress_array.setdefault(prompt_id, ProgressService.ProgressArray('prompt'))

        if parent_id:
            self.progress_array[parent_id].children_is_complete_array[prompt_id] = False
            self.progress_array[parent_id].tracking_id = tracking_id
            self.lookup_array[prompt_id] = parent_id
        else:
            self.progress_array[prompt_id].tracking_id = tracking_id

            self.send_message_async(
                Service.Topic.PROGRESS_UPDATED,
                {
                    'progress_type': 'lesson',
                    'id': prompt_id,
                    'target_id': prompt_id,
                    'percent_complete': 0.05,
                    'tracking_id': tracking_id,
                },
            )

    def on_document_created(self, msg: dict[str, Any]) -> None:
        """
        Handles the creation of a new document in the system.

        Sets up progress tracking for the document and connects it to its parent if one exists.

        Args:
            msg (dict[str, Any]): Message containing document creation details.
        """
        doc_id = msg['id']
        tracking_id = msg['tracking_id']

        parent_id = None
        if 'parent_id' in msg:
            parent_id = msg['parent_id']

        self.progress_array.setdefault(doc_id, ProgressService.ProgressArray('document'))

        if parent_id:
            self.progress_array[parent_id].children_is_complete_array[doc_id] = False
            self.progress_array[parent_id].tracking_id = tracking_id
            self.progress_array[parent_id].target_id = doc_id
            self.lookup_array[doc_id] = parent_id
        else:  # an originating node
            self.progress_array[doc_id].tracking_id = tracking_id
            self.progress_array[doc_id].target_id = doc_id
            self.send_message_async(
                Service.Topic.PROGRESS_UPDATED,
                {
                    'progress_type': 'document',
                    'id': doc_id,
                    'target_id': doc_id,
                    'percent_complete': 0.05,
                    'tracking_id': tracking_id,
                },
            )

    def on_observation_created(self, msg: dict[str, Any]) -> None:
        """
        Handles the creation of a new observation in the system.

        Sets up progress tracking for the observation and connects it to its parent.

        Args:
            msg (dict[str, Any]): Message containing observation creation details.
        """
        obs_id = msg['id']
        parent_id = msg['parent_id']

        self.progress_array.setdefault(obs_id, ProgressService.ProgressArray('observation'))
        self.progress_array[parent_id].children_is_complete_array[obs_id] = False
        self.lookup_array[obs_id] = parent_id

    def on_engrams_created(self, msg: dict[str, Any]) -> None:
        """
        Handles the creation of new engrams in the system.

        Sets up progress tracking for multiple engrams and connects them to their parent.

        Args:
            msg (dict[str, Any]): Message containing engram creation details.
        """
        parent_id = msg['parent_id']
        for engram_id in msg['engram_id_array']:
            self.progress_array.setdefault(engram_id, ProgressService.ProgressArray('engram'))
            self.progress_array[parent_id].children_is_complete_array[engram_id] = False
            self.lookup_array[engram_id] = parent_id

    def on_indices_created(self, msg: dict[str, Any]) -> None:
        """
        Handles the creation of new indices in the system.

        Sets up progress tracking for multiple indices and connects them to their parent.
        Updates tracking metrics for the processing chain.

        Args:
            msg (dict[str, Any]): Message containing index creation details.
        """
        parent_id = msg['parent_id']
        tracking_id = msg['tracking_id']

        for index_id in msg['index_id_array']:
            self.progress_array[parent_id].children_is_complete_array[index_id] = False
            self.lookup_array[index_id] = parent_id

        if tracking_id not in self.tracking_array:
            bubble_return = ProgressService.BubbleReturn()
            self._get_root_node(parent_id, bubble_return)
            self.tracking_array[tracking_id] = bubble_return

        self.tracking_array[tracking_id].total_indices += len(msg['index_id_array'])

    # ------------------------------------------------------------------ #
    # propagation logic                                                  #
    # ------------------------------------------------------------------ #
    def _on_indices_inserted(self, msg: dict[str, Any]) -> None:
        """
        Handles the insertion of indices into the system.

        Marks indices as complete and triggers the bubble-up process to update
        progress metrics and potentially mark parent objects as complete.

        Args:
            msg (dict[str, Any]): Message containing index insertion details.
        """
        parent_id = msg['parent_id']
        tracking_id = msg['tracking_id']

        for index_id in msg['index_id_array']:
            self.progress_array[parent_id].children_is_complete_array[index_id] = True
            # (no need to fill lookup_array here it was done in on_indices_created)

        bubble_return = self.tracking_array[tracking_id]

        # Kick off bubble-up test from the *parent* node
        self._bubble_up_if_complete(parent_id, bubble_return)
        originating_object = self.progress_array[bubble_return.root_node]

        self.send_message_async(
            Service.Topic.PROGRESS_UPDATED,
            {
                'progress_type': originating_object.item_type,
                'id': bubble_return.root_node,
                'target_id': originating_object.target_id,
                'percent_complete': bubble_return.completed_indices / bubble_return.total_indices,
                'tracking_id': tracking_id,
            },
        )

        if bubble_return.is_complete:
            self._cleanup_subtree(bubble_return.root_node)
            del self.tracking_array[tracking_id]

    def _bubble_up_if_complete(self, node_id: str, bubble_return: ProgressService.BubbleReturn) -> None:
        """
        Recursively marks nodes as complete and propagates completion status upward.

        Checks if all children of a node are complete, and if so, marks the node as complete
        in its parent. This process continues up the hierarchy until reaching the root node.

        Args:
            node_id (str): ID of the node to check for completion.
            bubble_return (BubbleReturn): Object to track aggregated progress metrics.
        """
        progress = self.progress_array[node_id]

        if progress.item_type == 'engram':
            bubble_return.completed_indices += sum(progress.children_is_complete_array.values())

        if not progress.children_is_complete_array:
            return

        if all(progress.children_is_complete_array.values()):
            # Notify whoever cares that this node is done
            parent_id: str | None = self.lookup_array.get(node_id)

            if progress.item_type == 'document':
                self.send_message_async(Service.Topic.DOCUMENT_INSERTED, {'id': node_id})
            elif progress.item_type == 'lesson':
                self.send_message_async(Service.Topic.LESSON_INSERTED, {'id': node_id})
            elif progress.item_type == 'prompt':
                self.send_message_async(Service.Topic.PROMPT_INSERTED, {'id': node_id})

            # mark completion in the parent (if any)
            if parent_id is not None:
                self.progress_array[parent_id].children_is_complete_array[node_id] = True
            else:
                bubble_return.is_complete = True
                bubble_return.target_id = progress.target_id
                return

            self._bubble_up_if_complete(parent_id, bubble_return)

        return

    def _get_root_node(self, node_id: str, bubble_return: ProgressService.BubbleReturn) -> None:
        """
        Recursively finds the root node of a processing hierarchy.

        Args:
            node_id (str): ID of the node to start the search from.
            bubble_return (BubbleReturn): Object to store the root node ID once found.
        """
        parent_id: str | None = self.lookup_array.get(node_id)
        if parent_id is None:
            bubble_return.root_node = node_id
        else:
            self._get_root_node(parent_id, bubble_return)

    def _cleanup_subtree(self, root_node_id: str) -> None:
        """
        Recursively removes completed nodes and their children from tracking structures.

        Cleans up memory by removing objects that have completed processing.

        Args:
            root_node_id (str): ID of the root node of the subtree to clean up.
        """
        node = self.progress_array.get(root_node_id)
        if node is None:
            return

        # Defensive copy because we mutate inside the loop
        for child_id in list(node.children_is_complete_array):
            if child_id in self.progress_array:
                self._cleanup_subtree(child_id)

            self.lookup_array.pop(child_id, None)
            self.progress_array.pop(child_id, None)

        # Remove the node itself
        self.lookup_array.pop(root_node_id, None)
        self.progress_array.pop(root_node_id, None)
