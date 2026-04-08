from system_prompt import system_prompt
from openai import OpenAI

client = OpenAI(
  base_url="https://openrouter.ai/api/v1",
  api_key="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",
)

messages = [{'role': 'system', 'content': [{'type': 'text', 'text': system_prompt}]}]

def kaine():
    usr_input = input("You: ")
    messages.append({'role': 'user', 'content': [{'type': 'text', 'text': usr_input}]})
    completion = client.chat.completions.create(
        model="google/gemini-2.5-flash-lite",
        messages=messages
    )
    answer = completion.choices[0].message.content
    print(answer)
    messages.append({'role': 'assistant', 'content': answer})

while True:
    kaine()
