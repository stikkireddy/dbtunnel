# pip install langchain-community tiktoken langchain mlflow-skinny chromadb rank_bm25 simsimd

import asyncio
from typing import TypeVar, Protocol, AsyncIterator
import chainlit as cl
from databricks_genai_inference.api.chat_completion import ChatCompletion
from langchain.retrievers import MergerRetriever, ContextualCompressionRetriever
from langchain.retrievers.document_compressors import DocumentCompressorPipeline
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.document_loaders import GutenbergLoader
from langchain_community.document_transformers import EmbeddingsRedundantFilter, LongContextReorder
from langchain_community.embeddings import DatabricksEmbeddings
from langchain_community.retrievers import BM25Retriever
from langchain_community.vectorstores.chroma import Chroma
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate, PromptTemplate
from langchain_core.runnables import RunnablePassthrough


class HasMessage(Protocol):
    message: str


T = TypeVar('T', bound=HasMessage)


class AsyncGeneratorWrapper(AsyncIterator[T]):
    def __init__(self, gen):
        self.gen = gen

    def __aiter__(self) -> 'AsyncGeneratorWrapper[T]':
        return self

    async def __anext__(self) -> T:
        try:
            # Use asyncio to yield control and create asynchronous behavior
            await asyncio.sleep(0)
            return next(self.gen)
        except StopIteration:
            raise StopAsyncIteration


def format_docs(docs):
    return "\n\n".join(
        f"{doc.page_content}"
        for doc in docs)


v0_template = """
[INST] You are going to answer questions about the book of Frankenstein; Or, The Modern Prometheus by Mary Wollstonecraft Shelley
You will not answer anything else.

Here's some context which might or might not help you answer: {context}

Based on this context, answer this question: {question}
[/INST]
"""

prompt = ChatPromptTemplate(input_variables=['context', 'question'],
                            messages=[
                                HumanMessagePromptTemplate(
                                    prompt=PromptTemplate(
                                        input_variables=['context', 'question'],
                                        template=v0_template))])

loader = GutenbergLoader("https://www.gutenberg.org/cache/epub/84/pg84.txt")
docs = loader.load()
text_splitter = CharacterTextSplitter.from_tiktoken_encoder(
    chunk_size=512, chunk_overlap=100
)
docs = [Document(page_content=text) for text in text_splitter.split_text(docs[0].page_content)]
embeddings = DatabricksEmbeddings(endpoint="databricks-bge-large-en")
chroma = Chroma.from_documents(docs, embeddings)
chroma_retriever = chroma.as_retriever(search_type="mmr", search_kwargs={"k": 5, "include_metadata": True})
bm25_retriever = BM25Retriever.from_documents(docs, search_type="mmr", search_kwargs={"k": 5, "include_metadata": True})
lotr = MergerRetriever(retrievers=[chroma_retriever, bm25_retriever])
#
filter_ = EmbeddingsRedundantFilter(embeddings=embeddings)
reordering = LongContextReorder()
pipeline = DocumentCompressorPipeline(transformers=[filter_, reordering])
compression_retriever = ContextualCompressionRetriever(
    base_compressor=pipeline, base_retriever=lotr
)

rag_prompt = (
        {"context": compression_retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
)


def run_chat_completion(msgs) -> AsyncGeneratorWrapper[HasMessage]:
    resp = ChatCompletion.create(model="mixtral-8x7b-instruct",
                                 messages=[{"role": "system", "content": "You are a helpful assistant."},
                                           *msgs],
                                 temperature=0.1,
                                 stream=True, )
    return AsyncGeneratorWrapper(resp)


@cl.step
async def retriever(content: str):
    loop = asyncio.get_event_loop()
    await cl.sleep(0)
    processed_prompt = await loop.run_in_executor(None, rag_prompt.invoke, content)
    return [{"content": msg.content, "role": "user"} for msg in processed_prompt.to_messages()]


@cl.on_chat_start
async def on_start():
    msg = cl.Message(content="Please ask any questions about the book of Frankenstein; Or, The Modern Prometheus by Mary Wollstonecraft Shelley. Example: Who is Frankenstein's monster?")

    await msg.send()


@cl.on_message
async def main(message: cl.Message):
    # Your custom logic goes here...
    response = cl.Message(content="")
    loop = asyncio.get_event_loop()
    await response.send()  # causes loading indicator
    msgs = await retriever(message.content)
    token_stream = await loop.run_in_executor(None, run_chat_completion, msgs)
    async for token_chunk in token_stream:
        chunk: HasMessage = token_chunk  # noqa token_chunk is a ChatCompletionChunkObject not Future
        await response.stream_token(chunk.message)

    # Send a response back to the user
    await response.update()
