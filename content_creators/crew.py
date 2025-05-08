from typing import List, Optional
from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import os
from uuid import uuid4

load_dotenv()

class TextContent(BaseModel):
    """Text content for a specific platform"""
    platform: str = Field(..., description="Platform name")
    text: str = Field(..., description="Text content for the post")
    hashtags: List[str] = Field(default_factory=list, description="Recommended hashtags")

class CrossPlatformTextPackage(BaseModel):
    """Complete cross-platform text content package"""
    core_message: str = Field(..., description="Core message consistent across platforms")
    image_prompt: str = Field(..., description="Prompt used to generate the image")
    x_content: TextContent = Field(..., description="Content adapted for X/Twitter")
    facebook_content: TextContent = Field(..., description="Content adapted for Facebook")
    instagram_content: TextContent = Field(..., description="Content adapted for Instagram")
    linkedin_content: TextContent = Field(..., description="Content adapted for LinkedIn")
    brand_alignment_notes: str = Field(..., description="Notes on how content aligns with brand guidelines")

@CrewBase
class ContentAdapterCrew():
    """Content Adapter crew for cross-platform social media posts"""
    agents_config = 'config/agents.yml'
    tasks_config = 'config/tasks.yml'
    llm = LLM(
        model="gpt-4o", # Updated to use GPT-4o - adjust based on your access
        temperature=0.7
    )
    
    @agent
    def lead_content_creator(self) -> Agent:
        return Agent(
            config=self.agents_config['lead_content_creator'],
            verbose=True,
            memory=False,
            llm=self.llm
        )
    
    @agent
    def image_prompt_creator(self) -> Agent:
        return Agent(
            config=self.agents_config['image_prompt_creator'],
            verbose=True,
            memory=False,
            llm=self.llm
        )
    
    @agent
    def x_content_specialist(self) -> Agent:
        return Agent(
            config=self.agents_config['x_content_specialist'],
            verbose=True,
            memory=False,
            llm=self.llm
        )
    
    @agent
    def facebook_content_specialist(self) -> Agent:
        return Agent(
            config=self.agents_config['facebook_content_specialist'],
            verbose=True,
            memory=False,
            llm=self.llm
        )
    
    @agent
    def instagram_content_specialist(self) -> Agent:
        return Agent(
            config=self.agents_config['instagram_content_specialist'],
            verbose=True,
            memory=False,
            llm=self.llm
        )
    
    @agent
    def linkedin_content_specialist(self) -> Agent:
        return Agent(
            config=self.agents_config['linkedin_content_specialist'],
            verbose=True,
            memory=False,
            llm=self.llm
        )
    
    @agent
    def brand_guidelines_critic(self) -> Agent:
        return Agent(
            config=self.agents_config['brand_guidelines_critic'],
            verbose=True,
            memory=False,
            llm=self.llm
        )
    
    @task
    def core_message_creation_task(self) -> Task:
        return Task(
            config=self.tasks_config['core_message_creation_task'],
            agent=self.lead_content_creator()
        )
    
    @task
    def image_prompt_creation_task(self) -> Task:
        return Task(
            config=self.tasks_config['image_prompt_creation_task'],
            agent=self.image_prompt_creator(),
            context=[self.core_message_creation_task()]
        )
    
    @task
    def x_content_adaptation_task(self) -> Task:
        return Task(
            config=self.tasks_config['x_content_adaptation_task'],
            agent=self.x_content_specialist(),
            context=[self.core_message_creation_task()]
        )
    
    @task
    def facebook_content_adaptation_task(self) -> Task:
        return Task(
            config=self.tasks_config['facebook_content_adaptation_task'],
            agent=self.facebook_content_specialist(),
            context=[self.core_message_creation_task()]
        )
    
    @task
    def instagram_content_adaptation_task(self) -> Task:
        return Task(
            config=self.tasks_config['instagram_content_adaptation_task'],
            agent=self.instagram_content_specialist(),
            context=[self.core_message_creation_task()]
        )
    
    @task
    def linkedin_content_adaptation_task(self) -> Task:
        return Task(
            config=self.tasks_config['linkedin_content_adaptation_task'],
            agent=self.linkedin_content_specialist(),
            context=[self.core_message_creation_task()]
        )
    
    @task
    def brand_consistency_review_task(self) -> Task:
        return Task(
            config=self.tasks_config['brand_consistency_review_task'],
            agent=self.brand_guidelines_critic(),
            context=[
                self.core_message_creation_task(),
                self.x_content_adaptation_task(),
                self.facebook_content_adaptation_task(),
                self.instagram_content_adaptation_task(),
                self.linkedin_content_adaptation_task()
            ]
        )
    
    @task
    def content_finalization_task(self) -> Task:
        return Task(
            config=self.tasks_config['content_finalization_task'],
            agent=self.lead_content_creator(),
            context=[
                self.core_message_creation_task(),
                self.image_prompt_creation_task(),
                self.x_content_adaptation_task(),
                self.facebook_content_adaptation_task(),
                self.instagram_content_adaptation_task(),
                self.linkedin_content_adaptation_task(),
                self.brand_consistency_review_task()
            ],
            output_json=CrossPlatformTextPackage
        )
    
    @crew
    def crew(self) -> Crew:
        """Creates the Content Adapter crew"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )