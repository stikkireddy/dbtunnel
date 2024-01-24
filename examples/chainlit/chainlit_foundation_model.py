import asyncio
from typing import TypeVar, Protocol, AsyncIterator
import chainlit as cl
from databricks_genai_inference.api.chat_completion import ChatCompletion


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


def run_chat_completion(msgs) -> AsyncGeneratorWrapper[HasMessage]:
    resp = ChatCompletion.create(model="mixtral-8x7b-instruct",
                                 messages=[{"role": "system", "content": "You are a helpful assistant."},
                                           *msgs],
                                 temperature=0.1,
                                 stream=True, )
    return AsyncGeneratorWrapper(resp)

@cl.on_message
async def main(message: cl.Message):
    # Your custom logic goes here...
    response = cl.Message(content="")
    loop = asyncio.get_event_loop()
    await response.send() # causes loading indicator
    msgs = [{"content": message.content, "role": "user"}]
    token_stream = await loop.run_in_executor(None, run_chat_completion, msgs)
    async for token_chunk in token_stream:
        chunk: HasMessage = token_chunk  # noqa token_chunk is a ChatCompletionChunkObject not Future
        await response.stream_token(chunk.message)

    # Send a response back to the user
    await response.update()
