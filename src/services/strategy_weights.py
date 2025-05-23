# /services/strategy_weights.py
def weight_prompts(prompts: list[str], priority: list[str]) -> list[str]:
    scored = []
    for prompt in prompts:
        score = 0
        for pri in priority:
            if pri.lower() in prompt.lower():
                score += 2
        scored.append((prompt, score))
    scored.sort(key=lambda x: x[1], reverse=True)
    return [p[0] for p in scored]
