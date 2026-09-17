# Terminator1 — App Structure

_Auto-generated on 2026-09-17T10:51:14 by `scripts/update_docs.py`._


```
genV2_Interface_projectManager/

|-- about
|   `-- set_title.py
|-- agent_monitoring
|   |-- __init__.py
|   |-- backup.py
|   |-- collector.py
|   |-- manager.py
|   |-- router.py
|   `-- store.py
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
|   |   |   |-- chat-window.js
|   |   |   `-- terminal-window-out.js
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
|   |   |-- config-page.js
|   |   `-- logs-page.js
|   |-- chat.html
|   |-- config.html
|   |-- index.html
|   `-- logs.html
|-- docs
|   |-- phase-1-2-3-update
|   |   |-- about
|   |   |   `-- set_title.py
|   |   |-- dashboard
|   |   |   `-- js
|   |   |       |-- ui
|   |   |       |   |-- config-form.js
|   |   |       |   `-- header-nav.js
|   |   |       `-- app.js
|   |   |-- interface
|   |   |   |-- wiring
|   |   |   |   |-- __init__.py
|   |   |   |   `-- bridges.py
|   |   |   `-- custom_module_manager.py
|   |   |-- server
|   |   |   |-- paths.py
|   |   |   `-- server.py
|   |   `-- INSTRUCTIONS.md
|   |-- APP_CODE_SNAPSHOT.md
|   |-- APP_STRUCTURE.md
|   |-- CHANGELOG.md
|   |-- CUSTOM_MODULE_DEV_GUIDE.md
|   `-- HOW_TO_USE.md
|-- engine
|   |-- agent_library
|   |   |-- Feature Planner Agent
|   |   |   |-- agent.json
|   |   |   `-- agent.md
|   |   |-- feature-clarifier-agent
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
|   |   |   `-- __init__.py
|   |   |-- server
|   |   |   `-- __init__.py
|   |   |-- tools
|   |   |   `-- __init__.py
|   |   `-- __init__.py
|   |-- wiring
|   |   |-- __init__.py
|   |   `-- bridges.py
|   |-- __init__.py
|   |-- custom_module_manager.py
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
|   |-- console_log.py
|   |-- paths.py
|   |-- server.py
|   `-- tool_log.py
|-- tools
|   |-- __init__.py
|   |-- registry.py
|   |-- state.py
|   `-- tools.py
|-- .gitignore
|-- README.md
|-- plan1.md
`-- requirements.txt
```

_94 tracked source file(s)._
