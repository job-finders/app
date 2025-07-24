from typing import List
from pydantic import BaseModel, Field
from src.agents.base import BaseAgent, UserRole
from .schemas import (
    Topic,
    ArticleOutline,
    PerformanceMetrics,
    RefinementInstructions,
    ArticleMarkdown,
    SEOScoreReport,
    PublishDecision,
    SocialCopySet,
    ABVariants,
    ArchiveActions)


# ------------------------------------------------------------------
# Topic Discovery Agent
# ------------------------------------------------------------------
class TopicDiscoveryAgent(BaseAgent):
    name = "TopicDiscoveryAgent"

    def system_prompt(self) -> str:
        return (
            "You are an expert content strategist.\n"
            "Return ONLY valid JSON that matches the Topic schema."
        )

    def prompt(self, site_map: dict) -> str:
        sections = ", ".join(site_map.keys())
        return (
            f"Site sections: {sections}\n"
            f"Site map JSON: {site_map}\n"
            "Generate a list of high-value blog topics for each section."
        )

    def output_model(self):
        return List[Topic]


# ------------------------------------------------------------------
# Article Planner Agent
# ------------------------------------------------------------------
class ArticlePlannerAgent(BaseAgent):
    name = "ArticlePlannerAgent"

    def system_prompt(self) -> str:
        return (
            "You are a senior blog editor.\n"
            "Return ONLY valid JSON that matches the ArticleOutline schema."
        )

    def prompt(self, topic: Topic) -> str:
        return (
            f"Topic: {topic.title}\n"
            f"Keywords: {', '.join(topic.keywords)}"
        )

    def output_model(self):
        return ArticleOutline


# ------------------------------------------------------------------
# Performance Monitor Agent
# ------------------------------------------------------------------
class PerformanceMonitorAgent(BaseAgent):
    name = "PerformanceMonitorAgent"

    def system_prompt(self) -> str:
        return (
            "You are a data analyst for blog performance.\n"
            "Return ONLY valid JSON that matches the PerformanceMetrics schema."
        )

    def prompt(self, slug: str) -> str:
        return f"Slug: {slug}"

    def output_model(self):
        return PerformanceMetrics


# ------------------------------------------------------------------
# Refiner Agent
# ------------------------------------------------------------------
class RefinerAgent(BaseAgent):
    name = "RefinerAgent"

    def system_prompt(self) -> str:
        return (
            "You are a blog optimisation strategist.\n"
            "Return ONLY valid JSON that matches the RefinementInstructions schema."
        )

    def prompt(self, metrics: PerformanceMetrics) -> str:
        return f"Performance metrics: {metrics.model_dump_json()}"

    def output_model(self):
        return RefinementInstructions


# ------------------------------------------------------------------
# 1. Content Generator Agent
# ------------------------------------------------------------------
class ContentGeneratorAgent(BaseAgent):
    name = "ContentGeneratorAgent"

    def system_prompt(self) -> str:
        return (
            "You are a senior technical writer.\n"
            "Return ONLY valid JSON matching the ArticleMarkdown schema.\n"
            "The markdown field must be complete, human-readable, and SEO-ready."
        )

    def prompt(self, outline: ArticleOutline) -> str:
        return (
            f"Write a full, engaging blog post from the following outline:\n"
            f"{outline.model_dump_json(indent=2)}\n"
            f"Requirements:\n"
            f"- 800–1 200 words\n"
            f"- Use H2/H3 headings exactly as listed\n"
            f"- Include 1–2 internal link placeholders: [[slug]]\n"
            f"- End with a clear call-to-action\n"
            f"- Return ONLY JSON with keys: slug, title, markdown, estimated_reading_time"
        )

    def output_model(self):
        return ArticleMarkdown


# ------------------------------------------------------------------
# 2. SEO Audit Agent
# ------------------------------------------------------------------
class SEOAuditAgent(BaseAgent):
    name = "SEOAuditAgent"

    def system_prompt(self) -> str:
        return (
            "You are an SEO specialist.\n"
            "Return ONLY valid JSON matching the SEOScoreReport schema.\n"
            "Be precise and quantitative."
        )

    def prompt(self, content: ArticleMarkdown) -> str:
        return (
            f"Audit this article for SEO:\n"
            f"Title: {content.title}\n"
            f"Markdown:\n{content.markdown}\n\n"
            f"Evaluate:\n"
            f"1. Keyword density (count occurrences / total words)\n"
            f"2. Meta title length (ideal 50–60 chars)\n"
            f"3. Meta description length (ideal 120–160 chars)\n"
            f"4. Count H1, H2, H3 tags\n"
            f"5. Suggest 3 internal link slugs\n"
            f"6. Count images missing alt text\n"
            f"7. Flesch-Kincaid readability score\n"
            f"Return only the JSON object."
        )

    def output_model(self):
        return SEOScoreReport


# ------------------------------------------------------------------
# 3. Publishing Decision Agent
# ------------------------------------------------------------------
class PublishingDecisionAgent(BaseAgent):
    name = "PublishingDecisionAgent"

    def system_prompt(self) -> str:
        return (
            "You are a content strategist.\n"
            "Return ONLY valid JSON matching the PublishDecision schema."
        )

    def prompt(self, seo: SEOScoreReport) -> str:
        return (
            f"SEO audit result:\n{seo.model_dump_json(indent=2)}\n\n"
            f"Rules:\n"
            f"- overall_score ≥ 0.8 → publish\n"
            f"- 0.6 ≤ overall_score < 0.8 → revise\n"
            f"- overall_score < 0.6 → hold\n\n"
            f"Return JSON with keys: slug, action, reasoning"
        )

    def output_model(self):
        return PublishDecision


# ------------------------------------------------------------------
# 4. Social Amplifier Agent
# ------------------------------------------------------------------
class SocialAmplifierAgent(BaseAgent):
    name = "SocialAmplifierAgent"

    def system_prompt(self) -> str:
        return (
            "You are a social-media copywriter.\n"
            "Return ONLY valid JSON matching the SocialCopySet schema."
        )

    def prompt(self, content: ArticleMarkdown) -> str:
        return (
            f"Create platform-specific social copy for this post:\n"
            f"Title: {content.title}\n"
            f"Markdown preview:\n{content.markdown[:600]}...\n\n"
            f"Rules:\n"
            f"- Twitter ≤ 280 chars, include 3 hashtags\n"
            f"- LinkedIn ≤ 3 000 chars, professional tone, 5 hashtags\n"
            f"- Hashtags must be lowercase, no spaces\n"
            f"Return JSON with keys: slug, twitter, linkedin, hashtags"
        )

    def output_model(self):
        return SocialCopySet


# ------------------------------------------------------------------
# 5. A/B Test Designer Agent
# ------------------------------------------------------------------
class ABTestDesignerAgent(BaseAgent):
    name = "ABTestDesignerAgent"

    def system_prompt(self) -> str:
        return (
            "You are a growth marketer.\n"
            "Return ONLY valid JSON matching the ABVariants schema."
        )

    def prompt(self, content: ArticleMarkdown) -> str:
        return (
            f"Generate 2–5 headline/hook variants for A/B testing this post:\n"
            f"Title: {content.title}\n"
            f"Markdown:\n{content.markdown[:400]}...\n\n"
            f"Rules:\n"
            f"- Each variant ≤ 90 characters\n"
            f"- Highlight different angles: benefit, curiosity, urgency, data\n"
            f"Return JSON with keys: slug, variants"
        )

    def output_model(self):
        return ABVariants


# ------------------------------------------------------------------
# 6. Archive Curator Agent
# ------------------------------------------------------------------
class ArchiveCuratorAgent(BaseAgent):
    name = "ArchiveCuratorAgent"

    def system_prompt(self) -> str:
        return (
            "You are a content librarian.\n"
            "Return ONLY valid JSON matching the ArchiveActions schema."
        )

    def prompt(self, metrics_list: List[PerformanceMetrics]) -> str:
        data = "\n".join(m.model_dump_json() for m in metrics_list)
        return (
            f"Performance data:\n{data}\n\n"
            f"Rules:\n"
            f"- Views > 10 000 & CTR > 5 % → repurpose\n"
            f"- Views < 100 & age > 180 days → delete\n"
            f"- Views 100–1 000 & CTR < 2 % → update\n"
            f"- Similar slugs with overlapping keywords → merge\n"
            f"Return JSON with keys: slugs, action, justification"
        )

    def output_model(self):
        return ArchiveActions
