Please evaluate this research paper based on the following criteria:

{criteria_text}

Rate each criterion on a scale of 1-10 where:
- 1-3: Poor/Below average
- 4-6: Average/Adequate  
- 7-8: Good/Above average
- 9-10: Excellent/Outstanding

Paper content:
{paper_text}

Provide your response as a single JSON object. The keys of the object should be the criteria names. For each criterion, provide a nested JSON object with "score" (a numerical rating from 1-10) and "justification" (a brief explanation for the score).

Here is an example of the desired output format:
```json
{
    "CriteriaA": {
        "score": 8,
        "justification": "This is the reason why the paper meets criteria A"
    },
    "CriteriaB": {
        "score": 2,
        "justficication": "This describes why the paper is bad in criteria B"
    }
}
```