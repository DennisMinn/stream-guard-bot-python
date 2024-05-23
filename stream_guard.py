import os
import json
import numpy as np
import faiss
from openai import OpenAI

from typing import List

client = OpenAI()
embedding_size = 1536
embedding_model_id = 'text-embedding-3-small'
generation_model_id = 'gpt-3.5-turbo'

class StreamGuardBot:
    def __init__(self, channel: str):
        self.channel = channel
        self.faq = []
        self.response_threshold = 1
        self.vector_database = faiss.IndexFlatL2(embedding_size)

        faq = []
        if os.path.exists(f'channels/{self.channel}.jsonl'):
            with open(f'channels/{self.channel}.jsonl') as channel_file:
                faq = [json.loads(line) for line in channel_file]

            # Remove the old FAQ, otherwise there will be duplicates
            os.remove(f'channels/{self.channel}.jsonl')

        # Re-add the FAQ
        for qa in faq:
            self.add_qa(qa['question'], qa['answer'])
                    
    def add_qa(self, question: str, answer: str):
        qa = {'question': question, 'answer': answer}
        self.faq.append(qa)

        response = client.embeddings.create(
            input=[question],
            model=embedding_model_id
        )

        qa_embedding = np.array([response.data[0].embedding])
        self.vector_database.add(qa_embedding)
        with open(f'channels/{self.channel}.jsonl', 'a') as channel_file:
            qa_json = json.dumps(qa)
            channel_file.write(qa_json + '\n')

    def remove_qa(self, index: int):
        index = index - 1
        qa = self.faq.pop(index)

        # FAISS expects a 2-d np.array
        self.vector_database.remove_ids(np.array([index]))
        with open(f'channels/{self.channel}.jsonl', 'w') as channel_file:
            for qa in self.faq:
                qa_json = json.dumps(qa)
                channel_file.write(qa_json + '\n')

        return f"{qa['question']} -> {qa['answer']}"

    def list_faq(self):
        faq = [
            f'{i + 1}. {qa_dict["question"]} -> {qa_dict["answer"]}'
            for i, qa_dict in enumerate(self.faq)
        ]

        faq = ' | '.join(faq)
        return faq
    
    def respond(self, question: str):
        # Ignores query if empty database is empty
        if self.vector_database.ntotal < 1:
            return ''
        
        system_prompt = (
            "Users are communicating with {channel}, not the AI "
            "To answer, refer to the << FAQ >>."
            "Keep your responses concise and respond in the 3rd person. "
            "Do not make up your response or use external information.\n"
            "<< FAQ >>\n"
            "{faq}\n"
        )

        embedding_api_response = client.embeddings.create(
            input=[question],
            model=embedding_model_id
        )
        question_embedding = np.array([embedding_api_response.data[0].embedding])
        
        distance, faq_index = self.vector_database.search(question_embedding, 1)
        distance, faq_index = distance.item(), faq_index.item()

        bot_prompt = system_prompt.format(
            channel=self.channel,
            faq=str(self.faq[faq_index])
        )
        
        generation_api_response = client.chat.completions.create(
            model=generation_model_id,
            messages=[
                {'role': 'system', 'content': bot_prompt},
                {'role': 'user', 'content': question}
            ],
            max_tokens=75,
            temperature=0
        )

        message = generation_api_response.choices[0].message.content
        return message
    
    def _respond(self, question: str):
        # Ignores query if empty database is empty
        if self.vector_database.ntotal < 1:
            return ''

        system_prompt = (
            "Users are communicating with {channel}, not the AI "
            "To answer, refer to the << FAQ >>."
            "Keep your responses concise and respond in the 3rd person. "
            "If the answer is not provided in the << FAQ >>, respond with 'I do not know'. "
            "Do not make up your response or use external information.\n"
            "<< FAQ >>\n"
            "{faq}\n"
        )
        
        embedding_api_response = client.embeddings.create(
            input=[question],
            model=embedding_model_id
        )
        question_embedding = np.array([embedding_api_response.data[0].embedding])
        
        distance, faq_index = self.vector_database.search(question_embedding, 1)
        distance, faq_index = distance.item(), faq_index.item()

        if distance > self.response_threshold:
            return ''

        bot_prompt = system_prompt.format(
            channel=self.channel,
            faq=str(self.faq[faq_index])
        )
        
        generation_api_response = client.chat.completions.create(
            model=generation_model_id,
            messages=[
                {'role': 'system', 'content': bot_prompt},
                {'role': 'user', 'content': question}
            ],
            max_tokens=75,
            temperature=0
        )

        message = generation_api_response.choices[0].message.content
        return message if message != 'I do not know.' else ''