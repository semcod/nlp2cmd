# System Architecture Analysis

## Overview

- **Project**: /home/tom/github/wronai/nlp2cmd
- **Analysis Mode**: static
- **Total Functions**: 6817
- **Total Classes**: 966
- **Modules**: 840
- **Entry Points**: 5893

## Architecture by Module

### src.nlp2cmd.generation.template_generator
- **Functions**: 100
- **Classes**: 2
- **File**: `template_generator.py`

### networkx-3.6.1-py3-none-any.networkx.classes.reportviews
- **Functions**: 99
- **Classes**: 23
- **File**: `reportviews.py`

### webops.nlp2cmd-repo.examples.devops.nlp2cmd_web_controller
- **Functions**: 52
- **Classes**: 8
- **File**: `nlp2cmd_web_controller.py`

### examples.03_integrations.web_development.nlp2cmd_web_controller
- **Functions**: 52
- **Classes**: 8
- **File**: `nlp2cmd_web_controller.py`

### networkx-3.6.1-py3-none-any.networkx.classes.coreviews
- **Functions**: 49
- **Classes**: 11
- **File**: `coreviews.py`

### src.nlp2cmd.web_schema.form_data_loader
- **Functions**: 47
- **Classes**: 1
- **File**: `form_data_loader.py`

### networkx-3.6.1-py3-none-any.networkx.algorithms.planarity
- **Functions**: 46
- **Classes**: 4
- **File**: `planarity.py`

### networkx-3.6.1-py3-none-any.networkx.classes.graph
- **Functions**: 45
- **Classes**: 3
- **File**: `graph.py`

### webops.nlp2cmd-repo.src.nlp2cmd.schema_extraction
- **Functions**: 45
- **Classes**: 9
- **File**: `__init__.py`

### webops.nlp2cmd-repo.src.nlp2cmd.schemas
- **Functions**: 43
- **Classes**: 2
- **File**: `__init__.py`

### src.nlp2cmd.schemas
- **Functions**: 43
- **Classes**: 2
- **File**: `__init__.py`

### networkx-3.6.1-py3-none-any.networkx.classes.function
- **Functions**: 42
- **File**: `function.py`

### scripts.thermodynamic.termo2
- **Functions**: 38
- **Classes**: 12
- **File**: `termo2.py`

### webops.nlp2cmd-repo.termo2
- **Functions**: 38
- **Classes**: 12
- **File**: `termo2.py`

### webops.nlp2cmd-repo.src.nlp2cmd.web_schema.form_data_loader
- **Functions**: 38
- **Classes**: 1
- **File**: `form_data_loader.py`

### tools.schema.enhanced_schema_generator
- **Functions**: 37
- **Classes**: 3
- **File**: `enhanced_schema_generator.py`

### webops.nlp2cmd-repo.tools.schema.enhanced_schema_generator
- **Functions**: 37
- **Classes**: 3
- **File**: `enhanced_schema_generator.py`

### webops.nlp2cmd-repo.src.nlp2cmd.adapters.shell
- **Functions**: 36
- **Classes**: 3
- **File**: `shell.py`

### networkx-3.6.1-py3-none-any.networkx.readwrite.graphml
- **Functions**: 33
- **Classes**: 5
- **File**: `graphml.py`

### webops.nlp2cmd-repo.src.nlp2cmd.core
- **Functions**: 33
- **Classes**: 10
- **File**: `core.py`

## Key Entry Points

Main execution flows into the system:

### src.nlp2cmd.pipeline_runner_plans.PlanExecutionMixin._execute_plan_step
> Execute a single ActionPlan step. Returns extracted value or None.
- **Calls**: self._resolve_plan_variables, Console, webops.nlp2cmd-repo.src.nlp2cmd.pipeline_runner._MarkdownConsoleWrapper.print, params.get, page.goto, page.wait_for_timeout, ValueError, url.startswith

### src.nlp2cmd.pipeline_runner_browser.BrowserExecutionMixin._run_dom_multi_action
> Execute multiple browser actions in sequence.
- **Calls**: payload.get, Console, _MarkdownConsoleWrapper, payload.get, RunnerResult, RunnerResult, sync_playwright, p.chromium.launch

### src.nlp2cmd.pipeline_runner_plans.PlanExecutionMixin.execute_action_plan
> Execute an ActionPlan step by step using Playwright.

Args:
    plan: ActionPlan instance with steps to execute
    dry_run: If True, only show the pl
- **Calls**: Console, frozenset, console.print, console.print, enumerate, None.strip, RunnerResult, any

### networkx-3.6.1-py3-none-any.networkx.generators.social.les_miserables_graph
> Returns coappearance network of characters in the novel Les Miserables.

References
----------
.. [1] D. E. Knuth, 1993.
   The Stanford GraphBase: a 
- **Calls**: nx._dispatchable, nx.Graph, G.add_edge, G.add_edge, G.add_edge, G.add_edge, G.add_edge, G.add_edge

### webops.nlp2cmd-repo.src.nlp2cmd.generation.templates.TemplateGenerator._prepare_shell_entities
> Prepare shell entities.
- **Calls**: entities.copy, entities.get, entities.get, entities.get, entities.get, str, entities.get, result.setdefault

### networkx-3.6.1-py3-none-any.networkx.drawing.nx_pylab.display
> Draw the graph G.

Draw the graph as a collection of nodes connected by edges.
The exact details of what the graph looks like are controlled by the be
- **Calls**: kwargs.get, kwargs.get, isinstance, G.subgraph, kwargs.get, callable, kwargs.get, kwargs.get

### webops.nlp2cmd-repo.examples.shell.environment_analysis.main
- **Calls**: webops.nlp2cmd-repo.src.nlp2cmd.pipeline_runner._MarkdownConsoleWrapper.print, webops.nlp2cmd-repo.src.nlp2cmd.pipeline_runner._MarkdownConsoleWrapper.print, webops.nlp2cmd-repo.src.nlp2cmd.pipeline_runner._MarkdownConsoleWrapper.print, EnvironmentAnalyzer, webops.nlp2cmd-repo.src.nlp2cmd.pipeline_runner._MarkdownConsoleWrapper.print, webops.nlp2cmd-repo.src.nlp2cmd.pipeline_runner._MarkdownConsoleWrapper.print, webops.nlp2cmd-repo.src.nlp2cmd.pipeline_runner._MarkdownConsoleWrapper.print, analyzer.analyze

### examples.01_basics.shell_fundamentals.environment_analysis.main
- **Calls**: examples._example_helpers.print_separator, EnvironmentAnalyzer, examples._example_helpers.print_rule, webops.nlp2cmd-repo.src.nlp2cmd.pipeline_runner._MarkdownConsoleWrapper.print, examples._example_helpers.print_rule, analyzer.analyze, webops.nlp2cmd-repo.src.nlp2cmd.pipeline_runner._MarkdownConsoleWrapper.print, webops.nlp2cmd-repo.src.nlp2cmd.pipeline_runner._MarkdownConsoleWrapper.print

### webops.nlp2cmd-repo.src.nlp2cmd.pipeline_runner.PipelineRunner._run_dom_multi_action
> Execute multiple browser actions in sequence.
- **Calls**: payload.get, Console, _MarkdownConsoleWrapper, payload.get, RunnerResult, RunnerResult, sync_playwright, p.chromium.launch

### src.nlp2cmd.cli.main.main
> NLP2CMD - Natural Language to Domain-Specific Commands.
- **Calls**: click.group, click.option, click.option, click.option, click.option, click.option, click.option, click.option

### src.nlp2cmd.execution.runner.ExecutionRunner.run_command
> Execute a shell command with real-time output.

Args:
    command: Shell command to execute
    cwd: Working directory
    env: Environment variables

- **Calls**: time.time, self.print_markdown_block, ExecutionResult, self.execution_history.append, subprocess.Popen, None.join, None.join, subprocess.run

### examples.03_integrations.web_development.demo.demo_nlp_commands
> Interaktywna demonstracja poleceń NLP.
- **Calls**: NLP2CMDWebController, examples._example_helpers.print_separator, webops.nlp2cmd-repo.src.nlp2cmd.pipeline_runner._MarkdownConsoleWrapper.print, webops.nlp2cmd-repo.src.nlp2cmd.pipeline_runner._MarkdownConsoleWrapper.print, None.strip, webops.nlp2cmd-repo.src.nlp2cmd.pipeline_runner._MarkdownConsoleWrapper.print, examples._example_helpers.print_rule, webops.nlp2cmd-repo.src.nlp2cmd.pipeline_runner._MarkdownConsoleWrapper.print

### webops.nlp2cmd-repo.src.nlp2cmd.registry.ActionRegistry._register_builtin_actions
> Register built-in actions.
- **Calls**: self.register, self.register, self.register, self.register, self.register, self.register, self.register, self.register

### src.nlp2cmd.registry.ActionRegistry._register_builtin_actions
> Register built-in actions.
- **Calls**: self.register, self.register, self.register, self.register, self.register, self.register, self.register, self.register

### webops.nlp2cmd-repo.examples.devops.demo_batch.run_batch_demo
> Run all commands from prompt.txt automatically.
- **Calls**: webops.nlp2cmd-repo.src.nlp2cmd.pipeline_runner._MarkdownConsoleWrapper.print, webops.nlp2cmd-repo.src.nlp2cmd.pipeline_runner._MarkdownConsoleWrapper.print, webops.nlp2cmd-repo.src.nlp2cmd.pipeline_runner._MarkdownConsoleWrapper.print, webops.nlp2cmd-repo.src.nlp2cmd.pipeline_runner._MarkdownConsoleWrapper.print, webops.nlp2cmd-repo.src.nlp2cmd.pipeline_runner._MarkdownConsoleWrapper.print, webops.nlp2cmd-repo.src.nlp2cmd.pipeline_runner._MarkdownConsoleWrapper.print, webops.nlp2cmd-repo.src.nlp2cmd.pipeline_runner._MarkdownConsoleWrapper.print, webops.nlp2cmd-repo.src.nlp2cmd.pipeline_runner._MarkdownConsoleWrapper.print

### networkx-3.6.1-py3-none-any.networkx.utils.backends._dispatchable._convert_and_call_for_tests
> Call this dispatchable function with a backend; for use with testing.
- **Calls**: networkx-3.6.1-py3-none-any.networkx.utils.backends._load_backend, _logger.debug, self.name.endswith, backend.convert_to_nx, self._can_backend_run, hasattr, pytest.xfail, self._will_call_mutate_input

### examples.03_integrations.web_development.demo_batch.run_batch_demo
> Run all commands from prompt.txt automatically.
- **Calls**: webops.nlp2cmd-repo.src.nlp2cmd.pipeline_runner._MarkdownConsoleWrapper.print, webops.nlp2cmd-repo.src.nlp2cmd.pipeline_runner._MarkdownConsoleWrapper.print, webops.nlp2cmd-repo.src.nlp2cmd.pipeline_runner._MarkdownConsoleWrapper.print, webops.nlp2cmd-repo.src.nlp2cmd.pipeline_runner._MarkdownConsoleWrapper.print, webops.nlp2cmd-repo.src.nlp2cmd.pipeline_runner._MarkdownConsoleWrapper.print, webops.nlp2cmd-repo.src.nlp2cmd.pipeline_runner._MarkdownConsoleWrapper.print, webops.nlp2cmd-repo.src.nlp2cmd.pipeline_runner._MarkdownConsoleWrapper.print, examples._example_helpers.print_separator

### src.nlp2cmd.pipeline_runner_desktop.DesktopExecutionMixin._execute_desktop_plan_step
> Execute an ActionPlan step via local desktop automation.

Supports three backends:
- ydotool: works on Wayland (requires ydotoold daemon)
- xdotool: w
- **Calls**: self._resolve_plan_variables, str, self._detect_desktop_backend, ValueError, ValueError, str, str, int

### src.nlp2cmd.automation.action_planner.ActionPlanner._generate_rule_based_canvas_plan
> Generate a drawing plan for an arbitrary object using rules.

This is a fallback when LLM is not available. Uses object name to determine
shape compos
- **Calls**: re.search, None.strip, object_name.lower, any, ActionPlan, None.strip, ActionStep, ActionStep

### webops.nlp2cmd-repo.src.nlp2cmd.adapters.shell.ShellAdapter._generate_file_search
> Generate find command.
- **Calls**: entities.get, entities.get, entities.get, None.join, entities.get, cmd_parts.append, cmd_parts.extend, isinstance

### networkx-3.6.1-py3-none-any.networkx.utils.backends._dispatchable._call_if_any_backends_installed
> Returns the result of the original function, or the backend function if
the backend is specified and that backend implements `func`.
- **Calls**: self.graphs.items, nx.config.backend_priority.get, graph_backend_names.discard, self._will_call_mutate_input, webops.nlp2cmd-repo.src.nlp2cmd.executor.ExecutionContext.set, list, enumerate, NotImplementedError

### webops.nlp2cmd-repo.examples.architecture.end_to_end_demo.main
- **Calls**: webops.nlp2cmd-repo.examples.architecture.end_to_end_demo.print_section, webops.nlp2cmd-repo.examples.architecture.end_to_end_demo.print_step, DecisionRouter, webops.nlp2cmd-repo.src.nlp2cmd.registry.get_registry, LLMPlanner, PlanExecutor, executor.register_handler, executor.register_handler

### examples.05_advanced_features.schema_driven_architecture.end_to_end_demo.main
- **Calls**: webops.nlp2cmd-repo.examples.architecture.end_to_end_demo.print_section, webops.nlp2cmd-repo.examples.architecture.end_to_end_demo.print_step, DecisionRouter, webops.nlp2cmd-repo.src.nlp2cmd.registry.get_registry, LLMPlanner, PlanExecutor, executor.register_handler, executor.register_handler

### webops.nlp2cmd-repo.src.nlp2cmd.adapters.shell.ShellAdapter._generate_find
> Generate find command using entities.
- **Calls**: entities.get, entities.get, entities.get, None.lower, None.join, entities.get, cmd_parts.append, cmd_parts.extend

### src.nlp2cmd.web_schema.form_handler.FormHandler.detect_form_fields
> Detect all form fields on a page.

Args:
    page: Playwright page object

Returns:
    List of FormField objects
- **Calls**: page.query_selector_all, self._print_yaml, page.query_selector_all, self._print_yaml, page.query_selector_all, self._print_yaml, page.query_selector_all, self._print_yaml

### webops.nlp2cmd-repo.examples.shell.feedback_loop.simulate_interactive_session
> Simulate an interactive session with feedback loop.
- **Calls**: webops.nlp2cmd-repo.src.nlp2cmd.pipeline_runner._MarkdownConsoleWrapper.print, webops.nlp2cmd-repo.src.nlp2cmd.pipeline_runner._MarkdownConsoleWrapper.print, webops.nlp2cmd-repo.src.nlp2cmd.pipeline_runner._MarkdownConsoleWrapper.print, SQLAdapter, FeedbackAnalyzer, SQLValidator, CorrectionEngine, NLP2CMD

### webops.nlp2cmd-repo.src.nlp2cmd.cli.main.main
> NLP2CMD - Natural Language to Domain-Specific Commands.
- **Calls**: click.group, click.option, click.option, click.option, click.option, click.option, click.option, click.option

### webops.nlp2cmd-repo.examples.sql.sql_workflows.main
- **Calls**: webops.nlp2cmd-repo.examples.architecture.end_to_end_demo.print_section, webops.nlp2cmd-repo.examples.architecture.end_to_end_demo.print_section, SQLAdapter, adapter.generate, webops.nlp2cmd-repo.src.nlp2cmd.pipeline_runner._MarkdownConsoleWrapper.print, webops.nlp2cmd-repo.src.nlp2cmd.pipeline_runner._MarkdownConsoleWrapper.print, webops.nlp2cmd-repo.src.nlp2cmd.pipeline_runner._MarkdownConsoleWrapper.print, webops.nlp2cmd-repo.src.nlp2cmd.pipeline_runner._MarkdownConsoleWrapper.print

### examples.01_basics.sql_basics.workflows.main
- **Calls**: webops.nlp2cmd-repo.examples.architecture.end_to_end_demo.print_section, webops.nlp2cmd-repo.examples.architecture.end_to_end_demo.print_section, SQLAdapter, adapter.generate, webops.nlp2cmd-repo.src.nlp2cmd.pipeline_runner._MarkdownConsoleWrapper.print, webops.nlp2cmd-repo.src.nlp2cmd.pipeline_runner._MarkdownConsoleWrapper.print, webops.nlp2cmd-repo.src.nlp2cmd.pipeline_runner._MarkdownConsoleWrapper.print, webops.nlp2cmd-repo.src.nlp2cmd.pipeline_runner._MarkdownConsoleWrapper.print

### webops.nlp2cmd-repo.examples.use_cases.shell_validation.ShellCommandValidator.get_test_cases
> Zwróć listę przypadków testowych.
- **Calls**: CommandTest, CommandTest, CommandTest, CommandTest, CommandTest, CommandTest, CommandTest, CommandTest

## Process Flows

Key execution flows identified:

### Flow 1: _execute_plan_step
```
_execute_plan_step [src.nlp2cmd.pipeline_runner_plans.PlanExecutionMixin]
  └─ →> print
```

### Flow 2: _run_dom_multi_action
```
_run_dom_multi_action [src.nlp2cmd.pipeline_runner_browser.BrowserExecutionMixin]
```

### Flow 3: execute_action_plan
```
execute_action_plan [src.nlp2cmd.pipeline_runner_plans.PlanExecutionMixin]
```

### Flow 4: les_miserables_graph
```
les_miserables_graph [networkx-3.6.1-py3-none-any.networkx.generators.social]
```

### Flow 5: _prepare_shell_entities
```
_prepare_shell_entities [webops.nlp2cmd-repo.src.nlp2cmd.generation.templates.TemplateGenerator]
```

### Flow 6: display
```
display [networkx-3.6.1-py3-none-any.networkx.drawing.nx_pylab]
```

### Flow 7: main
```
main [webops.nlp2cmd-repo.examples.shell.environment_analysis]
  └─ →> print
  └─ →> print
```

### Flow 8: run_command
```
run_command [src.nlp2cmd.execution.runner.ExecutionRunner]
```

### Flow 9: demo_nlp_commands
```
demo_nlp_commands [examples.03_integrations.web_development.demo]
  └─ →> print_separator
      └─ →> print
      └─ →> print
  └─ →> print
  └─ →> print
```

### Flow 10: _register_builtin_actions
```
_register_builtin_actions [webops.nlp2cmd-repo.src.nlp2cmd.registry.ActionRegistry]
```

## Key Classes

### src.nlp2cmd.generation.template_generator.TemplateGenerator
> Generate DSL commands from templates.

Uses predefined templates filled with extracted entities.
Fal
- **Methods**: 100
- **Key Methods**: src.nlp2cmd.generation.template_generator.TemplateGenerator.__init__, src.nlp2cmd.generation.template_generator.TemplateGenerator._load_defaults_from_json, src.nlp2cmd.generation.template_generator.TemplateGenerator._load_templates_from_json, src.nlp2cmd.generation.template_generator.TemplateGenerator._get_default, src.nlp2cmd.generation.template_generator.TemplateGenerator.generate, src.nlp2cmd.generation.template_generator.TemplateGenerator._find_alternative_template, src.nlp2cmd.generation.template_generator.TemplateGenerator._get_intent_aliases, src.nlp2cmd.generation.template_generator.TemplateGenerator._prepare_entities, src.nlp2cmd.generation.template_generator.TemplateGenerator._prepare_sql_entities, src.nlp2cmd.generation.template_generator.TemplateGenerator._prepare_shell_entities

### src.nlp2cmd.web_schema.form_data_loader.FormDataLoader
> Loads form field data from multiple sources:
1. .env file (for sensitive data like email, name, phon
- **Methods**: 45
- **Key Methods**: src.nlp2cmd.web_schema.form_data_loader.FormDataLoader.__init__, src.nlp2cmd.web_schema.form_data_loader.FormDataLoader._dedupe_preserve_order, src.nlp2cmd.web_schema.form_data_loader.FormDataLoader.dedupe_selectors, src.nlp2cmd.web_schema.form_data_loader.FormDataLoader._parse_domain, src.nlp2cmd.web_schema.form_data_loader.FormDataLoader._safe_domain_filename, src.nlp2cmd.web_schema.form_data_loader.FormDataLoader._user_sites_dir, src.nlp2cmd.web_schema.form_data_loader.FormDataLoader._project_sites_dir, src.nlp2cmd.web_schema.form_data_loader.FormDataLoader._site_profile_paths, src.nlp2cmd.web_schema.form_data_loader.FormDataLoader.get_site_profile_write_path, src.nlp2cmd.web_schema.form_data_loader.FormDataLoader._load_site_profile_payload

### networkx-3.6.1-py3-none-any.networkx.classes.graph.Graph
> Base class for undirected graphs.

A Graph stores nodes and edges with optional data, or attributes.
- **Methods**: 44
- **Key Methods**: networkx-3.6.1-py3-none-any.networkx.classes.graph.Graph.to_directed_class, networkx-3.6.1-py3-none-any.networkx.classes.graph.Graph.to_undirected_class, networkx-3.6.1-py3-none-any.networkx.classes.graph.Graph.__new__, networkx-3.6.1-py3-none-any.networkx.classes.graph.Graph.__init__, networkx-3.6.1-py3-none-any.networkx.classes.graph.Graph.adj, networkx-3.6.1-py3-none-any.networkx.classes.graph.Graph.name, networkx-3.6.1-py3-none-any.networkx.classes.graph.Graph.name, networkx-3.6.1-py3-none-any.networkx.classes.graph.Graph.__str__, networkx-3.6.1-py3-none-any.networkx.classes.graph.Graph.__iter__, networkx-3.6.1-py3-none-any.networkx.classes.graph.Graph.__contains__

### webops.nlp2cmd-repo.src.nlp2cmd.schemas.SchemaRegistry
> Registry for file format schemas with validation and repair capabilities.
- **Methods**: 37
- **Key Methods**: webops.nlp2cmd-repo.src.nlp2cmd.schemas.SchemaRegistry.__init__, webops.nlp2cmd-repo.src.nlp2cmd.schemas.SchemaRegistry._register_builtin_schemas, webops.nlp2cmd-repo.src.nlp2cmd.schemas.SchemaRegistry.register, webops.nlp2cmd-repo.src.nlp2cmd.schemas.SchemaRegistry.get, webops.nlp2cmd-repo.src.nlp2cmd.schemas.SchemaRegistry.has_schema, webops.nlp2cmd-repo.src.nlp2cmd.schemas.SchemaRegistry.list_schemas, webops.nlp2cmd-repo.src.nlp2cmd.schemas.SchemaRegistry.unregister, webops.nlp2cmd-repo.src.nlp2cmd.schemas.SchemaRegistry.find_schema_for_file, webops.nlp2cmd-repo.src.nlp2cmd.schemas.SchemaRegistry.find_schema_by_mime_type, webops.nlp2cmd-repo.src.nlp2cmd.schemas.SchemaRegistry.find_extension_conflicts

### src.nlp2cmd.schemas.SchemaRegistry
> Registry for file format schemas with validation and repair capabilities.
- **Methods**: 37
- **Key Methods**: src.nlp2cmd.schemas.SchemaRegistry.__init__, src.nlp2cmd.schemas.SchemaRegistry._register_builtin_schemas, src.nlp2cmd.schemas.SchemaRegistry.register, src.nlp2cmd.schemas.SchemaRegistry.get, src.nlp2cmd.schemas.SchemaRegistry.has_schema, src.nlp2cmd.schemas.SchemaRegistry.list_schemas, src.nlp2cmd.schemas.SchemaRegistry.unregister, src.nlp2cmd.schemas.SchemaRegistry.find_schema_for_file, src.nlp2cmd.schemas.SchemaRegistry.find_schema_by_mime_type, src.nlp2cmd.schemas.SchemaRegistry.find_extension_conflicts

### tools.schema.enhanced_schema_generator.EnhancedSchemaExtractor
> Enhanced schema extractor with multiple strategies.
- **Methods**: 36
- **Key Methods**: tools.schema.enhanced_schema_generator.EnhancedSchemaExtractor.__init__, tools.schema.enhanced_schema_generator.EnhancedSchemaExtractor.extract_schema, tools.schema.enhanced_schema_generator.EnhancedSchemaExtractor._select_strategy, tools.schema.enhanced_schema_generator.EnhancedSchemaExtractor._extract_with_strategy, tools.schema.enhanced_schema_generator.EnhancedSchemaExtractor._extract_from_help, tools.schema.enhanced_schema_generator.EnhancedSchemaExtractor._extract_from_man, tools.schema.enhanced_schema_generator.EnhancedSchemaExtractor._extract_with_llm, tools.schema.enhanced_schema_generator.EnhancedSchemaExtractor._extract_hybrid, tools.schema.enhanced_schema_generator.EnhancedSchemaExtractor._extract_from_patterns, tools.schema.enhanced_schema_generator.EnhancedSchemaExtractor._get_help_text

### webops.nlp2cmd-repo.tools.schema.enhanced_schema_generator.EnhancedSchemaExtractor
> Enhanced schema extractor with multiple strategies.
- **Methods**: 36
- **Key Methods**: webops.nlp2cmd-repo.tools.schema.enhanced_schema_generator.EnhancedSchemaExtractor.__init__, webops.nlp2cmd-repo.tools.schema.enhanced_schema_generator.EnhancedSchemaExtractor.extract_schema, webops.nlp2cmd-repo.tools.schema.enhanced_schema_generator.EnhancedSchemaExtractor._select_strategy, webops.nlp2cmd-repo.tools.schema.enhanced_schema_generator.EnhancedSchemaExtractor._extract_with_strategy, webops.nlp2cmd-repo.tools.schema.enhanced_schema_generator.EnhancedSchemaExtractor._extract_from_help, webops.nlp2cmd-repo.tools.schema.enhanced_schema_generator.EnhancedSchemaExtractor._extract_from_man, webops.nlp2cmd-repo.tools.schema.enhanced_schema_generator.EnhancedSchemaExtractor._extract_with_llm, webops.nlp2cmd-repo.tools.schema.enhanced_schema_generator.EnhancedSchemaExtractor._extract_hybrid, webops.nlp2cmd-repo.tools.schema.enhanced_schema_generator.EnhancedSchemaExtractor._extract_from_patterns, webops.nlp2cmd-repo.tools.schema.enhanced_schema_generator.EnhancedSchemaExtractor._get_help_text

### webops.nlp2cmd-repo.src.nlp2cmd.web_schema.form_data_loader.FormDataLoader
> Loads form field data from multiple sources:
1. .env file (for sensitive data like email, name, phon
- **Methods**: 36
- **Key Methods**: webops.nlp2cmd-repo.src.nlp2cmd.web_schema.form_data_loader.FormDataLoader.__init__, webops.nlp2cmd-repo.src.nlp2cmd.web_schema.form_data_loader.FormDataLoader._dedupe_preserve_order, webops.nlp2cmd-repo.src.nlp2cmd.web_schema.form_data_loader.FormDataLoader.dedupe_selectors, webops.nlp2cmd-repo.src.nlp2cmd.web_schema.form_data_loader.FormDataLoader._parse_domain, webops.nlp2cmd-repo.src.nlp2cmd.web_schema.form_data_loader.FormDataLoader._safe_domain_filename, webops.nlp2cmd-repo.src.nlp2cmd.web_schema.form_data_loader.FormDataLoader._user_sites_dir, webops.nlp2cmd-repo.src.nlp2cmd.web_schema.form_data_loader.FormDataLoader._project_sites_dir, webops.nlp2cmd-repo.src.nlp2cmd.web_schema.form_data_loader.FormDataLoader._site_profile_paths, webops.nlp2cmd-repo.src.nlp2cmd.web_schema.form_data_loader.FormDataLoader.get_site_profile_write_path, webops.nlp2cmd-repo.src.nlp2cmd.web_schema.form_data_loader.FormDataLoader._load_site_profile_payload

### webops.nlp2cmd-repo.src.nlp2cmd.adapters.shell.ShellAdapter
> Shell adapter supporting multiple shell types.

Transforms natural language into shell commands with
- **Methods**: 36
- **Key Methods**: webops.nlp2cmd-repo.src.nlp2cmd.adapters.shell.ShellAdapter.__init__, webops.nlp2cmd-repo.src.nlp2cmd.adapters.shell.ShellAdapter._parse_environment_context, webops.nlp2cmd-repo.src.nlp2cmd.adapters.shell.ShellAdapter.generate, webops.nlp2cmd-repo.src.nlp2cmd.adapters.shell.ShellAdapter._generate_file_search, webops.nlp2cmd-repo.src.nlp2cmd.adapters.shell.ShellAdapter._generate_find, webops.nlp2cmd-repo.src.nlp2cmd.adapters.shell.ShellAdapter._normalize_find_size_value, webops.nlp2cmd-repo.src.nlp2cmd.adapters.shell.ShellAdapter._generate_file_operation, webops.nlp2cmd-repo.src.nlp2cmd.adapters.shell.ShellAdapter._generate_process_management, webops.nlp2cmd-repo.src.nlp2cmd.adapters.shell.ShellAdapter._generate_process_monitoring, webops.nlp2cmd-repo.src.nlp2cmd.adapters.shell.ShellAdapter._generate_network
- **Inherits**: BaseDSLAdapter

### webops.nlp2cmd-repo.examples.devops.nlp2cmd_web_controller.NLP2CMDWebController
> Main controller for NLP2CMD-powered web infrastructure.

This class orchestrates the deployment and 
- **Methods**: 30
- **Key Methods**: webops.nlp2cmd-repo.examples.devops.nlp2cmd_web_controller.NLP2CMDWebController.__init__, webops.nlp2cmd-repo.examples.devops.nlp2cmd_web_controller.NLP2CMDWebController.execute, webops.nlp2cmd-repo.examples.devops.nlp2cmd_web_controller.NLP2CMDWebController._handle_deploy, webops.nlp2cmd-repo.examples.devops.nlp2cmd_web_controller.NLP2CMDWebController._handle_configure, webops.nlp2cmd-repo.examples.devops.nlp2cmd_web_controller.NLP2CMDWebController._handle_scale, webops.nlp2cmd-repo.examples.devops.nlp2cmd_web_controller.NLP2CMDWebController._handle_status, webops.nlp2cmd-repo.examples.devops.nlp2cmd_web_controller.NLP2CMDWebController._handle_stop, webops.nlp2cmd-repo.examples.devops.nlp2cmd_web_controller.NLP2CMDWebController._handle_unknown, webops.nlp2cmd-repo.examples.devops.nlp2cmd_web_controller.NLP2CMDWebController._execute_with_nlp2cmd, webops.nlp2cmd-repo.examples.devops.nlp2cmd_web_controller.NLP2CMDWebController._try_llm_fallback

### examples.03_integrations.web_development.nlp2cmd_web_controller.NLP2CMDWebController
> Main controller for NLP2CMD-powered web infrastructure.

This class orchestrates the deployment and 
- **Methods**: 30
- **Key Methods**: examples.03_integrations.web_development.nlp2cmd_web_controller.NLP2CMDWebController.__init__, examples.03_integrations.web_development.nlp2cmd_web_controller.NLP2CMDWebController.execute, examples.03_integrations.web_development.nlp2cmd_web_controller.NLP2CMDWebController._handle_deploy, examples.03_integrations.web_development.nlp2cmd_web_controller.NLP2CMDWebController._handle_configure, examples.03_integrations.web_development.nlp2cmd_web_controller.NLP2CMDWebController._handle_scale, examples.03_integrations.web_development.nlp2cmd_web_controller.NLP2CMDWebController._handle_status, examples.03_integrations.web_development.nlp2cmd_web_controller.NLP2CMDWebController._handle_stop, examples.03_integrations.web_development.nlp2cmd_web_controller.NLP2CMDWebController._handle_unknown, examples.03_integrations.web_development.nlp2cmd_web_controller.NLP2CMDWebController._execute_with_nlp2cmd, examples.03_integrations.web_development.nlp2cmd_web_controller.NLP2CMDWebController._try_llm_fallback

### networkx-3.6.1-py3-none-any.networkx.classes.digraph.DiGraph
> Base class for directed graphs.

A DiGraph stores nodes and edges with optional data, or attributes.
- **Methods**: 29
- **Key Methods**: networkx-3.6.1-py3-none-any.networkx.classes.digraph.DiGraph.__new__, networkx-3.6.1-py3-none-any.networkx.classes.digraph.DiGraph.__init__, networkx-3.6.1-py3-none-any.networkx.classes.digraph.DiGraph.adj, networkx-3.6.1-py3-none-any.networkx.classes.digraph.DiGraph.succ, networkx-3.6.1-py3-none-any.networkx.classes.digraph.DiGraph.pred, networkx-3.6.1-py3-none-any.networkx.classes.digraph.DiGraph.add_node, networkx-3.6.1-py3-none-any.networkx.classes.digraph.DiGraph.add_nodes_from, networkx-3.6.1-py3-none-any.networkx.classes.digraph.DiGraph.remove_node, networkx-3.6.1-py3-none-any.networkx.classes.digraph.DiGraph.remove_nodes_from, networkx-3.6.1-py3-none-any.networkx.classes.digraph.DiGraph.add_edge
- **Inherits**: Graph

### tools.schema.non_llm_schema_extractor.NonLLMSchemaExtractor
> Non-LLM schema extractor with multiple strategies.
- **Methods**: 27
- **Key Methods**: tools.schema.non_llm_schema_extractor.NonLLMSchemaExtractor.__init__, tools.schema.non_llm_schema_extractor.NonLLMSchemaExtractor.extract_schema, tools.schema.non_llm_schema_extractor.NonLLMSchemaExtractor._extract_with_strategy, tools.schema.non_llm_schema_extractor.NonLLMSchemaExtractor._extract_from_help, tools.schema.non_llm_schema_extractor.NonLLMSchemaExtractor._extract_from_man, tools.schema.non_llm_schema_extractor.NonLLMSchemaExtractor._extract_from_patterns, tools.schema.non_llm_schema_extractor.NonLLMSchemaExtractor._extract_from_templates, tools.schema.non_llm_schema_extractor.NonLLMSchemaExtractor._enhance_schema, tools.schema.non_llm_schema_extractor.NonLLMSchemaExtractor._evaluate_quality, tools.schema.non_llm_schema_extractor.NonLLMSchemaExtractor._create_fallback_schema

### webops.nlp2cmd-repo.tools.schema.non_llm_schema_extractor.NonLLMSchemaExtractor
> Non-LLM schema extractor with multiple strategies.
- **Methods**: 27
- **Key Methods**: webops.nlp2cmd-repo.tools.schema.non_llm_schema_extractor.NonLLMSchemaExtractor.__init__, webops.nlp2cmd-repo.tools.schema.non_llm_schema_extractor.NonLLMSchemaExtractor.extract_schema, webops.nlp2cmd-repo.tools.schema.non_llm_schema_extractor.NonLLMSchemaExtractor._extract_with_strategy, webops.nlp2cmd-repo.tools.schema.non_llm_schema_extractor.NonLLMSchemaExtractor._extract_from_help, webops.nlp2cmd-repo.tools.schema.non_llm_schema_extractor.NonLLMSchemaExtractor._extract_from_man, webops.nlp2cmd-repo.tools.schema.non_llm_schema_extractor.NonLLMSchemaExtractor._extract_from_patterns, webops.nlp2cmd-repo.tools.schema.non_llm_schema_extractor.NonLLMSchemaExtractor._extract_from_templates, webops.nlp2cmd-repo.tools.schema.non_llm_schema_extractor.NonLLMSchemaExtractor._enhance_schema, webops.nlp2cmd-repo.tools.schema.non_llm_schema_extractor.NonLLMSchemaExtractor._evaluate_quality, webops.nlp2cmd-repo.tools.schema.non_llm_schema_extractor.NonLLMSchemaExtractor._create_fallback_schema

### webops.nlp2cmd-repo.src.nlp2cmd.generation.keywords.KeywordIntentDetector
> Rule-based intent detection using keyword matching.

No LLM needed - uses predefined keyword pattern
- **Methods**: 27
- **Key Methods**: webops.nlp2cmd-repo.src.nlp2cmd.generation.keywords.KeywordIntentDetector.__init__, webops.nlp2cmd-repo.src.nlp2cmd.generation.keywords.KeywordIntentDetector._load_detector_config_from_json, webops.nlp2cmd-repo.src.nlp2cmd.generation.keywords.KeywordIntentDetector._load_patterns_from_json, webops.nlp2cmd-repo.src.nlp2cmd.generation.keywords.KeywordIntentDetector._match_keyword, webops.nlp2cmd-repo.src.nlp2cmd.generation.keywords.KeywordIntentDetector._normalize_text_lower, webops.nlp2cmd-repo.src.nlp2cmd.generation.keywords.KeywordIntentDetector._maybe_lemmatize_text_lower, webops.nlp2cmd-repo.src.nlp2cmd.generation.keywords.KeywordIntentDetector._normalize_intent, webops.nlp2cmd-repo.src.nlp2cmd.generation.keywords.KeywordIntentDetector._has_shell_file_context, webops.nlp2cmd-repo.src.nlp2cmd.generation.keywords.KeywordIntentDetector._detect_fast_path, webops.nlp2cmd-repo.src.nlp2cmd.generation.keywords.KeywordIntentDetector._detect_fast_path_docker_run_detached

### webops.nlp2cmd-repo.src.nlp2cmd.core.toon_integration.ToonDataManager
> Unified data manager using TOON format
- **Methods**: 27
- **Key Methods**: webops.nlp2cmd-repo.src.nlp2cmd.core.toon_integration.ToonDataManager.__init__, webops.nlp2cmd-repo.src.nlp2cmd.core.toon_integration.ToonDataManager._ensure_loaded, webops.nlp2cmd-repo.src.nlp2cmd.core.toon_integration.ToonDataManager.get_all_commands, webops.nlp2cmd-repo.src.nlp2cmd.core.toon_integration.ToonDataManager.get_shell_commands, webops.nlp2cmd-repo.src.nlp2cmd.core.toon_integration.ToonDataManager.get_browser_commands, webops.nlp2cmd-repo.src.nlp2cmd.core.toon_integration.ToonDataManager.get_command_by_name, webops.nlp2cmd-repo.src.nlp2cmd.core.toon_integration.ToonDataManager.search_commands, webops.nlp2cmd-repo.src.nlp2cmd.core.toon_integration.ToonDataManager.get_config, webops.nlp2cmd-repo.src.nlp2cmd.core.toon_integration.ToonDataManager.get_llm_config, webops.nlp2cmd-repo.src.nlp2cmd.core.toon_integration.ToonDataManager.get_test_commands

### src.nlp2cmd.core.toon_integration.ToonDataManager
> Unified data manager using TOON format
- **Methods**: 27
- **Key Methods**: src.nlp2cmd.core.toon_integration.ToonDataManager.__init__, src.nlp2cmd.core.toon_integration.ToonDataManager._ensure_loaded, src.nlp2cmd.core.toon_integration.ToonDataManager.get_all_commands, src.nlp2cmd.core.toon_integration.ToonDataManager.get_shell_commands, src.nlp2cmd.core.toon_integration.ToonDataManager.get_browser_commands, src.nlp2cmd.core.toon_integration.ToonDataManager.get_command_by_name, src.nlp2cmd.core.toon_integration.ToonDataManager.search_commands, src.nlp2cmd.core.toon_integration.ToonDataManager.get_config, src.nlp2cmd.core.toon_integration.ToonDataManager.get_llm_config, src.nlp2cmd.core.toon_integration.ToonDataManager.get_test_commands

### src.nlp2cmd.web_schema.site_explorer.SiteExplorer
> Explores website to find forms, contact pages, and other content.

Usage:
    explorer = SiteExplore
- **Methods**: 27
- **Key Methods**: src.nlp2cmd.web_schema.site_explorer.SiteExplorer.__init__, src.nlp2cmd.web_schema.site_explorer.SiteExplorer._setup_resource_blocking, src.nlp2cmd.web_schema.site_explorer.SiteExplorer._resolve_platform_url, src.nlp2cmd.web_schema.site_explorer.SiteExplorer._goto_with_retry, src.nlp2cmd.web_schema.site_explorer.SiteExplorer._try_github_api, src.nlp2cmd.web_schema.site_explorer.SiteExplorer._detect_docs_framework, src.nlp2cmd.web_schema.site_explorer.SiteExplorer._record_timing, src.nlp2cmd.web_schema.site_explorer.SiteExplorer.get_timing_stats, src.nlp2cmd.web_schema.site_explorer.SiteExplorer._fallback_static_scrape, src.nlp2cmd.web_schema.site_explorer.SiteExplorer.find_content

### networkx-3.6.1-py3-none-any.networkx.utils.configs.Config
> The base class for NetworkX configuration.

There are two ways to use this to create configurations.
- **Methods**: 24
- **Key Methods**: networkx-3.6.1-py3-none-any.networkx.utils.configs.Config.__init_subclass__, networkx-3.6.1-py3-none-any.networkx.utils.configs.Config.__new__, networkx-3.6.1-py3-none-any.networkx.utils.configs.Config._on_setattr, networkx-3.6.1-py3-none-any.networkx.utils.configs.Config._on_delattr, networkx-3.6.1-py3-none-any.networkx.utils.configs.Config.__dir__, networkx-3.6.1-py3-none-any.networkx.utils.configs.Config.__setattr__, networkx-3.6.1-py3-none-any.networkx.utils.configs.Config.__delattr__, networkx-3.6.1-py3-none-any.networkx.utils.configs.Config.__contains__, networkx-3.6.1-py3-none-any.networkx.utils.configs.Config.__iter__, networkx-3.6.1-py3-none-any.networkx.utils.configs.Config.__len__

### webops.nlp2cmd-repo.src.nlp2cmd.adapters.shell_backup.ShellAdapter
> Shell adapter supporting multiple shell types.

Transforms natural language into shell commands with
- **Methods**: 24
- **Key Methods**: webops.nlp2cmd-repo.src.nlp2cmd.adapters.shell_backup.ShellAdapter.__init__, webops.nlp2cmd-repo.src.nlp2cmd.adapters.shell_backup.ShellAdapter._parse_environment_context, webops.nlp2cmd-repo.src.nlp2cmd.adapters.shell_backup.ShellAdapter.generate, webops.nlp2cmd-repo.src.nlp2cmd.adapters.shell_backup.ShellAdapter._generate_file_search, webops.nlp2cmd-repo.src.nlp2cmd.adapters.shell_backup.ShellAdapter._generate_find, webops.nlp2cmd-repo.src.nlp2cmd.adapters.shell_backup.ShellAdapter._normalize_find_size_value, webops.nlp2cmd-repo.src.nlp2cmd.adapters.shell_backup.ShellAdapter._generate_file_operation, webops.nlp2cmd-repo.src.nlp2cmd.adapters.shell_backup.ShellAdapter._generate_process_management, webops.nlp2cmd-repo.src.nlp2cmd.adapters.shell_backup.ShellAdapter._generate_process_monitoring, webops.nlp2cmd-repo.src.nlp2cmd.adapters.shell_backup.ShellAdapter._generate_network
- **Inherits**: BaseDSLAdapter

## Data Transformation Functions

Key functions that process and transform data:

### demos.demo_intelligent_nlp2cmd.IntelligentNLP2CMD.transform
> Transform natural language to command with version detection.

Args:
    query: Natural language que
- **Output to**: ActionIR, self.base_nlp.transform_ir, self.generator.generate_command, ActionIR, webops.nlp2cmd-repo.src.nlp2cmd.pipeline_runner._MarkdownConsoleWrapper.print

### webops.docker_app.VoiceServiceManager.process_voice_command
> Process voice command and return response.
- **Output to**: self.pipeline.process, VoiceCommandResponse, VoiceCommandResponse, VoiceCommandResponse, VoiceCommandResponse

### webops.docker_app.process_voice_command
> Process voice command and execute shell command.
- **Output to**: app.post, voice_manager.process_voice_command

### networkx-3.6.1-py3-none-any.networkx.relabel.convert_node_labels_to_integers
> Returns a copy of the graph G with the nodes relabeled using
consecutive integers.

Parameters
-----
- **Output to**: nx._dispatchable, networkx-3.6.1-py3-none-any.networkx.relabel.relabel_nodes, G.number_of_nodes, dict, nx.set_node_attributes

### networkx-3.6.1-py3-none-any.networkx.convert_matrix.to_scipy_sparse_array
> Returns the graph adjacency matrix as a SciPy sparse array.

Parameters
----------
G : graph
    The
- **Output to**: nx._dispatchable, dict, zip, G.is_directed, len

### networkx-3.6.1-py3-none-any.networkx.convert_matrix.from_scipy_sparse_array
> Creates a new graph from an adjacency matrix given as a SciPy sparse
array.

Parameters
----------
A
- **Output to**: nx._dispatchable, nx.empty_graph, G.add_nodes_from, networkx-3.6.1-py3-none-any.networkx.convert_matrix._generate_weighted_edges, G.add_weighted_edges_from

### networkx-3.6.1-py3-none-any.networkx.readwrite.p2g.parse_p2g
> Parse p2g format graph from string or iterable.

Returns
-------
MultiDiGraph
- **Output to**: nx._dispatchable, None.strip, nx.MultiDiGraph, map, range

### webops.voice_service.VoiceServiceManager.process_voice_command
> Process voice command and return response.
- **Output to**: webops.nlp2cmd-repo.src.nlp2cmd.pipeline_runner._MarkdownConsoleWrapper.print, webops.nlp2cmd-repo.src.nlp2cmd.pipeline_runner._MarkdownConsoleWrapper.print, webops.nlp2cmd-repo.src.nlp2cmd.pipeline_runner._MarkdownConsoleWrapper.print, webops.nlp2cmd-repo.src.nlp2cmd.pipeline_runner._MarkdownConsoleWrapper.print, self._normalize_cache_key

### webops.voice_service.VoiceServiceManager._process_with_mock_pipeline
> Process command using mock pipeline.
- **Output to**: self.pipeline.process, self.broadcast_log, self.executor.execute_command, execution_result.get, hasattr

### webops.voice_service.VoiceServiceManager._process_with_nlp2cmd_service
> Process command using NLP2CMD service.
- **Output to**: pipeline.process, execution_result.get, self._process_with_mock_pipeline, self.broadcast_log, self.executor.execute_command

### webops.voice_service.process_voice_command
> Process voice command and execute shell command.
- **Output to**: app.post, webops.nlp2cmd-repo.src.nlp2cmd.pipeline_runner._MarkdownConsoleWrapper.print, webops.nlp2cmd-repo.src.nlp2cmd.pipeline_runner._MarkdownConsoleWrapper.print, webops.nlp2cmd-repo.src.nlp2cmd.pipeline_runner._MarkdownConsoleWrapper.print, webops.nlp2cmd-repo.src.nlp2cmd.pipeline_runner._MarkdownConsoleWrapper.print

### webops.voice_service_clean.VoiceServiceManager.process_voice_command
> Process voice command and return response.
- **Output to**: webops.nlp2cmd-repo.src.nlp2cmd.pipeline_runner._MarkdownConsoleWrapper.print, webops.nlp2cmd-repo.src.nlp2cmd.pipeline_runner._MarkdownConsoleWrapper.print, webops.nlp2cmd-repo.src.nlp2cmd.pipeline_runner._MarkdownConsoleWrapper.print, webops.nlp2cmd-repo.src.nlp2cmd.pipeline_runner._MarkdownConsoleWrapper.print, webops.nlp2cmd-repo.src.nlp2cmd.pipeline_runner._MarkdownConsoleWrapper.print

### webops.voice_service_clean.process_voice_command
> Process voice command and execute shell command.
- **Output to**: app.post, webops.nlp2cmd-repo.src.nlp2cmd.pipeline_runner._MarkdownConsoleWrapper.print, webops.nlp2cmd-repo.src.nlp2cmd.pipeline_runner._MarkdownConsoleWrapper.print, webops.nlp2cmd-repo.src.nlp2cmd.pipeline_runner._MarkdownConsoleWrapper.print, webops.nlp2cmd-repo.src.nlp2cmd.pipeline_runner._MarkdownConsoleWrapper.print

### networkx-3.6.1-py3-none-any.networkx.readwrite.graphml.parse_graphml
> Read graph in GraphML format from string.

Parameters
----------
graphml_string : string
   String c
- **Output to**: nx._dispatchable, GraphMLReader, list, reader, len

### networkx-3.6.1-py3-none-any.networkx.readwrite.graphml.GraphMLReader.decode_data_elements
> Use the key information to decode the data XML if present.
- **Output to**: obj_xml.findall, data_element.get, nx.NetworkXError, len, data_type

### networkx-3.6.1-py3-none-any.networkx.readwrite.adjlist.parse_adjlist
> Parse lines of a graph adjacency list representation.

Parameters
----------
lines : list or iterato
- **Output to**: nx._dispatchable, nx.empty_graph, line.find, None.split, vlist.pop

### networkx-3.6.1-py3-none-any.networkx.readwrite.leda.parse_leda
> Read graph in LEDA format from string or iterable.

Parameters
----------
lines : string or iterable
- **Output to**: nx._dispatchable, isinstance, iter, range, int

### networkx-3.6.1-py3-none-any.networkx.readwrite.pajek.parse_pajek
> Parse Pajek format graph from string or iterable.

Parameters
----------
lines : string or iterable

- **Output to**: nx._dispatchable, isinstance, iter, nx.MultiDiGraph, iter

### networkx-3.6.1-py3-none-any.networkx.readwrite.text._parse_network_text
> Reconstructs a graph from a network text representation.

This is mainly used for testing.  Network 
- **Output to**: iter, webops.nlp2cmd-repo.src.nlp2cmd.executor.ExecutionContext.set, webops.nlp2cmd-repo.src.nlp2cmd.executor.ExecutionContext.set, chain, object

### networkx-3.6.1-py3-none-any.networkx.readwrite.edgelist.parse_edgelist
> Parse lines of an edge list representation of a graph.

Parameters
----------
lines : list or iterat
- **Output to**: nx._dispatchable, nx.empty_graph, None.split, s.pop, s.pop

### networkx-3.6.1-py3-none-any.networkx.readwrite.gexf.GEXFWriter.alter_graph_mode_timeformat
- **Output to**: isinstance, self.graph_element.set, isinstance, self.graph_element.get, self.graph_element.set

### networkx-3.6.1-py3-none-any.networkx.readwrite.gexf.GEXFReader.decode_attr_elements
- **Output to**: obj_xml.find, attr_element.findall, a.get, a.get, nx.NetworkXError

### networkx-3.6.1-py3-none-any.networkx.readwrite.sparse6._generate_sparse6_bytes
> Yield bytes in the sparse6 encoding of a graph.

`G` is an undirected simple graph. `nodes` is the l
- **Output to**: len, networkx-3.6.1-py3-none-any.networkx.readwrite.graph6.n_to_data, sorted, ValueError, bits.append

### networkx-3.6.1-py3-none-any.networkx.readwrite.sparse6.from_sparse6_bytes
> Read an undirected graph in sparse6 format from string.

Parameters
----------
string : string
   Da
- **Output to**: nx._dispatchable, string.startswith, networkx-3.6.1-py3-none-any.networkx.readwrite.graph6.data_to_n, nx.MultiGraph, G.add_nodes_from

### networkx-3.6.1-py3-none-any.networkx.readwrite.sparse6.to_sparse6_bytes
> Convert an undirected graph to bytes in sparse6 format.

Parameters
----------
G : Graph (undirected
- **Output to**: nx.convert_node_labels_to_integers, None.join, G.subgraph, networkx-3.6.1-py3-none-any.networkx.readwrite.sparse6._generate_sparse6_bytes

## Behavioral Patterns

### recursion__select_starting_cell
- **Type**: recursion
- **Confidence**: 0.90
- **Functions**: networkx-3.6.1-py3-none-any.networkx.generators.line._select_starting_cell

### recursion__rooted_trees
- **Type**: recursion
- **Confidence**: 0.90
- **Functions**: networkx-3.6.1-py3-none-any.networkx.generators.nonisomorphic_trees._rooted_trees

### recursion__random_unlabeled_rooted_tree
- **Type**: recursion
- **Confidence**: 0.90
- **Functions**: networkx-3.6.1-py3-none-any.networkx.generators.trees._random_unlabeled_rooted_tree

### recursion__random_unlabeled_rooted_forest
- **Type**: recursion
- **Confidence**: 0.90
- **Functions**: networkx-3.6.1-py3-none-any.networkx.generators.trees._random_unlabeled_rooted_forest

### recursion_flatten
- **Type**: recursion
- **Confidence**: 0.90
- **Functions**: networkx-3.6.1-py3-none-any.networkx.utils.misc.flatten

### recursion_compile
- **Type**: recursion
- **Confidence**: 0.90
- **Functions**: networkx-3.6.1-py3-none-any.networkx.utils.decorators.argmap.compile

### recursion__flatten
- **Type**: recursion
- **Confidence**: 0.90
- **Functions**: networkx-3.6.1-py3-none-any.networkx.utils.decorators.argmap._flatten

### recursion_hamiltonian_path
- **Type**: recursion
- **Confidence**: 0.90
- **Functions**: networkx-3.6.1-py3-none-any.networkx.algorithms.tournament.hamiltonian_path

### recursion_ramsey_R2
- **Type**: recursion
- **Confidence**: 0.90
- **Functions**: networkx-3.6.1-py3-none-any.networkx.algorithms.approximation.ramsey.ramsey_R2

### recursion_procedure_P
- **Type**: recursion
- **Confidence**: 0.90
- **Functions**: networkx-3.6.1-py3-none-any.networkx.algorithms.coloring.equitable_coloring.procedure_P

### recursion__dfbnb
- **Type**: recursion
- **Confidence**: 0.90
- **Functions**: networkx-3.6.1-py3-none-any.networkx.algorithms.centrality.group._dfbnb

### recursion_export_analytics
- **Type**: recursion
- **Confidence**: 0.90
- **Functions**: webops.nlp2cmd-repo.src.nlp2cmd.cli.history.export_analytics

### state_machine_VoiceServiceManager
- **Type**: state_machine
- **Confidence**: 0.70
- **Functions**: webops.docker_app.VoiceServiceManager.__init__, webops.docker_app.VoiceServiceManager.connect, webops.docker_app.VoiceServiceManager.disconnect, webops.docker_app.VoiceServiceManager.broadcast_log, webops.docker_app.VoiceServiceManager.process_voice_command

### state_machine_VoiceServiceManager
- **Type**: state_machine
- **Confidence**: 0.70
- **Functions**: webops.voice_service.VoiceServiceManager.__init__, webops.voice_service.VoiceServiceManager._create_nlp2cmd_pipeline, webops.voice_service.VoiceServiceManager._normalize_cache_key, webops.voice_service.VoiceServiceManager._to_cached_result, webops.voice_service.VoiceServiceManager._get_cache_lock

### state_machine_VoiceServiceManager
- **Type**: state_machine
- **Confidence**: 0.70
- **Functions**: webops.voice_service_clean.VoiceServiceManager.__init__, webops.voice_service_clean.VoiceServiceManager._create_nlp2cmd_pipeline, webops.voice_service_clean.VoiceServiceManager.connect, webops.voice_service_clean.VoiceServiceManager.disconnect, webops.voice_service_clean.VoiceServiceManager.broadcast_log

## Public API Surface

Functions exposed as public API (no underscore prefix):

- `src.nlp2cmd.pipeline_runner_plans.PlanExecutionMixin.execute_action_plan` - 261 calls
- `src.nlp2cmd.cli.commands.run.handle_run_mode` - 261 calls
- `networkx-3.6.1-py3-none-any.networkx.generators.social.les_miserables_graph` - 256 calls
- `src.nlp2cmd.adapters.canvas.CanvasAdapter.execute_drawing_plan` - 193 calls
- `networkx-3.6.1-py3-none-any.networkx.drawing.nx_pylab.display` - 188 calls
- `networkx-3.6.1-py3-none-any.networkx.algorithms.similarity.optimize_edit_paths` - 168 calls
- `networkx-3.6.1-py3-none-any.networkx.algorithms.matching.max_weight_matching` - 150 calls
- `webops.nlp2cmd-repo.examples.shell.environment_analysis.main` - 143 calls
- `examples.01_basics.shell_fundamentals.environment_analysis.main` - 139 calls
- `src.nlp2cmd.cli.main.main` - 115 calls
- `src.nlp2cmd.execution.runner.ExecutionRunner.run_command` - 109 calls
- `webops.nlp2cmd-repo.examples.devops.demo.demo_nlp_commands` - 108 calls
- `examples.03_integrations.web_development.demo.demo_nlp_commands` - 106 calls
- `docker.novnc.demos.demo_desktop_gui.run_demo` - 103 calls
- `webops.nlp2cmd-repo.examples.devops.demo_batch.run_batch_demo` - 99 calls
- `examples.03_integrations.web_development.demo_batch.run_batch_demo` - 95 calls
- `networkx-3.6.1-py3-none-any.networkx.readwrite.gml.parse_gml_lines` - 92 calls
- `networkx-3.6.1-py3-none-any.networkx.algorithms.tree.branchings.maximum_branching` - 89 calls
- `webops.nlp2cmd-repo.examples.architecture.end_to_end_demo.main` - 87 calls
- `examples.05_advanced_features.schema_driven_architecture.end_to_end_demo.main` - 87 calls
- `src.nlp2cmd.generation.train_model.train_all_models` - 86 calls
- `src.nlp2cmd.web_schema.form_handler.FormHandler.detect_form_fields` - 83 calls
- `webops.nlp2cmd-repo.examples.shell.feedback_loop.simulate_interactive_session` - 82 calls
- `webops.nlp2cmd-repo.src.nlp2cmd.cli.main.main` - 81 calls
- `webops.nlp2cmd-repo.examples.sql.sql_workflows.main` - 81 calls
- `examples.01_basics.sql_basics.workflows.main` - 81 calls
- `webops.nlp2cmd-repo.examples.use_cases.shell_validation.ShellCommandValidator.get_test_cases` - 79 calls
- `examples.04_domain_specific.debugging.validation.ShellCommandValidator.get_test_cases` - 79 calls
- `networkx-3.6.1-py3-none-any.networkx.algorithms.flow.networksimplex.network_simplex` - 78 calls
- `examples.01_basics.shell_fundamentals.feedback_loop.simulate_interactive_session` - 78 calls
- `examples.benchmark_nlp2cmd.generate_html` - 77 calls
- `src.nlp2cmd.web_schema.site_explorer.SiteExplorer.find_form` - 77 calls
- `examples.03_integrations.toon_format.usage_example.main` - 77 calls
- `networkx-3.6.1-py3-none-any.networkx.drawing.nx_pylab.draw_networkx_edges` - 76 calls
- `webops.nlp2cmd-repo.examples.toon_usage_example.main` - 73 calls
- `scripts.maintenance.refactoring_summary.print_summary` - 72 calls
- `networkx-3.6.1-py3-none-any.networkx.algorithms.approximation.traveling_salesman.held_karp_ascent` - 70 calls
- `webops.nlp2cmd-repo.src.app2schema.extract.extract_schema` - 70 calls
- `webops.nlp2cmd-repo.examples.docker.file_repair.main` - 70 calls
- `src.app2schema.extract.extract_schema` - 70 calls

## System Interactions

How components interact:

```mermaid
graph TD
    _execute_plan_step --> _resolve_plan_variab
    _execute_plan_step --> Console
    _execute_plan_step --> print
    _execute_plan_step --> get
    _execute_plan_step --> goto
    _run_dom_multi_actio --> get
    _run_dom_multi_actio --> Console
    _run_dom_multi_actio --> _MarkdownConsoleWrap
    _run_dom_multi_actio --> RunnerResult
    execute_action_plan --> Console
    execute_action_plan --> frozenset
    execute_action_plan --> print
    execute_action_plan --> enumerate
    les_miserables_graph --> _dispatchable
    les_miserables_graph --> Graph
    les_miserables_graph --> add_edge
    _prepare_shell_entit --> copy
    _prepare_shell_entit --> get
    display --> get
    display --> isinstance
    display --> subgraph
    main --> print
    main --> EnvironmentAnalyzer
    main --> print_separator
    main --> print_rule
    main --> group
    main --> option
    run_command --> time
    run_command --> print_markdown_block
    run_command --> ExecutionResult
```

## Reverse Engineering Guidelines

1. **Entry Points**: Start analysis from the entry points listed above
2. **Core Logic**: Focus on classes with many methods
3. **Data Flow**: Follow data transformation functions
4. **Process Flows**: Use the flow diagrams for execution paths
5. **API Surface**: Public API functions reveal the interface

## Context for LLM

Maintain the identified architectural patterns and public API surface when suggesting changes.