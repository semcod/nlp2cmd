# System Architecture Analysis

## Overview

- **Project**: /home/tom/github/wronai/nlp2cmd
- **Primary Language**: python
- **Languages**: python: 757, shell: 62
- **Analysis Mode**: static
- **Total Functions**: 5362
- **Total Classes**: 810
- **Modules**: 819
- **Entry Points**: 4392

## Architecture by Module

### src.nlp2cmd.generation.template_generator
- **Functions**: 100
- **Classes**: 2
- **File**: `template_generator.py`

### networkx-3.6.1-py3-none-any.networkx.classes.reportviews
- **Functions**: 99
- **Classes**: 23
- **File**: `reportviews.py`

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

### src.nlp2cmd.skills.drawing.shapes
- **Functions**: 38
- **Classes**: 35
- **File**: `shapes.py`

### tools.schema.enhanced_schema_generator
- **Functions**: 37
- **Classes**: 3
- **File**: `enhanced_schema_generator.py`

### src.nlp2cmd.web_schema.site_explorer
- **Functions**: 34
- **Classes**: 3
- **File**: `site_explorer.py`

### networkx-3.6.1-py3-none-any.networkx.readwrite.graphml
- **Functions**: 33
- **Classes**: 5
- **File**: `graphml.py`

### networkx-3.6.1-py3-none-any.networkx.readwrite.gexf
- **Functions**: 32
- **Classes**: 3
- **File**: `gexf.py`

### networkx-3.6.1-py3-none-any.networkx.utils.misc
- **Functions**: 32
- **Classes**: 2
- **File**: `misc.py`

### src.nlp2cmd.core.toon_integration
- **Functions**: 32
- **Classes**: 1
- **File**: `toon_integration.py`

### networkx-3.6.1-py3-none-any.networkx.classes.digraph
- **Functions**: 31
- **Classes**: 3
- **File**: `digraph.py`

### src.nlp2cmd.generation.semantic_matcher_optimized
- **Functions**: 30
- **Classes**: 3
- **File**: `semantic_matcher_optimized.py`

### networkx-3.6.1-py3-none-any.networkx.utils.configs
- **Functions**: 28
- **Classes**: 3
- **File**: `configs.py`

## Key Entry Points

Main execution flows into the system:

### src.nlp2cmd.pipeline_runner_plans.PlanExecutionMixin._execute_plan_step
> Execute a single ActionPlan step. Returns extracted value or None.
- **Calls**: self._resolve_plan_variables, Console, src.nlp2cmd.pipeline_runner_utils._MarkdownConsoleWrapper.print, StepDispatcher.has_handler, params.get, page.goto, page.wait_for_timeout, StepDispatcher.dispatch

### src.nlp2cmd.pipeline_runner_browser.BrowserExecutionMixin._run_dom_multi_action
> Execute multiple browser actions in sequence.
- **Calls**: payload.get, Console, _MarkdownConsoleWrapper, payload.get, RunnerResult, RunnerResult, sync_playwright, p.chromium.launch

### networkx-3.6.1-py3-none-any.networkx.generators.social.les_miserables_graph
> Returns coappearance network of characters in the novel Les Miserables.

References
----------
.. [1] D. E. Knuth, 1993.
   The Stanford GraphBase: a 
- **Calls**: nx._dispatchable, nx.Graph, G.add_edge, G.add_edge, G.add_edge, G.add_edge, G.add_edge, G.add_edge

### src.nlp2cmd.pipeline_runner_plans.PlanExecutionMixin.execute_action_plan
> Execute an ActionPlan step by step using Playwright.

Args:
    plan: ActionPlan instance with steps to execute
    dry_run: If True, only show the pl
- **Calls**: Console, self._detect_desktop_steps, console.print, console.print, enumerate, None.strip, RunnerResult, console.print

### src.nlp2cmd.adapters.canvas.CanvasAdapter.execute_drawing_plan
> Execute a canvas drawing plan on a Playwright page.

IMPROVED: Added detailed diagnostic logging for each step.
- **Calls**: plan.get, MouseController, enumerate, json.loads, step.get, step.get, src.nlp2cmd.pipeline_runner_utils._MarkdownConsoleWrapper.print, src.nlp2cmd.pipeline_runner_utils._MarkdownConsoleWrapper.print

### networkx-3.6.1-py3-none-any.networkx.drawing.nx_pylab.display
> Draw the graph G.

Draw the graph as a collection of nodes connected by edges.
The exact details of what the graph looks like are controlled by the be
- **Calls**: kwargs.get, kwargs.get, isinstance, G.subgraph, kwargs.get, callable, kwargs.get, kwargs.get

### examples.01_basics.shell_fundamentals.environment_analysis.main
- **Calls**: examples._example_helpers.print_separator, EnvironmentAnalyzer, examples._example_helpers.print_rule, src.nlp2cmd.pipeline_runner_utils._MarkdownConsoleWrapper.print, examples._example_helpers.print_rule, analyzer.analyze, src.nlp2cmd.pipeline_runner_utils._MarkdownConsoleWrapper.print, src.nlp2cmd.pipeline_runner_utils._MarkdownConsoleWrapper.print

### examples.10_online_code_editors.03_adaptive_code.main
- **Calls**: argparse.ArgumentParser, parser.add_argument, parser.add_argument, parser.add_argument, parser.add_argument, parser.add_argument, parser.add_argument, parser.parse_args

### examples.10_online_code_editors.02_mycompiler_run.main
- **Calls**: argparse.ArgumentParser, parser.add_argument, parser.add_argument, parser.add_argument, parser.add_argument, parser.add_argument, parser.add_argument, parser.add_argument

### src.nlp2cmd.execution.runner.ExecutionRunner.run_command
> Execute a shell command with real-time output.

Args:
    command: Shell command to execute
    cwd: Working directory
    env: Environment variables

- **Calls**: time.time, self.print_markdown_block, ExecutionResult, self.execution_history.append, subprocess.Popen, None.join, None.join, subprocess.run

### src.nlp2cmd.registry.ActionRegistry._register_builtin_actions
> Register built-in actions.
- **Calls**: self.register, self.register, self.register, self.register, self.register, self.register, self.register, self.register

### networkx-3.6.1-py3-none-any.networkx.utils.backends._dispatchable._convert_and_call_for_tests
> Call this dispatchable function with a backend; for use with testing.
- **Calls**: networkx-3.6.1-py3-none-any.networkx.utils.backends._load_backend, _logger.debug, self.name.endswith, backend.convert_to_nx, self._can_backend_run, hasattr, pytest.xfail, self._will_call_mutate_input

### examples.03_integrations.web_development.demo_batch.run_batch_demo
> Run all commands from prompt.txt automatically.
- **Calls**: src.nlp2cmd.pipeline_runner_utils._MarkdownConsoleWrapper.print, src.nlp2cmd.pipeline_runner_utils._MarkdownConsoleWrapper.print, src.nlp2cmd.pipeline_runner_utils._MarkdownConsoleWrapper.print, src.nlp2cmd.pipeline_runner_utils._MarkdownConsoleWrapper.print, src.nlp2cmd.pipeline_runner_utils._MarkdownConsoleWrapper.print, src.nlp2cmd.pipeline_runner_utils._MarkdownConsoleWrapper.print, src.nlp2cmd.pipeline_runner_utils._MarkdownConsoleWrapper.print, examples._example_helpers.print_separator

### src.nlp2cmd.pipeline_runner_desktop.DesktopExecutionMixin._execute_desktop_plan_step
> Execute an ActionPlan step via local desktop automation.

Supports three backends:
- ydotool: works on Wayland (requires ydotoold daemon)
- xdotool: w
- **Calls**: self._resolve_plan_variables, str, self._detect_desktop_backend, ValueError, ValueError, str, str, int

### examples.09_online_drawing._old.03_adaptive_drawing.main
- **Calls**: argparse.ArgumentParser, parser.add_argument, parser.add_argument, parser.add_argument, parser.add_argument, parser.add_argument, parser.parse_args, examples._verbose_helper.init_verbose

### src.nlp2cmd.automation.action_planner.ActionPlanner._generate_rule_based_canvas_plan
> Generate a drawing plan for an arbitrary object using rules.

This is a fallback when LLM is not available. Uses object name to determine
shape compos
- **Calls**: re.search, None.strip, object_name.lower, any, ActionPlan, None.strip, ActionStep, ActionStep

### networkx-3.6.1-py3-none-any.networkx.utils.backends._dispatchable._call_if_any_backends_installed
> Returns the result of the original function, or the backend function if
the backend is specified and that backend implements `func`.
- **Calls**: self.graphs.items, nx.config.backend_priority.get, graph_backend_names.discard, self._will_call_mutate_input, src.nlp2cmd.executor.ExecutionContext.set, src.nlp2cmd.cli.commands.examples.ExamplesRegistry.list, enumerate, NotImplementedError

### examples.10_online_code_editors.01_codepen_live.main
- **Calls**: argparse.ArgumentParser, parser.add_argument, parser.add_argument, parser.add_argument, parser.add_argument, parser.add_argument, parser.add_argument, parser.add_argument

### examples.05_advanced_features.schema_driven_architecture.end_to_end_demo.main
- **Calls**: examples.05_advanced_features.schema_driven_architecture.end_to_end_demo.print_section, examples.05_advanced_features.schema_driven_architecture.end_to_end_demo.print_step, DecisionRouter, src.nlp2cmd.registry.get_registry, LLMPlanner, PlanExecutor, executor.register_handler, executor.register_handler

### src.nlp2cmd.web_schema.form_handler.FormHandler.detect_form_fields
> Detect all form fields on a page.

Args:
    page: Playwright page object

Returns:
    List of FormField objects
- **Calls**: page.query_selector_all, self._print_yaml, page.query_selector_all, self._print_yaml, page.query_selector_all, self._print_yaml, page.query_selector_all, self._print_yaml

### examples.10_online_code_editors.04_jsfiddle_frontend.main
- **Calls**: argparse.ArgumentParser, parser.add_argument, parser.add_argument, parser.add_argument, parser.add_argument, parser.add_argument, parser.parse_args, examples._verbose_helper.init_verbose

### examples.01_basics.sql_basics.workflows.main
- **Calls**: examples.01_basics.sql_basics.workflows.print_section, examples.01_basics.sql_basics.workflows.print_section, SQLAdapter, adapter.generate, src.nlp2cmd.pipeline_runner_utils._MarkdownConsoleWrapper.print, src.nlp2cmd.pipeline_runner_utils._MarkdownConsoleWrapper.print, src.nlp2cmd.pipeline_runner_utils._MarkdownConsoleWrapper.print, src.nlp2cmd.pipeline_runner_utils._MarkdownConsoleWrapper.print

### examples.04_domain_specific.debugging.validation.ShellCommandValidator.get_test_cases
> Zwróć listę przypadków testowych.
- **Calls**: CommandTest, CommandTest, CommandTest, CommandTest, CommandTest, CommandTest, CommandTest, CommandTest

### networkx-3.6.1-py3-none-any.networkx.algorithms.flow.networksimplex.network_simplex
> Find a minimum cost flow satisfying all demands in digraph G.

This is a primal network simplex algorithm that uses the leaving
arc rule to prevent cy
- **Calls**: networkx-3.6.1-py3-none-any.networkx.utils.decorators.not_implemented_for, nx._dispatchable, G.is_multigraph, _DataEssentialsAndFunctions, float, zip, zip, zip

### examples.01_basics.shell_fundamentals.feedback_loop.simulate_interactive_session
> Simulate an interactive session with feedback loop.
- **Calls**: examples._example_helpers.print_separator, SQLAdapter, FeedbackAnalyzer, SQLValidator, CorrectionEngine, NLP2CMD, examples._example_helpers.print_rule, src.nlp2cmd.pipeline_runner_utils._MarkdownConsoleWrapper.print

### examples.show_metrics.main
- **Calls**: argparse.ArgumentParser, parser.add_argument, parser.add_argument, parser.add_argument, parser.add_argument, parser.parse_args, src.nlp2cmd.orchestration.metrics.get_workspace, MetricsCollector

### src.nlp2cmd.web_schema.site_explorer.SiteExplorer.find_form
> Find a form on the website matching the intent.

Args:
    url: Starting URL (homepage)
    intent: Type of form to find (contact, search, newsletter,
- **Calls**: time.perf_counter, src.nlp2cmd.executor.ExecutionContext.set, self._find_best_form_candidate, ExplorationResult, None.start, p.chromium.launch, browser.new_context, context.new_page

### examples.03_integrations.toon_format.usage_example.main
> Demonstrate TOON usage
- **Calls**: src.nlp2cmd.pipeline_runner_utils._MarkdownConsoleWrapper.print, src.nlp2cmd.core.toon_integration.get_data_manager, src.nlp2cmd.pipeline_runner_utils._MarkdownConsoleWrapper.print, manager.get_project_metadata, src.nlp2cmd.pipeline_runner_utils._MarkdownConsoleWrapper.print, src.nlp2cmd.pipeline_runner_utils._MarkdownConsoleWrapper.print, src.nlp2cmd.pipeline_runner_utils._MarkdownConsoleWrapper.print, src.nlp2cmd.pipeline_runner_utils._MarkdownConsoleWrapper.print

### src.nlp2cmd.web_schema.site_explorer.SiteExplorer._analyze_page
> Analyze a page for forms, iframes, and links.
- **Calls**: PageInfo, self._score_page, src.nlp2cmd.executor.ExecutionContext.set, page.query_selector_all, page.query_selector_all, page.query_selector_all, self._normalize_url, page.title

### scripts.maintenance.refactoring_summary.print_summary
> Print a summary of the refactoring work completed.
- **Calls**: src.nlp2cmd.pipeline_runner_utils._MarkdownConsoleWrapper.print, src.nlp2cmd.pipeline_runner_utils._MarkdownConsoleWrapper.print, src.nlp2cmd.pipeline_runner_utils._MarkdownConsoleWrapper.print, src.nlp2cmd.pipeline_runner_utils._MarkdownConsoleWrapper.print, src.nlp2cmd.pipeline_runner_utils._MarkdownConsoleWrapper.print, src.nlp2cmd.pipeline_runner_utils._MarkdownConsoleWrapper.print, src.nlp2cmd.pipeline_runner_utils._MarkdownConsoleWrapper.print, src.nlp2cmd.pipeline_runner_utils._MarkdownConsoleWrapper.print

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

### Flow 3: les_miserables_graph
```
les_miserables_graph [networkx-3.6.1-py3-none-any.networkx.generators.social]
```

### Flow 4: execute_action_plan
```
execute_action_plan [src.nlp2cmd.pipeline_runner_plans.PlanExecutionMixin]
```

### Flow 5: execute_drawing_plan
```
execute_drawing_plan [src.nlp2cmd.adapters.canvas.CanvasAdapter]
```

### Flow 6: display
```
display [networkx-3.6.1-py3-none-any.networkx.drawing.nx_pylab]
```

### Flow 7: main
```
main [examples.01_basics.shell_fundamentals.environment_analysis]
  └─ →> print_separator
      └─ →> print
      └─ →> print
  └─ →> print_rule
      └─ →> print
  └─ →> print
```

### Flow 8: run_command
```
run_command [src.nlp2cmd.execution.runner.ExecutionRunner]
```

### Flow 9: _register_builtin_actions
```
_register_builtin_actions [src.nlp2cmd.registry.ActionRegistry]
```

### Flow 10: _convert_and_call_for_tests
```
_convert_and_call_for_tests [networkx-3.6.1-py3-none-any.networkx.utils.backends._dispatchable]
  └─ →> _load_backend
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

### src.nlp2cmd.schemas.SchemaRegistry
> Registry for file format schemas with validation and repair capabilities.
- **Methods**: 37
- **Key Methods**: src.nlp2cmd.schemas.SchemaRegistry.__init__, src.nlp2cmd.schemas.SchemaRegistry._register_builtin_schemas, src.nlp2cmd.schemas.SchemaRegistry.register, src.nlp2cmd.schemas.SchemaRegistry.get, src.nlp2cmd.schemas.SchemaRegistry.has_schema, src.nlp2cmd.schemas.SchemaRegistry.list_schemas, src.nlp2cmd.schemas.SchemaRegistry.unregister, src.nlp2cmd.schemas.SchemaRegistry.find_schema_for_file, src.nlp2cmd.schemas.SchemaRegistry.find_schema_by_mime_type, src.nlp2cmd.schemas.SchemaRegistry.find_extension_conflicts

### tools.schema.enhanced_schema_generator.EnhancedSchemaExtractor
> Enhanced schema extractor with multiple strategies.
- **Methods**: 36
- **Key Methods**: tools.schema.enhanced_schema_generator.EnhancedSchemaExtractor.__init__, tools.schema.enhanced_schema_generator.EnhancedSchemaExtractor.extract_schema, tools.schema.enhanced_schema_generator.EnhancedSchemaExtractor._select_strategy, tools.schema.enhanced_schema_generator.EnhancedSchemaExtractor._extract_with_strategy, tools.schema.enhanced_schema_generator.EnhancedSchemaExtractor._extract_from_help, tools.schema.enhanced_schema_generator.EnhancedSchemaExtractor._extract_from_man, tools.schema.enhanced_schema_generator.EnhancedSchemaExtractor._extract_with_llm, tools.schema.enhanced_schema_generator.EnhancedSchemaExtractor._extract_hybrid, tools.schema.enhanced_schema_generator.EnhancedSchemaExtractor._extract_from_patterns, tools.schema.enhanced_schema_generator.EnhancedSchemaExtractor._get_help_text

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

### src.nlp2cmd.web_schema.site_explorer.SiteExplorer
> Explores website to find forms, contact pages, and other content.

Usage:
    explorer = SiteExplore
- **Methods**: 28
- **Key Methods**: src.nlp2cmd.web_schema.site_explorer.SiteExplorer.__init__, src.nlp2cmd.web_schema.site_explorer.SiteExplorer._setup_resource_blocking, src.nlp2cmd.web_schema.site_explorer.SiteExplorer._resolve_platform_url, src.nlp2cmd.web_schema.site_explorer.SiteExplorer._goto_with_retry, src.nlp2cmd.web_schema.site_explorer.SiteExplorer._try_github_api, src.nlp2cmd.web_schema.site_explorer.SiteExplorer._detect_docs_framework, src.nlp2cmd.web_schema.site_explorer.SiteExplorer._record_timing, src.nlp2cmd.web_schema.site_explorer.SiteExplorer.get_timing_stats, src.nlp2cmd.web_schema.site_explorer.SiteExplorer._fallback_static_scrape, src.nlp2cmd.web_schema.site_explorer.SiteExplorer.find_content

### tools.schema.non_llm_schema_extractor.NonLLMSchemaExtractor
> Non-LLM schema extractor with multiple strategies.
- **Methods**: 27
- **Key Methods**: tools.schema.non_llm_schema_extractor.NonLLMSchemaExtractor.__init__, tools.schema.non_llm_schema_extractor.NonLLMSchemaExtractor.extract_schema, tools.schema.non_llm_schema_extractor.NonLLMSchemaExtractor._extract_with_strategy, tools.schema.non_llm_schema_extractor.NonLLMSchemaExtractor._extract_from_help, tools.schema.non_llm_schema_extractor.NonLLMSchemaExtractor._extract_from_man, tools.schema.non_llm_schema_extractor.NonLLMSchemaExtractor._extract_from_patterns, tools.schema.non_llm_schema_extractor.NonLLMSchemaExtractor._extract_from_templates, tools.schema.non_llm_schema_extractor.NonLLMSchemaExtractor._enhance_schema, tools.schema.non_llm_schema_extractor.NonLLMSchemaExtractor._evaluate_quality, tools.schema.non_llm_schema_extractor.NonLLMSchemaExtractor._create_fallback_schema

### src.nlp2cmd.core.toon_integration.ToonDataManager
> Unified data manager using TOON format
- **Methods**: 27
- **Key Methods**: src.nlp2cmd.core.toon_integration.ToonDataManager.__init__, src.nlp2cmd.core.toon_integration.ToonDataManager._ensure_loaded, src.nlp2cmd.core.toon_integration.ToonDataManager.get_all_commands, src.nlp2cmd.core.toon_integration.ToonDataManager.get_shell_commands, src.nlp2cmd.core.toon_integration.ToonDataManager.get_browser_commands, src.nlp2cmd.core.toon_integration.ToonDataManager.get_command_by_name, src.nlp2cmd.core.toon_integration.ToonDataManager.search_commands, src.nlp2cmd.core.toon_integration.ToonDataManager.get_config, src.nlp2cmd.core.toon_integration.ToonDataManager.get_llm_config, src.nlp2cmd.core.toon_integration.ToonDataManager.get_test_commands

### networkx-3.6.1-py3-none-any.networkx.utils.configs.Config
> The base class for NetworkX configuration.

There are two ways to use this to create configurations.
- **Methods**: 24
- **Key Methods**: networkx-3.6.1-py3-none-any.networkx.utils.configs.Config.__init_subclass__, networkx-3.6.1-py3-none-any.networkx.utils.configs.Config.__new__, networkx-3.6.1-py3-none-any.networkx.utils.configs.Config._on_setattr, networkx-3.6.1-py3-none-any.networkx.utils.configs.Config._on_delattr, networkx-3.6.1-py3-none-any.networkx.utils.configs.Config.__dir__, networkx-3.6.1-py3-none-any.networkx.utils.configs.Config.__setattr__, networkx-3.6.1-py3-none-any.networkx.utils.configs.Config.__delattr__, networkx-3.6.1-py3-none-any.networkx.utils.configs.Config.__contains__, networkx-3.6.1-py3-none-any.networkx.utils.configs.Config.__iter__, networkx-3.6.1-py3-none-any.networkx.utils.configs.Config.__len__

### tools.schema.comprehensive_command_scanner.ComprehensiveCommandScanner
> Scanner that extracts ALL command options.
- **Methods**: 23
- **Key Methods**: tools.schema.comprehensive_command_scanner.ComprehensiveCommandScanner.__init__, tools.schema.comprehensive_command_scanner.ComprehensiveCommandScanner.scan_command, tools.schema.comprehensive_command_scanner.ComprehensiveCommandScanner._parse_all_options, tools.schema.comprehensive_command_scanner.ComprehensiveCommandScanner._parse_options_from_text, tools.schema.comprehensive_command_scanner.ComprehensiveCommandScanner._parse_option_line, tools.schema.comprehensive_command_scanner.ComprehensiveCommandScanner._detect_option_type, tools.schema.comprehensive_command_scanner.ComprehensiveCommandScanner._detect_relationships, tools.schema.comprehensive_command_scanner.ComprehensiveCommandScanner._create_parameters_from_options, tools.schema.comprehensive_command_scanner.ComprehensiveCommandScanner._map_option_type_to_param_type, tools.schema.comprehensive_command_scanner.ComprehensiveCommandScanner._generate_comprehensive_examples

### src.nlp2cmd.core.core_transform.NLP2CMD
> Main class for Natural Language to Command transformation.

This class orchestrates the transformati
- **Methods**: 23
- **Key Methods**: src.nlp2cmd.core.core_transform.NLP2CMD.__init__, src.nlp2cmd.core.core_transform.NLP2CMD.transform, src.nlp2cmd.core.core_transform.NLP2CMD.transform_ir, src.nlp2cmd.core.core_transform.NLP2CMD._normalize_entities, src.nlp2cmd.core.core_transform.NLP2CMD._normalize_entities_sql, src.nlp2cmd.core.core_transform.NLP2CMD._normalize_entities_shell, src.nlp2cmd.core.core_transform.NLP2CMD._normalize_entities_docker, src.nlp2cmd.core.core_transform.NLP2CMD._normalize_entities_kubernetes, src.nlp2cmd.core.core_transform.NLP2CMD._normalize_entities_dql, src.nlp2cmd.core.core_transform.NLP2CMD._normalize_shell_entities

### src.nlp2cmd.evolutionary_orchestrator.EvolutionaryRecoveryEngine
> Silnik ewolucyjnych napraw - uczy się z każdej sytuacji.
- **Methods**: 22
- **Key Methods**: src.nlp2cmd.evolutionary_orchestrator.EvolutionaryRecoveryEngine.__init__, src.nlp2cmd.evolutionary_orchestrator.EvolutionaryRecoveryEngine._load_knowledge, src.nlp2cmd.evolutionary_orchestrator.EvolutionaryRecoveryEngine._save_knowledge, src.nlp2cmd.evolutionary_orchestrator.EvolutionaryRecoveryEngine._print, src.nlp2cmd.evolutionary_orchestrator.EvolutionaryRecoveryEngine.consult_llm_for_strategy, src.nlp2cmd.evolutionary_orchestrator.EvolutionaryRecoveryEngine._select_from_learned_patterns, src.nlp2cmd.evolutionary_orchestrator.EvolutionaryRecoveryEngine.execute_recovery, src.nlp2cmd.evolutionary_orchestrator.EvolutionaryRecoveryEngine._recover_install_dependency, src.nlp2cmd.evolutionary_orchestrator.EvolutionaryRecoveryEngine._recover_switch_fallback, src.nlp2cmd.evolutionary_orchestrator.EvolutionaryRecoveryEngine._recover_configure_env

### src.nlp2cmd.automation.action_planner.ActionPlanner
> Decomposes complex NL commands into ActionPlan via rules or LLM.

Costs:
- Rule match (known service
- **Methods**: 22
- **Key Methods**: src.nlp2cmd.automation.action_planner.ActionPlanner.__init__, src.nlp2cmd.automation.action_planner.ActionPlanner.decompose, src.nlp2cmd.automation.action_planner.ActionPlanner.decompose_sync, src.nlp2cmd.automation.action_planner.ActionPlanner._try_rule_decomposition, src.nlp2cmd.automation.action_planner.ActionPlanner._resolve_service, src.nlp2cmd.automation.action_planner.ActionPlanner._wants_new_tab, src.nlp2cmd.automation.action_planner.ActionPlanner._wants_existing_firefox, src.nlp2cmd.automation.action_planner.ActionPlanner._wants_create_key, src.nlp2cmd.automation.action_planner.ActionPlanner._build_navigation_steps, src.nlp2cmd.automation.action_planner.ActionPlanner._build_session_check_steps

### src.nlp2cmd.adapters.browser.BrowserAdapter
> Minimal adapter that turns NL into dom_dql.v1 navigation (Playwright).
- **Methods**: 22
- **Key Methods**: src.nlp2cmd.adapters.browser.BrowserAdapter.__init__, src.nlp2cmd.adapters.browser.BrowserAdapter._extract_url, src.nlp2cmd.adapters.browser.BrowserAdapter._extract_type_text, src.nlp2cmd.adapters.browser.BrowserAdapter._has_type_action, src.nlp2cmd.adapters.browser.BrowserAdapter._should_explore_for_content, src.nlp2cmd.adapters.browser.BrowserAdapter._should_explore_for_forms, src.nlp2cmd.adapters.browser.BrowserAdapter._has_fill_form_action, src.nlp2cmd.adapters.browser.BrowserAdapter._has_press_enter, src.nlp2cmd.adapters.browser.BrowserAdapter._has_form_action, src.nlp2cmd.adapters.browser.BrowserAdapter._has_submit_action
- **Inherits**: BaseDSLAdapter

### src.nlp2cmd.adapters.kubernetes.KubernetesAdapter
> Kubernetes adapter for kubectl commands and manifests.

Transforms natural language into kubectl com
- **Methods**: 22
- **Key Methods**: src.nlp2cmd.adapters.kubernetes.KubernetesAdapter.__init__, src.nlp2cmd.adapters.kubernetes.KubernetesAdapter._parse_cluster_context, src.nlp2cmd.adapters.kubernetes.KubernetesAdapter._normalize_resource, src.nlp2cmd.adapters.kubernetes.KubernetesAdapter.generate, src.nlp2cmd.adapters.kubernetes.KubernetesAdapter._generate_get, src.nlp2cmd.adapters.kubernetes.KubernetesAdapter._generate_describe, src.nlp2cmd.adapters.kubernetes.KubernetesAdapter._generate_apply, src.nlp2cmd.adapters.kubernetes.KubernetesAdapter._generate_delete, src.nlp2cmd.adapters.kubernetes.KubernetesAdapter._generate_scale, src.nlp2cmd.adapters.kubernetes.KubernetesAdapter._generate_logs
- **Inherits**: BaseDSLAdapter

### src.nlp2cmd.skills.drawing.skill.DrawingSkill
> Facade for the drawing skill — single entry point for all drawing operations.

Combines:
- CQRS (Com
- **Methods**: 21
- **Key Methods**: src.nlp2cmd.skills.drawing.skill.DrawingSkill.__init__, src.nlp2cmd.skills.drawing.skill.DrawingSkill.init_canvas, src.nlp2cmd.skills.drawing.skill.DrawingSkill.draw, src.nlp2cmd.skills.drawing.skill.DrawingSkill.set_color, src.nlp2cmd.skills.drawing.skill.DrawingSkill.select_tool, src.nlp2cmd.skills.drawing.skill.DrawingSkill.clear, src.nlp2cmd.skills.drawing.skill.DrawingSkill.execute_nl, src.nlp2cmd.skills.drawing.skill.DrawingSkill.detect_shape, src.nlp2cmd.skills.drawing.skill.DrawingSkill.detect_color, src.nlp2cmd.skills.drawing.skill.DrawingSkill.get_state

### networkx-3.6.1-py3-none-any.networkx.classes.multigraph.MultiGraph
> An undirected graph class that can store multiedges.

Multiedges are multiple edges between two node
- **Methods**: 20
- **Key Methods**: networkx-3.6.1-py3-none-any.networkx.classes.multigraph.MultiGraph.to_directed_class, networkx-3.6.1-py3-none-any.networkx.classes.multigraph.MultiGraph.to_undirected_class, networkx-3.6.1-py3-none-any.networkx.classes.multigraph.MultiGraph.__new__, networkx-3.6.1-py3-none-any.networkx.classes.multigraph.MultiGraph.__init__, networkx-3.6.1-py3-none-any.networkx.classes.multigraph.MultiGraph.adj, networkx-3.6.1-py3-none-any.networkx.classes.multigraph.MultiGraph.new_edge_key, networkx-3.6.1-py3-none-any.networkx.classes.multigraph.MultiGraph.add_edge, networkx-3.6.1-py3-none-any.networkx.classes.multigraph.MultiGraph.add_edges_from, networkx-3.6.1-py3-none-any.networkx.classes.multigraph.MultiGraph.remove_edge, networkx-3.6.1-py3-none-any.networkx.classes.multigraph.MultiGraph.remove_edges_from
- **Inherits**: Graph

### networkx-3.6.1-py3-none-any.networkx.algorithms.planarity.PlanarEmbedding
> Represents a planar graph with its planar embedding.

The planar embedding is given by a `combinator
- **Methods**: 20
- **Key Methods**: networkx-3.6.1-py3-none-any.networkx.algorithms.planarity.PlanarEmbedding.__init__, networkx-3.6.1-py3-none-any.networkx.algorithms.planarity.PlanarEmbedding._forbidden, networkx-3.6.1-py3-none-any.networkx.algorithms.planarity.PlanarEmbedding.get_data, networkx-3.6.1-py3-none-any.networkx.algorithms.planarity.PlanarEmbedding.set_data, networkx-3.6.1-py3-none-any.networkx.algorithms.planarity.PlanarEmbedding.remove_node, networkx-3.6.1-py3-none-any.networkx.algorithms.planarity.PlanarEmbedding.remove_nodes_from, networkx-3.6.1-py3-none-any.networkx.algorithms.planarity.PlanarEmbedding.neighbors_cw_order, networkx-3.6.1-py3-none-any.networkx.algorithms.planarity.PlanarEmbedding.add_half_edge, networkx-3.6.1-py3-none-any.networkx.algorithms.planarity.PlanarEmbedding.check_structure, networkx-3.6.1-py3-none-any.networkx.algorithms.planarity.PlanarEmbedding.add_half_edge_ccw
- **Inherits**: nx.DiGraph

## Data Transformation Functions

Key functions that process and transform data:

### demos.demo_intelligent_nlp2cmd.IntelligentNLP2CMD.transform
> Transform natural language to command with version detection.

Args:
    query: Natural language que
- **Output to**: ActionIR, self.base_nlp.transform_ir, self.generator.generate_command, ActionIR, src.nlp2cmd.pipeline_runner_utils._MarkdownConsoleWrapper.print

### networkx-3.6.1-py3-none-any.networkx.relabel.convert_node_labels_to_integers
> Returns a copy of the graph G with the nodes relabeled using
consecutive integers.

Parameters
-----
- **Output to**: nx._dispatchable, networkx-3.6.1-py3-none-any.networkx.relabel.relabel_nodes, G.number_of_nodes, dict, nx.set_node_attributes

### networkx-3.6.1-py3-none-any.networkx.readwrite.p2g.parse_p2g
> Parse p2g format graph from string or iterable.

Returns
-------
MultiDiGraph
- **Output to**: nx._dispatchable, None.strip, nx.MultiDiGraph, map, range

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

### networkx-3.6.1-py3-none-any.networkx.readwrite.graphml.parse_graphml
> Read graph in GraphML format from string.

Parameters
----------
graphml_string : string
   String c
- **Output to**: nx._dispatchable, GraphMLReader, src.nlp2cmd.cli.commands.examples.ExamplesRegistry.list, reader, len

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

### networkx-3.6.1-py3-none-any.networkx.readwrite.gexf.GEXFWriter.alter_graph_mode_timeformat
- **Output to**: isinstance, self.graph_element.set, isinstance, self.graph_element.get, self.graph_element.set

### networkx-3.6.1-py3-none-any.networkx.readwrite.gexf.GEXFReader.decode_attr_elements
- **Output to**: obj_xml.find, attr_element.findall, a.get, a.get, nx.NetworkXError

### networkx-3.6.1-py3-none-any.networkx.readwrite.edgelist.parse_edgelist
> Parse lines of an edge list representation of a graph.

Parameters
----------
lines : list or iterat
- **Output to**: nx._dispatchable, nx.empty_graph, None.split, s.pop, s.pop

### networkx-3.6.1-py3-none-any.networkx.readwrite.text._parse_network_text
> Reconstructs a graph from a network text representation.

This is mainly used for testing.  Network 
- **Output to**: iter, src.nlp2cmd.executor.ExecutionContext.set, src.nlp2cmd.executor.ExecutionContext.set, chain, object

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

### networkx-3.6.1-py3-none-any.networkx.readwrite.sparse6.read_sparse6
> Read an undirected graph in sparse6 format from path.

Parameters
----------
path : file or string
 
- **Output to**: networkx-3.6.1-py3-none-any.networkx.utils.decorators.open_file, nx._dispatchable, line.strip, glist.append, len

### networkx-3.6.1-py3-none-any.networkx.readwrite.sparse6.write_sparse6
> Write graph G to given path in sparse6 format.

Parameters
----------
G : Graph (undirected)

path :
- **Output to**: networkx-3.6.1-py3-none-any.networkx.utils.decorators.not_implemented_for, networkx-3.6.1-py3-none-any.networkx.utils.decorators.open_file, nx.convert_node_labels_to_integers, networkx-3.6.1-py3-none-any.networkx.readwrite.sparse6._generate_sparse6_bytes, G.subgraph

### networkx-3.6.1-py3-none-any.networkx.readwrite.multiline_adjlist.parse_multiline_adjlist
> Parse lines of a multiline adjacency list representation of a graph.

Parameters
----------
lines : 
- **Output to**: nx._dispatchable, nx.empty_graph, line.find, G.add_node, range

### networkx-3.6.1-py3-none-any.networkx.readwrite.gml.parse_gml
> Parse GML graph from a string or iterable.

Parameters
----------
lines : string or iterable of stri
- **Output to**: nx._dispatchable, networkx-3.6.1-py3-none-any.networkx.readwrite.gml.parse_gml_lines, isinstance, isinstance, filter_lines

### networkx-3.6.1-py3-none-any.networkx.readwrite.gml.parse_gml_lines
> Parse GML `lines` into a graph.
- **Output to**: src.nlp2cmd.nlp.normalizer.tokenize, parse_graph, graph.pop, graph.pop, G.graph.update

### networkx-3.6.1-py3-none-any.networkx.utils.configs.Config._deserialize
- **Output to**: cls

### networkx-3.6.1-py3-none-any.networkx.utils.backends._dispatchable._can_convert
- **Output to**: graph_backend_names.issubset, _logger.debug

### networkx-3.6.1-py3-none-any.networkx.utils.backends._dispatchable._convert_arguments
> Convert graph arguments to the specified backend.

Returns
-------
args tuple and kwargs dict
- **Output to**: self.__signature__.bind, bound.apply_defaults, isinstance, isinstance, isinstance

## Behavioral Patterns

### recursion_subgraph
- **Type**: recursion
- **Confidence**: 0.90
- **Functions**: networkx-3.6.1-py3-none-any.networkx.classes.graph.Graph.subgraph

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

### recursion_hamiltonian_path
- **Type**: recursion
- **Confidence**: 0.90
- **Functions**: networkx-3.6.1-py3-none-any.networkx.algorithms.tournament.hamiltonian_path

### recursion_compile
- **Type**: recursion
- **Confidence**: 0.90
- **Functions**: networkx-3.6.1-py3-none-any.networkx.utils.decorators.argmap.compile

### recursion_ramsey_R2
- **Type**: recursion
- **Confidence**: 0.90
- **Functions**: networkx-3.6.1-py3-none-any.networkx.algorithms.approximation.ramsey.ramsey_R2

### recursion_k_edge_subgraphs
- **Type**: recursion
- **Confidence**: 0.90
- **Functions**: networkx-3.6.1-py3-none-any.networkx.algorithms.connectivity.edge_kcomponents.EdgeComponentAuxGraph.k_edge_subgraphs

### recursion_procedure_P
- **Type**: recursion
- **Confidence**: 0.90
- **Functions**: networkx-3.6.1-py3-none-any.networkx.algorithms.coloring.equitable_coloring.procedure_P

### recursion__dfbnb
- **Type**: recursion
- **Confidence**: 0.90
- **Functions**: networkx-3.6.1-py3-none-any.networkx.algorithms.centrality.group._dfbnb

### recursion__debug
- **Type**: recursion
- **Confidence**: 0.90
- **Functions**: src.nlp2cmd.dom_actions.base.DomAction._debug

### recursion__debug
- **Type**: recursion
- **Confidence**: 0.90
- **Functions**: src.nlp2cmd.step_handlers.base.StepHandler._debug

### recursion_list
- **Type**: recursion
- **Confidence**: 0.90
- **Functions**: src.nlp2cmd.cli.commands.examples.ExamplesRegistry.list

## Public API Surface

Functions exposed as public API (no underscore prefix):

- `src.nlp2cmd.cli.commands.run.handle_run_mode` - 261 calls
- `networkx-3.6.1-py3-none-any.networkx.generators.social.les_miserables_graph` - 256 calls
- `src.nlp2cmd.pipeline_runner_plans.PlanExecutionMixin.execute_action_plan` - 219 calls
- `src.nlp2cmd.adapters.canvas.CanvasAdapter.execute_drawing_plan` - 193 calls
- `networkx-3.6.1-py3-none-any.networkx.drawing.nx_pylab.display` - 188 calls
- `networkx-3.6.1-py3-none-any.networkx.algorithms.similarity.optimize_edit_paths` - 168 calls
- `networkx-3.6.1-py3-none-any.networkx.algorithms.matching.max_weight_matching` - 150 calls
- `examples.01_basics.shell_fundamentals.environment_analysis.main` - 139 calls
- `examples.10_online_code_editors.03_adaptive_code.main` - 133 calls
- `examples.10_online_code_editors.02_mycompiler_run.main` - 116 calls
- `src.nlp2cmd.cli.main.main` - 115 calls
- `src.nlp2cmd.execution.runner.ExecutionRunner.run_command` - 109 calls
- `examples.03_integrations.web_development.demo.demo_nlp_commands` - 106 calls
- `docker.novnc.demos.demo_desktop_gui.run_demo` - 103 calls
- `examples.03_integrations.web_development.demo_batch.run_batch_demo` - 95 calls
- `examples.09_online_drawing._old.03_adaptive_drawing.main` - 93 calls
- `networkx-3.6.1-py3-none-any.networkx.readwrite.gml.parse_gml_lines` - 92 calls
- `networkx-3.6.1-py3-none-any.networkx.algorithms.tree.branchings.maximum_branching` - 89 calls
- `examples.10_online_code_editors.01_codepen_live.main` - 87 calls
- `examples.05_advanced_features.schema_driven_architecture.end_to_end_demo.main` - 87 calls
- `src.nlp2cmd.generation.train_model.train_all_models` - 86 calls
- `src.nlp2cmd.web_schema.form_handler.FormHandler.detect_form_fields` - 83 calls
- `examples.10_online_code_editors.04_jsfiddle_frontend.main` - 82 calls
- `examples.01_basics.sql_basics.workflows.main` - 81 calls
- `examples.04_domain_specific.debugging.validation.ShellCommandValidator.get_test_cases` - 79 calls
- `networkx-3.6.1-py3-none-any.networkx.algorithms.flow.networksimplex.network_simplex` - 78 calls
- `examples.01_basics.shell_fundamentals.feedback_loop.simulate_interactive_session` - 78 calls
- `examples.show_metrics.main` - 77 calls
- `src.nlp2cmd.web_schema.site_explorer.SiteExplorer.find_form` - 77 calls
- `examples.03_integrations.toon_format.usage_example.main` - 77 calls
- `networkx-3.6.1-py3-none-any.networkx.drawing.nx_pylab.draw_networkx_edges` - 76 calls
- `scripts.maintenance.refactoring_summary.print_summary` - 72 calls
- `networkx-3.6.1-py3-none-any.networkx.algorithms.approximation.traveling_salesman.held_karp_ascent` - 70 calls
- `src.app2schema.extract.extract_schema` - 70 calls
- `networkx-3.6.1-py3-none-any.networkx.drawing.nx_pylab.draw_networkx_edge_labels` - 69 calls
- `examples.03_integrations.validation.config_validation.main` - 68 calls
- `demos.demo_version_detection.demonstrate_version_detection` - 67 calls
- `networkx-3.6.1-py3-none-any.networkx.algorithms.flow.preflowpush.preflow_push_impl` - 67 calls
- `src.nlp2cmd.adapters.browser.BrowserAdapter.generate` - 66 calls
- `src.nlp2cmd.cli.commands.generate.handle_generate_query` - 66 calls

## System Interactions

How components interact:

```mermaid
graph TD
    _execute_plan_step --> _resolve_plan_variab
    _execute_plan_step --> Console
    _execute_plan_step --> print
    _execute_plan_step --> has_handler
    _execute_plan_step --> get
    _run_dom_multi_actio --> get
    _run_dom_multi_actio --> Console
    _run_dom_multi_actio --> _MarkdownConsoleWrap
    _run_dom_multi_actio --> RunnerResult
    les_miserables_graph --> _dispatchable
    les_miserables_graph --> Graph
    les_miserables_graph --> add_edge
    execute_action_plan --> Console
    execute_action_plan --> _detect_desktop_step
    execute_action_plan --> print
    execute_action_plan --> enumerate
    execute_drawing_plan --> get
    execute_drawing_plan --> MouseController
    execute_drawing_plan --> enumerate
    execute_drawing_plan --> loads
    display --> get
    display --> isinstance
    display --> subgraph
    main --> print_separator
    main --> EnvironmentAnalyzer
    main --> print_rule
    main --> print
    main --> ArgumentParser
    main --> add_argument
    run_command --> time
```

## Reverse Engineering Guidelines

1. **Entry Points**: Start analysis from the entry points listed above
2. **Core Logic**: Focus on classes with many methods
3. **Data Flow**: Follow data transformation functions
4. **Process Flows**: Use the flow diagrams for execution paths
5. **API Surface**: Public API functions reveal the interface

## Context for LLM

Maintain the identified architectural patterns and public API surface when suggesting changes.