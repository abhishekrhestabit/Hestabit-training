(venv) abhishekrai@hestabit-LP:~/Training/week9$ python day4_pipeline.py

╔═══════════════════════════════════════════════════════╗
║        DAY 4 — Memory-Augmented Chat                  ║
║                                                       ║
║  Three memory layers active:                          ║
║    🧠 Session memory  (current conversation, RAM)     ║
║    🧠 Vector store    (semantic FAISS, persists)      ║
║    🧠 Long-term DB    (tagged facts, SQLite, persists)║
║                                                       ║
║  Commands:                                            ║
║    memory              — show all stored memory       ║
║    recall <category>   — e.g. recall personal         ║
║    clear               — wipe everything              ║
║    exit                — quit                         ║
╚═══════════════════════════════════════════════════════╝
[ModelLoader] Using Gemini API → model: gemini-3.1-flash-lite-preview
/home/abhishekrai/Training/week9/venv/lib/python3.12/site-packages/autogen_ext/models/openai/_openai_client.py:466: UserWarning: Missing required field 'structured_output' in ModelInfo. This field will be required in a future version of AutoGen.
  validate_model_info(self._model_info)
[VectorStore] Loading embedding model: all-MiniLM-L6-v2 ...
[VectorStore] Loaded 0 stored memories.
[LongTermMemory] DB: memory/long_term.db  (0 facts stored)

  Memory loaded: 0 session turns | 0 vectors | 0 facts


───────────────────────────────────────────────────────
  You: Hey, my name is Abhishek RAI

───────────────────────────────────────────────────────
  MEMORY — recalling
───────────────────────────────────────────────────────
  🧠 No relevant memories found.

  Assistant: Hello, Abhishek Rai! It's nice to meet you. I've noted that down. How can I help you today?


───────────────────────────────────────────────────────
  MEMORY — storing
───────────────────────────────────────────────────────
  🧠 [personal] The user's name is Abhishek Rai.
  🧠 session=2 turns | vectors=1 | facts=1

───────────────────────────────────────────────────────
  You: Give me the symptoms of Malaria 

───────────────────────────────────────────────────────
  MEMORY — recalling
───────────────────────────────────────────────────────
  🧠 Context (232 chars):
── Recent conversation ──
User: Hey, my name is Abhishek RAI
Assistant: Hello, Abhishek Rai! It's nice to meet you. I've noted that down. How can I help you today?

── Relevant past memories ──
  [1] The user's name is Abhishek Rai.

  Assistant: Hi Abhishek Rai!

Common symptoms of malaria typically include:

*   Fever and chills
*   Headache
*   Muscle aches and fatigue
*   Nausea, vomiting, and diarrhea

Symptoms usually appear 10–15 days after being bitten by an infected mosquito. If you or someone you know is experiencing these, it’s important to seek medical attention promptly for a proper diagnosis and treatment.


───────────────────────────────────────────────────────
  MEMORY — storing
───────────────────────────────────────────────────────
  🧠 [health] Malaria symptoms include fever, chills, headache, muscle aches, fatigue, nausea,
  🧠 session=4 turns | vectors=2 | facts=2

───────────────────────────────────────────────────────
  You: how are you ?

───────────────────────────────────────────────────────
  MEMORY — recalling
───────────────────────────────────────────────────────
  🧠 Context (837 chars):
── Recent conversation ──
User: Hey, my name is Abhishek RAI
Assistant: Hello, Abhishek Rai! It's nice to meet you. I've noted that down. How can I help you today?
User: Give me the symptoms of Malaria
Assistant: Hi Abhishek Rai!

Common symptoms of malaria typically include:

*   Fever and chills
*   Headache
*   Muscle aches and fatigue
*   Nause...

  Assistant: I'm doing great, thank you for asking, Abhishek Rai! How are you doing today? Is there anything else I can help you with?


───────────────────────────────────────────────────────
  MEMORY — storing
───────────────────────────────────────────────────────
  🧠 No new facts to store.
  🧠 session=6 turns | vectors=2 | facts=2

───────────────────────────────────────────────────────
  You: exit
[Exiting]
(venv) abhishekrai@hestabit-LP:~/Training/week9$ python day4_pipeline.py

╔═══════════════════════════════════════════════════════╗
║        DAY 4 — Memory-Augmented Chat                  ║
║                                                       ║
║  Three memory layers active:                          ║
║    🧠 Session memory  (current conversation, RAM)     ║
║    🧠 Vector store    (semantic FAISS, persists)      ║
║    🧠 Long-term DB    (tagged facts, SQLite, persists)║
║                                                       ║
║  Commands:                                            ║
║    memory              — show all stored memory       ║
║    recall <category>   — e.g. recall personal         ║
║    clear               — wipe everything              ║
║    exit                — quit                         ║
╚═══════════════════════════════════════════════════════╝
[ModelLoader] Using Gemini API → model: gemini-3.1-flash-lite-preview
/home/abhishekrai/Training/week9/venv/lib/python3.12/site-packages/autogen_ext/models/openai/_openai_client.py:466: UserWarning: Missing required field 'structured_output' in ModelInfo. This field will be required in a future version of AutoGen.
  validate_model_info(self._model_info)
[VectorStore] Loading embedding model: all-MiniLM-L6-v2 ...
[VectorStore] Loaded 2 stored memories.
[LongTermMemory] DB: memory/long_term.db  (2 facts stored)

  Memory loaded: 0 session turns | 2 vectors | 2 facts


───────────────────────────────────────────────────────
  You: What is my name?

───────────────────────────────────────────────────────
  MEMORY — recalling
───────────────────────────────────────────────────────
  🧠 Context (242 chars):
── Relevant past memories ──
  [1] The user's name is Abhishek Rai.
  [2] Malaria symptoms include fever, chills, headache, muscle aches, fatigue, nausea, vomiting, and diarrhea, typically appearing 10–15 days after an infected mosquito bite.

  Assistant: Your name is Abhishek Rai.


───────────────────────────────────────────────────────
  MEMORY — storing
───────────────────────────────────────────────────────
  🧠 No new facts to store.
  🧠 session=2 turns | vectors=2 | facts=2

───────────────────────────────────────────────────────
  You: clear
[VectorStore] Cleared all memories.
[LongTermMemory] Cleared all facts.
  ✅ All memory cleared.

───────────────────────────────────────────────────────
  You: What is my name ?

───────────────────────────────────────────────────────
  MEMORY — recalling
───────────────────────────────────────────────────────
  🧠 No relevant memories found.

  Assistant: I don't have that information yet. Since we haven't discussed it before, I don't know your name!


───────────────────────────────────────────────────────
  MEMORY — storing
───────────────────────────────────────────────────────
  🧠 No new facts to store.
  🧠 session=2 turns | vectors=0 | facts=0

───────────────────────────────────────────────────────
  You: 