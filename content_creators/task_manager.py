"""Content Creation Task Manager.

This module handles task routing and response packing for the content creation agent,
supporting both text and image content delivery.
"""

import logging
import asyncio
import json
import traceback
import base64
from collections import defaultdict
from collections.abc import AsyncIterable
from typing import Any, Dict, List, Optional, Union

from content_creators.crew import ContentAdapterCrew
from content_creators.image_generator import generate_image
from common.server import utils
from common.server.task_manager import InMemoryTaskManager
from common.types import (
    Artifact,
    FileContent,
    FilePart,
    InternalError,
    InvalidParamsError,
    JSONRPCResponse,
    Message,
    PushNotificationConfig,
    SendTaskRequest,
    SendTaskResponse,
    SendTaskStreamingRequest,
    SendTaskStreamingResponse,
    Task,
    TaskArtifactUpdateEvent,
    TaskIdParams,
    TaskSendParams,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
    TextPart,
)
from common.utils.push_notification_auth import PushNotificationSenderAuth

logger = logging.getLogger(__name__)

class ContentTaskManager(InMemoryTaskManager):
    """Content Task Manager, handles content creation tasks and response formatting."""

    SUPPORTED_CONTENT_TYPES = ['text', 'text/plain', 'image/png', 'application/json']

    def __init__(
        self,
        agent,
        notification_sender_auth: Optional[PushNotificationSenderAuth] = None,
    ):
        super().__init__()
        self.agent = agent
        self.notification_sender_auth = notification_sender_auth
        # Initialize task messages storage
        self.task_messages = defaultdict(list)

    def _validate_request(
        self, request: Union[SendTaskRequest, SendTaskStreamingRequest]
    ) -> Optional[JSONRPCResponse]:
        """Validate incoming task requests."""
        task_send_params: TaskSendParams = request.params
        
        if not utils.are_modalities_compatible(
            task_send_params.acceptedOutputModes,
            self.SUPPORTED_CONTENT_TYPES,
        ):
            logger.warning(
                'Unsupported output mode. Received %s, Support %s',
                task_send_params.acceptedOutputModes,
                self.SUPPORTED_CONTENT_TYPES,
            )
            return utils.new_incompatible_types_error(request.id)

        if (
            task_send_params.pushNotification
            and not task_send_params.pushNotification.url
        ):
            logger.warning('Push notification URL is missing')
            return JSONRPCResponse(
                id=request.id,
                error=InvalidParamsError(
                    message='Push notification URL is missing'
                ),
            )

        return None

    async def on_send_task(
        self, request: SendTaskRequest
    ) -> SendTaskResponse:
        """Handle the 'send task' request for content creation."""
        
        validation_error = self._validate_request(request)
        if validation_error:
            return SendTaskResponse(id=request.id, error=validation_error.error)

        if request.params.pushNotification and self.notification_sender_auth:
            if not await self.set_push_notification_info(
                request.params.id, request.params.pushNotification
            ):
                return SendTaskResponse(
                    id=request.id,
                    error=InvalidParamsError(
                        message='Push notification URL is invalid'
                    ),
                )

        await self.upsert_task(request.params)
        task = await self.update_store(
            request.params.id, TaskStatus(state=TaskState.WORKING), None
        )
        
        if self.notification_sender_auth:
            await self.send_task_notification(task)

        task_send_params: TaskSendParams = request.params
        query = self._get_user_query(task_send_params)
        
        try:
            # Invoke the content creator agent
            logger.info(f"Invoking content creator with query: {query}")
            content_data, image_data = await self.agent.invoke(query)
            
            return await self._process_agent_response(request, content_data, image_data)
        except Exception as e:
            logger.error(f'Error invoking agent: {e}')
            logger.error(traceback.format_exc())
            task = await self.update_store(
                request.params.id, 
                TaskStatus(
                    state=TaskState.FAILED,  # Using FAILED instead of ERROR
                    message=Message(
                        role='agent', 
                        parts=[{'type': 'text', 'text': f'Error creating content: {str(e)}'}]
                    )
                ), 
                None
            )
            
            if self.notification_sender_auth:
                await self.send_task_notification(task)
            
            return SendTaskResponse(
                id=request.id,
                error=InternalError(message=f'Error invoking agent: {str(e)}')
            )

    async def _process_agent_response(
        self, 
        request: SendTaskRequest, 
        content_data: Dict[str, Any],
        image_data: Any
    ) -> SendTaskResponse:
        """Process the agent's response and update the task store."""
        task_send_params: TaskSendParams = request.params
        task_id = task_send_params.id
        history_length = task_send_params.historyLength
        
        # Create artifacts
        artifacts = []
        
        # 1. Add text artifact with JSON content
        json_content = json.dumps(content_data, indent=2)
        text_artifact = Artifact(
            parts=[{'type': 'text', 'text': json_content}],
            index=0,
            title="Content Package"
        )
        artifacts.append(text_artifact)
        
        # 2. Add image artifact if available
        if image_data and not image_data.error:
            image_artifact = Artifact(
                parts=[
                    FilePart(
                        file=FileContent(
                            bytes=base64.b64encode(image_data.bytestring).decode('utf-8'),
                            mimeType=image_data.mime_type,
                            name="generated_image.png"
                        )
                    )
                ],
                index=1,
                title="Generated Image"
            )
            artifacts.append(image_artifact)
        
        # Summary message
        platforms = list(set([
            content_data.get('x_content', {}).get('platform', ''),
            content_data.get('facebook_content', {}).get('platform', ''),
            content_data.get('instagram_content', {}).get('platform', ''),
            content_data.get('linkedin_content', {}).get('platform', '')
        ]))
        platforms = [p for p in platforms if p]
        
        summary = f"Created content package with posts for {', '.join(platforms)}."
        if image_data and not image_data.error:
            summary += " Generated matching image based on content theme."
        elif image_data and image_data.error:
            summary += f" Image generation failed: {image_data.error}"
        
        # Update task status
        task_status = TaskStatus(
            state=TaskState.COMPLETED,
            message=Message(
                role='agent', 
                parts=[{'type': 'text', 'text': summary}]
            )
        )
        
        task = await self.update_store(task_id, task_status, artifacts)
        task_result = self.append_task_history(task, history_length)
        
        if self.notification_sender_auth:
            await self.send_task_notification(task)
            
        return SendTaskResponse(id=request.id, result=task_result)

    async def on_send_task_subscribe(
        self, request: SendTaskStreamingRequest
    ) -> Union[AsyncIterable[SendTaskStreamingResponse], JSONRPCResponse]:
        """Handle the 'send task subscribe' request for streaming responses."""
        try:
            error = self._validate_request(request)
            if error:
                return error

            await self.upsert_task(request.params)

            if request.params.pushNotification and self.notification_sender_auth:
                if not await self.set_push_notification_info(
                    request.params.id, request.params.pushNotification
                ):
                    return JSONRPCResponse(
                        id=request.id,
                        error=InvalidParamsError(
                            message='Push notification URL is invalid'
                        ),
                    )

            task_send_params: TaskSendParams = request.params
            sse_event_queue = await self.setup_sse_consumer(
                task_send_params.id, False
            )

            # Start the streaming task
            asyncio.create_task(self._run_streaming_content_creation(request))

            return self.dequeue_events_for_sse(
                request.id, task_send_params.id, sse_event_queue
            )
        except Exception as e:
            logger.error(f'Error in SSE stream: {e}')
            print(traceback.format_exc())
            return JSONRPCResponse(
                id=request.id,
                error=InternalError(
                    message='An error occurred while streaming the response'
                ),
            )

    async def _run_streaming_content_creation(self, request: SendTaskStreamingRequest):
        """Run the content creation process with streaming updates."""
        task_send_params: TaskSendParams = request.params
        query = self._get_user_query(task_send_params)

        try:
            # Initial status update
            initial_message = Message(
                role='agent', 
                parts=[{'type': 'text', 'text': 'Starting content creation process...'}]
            )
            task_status = TaskStatus(state=TaskState.WORKING, message=initial_message)
            task = await self.update_store(task_send_params.id, task_status, None)
            
            if self.notification_sender_auth:
                await self.send_task_notification(task)
                
            task_update_event = TaskStatusUpdateEvent(
                id=task_send_params.id, status=task_status, final=False
            )
            await self.enqueue_events_for_sse(task_send_params.id, task_update_event)
            
            # Progress update
            progress_message = Message(
                role='agent', 
                parts=[{'type': 'text', 'text': 'Creating content package and generating image...'}]
            )
            task_status = TaskStatus(state=TaskState.WORKING, message=progress_message)
            task = await self.update_store(task_send_params.id, task_status, None)
            
            if self.notification_sender_auth:
                await self.send_task_notification(task)
                
            task_update_event = TaskStatusUpdateEvent(
                id=task_send_params.id, status=task_status, final=False
            )
            await self.enqueue_events_for_sse(task_send_params.id, task_update_event)
            
            # Invoke the agent (non-streaming)
            content_data, image_data = await self.agent.invoke(query)
            
            # Create artifacts
            artifacts = []
            
            # Add JSON text artifact
            json_content = json.dumps(content_data, indent=2)
            text_artifact = Artifact(
                parts=[{'type': 'text', 'text': json_content}],
                index=0,
                title="Content Package"
            )
            artifacts.append(text_artifact)
            await self.update_store(task_send_params.id, None, [text_artifact])
            
            task_artifact_update_event = TaskArtifactUpdateEvent(
                id=task_send_params.id, artifact=text_artifact
            )
            await self.enqueue_events_for_sse(task_send_params.id, task_artifact_update_event)
            
            # Add image artifact if available
            if image_data and not image_data.error:
                image_artifact = Artifact(
                    parts=[
                        FilePart(
                            file=FileContent(
                                bytes=base64.b64encode(image_data.bytestring).decode('utf-8'),
                                mimeType=image_data.mime_type,
                                name="generated_image.png"
                            )
                        )
                    ],
                    index=1,
                    title="Generated Image"
                )
                artifacts.append(image_artifact)
                await self.update_store(task_send_params.id, None, [image_artifact])
                
                task_artifact_update_event = TaskArtifactUpdateEvent(
                    id=task_send_params.id, artifact=image_artifact
                )
                await self.enqueue_events_for_sse(task_send_params.id, task_artifact_update_event)
            
            # Final message
            platforms = list(set([
                content_data.get('x_content', {}).get('platform', ''),
                content_data.get('facebook_content', {}).get('platform', ''),
                content_data.get('instagram_content', {}).get('platform', ''),
                content_data.get('linkedin_content', {}).get('platform', '')
            ]))
            platforms = [p for p in platforms if p]
            
            summary = f"Created content package with posts for {', '.join(platforms)}."
            if image_data and not image_data.error:
                summary += " Generated matching image based on content theme."
            elif image_data and image_data.error:
                summary += f" Image generation failed: {image_data.error}"
            
            # Completion message
            final_message = Message(role='agent', parts=[{'type': 'text', 'text': summary}])
            task_status = TaskStatus(state=TaskState.COMPLETED, message=final_message)
            task = await self.update_store(task_send_params.id, task_status, None)
            
            if self.notification_sender_auth:
                await self.send_task_notification(task)
                
            task_update_event = TaskStatusUpdateEvent(
                id=task_send_params.id, status=task_status, final=True
            )
            await self.enqueue_events_for_sse(task_send_params.id, task_update_event)

        except Exception as e:
            logger.error(f'An error occurred while streaming the response: {e}')
            logger.error(traceback.format_exc())
            
            error_message = Message(
                role='agent', 
                parts=[{'type': 'text', 'text': f'Error creating content: {str(e)}'}]
            )
            task_status = TaskStatus(state=TaskState.ERROR, message=error_message)
            task = await self.update_store(task_send_params.id, task_status, None)
            
            if self.notification_sender_auth:
                await self.send_task_notification(task)
                
            task_update_event = TaskStatusUpdateEvent(
                id=task_send_params.id, status=task_status, final=True
            )
            await self.enqueue_events_for_sse(task_send_params.id, task_update_event)

    async def on_resubscribe_to_task(
        self, request
    ) -> Union[AsyncIterable[SendTaskStreamingResponse], JSONRPCResponse]:
        """Handle the 'resubscribe to task' request."""
        task_id_params: TaskIdParams = request.params
        try:
            sse_event_queue = await self.setup_sse_consumer(
                task_id_params.id, True
            )
            return self.dequeue_events_for_sse(
                request.id, task_id_params.id, sse_event_queue
            )
        except Exception as e:
            logger.error(f'Error while reconnecting to SSE stream: {e}')
            return JSONRPCResponse(
                id=request.id,
                error=InternalError(
                    message=f'An error occurred while reconnecting to stream: {str(e)}'
                ),
            )

    def _get_user_query(self, task_send_params: TaskSendParams) -> str:
        """Extract the user query from the task parameters."""
        part = task_send_params.message.parts[0]
        if not isinstance(part, TextPart):
            raise ValueError('Only text parts are supported')
        return part.text

    async def send_task_notification(self, task: Task):
        """Send a push notification for the task."""
        if not self.notification_sender_auth:
            return
            
        if not await self.has_push_notification_info(task.id):
            logger.info(f'No push notification info found for task {task.id}')
            return
            
        push_info = await self.get_push_notification_info(task.id)

        logger.info(f'Notifying for task {task.id} => {task.status.state}')
        await self.notification_sender_auth.send_push_notification(
            push_info.url, data=task.model_dump(exclude_none=True)
        )

    async def set_push_notification_info(
        self, task_id: str, push_notification_config: PushNotificationConfig
    ) -> bool:
        """Set push notification information for a task."""
        if not self.notification_sender_auth:
            return False
            
        # Verify the ownership of notification URL by issuing a challenge request
        is_verified = (
            await self.notification_sender_auth.verify_push_notification_url(
                push_notification_config.url
            )
        )
        if not is_verified:
            return False

        await super().set_push_notification_info(
            task_id, push_notification_config
        )
        return True

    async def update_store(
        self, task_id: str, status: Optional[TaskStatus], artifacts: Optional[List[Artifact]]
    ) -> Task:
        """Update the task store with new status and/or artifacts."""
        async with self.lock:
            try:
                task = self.tasks[task_id]
            except KeyError as exc:
                logger.error('Task %s not found for updating the task', task_id)
                raise ValueError(f'Task {task_id} not found') from exc

            if status:
                task.status = status

                if status.message is not None:
                    self.task_messages[task_id].append(status.message)

            if artifacts:
                if task.artifacts is None:
                    task.artifacts = []
                task.artifacts.extend(artifacts)

            return task