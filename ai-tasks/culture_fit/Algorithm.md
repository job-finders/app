🧠 AI-Driven Fit Evaluation – Algorithm Sketch
Inputs:
CultureDefinition (traits, values)

Questionnaire with tagged questions

JobseekerCultureResponse (answers)

Steps:
Tag Match Analysis

Map answers to cultural tags.

Weight answers based on how strongly they reflect certain traits (e.g., "prefers autonomy").

Semantic Matching

Use embedding models (e.g., OpenAI embeddings or sentence-transformers) to compare:

CultureDefinition text vs. jobseeker response.

Calculate cosine similarity for each trait.

Score Aggregation

Combine:

Direct tag match scores

Semantic similarity scores

Output:

Final Fit Score (0–100%)

Top Matching Traits

Possible Conflict Areas

Optional: AI Feedback Generator

Generate a paragraph of advice like:

“You align well with collaborative environments, but may face challenges in high-autonomy teams.”