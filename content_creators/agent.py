from openai import OpenAI
import json
from pydantic import BaseModel
from content_creators.crew import ContentAdapterCrew
from content_creators.image_generator import generate_image
class ContentCreator:
    def __init__(self):
        self.crew = ContentAdapterCrew()

    def query2inputs(self, query: str):
        system_prompt = """
        You are a helpful assistant that converts a user's query into a set of inputs for a crew.
        Here is the expected format of the output:
        ```json
        {
            "brand_name": "...",
            "brand_description": "...",
            "target_audience": "...",
            "tone_of_voice": "...",
            "content_brief": {
                "topic": "...",
                "purpose": "...",
                "key_points": ["..."],
                "call_to_action": "..."
            },
            "brand_colors": {
                "primary": "...",
                "secondary": "...",
                "accent": "...",
                "background": "...",
                "text": "..."
            },
l
        }
        ```
        <INSTRUCTIONS>
        - Convert the user's query into the expected format.
        - The content_brief should be a detailed description of the content to be created.
        - The key_points should be a list of key points that should be included in the content.
        - If no key points are provided, create a list of 3-5 key points.
        - The call_to_action should be a call to action that should be included in the content.
        - If no call to action is provided, create a call to action.
        - if no purpose is provided, create a purpose.
        - if no brand_colors are provided, create a brand_colors.
        </INSTRUCTIONS>
        """

        user_prompt = f"""
        Here is the user's query:
        {query}
        """
        client = OpenAI()
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)

    async def invoke(self, query: str):
        print("Converting query to inputs...")
        inputs = self.query2inputs(query)


        print(f"Inputs: {inputs}")
        print("Running crew...")
        result = self.crew.crew().kickoff(inputs=inputs)

        # Parse the raw content from the CrewAI result
        result_data = result.model_dump()
        content_data = json.loads(result_data['raw'])
        
        # Extract the image prompt
        image_prompt = content_data['image_prompt']
        print(f"Found image prompt: {image_prompt[:50]}...")

        # Generate the image
        print("Generating image...")
        image_data = generate_image(image_prompt)

        return content_data, image_data


if __name__ == "__main__":
    import asyncio
    import os
    from dotenv import load_dotenv
    from content_creators.image_generator import generate_image
    load_dotenv()


    agent = ContentCreator()
    query = """Write social media content for the launch of a new AI Process Automation tool.
    The tool is a new AI Process Automation tool that is a web app that automates manual processes.
    You are doing this for TechInnovate, a tech consultancy specializing in AI solutions.
    The target audience is CTOs and Innovation Directors at mid-size enterprises.
    The tone of voice should be professional yet conversational, authoritative but approachable.
    """

    crew_result, image_data = asyncio.run(agent.invoke(query))
    print(crew_result)

    # make output directory
    os.makedirs("output", exist_ok=True)

    # Save the image to a file
    with open("output/generated_image.png", "wb") as f:
        f.write(image_data.bytestring)
    
    # Save the full content result to JSON
    with open("output/content_package.json", "w") as f:
        json.dump(crew_result, f, indent=2)
    print("Content package saved to content_package.json")
