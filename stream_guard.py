import os
import json
import numpy as np
import faiss
import openai
import groq
from dotenv import load_dotenv

from typing import List

load_dotenv(override=True)
openai.api_key = os.environ['OPENAI_API_KEY']
groq_api_key = os.environ['GROQ_API_KEY']

# Setup OpenAI client
openai_client = openai.OpenAI()
embedding_model_id = 'text-embedding-3-small'
embedding_size = 1536

groq_client = groq.Groq(api_key=groq_api_key)
generation_model_id = 'llama3-70b-8192'

class StreamGuardBot:
    def __init__(self, channel: str):
        self.channel = channel
        self.faq = []
        self.response_threshold = 1
        self.toggle_ask_command = False
        self.vector_database = faiss.IndexFlatL2(embedding_size)

        faq = []
        if os.path.exists(f'channels/{self.channel}.jsonl'):
            with open(f'channels/{self.channel}.jsonl') as channel_file:
                faq = [json.loads(line) for line in channel_file]

            # Remove the old FAQ, otherwise there will be duplicates
            os.remove(f'channels/{self.channel}.jsonl')

        # Rebuild vector database
        for qa in faq:
            self.add_qa(qa['question'], qa['answer'])

    def add_qa(self, question: str, answer: str) -> str:
        qa = {'question': question, 'answer': answer}
        self.faq.append(qa)

        response = openai_client.embeddings.create(
            input=[question],
            model=embedding_model_id
        )

        qa_embedding = np.array([response.data[0].embedding])
        self.vector_database.add(qa_embedding)
        with open(f'channels/{self.channel}.jsonl', 'a') as channel_file:
            qa_json = json.dumps(qa)
            channel_file.write(qa_json + '\n')

        return f'Added {question} -> {answer}'

    def remove_qa(self, index: int) -> str:
        index = index - 1
        removed_qa = self.faq.pop(index)

        # FAISS expects a 2-d np.array
        self.vector_database.remove_ids(np.array([index]))
        with open(f'channels/{self.channel}.jsonl', 'w') as channel_file:
            for qa in self.faq:
                qa_json = json.dumps(qa)
                channel_file.write(qa_json + '\n')

        return f"{removed_qa['question']} -> {removed_qa['answer']}"

    def list_faq(self) -> str:
        faq = [
            f'{i + 1}. {qa_dict["question"]} -> {qa_dict["answer"]}'
            for i, qa_dict in enumerate(self.faq)
        ]

        faq = ' | '.join(faq)
        return faq

    def respond(self, question: str) -> str:
        if not self.toggle_ask_command:
            return '!ask command is disabled.'

        system_prompt = (
            "You are Stream Guard Bot a helpful AI assistant to {channel}. "
            "Keep your responses concise and respond in the 3rd person. "
        )

        bot_prompt = system_prompt.format(channel=self.channel)

        generation_api_response = groq_client.chat.completions.create(
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
    
    def _respond(self, question: str) -> str:
        # Ignores query if empty database is empty
        if self.vector_database.ntotal < 1:
            return ''

        system_prompt = (
            "Users are communicating with {channel}, not the AI. "
            "Keep your responses concise and respond in the 3rd person. "
            "Answer questions that correspond to the FAQ. "
            "Respond with 'Not in {channel}'s FAQ.' to unrelated questions. "
            "Do NOT make up your answer .\n"
            "<<FAQ>>\n"
            "{faq}"
        )

        embedding_api_response = openai_client.embeddings.create(
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

        generation_api_response = groq_client.chat.completions.create(
            model=generation_model_id,
            messages=[
                {'role': 'system', 'content': bot_prompt},
                {'role': 'user', 'content': question}
            ],
            max_tokens=75,
            temperature=0
        )

        print("Not in {self.channel}'s FAQ.")
        message = generation_api_response.choices[0].message.content
        return message if message != f"Not in {self.channel}'s FAQ." else ""