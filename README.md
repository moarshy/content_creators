# Cross-Platform Content Adapter

This project implements a Social Media Marketing Agent that adapts content across multiple platforms while maintaining brand consistency. The system leverages CrewAI to coordinate specialized agents that work together to generate platform-specific content.

## Overview

The Cross-Platform Content Adapter takes brand information and a content brief as input, then generates optimized content for multiple social media platforms and creates an AI-generated image that aligns with the brand identity.

## Agents

The system is built around a crew of specialized agents:

1. **Lead Content Creator**: Develops the core messaging that maintains brand consistency across platforms.
2. **Image Prompt Creator**: Creates detailed prompts for AI image generation that align with the brand's identity and core message.
3. **Platform Specialists**:
   * **X/Twitter Specialist**: Optimizes content for Twitter's character limits and audience expectations.
   * **Facebook Specialist**: Adapts content for Facebook's algorithm and community-oriented features.
   * **Instagram Specialist**: Creates engaging captions with strategic hashtag use.
   * **LinkedIn Specialist**: Adapts content for professional audiences with appropriate tone.
4. **Brand Guidelines Critic**: Reviews all content to ensure adherence to brand voice and messaging consistency.

## Workflow

1. **Core Message Creation**: The Lead Content Creator develops strategic messaging based on the content brief.
2. **Image Prompt Creation**: The Image Prompt Creator crafts a detailed prompt for AI image generation.
3. **Platform Adaptation**: Specialists adapt the core message for each platform's unique requirements.
4. **Brand Review**: The Brand Guidelines Critic reviews all content for adherence to brand guidelines.
5. **Finalization**: The Lead Content Creator integrates feedback and finalizes all content.
6. **Image Generation**: After content creation, an AI image is generated using the prompt (handled outside the CrewAI workflow).

## Input

The system requires the following inputs:
* **Brand Information**: Name, description, target audience, tone of voice, brand guidelines, and colors
* **Social Accounts**: Handles for the brand's social media accounts
* **Content Brief**: Topic, purpose, key points, and call to action

## Output

The system generates:
1. **Cross-Platform Content Package**: A JSON file containing:
   * Core message
   * Image prompt
   * Platform-specific content for X/Twitter, Facebook, Instagram, and LinkedIn
   * Brand alignment notes
2. **Generated Image**: A PNG image created based on the image prompt.

## Usage

To run the content adapter:

```bash
python main.py
```

The system will generate content based on the provided inputs and save the results to the `output` directory.