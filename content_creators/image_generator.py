import os
import base64
from google import genai
from google.genai import types
from uuid import uuid4
from dotenv import load_dotenv
import logging
from pydantic import BaseModel
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Imagedata(BaseModel):
    id: str
    bytestring: bytes
    mime_type: str
    error: str | None = None

def generate_image(prompt):
    """Generate an image based on a text prompt using Gemini."""
    if not prompt:
        return Imagedata(error='Prompt cannot be empty')

    try:
        # Initialize Gemini with API key
        api_key = os.getenv("GOOGLE_API_KEY")
        logger.info(f"API key: {api_key}")
        if not api_key:
            return Imagedata(error="Google API key not found. Please set the GOOGLE_API_KEY environment variable.")
        
        client = genai.Client(api_key=api_key)
        
        logger.info(f"Generating image with prompt: {prompt}")
        
        # Generate the image
        response = client.models.generate_content(
            model='gemini-2.0-flash-exp',
            contents=prompt,
            config=types.GenerateContentConfig(
            response_modalities=['TEXT', 'IMAGE']
            )
        )

        logger.info(f"Response: {response}")


        # Process the response
        image_id = uuid4().hex
        
        # Extract image data
        for part in response.candidates[0].content.parts:
            if hasattr(part, 'inline_data') and part.inline_data is not None:
                return Imagedata(
                    id=image_id,
                    bytestring=part.inline_data.data,
                    mime_type=part.inline_data.mime_type
                )
        
        return Imagedata(error="No image was found in the response")
    
    except Exception as e:
        logger.error(f"Error generating image: {str(e)}")
        return Imagedata(error=f"Error generating image: {str(e)}")
    
if __name__ == "__main__":
    from PIL import Image
    import io
    prompt = "A children's book drawing of a veterinarian using a stethoscope to listen to the heartbeat of a baby otter."
    image_data = generate_image(prompt)

    if not image_data.error:
        image = Image.open(io.BytesIO(image_data.bytestring))
        image.show()


