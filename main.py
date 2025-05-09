#!/usr/bin/env python
import os
import json
from content_creators.crew import ContentAdapterCrew
from content_creators.image_generator import generate_image
import time
import openai
from pydantic import BaseModel

def run():
    # Sample inputs from onboarding
    inputs = {
        'brand_name': 'TechInnovate',
        'brand_description': 'A forward-thinking tech consultancy specializing in AI solutions',
        'target_audience': 'CTOs and Innovation Directors at mid-size enterprises',
        'tone_of_voice': 'Professional yet conversational, authoritative but approachable',
        'post_as_company': True,
        'website': 'techinnovate.com',
        'brand_guidelines': 'Focus on solutions not problems, avoid jargon, highlight human impact of technology',
        'brand_colors': {
            'primary': '#0052CC',
            'secondary': '#00B8D9',
            'accent': '#36B37E',
            'background': '#FFFFFF',
            'text': '#172B4D'
        },
        'social_accounts': {
            'instagram': '@techinnovate',
            'facebook': 'TechInnovate Solutions',
            'linkedin': 'TechInnovate',
            'twitter': '@TechInnovate'
        },
        'content_brief': {
            'topic': 'Launch of our new AI Process Automation tool',
            'purpose': 'Announce new product launch',
            'key_points': [
                'Reduces manual processing time by 75%',
                'Integrates with existing workflow tools',
                'No coding required for implementation',
                'Free 30-day trial available'
            ],
            'call_to_action': 'Sign up for the free trial at techinnovate.com/aia-trial'
        }
    }
    
    # Run the crew to generate all content
    print("Starting content generation...")
    start_time = time.time()
    crew_result = ContentAdapterCrew().crew().kickoff(inputs=inputs)
    end_time = time.time()
    print(f"Content generation completed in {end_time - start_time:.2f} seconds!")
    
    # Parse the raw content from the CrewAI result
    result_data = crew_result.model_dump()
    content_data = json.loads(result_data['raw'])
    
    # Extract the image prompt
    image_prompt = content_data['image_prompt']
    print(f"Found image prompt: {image_prompt[:50]}...")
    
    # Generate the image
    print("Generating image...")
    image_data = generate_image(image_prompt)

    # make output directory
    os.makedirs("output", exist_ok=True)

    # Save the image to a file
    with open("output/generated_image.png", "wb") as f:
        f.write(image_data.bytestring)
    
    # Save the full content result to JSON
    with open("output/content_package.json", "w") as f:
        json.dump(content_data, f, indent=2)
    print("Content package saved to content_package.json")
    
    return content_data

class Inputs(BaseModel):
    brand_name: str
    brand_description: str
    target_audience: str
    tone_of_voice: str
    post_as_company: bool
    website: str

if __name__ == "__main__":
    # run()

    requirements_description = """
    Write social media content for the launch of new AI Process Automation tool.
    
    """

