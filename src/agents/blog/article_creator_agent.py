# agents/blog/article_creator_agent.py
from src.agents.base import BaseAgent
from pydantic import BaseModel
import openai

class Article(BaseModel):
    title: str
    content: str
    cover_image_url: str | None = None

class ArticleCreatorAgent(BaseAgent):
    async def run(self, topic, prompt):
        system_prompt = f"Write a valuable, SEO-rich article for job seekers/employers. Topic: {topic}"
        user_input = f"Create an article: {prompt}"

        response = await openai.ChatCompletion.acreate(
            model="deepseek-coder:latest",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ]
        )

        article_text = response.choices[0].message.content.strip()
        return Article(title=prompt, content=article_text)
