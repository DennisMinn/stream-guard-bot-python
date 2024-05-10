import os
import numpy as np
import faiss
from dotenv import load_dotenv
from openai import OpenAI
from sentence_transformers import SentenceTransformer

from typing import List

load_dotenv(override=True)

system_prompt = (
    "Users are communicating with {channel}, not the AI "
    "To answer, refer to the << FAQ >>."
    "Keep your responses concise and respond in the 3rd person. "
    "If the answer is not provided in the << FAQ >>, respond with 'I do not know'. "
    "Do not make up your response or use external information.\n"
    "<< FAQ >>\n"
    "{documents}\n"
)

open_ai_secret = os.environ['OPENAI_API_KEY']

embedding_model_id = 'sentence-transformers/all-mpnet-base-v2'
embedding_model = SentenceTransformer(embedding_model_id)

client = OpenAI()

class StreamGuardBot:
    def __init__(self, channel: str):
        self.channel = channel
        self.embedding_model = embedding_model
        self.faq = []
        self.response_threshold = 1

        embedding_size = embedding_model.get_sentence_embedding_dimension()
        self.vector_database = faiss.IndexFlatL2(embedding_size)

    def add_qa(self, question: str, answer: str):
        document = {'question': question, 'answer': answer}
        self.faq.append(document)

        document_embedding = self.embedding_model.encode([document])
        self.vector_database.add(document_embedding)

    def remove_qa(self, index: int):
        # TODO allow for multiple indices

        index = index - 1
        self.faq.pop(index)
        # FAISS expects a 2-d np.array
        self.vector_database.remove_ids(np.array([index]))

    def list_faq(self):
        faq = [
            f'{i + 1}. {qa_dict["question"]} -> {qa_dict["answer"]}'
            for i, qa_dict in enumerate(self.faq)
        ]

        faq = ' | '.join(faq)
        return faq
    
    def respond(self, queries: List[str]):
        # TODO batch responses

        # Ignores query if empty database is empty
        if self.vector_database.ntotal < 1:
            return ''
        
        query_embeddings = self.embedding_model.encode(queries)
        distances, indices = self.vector_database.search(query_embeddings, 1)
        documents = [str(self.faq[index[0]]) for index in indices]

        # Ignores query if retrieved document is unrelated
        if distances[0] > self.response_threshold:
            return ''

        bot_prompt = system_prompt.format(
            channel=self.channel,
            documents='\n'.join(documents)
        )
        
        response = client.chat.completions.create(
            model='gpt-3.5-turbo',
            messages=[
                {'role': 'system', 'content': bot_prompt},
                {'role': 'user', 'content': queries[0]}
            ],
            max_tokens=75,
            temperature=0
        )

        message = response.choices[0].message.content
        
        return message if message != 'I do not know' else ''