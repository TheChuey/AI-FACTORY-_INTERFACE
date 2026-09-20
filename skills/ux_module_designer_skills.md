# UX Module Designer Agent - Implementation Skill Library

This document contains atomic implementation skills for the **UX Module Designer Agent**. Each skill addresses a single, self-contained concept, providing **pseudo-code** for logic flow and **concrete Python code examples** grounded in the Genessis application architecture [1, 17]. An AI agent reading this library can analyze a feature requirement plan and generate structured pseudo-code and executable Python custom modules.

---

### Skill 1: UI Manifest Declaration (`skill_ui_manifest_declaration`)
- **Concept**: Declaring the top-level UI manifest structure in a custom module [17].
- **Pseudo-Code**:
  ```text
  DECLARE UI_MANIFEST dictionary:
      SET module_id = "<module_name>"
      SET buttons = LIST of button configuration objects
  ```
- **Python Example**:
  ```python
  UI_MANIFEST = {
      "module_id": "feature_tracker",
      "buttons": [
          {
              "id": "btn-feature-tracker",
              "label": "⚡ Feature Tracker",
              "target": "header",
              "action": "prompt_input",
              "prompt_message": "Enter Feature Name:",
              "api_endpoint": "/api/feature_tracker/execute",
              "title": "Launch Feature Tracker"
          }
      ]
  }
  ```

---

### Skill 2: Prompt Input Action (`skill_action_prompt_input`)
- **Concept**: Handling simple text input button actions where the user is prompted for a string and the value is POSTed to the backend [17, 80].
- **Pseudo-Code**:
  ```text
  FUNCTION handle_prompt_input(payload):
      EXTRACT input_text FROM payload.input OR payload.project_name
      PROCESS logic with input_text
      RETURN dictionary with status="success" and message=user_feedback
  ```
- **Python Example**:
  ```python
  @app.post("/api/feature_tracker/execute")
  def execute_prompt_action(payload: dict):
      user_input = (payload.get("input") or payload.get("project_name") or "default").strip()
      
      # Execute custom feature logic
      return {
          "status": "success",
          "message": f"Successfully initialized feature: '{user_input}'"
      }
  ```

---

### Skill 3: Dropdown Menu Action (`skill_action_dropdown_menu`)
- **Concept**: Grouping flyout sub-actions under a single header menu button [17, 81, 223].
- **Pseudo-Code**:
  ```text
  DEFINE button configuration object:
      SET action = "dropdown_menu"
      SET items = LIST of sub-action objects (open_modal, qa_survey, prompt_input)
  ```
- **Python Example**:
  ```python
  UI_MANIFEST = {
      "module_id": "feature_manager",
      "buttons": [
          {
              "id": "btn-manager-menu",
              "label": "⚡ Manager Tools",
              "target": "header",
              "action": "dropdown_menu",
              "title": "Select Action",
              "items": [
                  {
                      "id": "item-open-dialog",
                      "label": "📋 Open Config Dialog",
                      "action": "open_modal",
                      "schema_endpoint": "/api/feature_manager/dialog_schema"
                  },
                  {
                      "id": "item-start-qa",
                      "label": "❓ Feature Setup Wizard",
                      "action": "qa_survey",
                      "qa_endpoint": "/api/feature_manager/qa_step"
                  }
              ]
          }
      ]
  }
  ```

---

### Skill 4: Open Modal Schema Action (`skill_action_open_modal`)
- **Concept**: Implementing schema-driven dialog forms (`GET` endpoint returns component schema, `POST` endpoint processes submitted form data) [17, 82, 225].
- **Pseudo-Code**:
  ```text
  ENDPOINT GET schema_endpoint:
      RETURN dictionary with title, target_endpoint, and components list [input, select, checkbox, submit button]

  ENDPOINT POST target_endpoint(payload):
      EXTRACT component values from payload dictionary
      PROCESS configuration logic
      RETURN dictionary with status="success", message, and indicate_success=True
  ```
- **Python Example**:
  ```python
  @app.get("/api/feature_manager/dialog_schema")
  def get_dialog_schema():
      return {
          "title": "Feature Manager Configuration",
          "target_endpoint": "/api/feature_manager/execute_dialog",
          "components": [
              {"type": "input", "name": "project_name", "label": "Project Name", "placeholder": "e.g. Alpha-1"},
              {"type": "select", "name": "priority", "label": "Priority Level", "options": ["Low", "Medium", "High"]},
              {"type": "checkbox", "name": "notify_team", "label": "Send Team Notification", "value": True},
              {"type": "button", "label": "Save & Deploy", "action": "submit"}
          ]
      }

  @app.post("/api/feature_manager/execute_dialog")
  def execute_dialog(payload: dict):
      p_name = payload.get("project_name", "Untitled")
      return {
          "status": "success",
          "message": f"Project '{p_name}' successfully configured!",
          "indicate_success": True
      }
  ```

---

### Skill 5: Interactive Q&A Survey Action (`skill_action_qa_survey`)
- **Concept**: Implementing step-by-step wizard surveys [17, 83, 225].
- **Pseudo-Code**:
  ```text
  ENDPOINT POST qa_endpoint(request_data):
      IF request.step == 1:
          RETURN step=1, completed=False, question, options
      ELSE IF request.step == 2:
          READ request.answers.step_1
          RETURN step=2, completed=False, question, options
      ELSE (Final Step):
          READ all answers
          PERSIST record JSON to disk
          RETURN step=N, completed=True, summary, message, indicate_success=True, record_path
  ```
- **Python Example**:
  ```python
  from pydantic import BaseModel

  class QARequest(BaseModel):
      step: int
      answers: dict = {}

  @app.post("/api/feature_manager/qa_step")
  def handle_qa_step(req: QARequest):
      if req.step == 1:
          return {
              "step": 1,
              "completed": False,
              "question": "What objective are you setting up for this project?",
              "type": "choice",
              "options": ["AI Agent Training", "Data Pipeline", "RAG Knowledge Indexing", "Custom Extension"]
          }

      if req.step == 2:
          prev_choice = req.answers.get("step_1", "General")
          return {
              "step": 2,
              "completed": False,
              "question": f"Got it: '{prev_choice}'. Which environment should handle execution?",
              "type": "choice",
              "options": ["Local Ollama Engine", "FastAPI Server", "Background Worker"]
          }

      # Completion Step
      choice_1 = req.answers.get("step_1", "N/A")
      choice_2 = req.answers.get("step_2", "N/A")
      summary = f"Setup Complete!\n• Objective: {choice_1}\n• Environment: {choice_2}"

      return {
          "step": 3,
          "completed": True,
          "summary": summary,
          "message": "Project Manager QA workflow completed successfully!",
          "indicate_success": True
      }
  ```

---

### Skill 6: Route Registration Entry Point (`skill_register_routes`)
- **Concept**: Exposing a top-level `register_routes(app)` function hooked automatically during server lifespan startup or live module reload [17, 78, 124].
- **Pseudo-Code**:
  ```text
  FUNCTION register_routes(app: FastAPI):
      DEFINE @app.get and @app.post handlers on app instance
  ```
- **Python Example**:
  ```python
  from fastapi import FastAPI

  def register_routes(app: FastAPI):
      """Called automatically during server lifespan startup or POST /api/interface/apply."""
      
      @app.get("/api/my_module/status")
      def get_status():
          return {"status": "success", "message": "Module is online"}

      @app.post("/api/my_module/process")
      def process_data(payload: dict):
          return {"status": "success", "message": "Data processed successfully"}
  ```

---

### Skill 7: Endpoint Response Contract (`skill_endpoint_response_contract`)
- **Concept**: Structuring JSON return payloads for front-end alert/modal display and status dot indicators [17, 84, 85].
- **Pseudo-Code**:
  ```text
  RETURN DICTIONARY:
      status: "success" | "error"
      message: "Human-readable feedback string"
      indicate_success: True | False (Optional: lights green dot on trigger button)
  ```
- **Python Example**:
  ```python
  # Success response with green status dot trigger
  return {
      "status": "success",
      "message": "Configuration saved to server.",
      "indicate_success": True
  }

  # Error response
  return {
      "status": "error",
      "message": "Invalid parameters supplied."
  }
  ```

---

### Skill 8: Path Authority (`skill_path_authority`)
- **Concept**: Resolving file storage locations using `server.paths` rather than hardcoded string paths [5, 86, 122].
- **Pseudo-Code**:
  ```text
  IMPORT path constants FROM server.paths
  CONSTRUCT file_path = TARGET_DIR / filename
  CREATE parent directories if missing
  WRITE/READ text with UTF-8 encoding
  ```
- **Python Example**:
  ```python
  from server.paths import DATA_DIR, EXPORTS_DIR, RECORDS_DIR, CHATS_DIR, RAG_DB_DIR, CUSTOM_MODULES_DIR

  def save_export_record(filename: str, content: str):
      EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
      target_file = EXPORTS_DIR / filename
      target_file.write_text(content, encoding="utf-8")
      return target_file
  ```

---

### Skill 9: Core-to-Module Wiring Bridge (`skill_wiring_bridge_execution`)
- **Concept**: Invoking custom module functions programmatically from core Python code via `InterfaceDispatcher` [18, 87, 120].
- **Pseudo-Code**:
  ```text
  IMPORT InterfaceDispatcher FROM interface.interface_dispatcher
  EXECUTE execute_action(
      domain_category="custom",
      submodule_name=module_name_string,
      function_to_call=function_name_string,
      *args, **kwargs
  )
  ```
- **Python Example**:
  ```python
  from interface.interface_dispatcher import InterfaceDispatcher

  # Invokes `some_function` in `custom_modules/feature_manager.py` with execution tracing
  result = InterfaceDispatcher().execute_action(
      "custom",
      "feature_manager",
      "some_internal_function",
      "arg_value",
      kwarg_key="value"
  )
  ```
