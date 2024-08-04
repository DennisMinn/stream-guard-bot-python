import os
import numpy as np
import pickle
import openai
from dotenv import load_dotenv
from collections import namedtuple


load_dotenv(override=True)
openai.api_key = os.environ['OPENAI_API_KEY']

# Setup OpenAI client
openai_client = openai.OpenAI()
expensive_generation_model_id = 'gpt-4o-2024-05-13'
budget_generation_model_id = 'gpt-4o-mini'
embedding_model_id = 'text-embedding-3-small'


FAQEmbedding = namedtuple('FAQEmbedding', ('question', 'answer', 'embedding'))


class StreamGuardBot:
    def __init__(self, channel: str):
        self.channel = channel
        self.response_threshold = 0.5
        self.toggle_ask_command = False
        self.faq_embeddings_list = []

    def add_faq(self, question: str, answer: str) -> str:
        # Create embeddings
        response = openai_client.embeddings.create(
            input=[question],
            model=embedding_model_id
        )
        embedding = np.array([response.data[0].embedding])

        faq_embedding = FAQEmbedding(question, answer, embedding)
        self.faq_embeddings_list.append(faq_embedding)

        self.to_pickle()

        return f'Added {question} -> {answer}'

    def remove_faq(self, index: int) -> str:
        removed_faq = self.faq_embeddings_list.pop(index)

        self.to_pickle()

        return f"Removed {removed_faq.question} -> {removed_faq.answer}"

    def update_faq(self, index: int, answer: str) -> str:
        faq_embedding = self.faq_embeddings_list[index]
        new_faq_embedding = FAQEmbedding(faq_embedding.question, answer, faq_embedding.embedding)

        self.faq_embeddings_list[index] = new_faq_embedding

        self.to_pickle()

        return f'Updated {new_faq_embedding.question} -> {answer}'

    def list_faq(self) -> str:
        faq_list = [
            f'{i + 1}. {faq_dict["question"]} -> {faq_dict["answer"]}'
            for i, faq_dict in enumerate(self.faq_embeddings_list)
        ]

        faq_list = ' | '.join(faq_list)
        return faq_list

    def respond(self, question: str) -> str:
        if not self.toggle_ask_command:
            return '!ask command is disabled.'

        system_prompt = (
            "You are Stream Guard Bot a helpful AI assistant to {channel}. "
            "Keep your responses concise and respond in the 3rd person. "
        )

        bot_prompt = system_prompt.format(channel=self.channel)

        generation_api_response = openai_client.chat.completions.create(
            model=budget_generation_model_id,
            messages=[
                {'role': 'system', 'content': bot_prompt},
                {'role': 'user', 'content': question}
            ],
            max_tokens=75,
            temperature=0
        )

        message = generation_api_response.choices[0].message.content
        return message

    def retrieval_respond(self, question: str, faq_index: int) -> str:
        system_prompt = (
            "Users are communicating with {channel}, not the AI. "
            "Keep your responses concise and respond in the 3rd person. "
            "Answer questions that correspond to the FAQ. "
            "Respond with 'Not in {channel}'s FAQ.' to unrelated questions. "
            "Do NOT make up your answer .\n"
            "<<FAQ>>\n"
            "{{question: {question}, answer: {answer}}}"
        )

        faq_embedding = self.faq_embeddings_list[faq_index]
        bot_prompt = system_prompt.format(
            channel=self.channel,
            question=faq_embedding.question,
            answer=faq_embedding.answer
        )

        generation_api_response = openai_client.chat.completions.create(
            model=budget_generation_model_id,
            messages=[
                {'role': 'system', 'content': bot_prompt},
                {'role': 'user', 'content': question}
            ],
            max_tokens=75,
            temperature=0
        )

        message = generation_api_response.choices[0].message.content
        return message if message != f"Not in {self.channel}'s FAQ." else ""

    def get_related_faq_index(self, question: str):
        # Ignores query if empty database is empty
        if len(self.faq_embeddings_list) < 1:
            return -1

        similiarity_scores = self.get_similiarity_scores(question)
        index = np.argmax(similiarity_scores).item()

        if similiarity_scores[index] < self.response_threshold:
            return -1
        else:
            return index

    def get_similiarity_scores(self, question: str):
        embedding_api_response = openai_client.embeddings.create(
            input=[question],
            model=embedding_model_id
        )

        question_embedding = np.array([embedding_api_response.data[0].embedding])

        _, _, embeddings = zip(*self.faq_embeddings_list)
        embeddings = np.concatenate(embeddings, axis=0)

        if len(embeddings) == 1:
            embeddings = embeddings.reshape(1, -1)

        similiarity_scores = np.dot(question_embedding, embeddings.T)
        similiarity_scores = similiarity_scores.squeeze()
        return similiarity_scores

    @classmethod
    def from_pickle(fpath):
        with open(fpath, 'rb') as pickle_file:
            stream_guard_bot = pickle.load(pickle_file)

        return stream_guard_bot

    def to_pickle(self):
        with open(f'channels/{self.channel}.pkl', 'wb') as pickle_file:
            pickle.dump(self, pickle_file)
