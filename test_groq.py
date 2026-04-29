from groq import Groq
import os

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

response = client.chat.completions.create(
    model="llama3-70b-8192",
    messages=[
        {"role": "user", "content": "Explain chest pain causes"}
    ]
)

print(response.choices[0].message.content)