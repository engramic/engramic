# Load And Query a Repo

```mermaid
flowchart LR
    sense --> repo
    repo --> sense

    classDef green fill:#b2f2bb;
    class sense green
```

A repo is collection of files located at a root folder. The RepoService provides the following abilities:

- Returns the set of all root folders.
- Returns all files within each root folder.
- Enables prompting filtering by repo.

## Example Code Walkthrough

The full code is available in the source code at `/engramic/examples/repo/repo.py`. 
You can download the files for this exercise at https://www.engramic.org/assets-page

Let's walk through how this example works step-by-step:

### 1. Setting Up the Environment

The example code creates a `TestService` class that demonstrates how to:

- Scan and discover repository folders
- Submit documents for processing
- Listen for repository and document events
- Query the system with repository filtering

### 2. Initializing Required Services

```python
def main() -> None:
    host = Host(
        'standard',
        [
            MessageService,
            SenseService,
            RetrieveService,
            ResponseService,
            StorageService,
            ConsolidateService,
            CodifyService,
            RepoService,  #<-- This is the key service for repository functionality
            ProgressService,
            TestService,
        ],
    )
```

This code sets up all necessary services, with `RepoService` being essential for the repository functionality.

### 3. Repository Discovery Process

```python
# In TestService.start():
def start(self):
    super().start()
    self.subscribe(Service.Topic.MAIN_PROMPT_COMPLETE, self.on_main_prompt_complete)
    self.subscribe(Service.Topic.REPO_FOLDERS, self._on_repo_folders)
    self.subscribe(Service.Topic.REPO_FILES, self._on_repo_files)
    self.subscribe(Service.Topic.DOCUMENT_INSERTED, self.on_document_inserted)
    repo_service = self.host.get_service(RepoService)
    repo_service.scan_folders()
    self.run_task(self.submit_documents())
```

This code:

1. Subscribes to repository-related events
2. Gets a reference to the RepoService
3. Initiates a scan of repository folders
4. Launches a task to submit documents for processing

### 4. Repository Event Handling

The TestService subscribes to key events related to repositories:

- `REPO_FOLDERS`: Triggered when repository folders are discovered
- `REPO_FILES`: Triggered after folders are discovered, providing file information
- `DOCUMENT_INSERTED`: Triggered when a document has been processed
- `MAIN_PROMPT_COMPLETE`: Triggered when a response to a prompt is ready

### 5. Processing Repository Folders

```python
def _on_repo_folders(self, message_in: dict[str, Any]) -> None:
    if message_in['repo_folders'] is not None:
        self.repos = message_in['repo_folders']
        self.repo_id1 = next((key for key, value in self.repos.items() if value == 'QuantumNetworking'), None)
        self.repo_id2 = next((key for key, value in self.repos.items() if value == 'ElysianFields'), None)
    else:
        logging.info('No repos found. You can add a repo by adding a folder to home/.local/share/engramic')
```

This code:

1. Stores the discovered repository folders
2. Looks up specific repository IDs by their folder names
3. Provides feedback if no repositories are found

### 6. Document Submission Process

```python
async def submit_documents(self) -> None:
    repo_service = self.host.get_service(RepoService)
    self.document_id1 = '97a1ae1b8461076cdc679d6e0a5f885e'  # 'IntroductiontoQuantumNetworking.pdf'
    self.document_id2 = '9c9f0237620b77fa69e2ca63e40a9f27'  # 'Elysian_Fields.pdf'
    repo_service.submit_ids([self.document_id1], overwrite=True)
    repo_service.submit_ids([self.document_id2])
```

This code:

1. Defines document IDs to be processed
2. Submits the first document with overwrite=True to force reprocessing
3. Submits the second document without overwrite, using cached version if available

### 7. Querying with Repository Filters

When documents are fully processed (`DOCUMENT_INSERTED` events), the code sends queries with different repository filters:

```python
def on_document_inserted(self, message_in: dict[str, Any]) -> None:
    document_id = message_in['id']
    if document_id in {self.document_id1, self.document_id2}:
        self.count += 1
        if self.count == TestService.DOCUMENT_COUNT:
            retrieve_service = self.host.get_service(RetrieveService)
            prompt1 = Prompt(
                'This is prompt 1. Briefly tell me about IntroductiontoQuantumNetworking.pdf and Elysian_Fields.pdf. Start with prompt number.',
                repo_ids_filters=[self.repo_id1, self.repo_id2],
            )
            retrieve_service.submit(prompt1)
            prompt2 = Prompt(
                'This is prompt 2. Briefly tell me about IntroductiontoQuantumNetworking.pdf and Elysian_Fields.pdf. Start with prompt number.',
                repo_ids_filters=[self.repo_id1],
            )
            retrieve_service.submit(prompt2)
            prompt3 = Prompt(
                'This is prompt 3. Briefly tell me about IntroductiontoQuantumNetworking.pdf and Elysian_Fields.pdf.  Start with prompt number.',
                repo_ids_filters=None,
            )
            retrieve_service.submit(prompt3)
```

This code:

1. Tracks when all documents are processed
2. Creates three different prompts with varying repository filters:
   - Prompt 1: Filters by both repositories
   - Prompt 2: Filters by only the first repository
   - Prompt 3: Uses no repository filtering (null repo)
3. Submits the prompts to the RetrieveService

## Repository Filtering Options

### Access Multiple Repositories
This prompt will access files from both repo_id1 and repo_id2.

```python
prompt1 = Prompt(
    'This is prompt 1. Tell me about document content.',
    repo_ids_filters=[self.repo_id1, self.repo_id2],
)
```

### Filter by a Single Repository
This prompt will only access files from repo_id1.

```python
prompt2 = Prompt(
    'This is prompt 2. Tell me about document content.',
    repo_ids_filters=[self.repo_id1],
)
```

### The 'Null' Repository
Documents are usable without using the repo system. In this case, the file is associated with a default repo known as the 'null' repo.

```python
prompt3 = Prompt(
    'This is prompt 3. Tell me about document content.',
    repo_ids_filters=None,
)
```

*Note: If you have previously run the document example, you may have IntroductiontoQuantumNetworking.pdf in the 'null' repo. To remove it you can delete the database (you can simply delete the sql lite file or run the following hatch command).*

```
hatch shell dev
```

```
hatch run delete_dbs
```

### Empty List (invalid)
❌  **Invalid** - Empty list repo filters are not allowed and will throw an error.

```python
# The following would throw an exception
# Prompt('This is prompt 4. Tell me about document content.', repo_ids_filters=[])
```

## Important Considerations

- In order to run the code, you must add the REPO_ROOT environment variable. For example, you can set repo root to a path like the following: `REPO_ROOT = "~/.local/share/engramic/"`.
- For security purposes, there is no ability to access all repos without explicitly providing each repo id as a filter.
- If you load a document under a repo, it is forever in that repo. For example, if you first scan a document under the 'null' repo and then scan that document as part of a repo it will be detected and not scanned. Because of this, when you query the repo, it will not display results as part of the repo because it is part of the 'null' repo.
