"""
train_router_classifier.py

One-time offline training script for the P4 router's stage-3 fallback classifier.
Run manually whenever the training set changes. Not part of the runtime path.
"""

import pickle
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

# --- Training data ---
# (prompt, label) pairs. Label is "coding" or "reasoning".
TRAINING_DATA = [
    # Coding
    ("this function isn't returning what I expect, can you look at it", "coding"),
    ("how do I structure a class hierarchy for this pipeline", "coding"),
    ("walk me through what this snippet is doing", "coding"),
    ("can you clean this up and make it more efficient", "coding"),
    ("I need help getting this to work with the rest of the codebase", "coding"),
    ("explain what's wrong with my logic here", "coding"),
    ("can you rewrite this so it handles edge cases better", "coding"),
    ("help me set up a config file for this", "coding"),
    ("how should I structure the folder layout for this project", "coding"),
    ("can you help me connect this to the database", "coding"),
    ("what's the best way to handle errors in this flow", "coding"),
    ("this keeps timing out, any idea why", "coding"),
    ("help me write something that processes this data automatically", "coding"),
    ("how do I make this run faster", "coding"),
    ("can you help me set up logging for this", "coding"),
    ("I want to automate this task, where do I start", "coding"),
    ("how do I test whether this is working correctly", "coding"),
    ("can you help me integrate this with the existing tool", "coding"),
    ("this isn't behaving the way I designed it to", "coding"),
    ("how do I structure the input/output for this component", "coding"),

    # Reasoning
    ("explain the tradeoffs between two different approval workflows", "reasoning"),
    ("summarize the key risks in this incident report", "reasoning"),
    ("help me think through how to present this to the review committee", "reasoning"),
    ("what factors should I weigh before recommending this approach", "reasoning"),
    ("can you help me structure an argument for why we need this change", "reasoning"),
    ("explain the implications of this policy on daily operations", "reasoning"),
    ("how would you compare these two vendor proposals", "reasoning"),
    ("help me think through the ethical considerations here", "reasoning"),
    ("what's the reasoning behind requiring three sign-off levels", "reasoning"),
    ("can you help me draft a justification for this decision", "reasoning"),
    ("summarize this document into key takeaways", "reasoning"),
    ("explain why this process might be a compliance risk", "reasoning"),
    ("help me think through the pros and cons of centralizing this", "reasoning"),
    ("what should I consider before escalating this issue", "reasoning"),
    ("can you help me understand the broader context behind this requirement", "reasoning"),
    ("how should I prioritize these competing concerns", "reasoning"),
    ("explain the reasoning a reviewer might use to reject this", "reasoning"),
    ("help me think through how this decision affects other departments", "reasoning"),
    ("what's a good way to frame this recommendation to leadership", "reasoning"),
    ("summarize the strengths and weaknesses of this proposal", "reasoning"),
]

def train():
    texts = [t for t, _ in TRAINING_DATA]
    labels = [l for _, l in TRAINING_DATA]

    vectorizer = TfidfVectorizer(lowercase=True, ngram_range=(1, 2))
    X = vectorizer.fit_transform(texts)

    classifier = LogisticRegression(max_iter=1000)
    classifier.fit(X, labels)

    with open("router_vectorizer.pkl", "wb") as f:
        pickle.dump(vectorizer, f)

    with open("router_classifier.pkl", "wb") as f:
        pickle.dump(classifier, f)

    print(f"Trained on {len(texts)} examples.")
    print("Saved router_vectorizer.pkl and router_classifier.pkl")

if __name__ == "__main__":
    train()