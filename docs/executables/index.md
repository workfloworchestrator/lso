---
icon: material/language-python
---

# Running an Executable

To run an executable with LSO, send an HTTP POST request to the API endpoint at `/api/execute`. Input and output
options are described in the following subsections. Callback and progress updates, and running (a)synchronously are
optional, allowing for more flexibility in use-cases.
