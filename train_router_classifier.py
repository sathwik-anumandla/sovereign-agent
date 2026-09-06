"""
train_router_classifier.py

Offline training script for Stage 3 fallback classifier in the P4 router.
Trains TF-IDF vectorizer + Logistic Regression model on expanded dataset of coding vs reasoning prompts.
"""

import pickle
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

# --- Expanded Training Data ---
# (prompt, label) pairs. Label is "coding" or "reasoning".
TRAINING_DATA = [
    # --- CODING (Explicit programming, debugging, refactoring, script creation, syntax, API execution) ---
    ("this function isn't returning what I expect, can you look at it", "coding"),
    ("how do I structure a class hierarchy for this pipeline", "coding"),
    ("walk me through what this snippet is doing", "coding"),
    ("can you clean this up and make it more efficient", "coding"),
    ("I need help getting this to work with the rest of the codebase", "coding"),
    ("explain what's wrong with my logic here in this function", "coding"),
    ("can you rewrite this code so it handles edge cases better", "coding"),
    ("help me set up a config file for this script", "coding"),
    ("how should I structure the folder layout for this python project", "coding"),
    ("can you help me connect this to the database using SQLAlchemy", "coding"),
    ("what's the best way to handle exceptions in this python script", "coding"),
    ("this loop keeps timing out, any idea why", "coding"),
    ("help me write a script that processes this CSV data automatically", "coding"),
    ("how do I make this code run faster using multiprocessing", "coding"),
    ("can you help me set up logging for this microservice", "coding"),
    ("I want to automate this task with python, where do I start", "coding"),
    ("how do I test whether this API endpoint is working correctly", "coding"),
    ("can you help me integrate this library with my existing script", "coding"),
    ("this function isn't behaving the way I designed it to", "coding"),
    ("how do I structure the input/output schemas for Pydantic", "coding"),
    ("write a python script to parse logs and extract error counts", "coding"),
    ("fix this KeyError in my dictionary lookup", "coding"),
    ("how do I filter a pandas dataframe by column value", "coding"),
    ("convert this JSON string into a python dictionary", "coding"),
    ("write a function to calculate Fibonacci numbers recursively", "coding"),
    ("how to make an HTTP POST request using Python requests library", "coding"),
    ("create a regex pattern to validate email addresses", "coding"),
    ("how do I handle async functions in Python asyncio", "coding"),
    ("write a unit test using pytest for this module", "coding"),
    ("how to mock a network call in python unittests", "coding"),
    ("implement a stack data structure in Python", "coding"),
    ("how to sort a list of objects by attribute in python", "coding"),
    ("write a script to scrape product prices from a web page", "coding"),
    ("how to execute bash commands inside python code", "coding"),
    ("fix the syntax error on line 42 in this script", "coding"),
    ("how do I pass command line arguments using argparse", "coding"),
    ("write a script to merge two Excel files into one sheet", "coding"),
    ("how to read environment variables from a .env file in python", "coding"),
    ("create a REST endpoint using FastAPI with GET and POST methods", "coding"),
    ("how to build a Docker container for a Python application", "coding"),
    ("write a function to check if a string is a palindrome", "coding"),
    ("how to use lambda functions with map and filter in python", "coding"),
    ("fix this AttributeError when calling methods on NoneType", "coding"),
    ("how to serialize a datetime object to JSON", "coding"),
    ("write a python script to bulk rename files in a folder", "coding"),
    ("how to handle CORS issues in my API server code", "coding"),
    ("implement binary search algorithm in python", "coding"),
    ("how to set up virtualenv and install packages via pip", "coding"),
    ("write a function to merge two sorted lists", "coding"),
    ("how to parse XML files using ElementTree in python", "coding"),
    ("write a script to generate synthetic benchmark data", "coding"),
    ("how to encrypt data using cryptography module in python", "coding"),
    ("fix this IndentationError in my Python file", "coding"),
    ("write a SQL query to join user and orders tables", "coding"),
    ("how to create a pandas pivot table from raw log data", "coding"),
    ("write a python decorator to measure function execution time", "coding"),
    ("how to connect python to PostgreSQL using psycopg2", "coding"),
    ("fix memory leak in this long-running Python process", "coding"),
    ("how to write custom middleware in FastAPI", "coding"),
    ("write a script to clean missing values from a dataset", "coding"),

    # --- REASONING (Conceptual questions, explanations, pros/cons, design trade-offs, analytical discussions, summaries) ---
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
    ("explain what an air-gapped computer system is in 2 concise sentences", "reasoning"),
    ("what are 3 main advantages of Python for rapid software prototyping", "reasoning"),
    ("explain the difference between synchronous and asynchronous execution", "reasoning"),
    ("what are the key security principles of Zero Trust architecture", "reasoning"),
    ("compare monolithic architecture vs microservices architecture", "reasoning"),
    ("explain how garbage collection works conceptually in programming languages", "reasoning"),
    ("what are the main differences between relational and non-relational databases", "reasoning"),
    ("explain the concept of rate limiting in web system architecture", "reasoning"),
    ("what are the benefits and drawbacks of using cloud storage vs on-premises storage", "reasoning"),
    ("explain how public key cryptography works at a high level", "reasoning"),
    ("what factors determine network latency and bandwidth in industrial networks", "reasoning"),
    ("explain the principles of agile methodology vs waterfall development", "reasoning"),
    ("what are the main risks associated with outdated open-source dependencies", "reasoning"),
    ("explain the concept of technical debt and how teams should manage it", "reasoning"),
    ("what are the key components of a high-availability disaster recovery plan", "reasoning"),
    ("explain the difference between authentication and authorization", "reasoning"),
    ("what are the strategic advantages of using open-weight AI models locally", "reasoning"),
    ("explain the trade-offs of using automated testing vs manual QA testing", "reasoning"),
    ("what are the core requirements of ISO 27001 compliance for data security", "reasoning"),
    ("explain how load balancers distribute traffic across server pools", "reasoning"),
    ("what are the main causes of database locks and deadlocks in enterprise systems", "reasoning"),
    ("explain the concept of idempotency in RESTful API design", "reasoning"),
    ("what are the advantages of containerization over traditional virtual machines", "reasoning"),
    ("explain the role of a message broker like Kafka or RabbitMQ in system integration", "reasoning"),
    ("what should be included in a technical post-mortem report after an outage", "reasoning"),
    ("explain how neural networks learn through backpropagation conceptually", "reasoning"),
    ("what are the primary considerations when designing an industrial IoT architecture", "reasoning"),
    ("explain the concept of eventual consistency in distributed systems", "reasoning"),
    ("what are the pros and cons of adopting micro-frontends in web applications", "reasoning"),
    ("explain the importance of data governance in enterprise analytics", "reasoning"),
    ("how to make cheese cakes", "reasoning"),
    ("how to bake a cake", "reasoning"),
    ("recipe for chocolate cake", "reasoning"),
    ("how to prepare tea or coffee", "reasoning"),
    ("what is the history of pizza", "reasoning"),
    ("how to cook pasta", "reasoning"),
    ("tell me a story about space", "reasoning"),
    ("how do birds fly", "reasoning"),
    ("how to make a sandwich", "reasoning"),
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

    print(f"Trained on {len(texts)} examples ({labels.count('coding')} coding, {labels.count('reasoning')} reasoning).")
    print("Saved router_vectorizer.pkl and router_classifier.pkl")

if __name__ == "__main__":
    train()