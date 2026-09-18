# Session 1: see RAG working

We are building in Python. Your earlier videos provide the concepts; this code will turn them into something you can inspect and explain. You do not need to learn every file today.

## What our application does

It finds useful passages in a PDF and can send those passages with your question to a language model. The model then writes an answer using that evidence. We are not training or fine-tuning the language model.

There are two separate stages:

**Preparation:** PDF → page text → smaller chunks → embedding vectors → Qdrant.

**Question time:** question → query vector → nearest chunks → question + evidence + instructions → LLM answer.

The preparation stage is called indexing. Searching for useful chunks is retrieval. Writing an answer from those chunks is generation. Search works without generation.

## Your first experiment

1. Launch the app using the README command. Use the fictional handbook.
2. Expand **See extracted text and chunks**. Compare page text with chunks. This sample is short enough that each page can fit in one chunk; larger PDFs produce more chunks.
3. Click **Index this document**. The model turns each chunk into a vector: a list of numbers used to compare meaning. Qdrant stores those vectors alongside their text and metadata.
4. Ask **What is the deadline for reimbursement?** Notice that the PDF says “expense claims,” not “reimbursement.” Semantic search should still bring page 1 to the top.
5. Read the actual passage: claims must be submitted within **30 calendar days of purchase**. That is evidence, before any LLM is involved.
6. Ask **How often can I do my job from home?** Look for page 2 and “up to two days per week.”
7. Ask **Where can I park my car?** There is no parking policy. Search may still show similar passages. This is why a high-ranking result is not proof that the answer exists.

With your own API key configured, try generation for both an answerable and an unanswerable question. The unanswerable case should say the evidence is insufficient. If it invents an answer, record that as a failure, not a feature.

## The terms in our own code

| Term | Meaning here |
| --- | --- |
| Document | A LangChain object holding text plus metadata; it can represent a page or a chunk, not necessarily an entire PDF. |
| Metadata | Labels such as filename, PDF page, document hash and chunk ID. They let us trace text to its origin. |
| Chunk | A manageable piece of page text. Smaller pieces can help precise retrieval but may lose context. |
| Overlap | Repeated text near neighboring chunk boundaries. Helps preserve context; is not guaranteed to be exactly 100 characters. |
| Embedding | A numerical representation produced by a pretrained model. Related text tends to have related vectors. |
| Vector store | Qdrant's collection of vectors, text and metadata. No separate Qdrant server is needed in this local version. |
| Top-k | The maximum number of passages returned. More passages are not automatically better. |
| Cosine similarity | A way to compare vector directions. Our score ranks relevance; it is not a probability that an answer is correct. |
| Context | Retrieved passages supplied to the answer model. These are not the model's training data or permanent memory. |
| Prompt | Instructions, question and evidence given to the answer model. |
| LangChain | The library connecting document objects, splitting, vectors and the answer model. It is not itself an LLM. |
| Citation | A source label such as [S1], mapped to a displayed passage and PDF page. It helps verification but does not prove a claim is supported. |

## Five things to explain in your own words

1. Why do we split documents instead of sending an entire PDF every time?
2. Why do stored chunks and questions need compatible embeddings?
3. Why retain the original page number before splitting?
4. Why can search return passages when the document has no answer?
5. What leaves your computer when you click Generate, versus Search?

Once these make sense, read `PROJECT_WALKTHROUGH.md` for the completed multi-stage implementation. We kept the baseline available so you can compare it with the advanced stages rather than assume they are always better.
