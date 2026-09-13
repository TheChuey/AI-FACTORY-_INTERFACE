# Terminator1 — App Structure

_Auto-generated on 2026-09-13T12:57:57 by `scripts/update_docs.py`._


```
genV2_Interface_projectManager/

|-- about
|   `-- set_title.py
|-- config
|   `-- models.json
|-- dashboard
|   |-- css
|   |   `-- styles.css
|   |-- js
|   |   |-- api
|   |   |   `-- api.js
|   |   |-- classes
|   |   |   |-- ChatSession.js
|   |   |   `-- chat-window.js
|   |   |-- logic
|   |   |   |-- chat-formatter.js
|   |   |   `-- models.js
|   |   |-- ui
|   |   |   |-- agent-editor.js
|   |   |   |-- agents.js
|   |   |   |-- appearance.js
|   |   |   |-- config-form.js
|   |   |   |-- header-nav.js
|   |   |   |-- interface-indicator.js
|   |   |   |-- interface-manager.js
|   |   |   `-- markdown.js
|   |   |-- app.js
|   |   `-- config-page.js
|   |-- chat.html
|   |-- config.html
|   `-- index.html
|-- docs
|   |-- 01_IDEA_AND_ARCHITECTURE.md
|   |-- 02_IMPLEMENTATION_PLAN.md
|   |-- APP_CODE_SNAPSHOT.md
|   |-- APP_STRUCTURE.md
|   |-- CHANGELOG.md
|   `-- RESTRUCTURE_README.md
|-- engine
|   |-- agent_library
|   |   |-- basic_chat
|   |   |   |-- agent.json
|   |   |   `-- agent.md
|   |   |-- dev_assistant
|   |   |   |-- agent.json
|   |   |   `-- agent.md
|   |   |-- problem_discovery_agent
|   |   |   |-- agent.json
|   |   |   `-- agent.md
|   |   `-- rag_assistant
|   |       |-- agent.json
|   |       `-- agent.md
|   |-- agents
|   |   |-- __init__.py
|   |   |-- factory.py
|   |   |-- loader.py
|   |   `-- registry.py
|   |-- core
|   |   |-- __init__.py
|   |   |-- agent.py
|   |   |-- llm.py
|   |   `-- prompt.py
|   `-- __init__.py
|-- interface
|   |-- updates
|   |   |-- engine
|   |   |   |-- __init__.py
|   |   |   |-- hello_update.py
|   |   |   |-- newfunction.py
|   |   |   `-- project_creator.py
|   |   |-- server
|   |   |   |-- __init__.py
|   |   |   `-- project_routes.py
|   |   |-- tools
|   |   |   `-- __init__.py
|   |   `-- __init__.py
|   |-- __init__.py
|   |-- interface_dispatcher.py
|   |-- restore_manager.py
|   `-- update_manager.py
|-- memory
|   |-- __init__.py
|   |-- ingest.py
|   |-- main.py
|   |-- rag_commit.py
|   `-- search.py
|-- scripts
|   |-- rebuild_rag.py
|   |-- update_docs.py
|   `-- version_chats.py
|-- server
|   |-- chat_store
|   |   |-- __init__.py
|   |   |-- logger.py
|   |   `-- store.py
|   |-- paths.py
|   `-- server.py
|-- tools
|   |-- __init__.py
|   |-- registry.py
|   |-- state.py
|   `-- tools.py
|-- .gitignore
|-- README.md
`-- requirements.txt
```

_76 tracked source file(s)._
