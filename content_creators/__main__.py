"""This file serves as the main entry point for the Content Creation application.
It initializes the A2A server, defines the agent's capabilities,
and starts the server to handle incoming requests.
"""

import logging
import os
import sys
import click
from content_creators.agent import ContentCreator
from content_creators.task_manager import ContentTaskManager
from common.server import A2AServer
from common.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
    MissingAPIKeyError,
)
from common.utils.push_notification_auth import PushNotificationSenderAuth
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@click.command()
@click.option('--host', 'host', default='localhost')
@click.option('--port', 'port', default=10000)
def main(host, port):
    """Entry point for the A2A Content Creation server."""
    try:
        # Check for required API keys
        required_keys = ['GOOGLE_API_KEY', 'OPENAI_API_KEY']
        missing_keys = [key for key in required_keys if not os.getenv(key)]
        
        if missing_keys:
            raise MissingAPIKeyError(
                f'Missing required API keys: {", ".join(missing_keys)}'
            )

        # Initialize capabilities
        capabilities = AgentCapabilities(streaming=True)
        
        # Define skills
        content_creation_skill = AgentSkill(
            id='content_creation',
            name='Content Creation',
            description=(
                'Create professional, cross-platform social media content packages. '
                'Generates unified messaging with platform-specific adaptations and matching images.'
            ),
            tags=['content creation', 'social media', 'marketing'],
            examples=[
                'Create social media content for our new product launch',
                'Generate posts for Facebook, Twitter, LinkedIn about our upcoming event',
                'Make a social media campaign about our sustainability initiatives'
            ],
        )
        
        # Initialize agent card
        agent_card = AgentCard(
            name='Content Creation Agent',
            description=(
                'Generate comprehensive, cross-platform social media content packages. '
                'This agent creates cohesive messaging adapted for different platforms '
                'along with matching visuals to ensure brand consistency and engagement.'
            ),
            url=f'http://{host}:{port}/',
            version='1.0.0',
            defaultInputModes=['text', 'text/plain'],
            defaultOutputModes=['text', 'text/plain', 'image/png', 'application/json'],
            capabilities=capabilities,
            skills=[content_creation_skill],
        )
        
        # Initialize notification sender auth if enabled
        notification_sender_auth = None
        if os.getenv("ENABLE_PUSH_NOTIFICATIONS", "false").lower() == "true":
            notification_sender_auth = PushNotificationSenderAuth(
                hmac_secret=os.getenv("PUSH_NOTIFICATION_SECRET")
            )
        
        # Initialize the agent and task manager
        content_agent = ContentCreator()
        task_manager = ContentTaskManager(
            agent=content_agent,
            notification_sender_auth=notification_sender_auth
        )
        
        # Start the server
        server = A2AServer(
            agent_card=agent_card,
            task_manager=task_manager,
            host=host,
            port=port,
        )
        
        logger.info(f'Starting Content Creation server on {host}:{port}')
        server.start()
        
    except MissingAPIKeyError as e:
        logger.error(f'Error: {e}')
        exit(1)
    except Exception as e:
        logger.error(f'An error occurred during server startup: {e}')
        logger.exception(e)
        exit(1)

if __name__ == '__main__':
    main()