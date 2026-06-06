# System Architecture Analysis
<!-- generated in 0.02s -->

## Overview

- **Project**: /home/tom/github/wronai/nlp2cmd
- **Primary Language**: python
- **Languages**: python: 1450, md: 233, json: 215, shell: 135, yaml: 32
- **Analysis Mode**: static
- **Total Functions**: 3912
- **Total Classes**: 747
- **Modules**: 2090
- **Entry Points**: 0

## Architecture by Module

### src.nlp2cmd.generation.template_generator
- **Functions**: 100
- **Classes**: 2
- **File**: `template_generator.py`

### nlp2cmd.generation.template_generator
- **Functions**: 100
- **Classes**: 2
- **File**: `template_generator.py`

### src.nlp2cmd.web_schema.form_data_loader
- **Functions**: 47
- **Classes**: 1
- **File**: `form_data_loader.py`

### nlp2cmd.web_schema.form_data_loader
- **Functions**: 47
- **Classes**: 1
- **File**: `form_data_loader.py`

### src.nlp2cmd.schemas
- **Functions**: 43
- **Classes**: 2
- **File**: `__init__.py`

### nlp2cmd.schemas
- **Functions**: 43
- **Classes**: 2
- **File**: `__init__.py`

### tools.schema.enhanced_schema_generator
- **Functions**: 37
- **Classes**: 3
- **File**: `enhanced_schema_generator.py`

### src.nlp2cmd.web_schema.site_explorer
- **Functions**: 34
- **Classes**: 3
- **File**: `site_explorer.py`

### nlp2cmd.web_schema.site_explorer
- **Functions**: 34
- **Classes**: 3
- **File**: `site_explorer.py`

### src.nlp2cmd.vql.schema.program
- **Functions**: 32
- **Classes**: 12
- **File**: `program.py`

### src.nlp2cmd.core.toon_integration
- **Functions**: 32
- **Classes**: 1
- **File**: `toon_integration.py`

### nlp2cmd.core.toon_integration
- **Functions**: 32
- **Classes**: 1
- **File**: `toon_integration.py`

### nlp2cmd.vql.schema.program
- **Functions**: 32
- **Classes**: 12
- **File**: `program.py`

### examples.03_integrations.web_development.nlp2_cmd_web_controller
- **Functions**: 30
- **Classes**: 1
- **File**: `nlp2_cmd_web_controller.py`

### src.nlp2cmd.generation.semantic_matcher_optimized
- **Functions**: 30
- **Classes**: 3
- **File**: `semantic_matcher_optimized.py`

### nlp2cmd.generation.semantic_matcher_optimized
- **Functions**: 30
- **Classes**: 3
- **File**: `semantic_matcher_optimized.py`

### 03_integrations.web_development.nlp2_cmd_web_controller
- **Functions**: 30
- **Classes**: 1
- **File**: `nlp2_cmd_web_controller.py`

### examples.09_online_drawing._run_utils
- **Functions**: 29
- **Classes**: 2
- **File**: `_run_utils.py`

### 09_online_drawing._run_utils
- **Functions**: 29
- **Classes**: 2
- **File**: `_run_utils.py`

### src.nlp2cmd.generation.data_loader
- **Functions**: 28
- **Classes**: 3
- **File**: `data_loader.py`

## Key Entry Points

Main execution flows into the system:

## Process Flows

Key execution flows identified:

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

### src.nlp2cmd.schemas.SchemaRegistry
> Registry for file format schemas with validation and repair capabilities.
- **Methods**: 37
- **Key Methods**: src.nlp2cmd.schemas.SchemaRegistry.__init__, src.nlp2cmd.schemas.SchemaRegistry._register_builtin_schemas, src.nlp2cmd.schemas.SchemaRegistry.register, src.nlp2cmd.schemas.SchemaRegistry.get, src.nlp2cmd.schemas.SchemaRegistry.has_schema, src.nlp2cmd.schemas.SchemaRegistry.list_schemas, src.nlp2cmd.schemas.SchemaRegistry.unregister, src.nlp2cmd.schemas.SchemaRegistry.find_schema_for_file, src.nlp2cmd.schemas.SchemaRegistry.find_schema_by_mime_type, src.nlp2cmd.schemas.SchemaRegistry.find_extension_conflicts

### tools.schema.enhanced_schema_generator.EnhancedSchemaExtractor
> Enhanced schema extractor with multiple strategies.
- **Methods**: 36
- **Key Methods**: tools.schema.enhanced_schema_generator.EnhancedSchemaExtractor.__init__, tools.schema.enhanced_schema_generator.EnhancedSchemaExtractor.extract_schema, tools.schema.enhanced_schema_generator.EnhancedSchemaExtractor._select_strategy, tools.schema.enhanced_schema_generator.EnhancedSchemaExtractor._extract_with_strategy, tools.schema.enhanced_schema_generator.EnhancedSchemaExtractor._extract_from_help, tools.schema.enhanced_schema_generator.EnhancedSchemaExtractor._extract_from_man, tools.schema.enhanced_schema_generator.EnhancedSchemaExtractor._extract_with_llm, tools.schema.enhanced_schema_generator.EnhancedSchemaExtractor._extract_hybrid, tools.schema.enhanced_schema_generator.EnhancedSchemaExtractor._extract_from_patterns, tools.schema.enhanced_schema_generator.EnhancedSchemaExtractor._get_help_text

### examples.03_integrations.web_development.nlp2_cmd_web_controller.NLP2CMDWebController
> Main controller for NLP2CMD-powered web infrastructure.

This class orchestrates the deployment and 
- **Methods**: 30
- **Key Methods**: examples.03_integrations.web_development.nlp2_cmd_web_controller.NLP2CMDWebController.__init__, examples.03_integrations.web_development.nlp2_cmd_web_controller.NLP2CMDWebController.execute, examples.03_integrations.web_development.nlp2_cmd_web_controller.NLP2CMDWebController._handle_deploy, examples.03_integrations.web_development.nlp2_cmd_web_controller.NLP2CMDWebController._handle_configure, examples.03_integrations.web_development.nlp2_cmd_web_controller.NLP2CMDWebController._handle_scale, examples.03_integrations.web_development.nlp2_cmd_web_controller.NLP2CMDWebController._handle_status, examples.03_integrations.web_development.nlp2_cmd_web_controller.NLP2CMDWebController._handle_stop, examples.03_integrations.web_development.nlp2_cmd_web_controller.NLP2CMDWebController._handle_unknown, examples.03_integrations.web_development.nlp2_cmd_web_controller.NLP2CMDWebController._execute_with_nlp2cmd, examples.03_integrations.web_development.nlp2_cmd_web_controller.NLP2CMDWebController._try_llm_fallback

### src.nlp2cmd.web_schema.site_explorer.SiteExplorer
> Explores website to find forms, contact pages, and other content.

Usage:
    explorer = SiteExplore
- **Methods**: 28
- **Key Methods**: src.nlp2cmd.web_schema.site_explorer.SiteExplorer.__init__, src.nlp2cmd.web_schema.site_explorer.SiteExplorer._setup_resource_blocking, src.nlp2cmd.web_schema.site_explorer.SiteExplorer._resolve_platform_url, src.nlp2cmd.web_schema.site_explorer.SiteExplorer._goto_with_retry, src.nlp2cmd.web_schema.site_explorer.SiteExplorer._try_github_api, src.nlp2cmd.web_schema.site_explorer.SiteExplorer._detect_docs_framework, src.nlp2cmd.web_schema.site_explorer.SiteExplorer._record_timing, src.nlp2cmd.web_schema.site_explorer.SiteExplorer.get_timing_stats, src.nlp2cmd.web_schema.site_explorer.SiteExplorer._fallback_static_scrape, src.nlp2cmd.web_schema.site_explorer.SiteExplorer.find_content

### src.nlp2cmd.core.toon_integration.ToonDataManager
> Unified data manager using TOON format
- **Methods**: 27
- **Key Methods**: src.nlp2cmd.core.toon_integration.ToonDataManager.__init__, src.nlp2cmd.core.toon_integration.ToonDataManager._ensure_loaded, src.nlp2cmd.core.toon_integration.ToonDataManager.get_all_commands, src.nlp2cmd.core.toon_integration.ToonDataManager.get_shell_commands, src.nlp2cmd.core.toon_integration.ToonDataManager.get_browser_commands, src.nlp2cmd.core.toon_integration.ToonDataManager.get_command_by_name, src.nlp2cmd.core.toon_integration.ToonDataManager.search_commands, src.nlp2cmd.core.toon_integration.ToonDataManager.get_config, src.nlp2cmd.core.toon_integration.ToonDataManager.get_llm_config, src.nlp2cmd.core.toon_integration.ToonDataManager.get_test_commands

### src.nlp2cmd.adapters.browser.BrowserAdapter
> Minimal adapter that turns NL into dom_dql.v1 navigation (Playwright).
- **Methods**: 27
- **Key Methods**: src.nlp2cmd.adapters.browser.BrowserAdapter.get_form_data_loader, src.nlp2cmd.adapters.browser.BrowserAdapter.__init__, src.nlp2cmd.adapters.browser.BrowserAdapter.site_explorer, src.nlp2cmd.adapters.browser.BrowserAdapter.site_explorer, src.nlp2cmd.adapters.browser.BrowserAdapter.form_data_loader, src.nlp2cmd.adapters.browser.BrowserAdapter.form_data_loader, src.nlp2cmd.adapters.browser.BrowserAdapter._extract_url, src.nlp2cmd.adapters.browser.BrowserAdapter._extract_type_text, src.nlp2cmd.adapters.browser.BrowserAdapter._has_type_action, src.nlp2cmd.adapters.browser.BrowserAdapter._should_explore_for_content
- **Inherits**: BaseDSLAdapter

### tools.schema.non_llm_schema_extractor.NonLLMSchemaExtractor
> Non-LLM schema extractor with multiple strategies.
- **Methods**: 27
- **Key Methods**: tools.schema.non_llm_schema_extractor.NonLLMSchemaExtractor.__init__, tools.schema.non_llm_schema_extractor.NonLLMSchemaExtractor.extract_schema, tools.schema.non_llm_schema_extractor.NonLLMSchemaExtractor._extract_with_strategy, tools.schema.non_llm_schema_extractor.NonLLMSchemaExtractor._extract_from_help, tools.schema.non_llm_schema_extractor.NonLLMSchemaExtractor._extract_from_man, tools.schema.non_llm_schema_extractor.NonLLMSchemaExtractor._extract_from_patterns, tools.schema.non_llm_schema_extractor.NonLLMSchemaExtractor._extract_from_templates, tools.schema.non_llm_schema_extractor.NonLLMSchemaExtractor._enhance_schema, tools.schema.non_llm_schema_extractor.NonLLMSchemaExtractor._evaluate_quality, tools.schema.non_llm_schema_extractor.NonLLMSchemaExtractor._create_fallback_schema

### src.nlp2cmd.core.core_transform.NLP2CMD
> Main class for Natural Language to Command transformation.

This class orchestrates the transformati
- **Methods**: 23
- **Key Methods**: src.nlp2cmd.core.core_transform.NLP2CMD.__init__, src.nlp2cmd.core.core_transform.NLP2CMD.transform, src.nlp2cmd.core.core_transform.NLP2CMD.transform_ir, src.nlp2cmd.core.core_transform.NLP2CMD._normalize_entities, src.nlp2cmd.core.core_transform.NLP2CMD._normalize_entities_sql, src.nlp2cmd.core.core_transform.NLP2CMD._normalize_entities_shell, src.nlp2cmd.core.core_transform.NLP2CMD._normalize_entities_docker, src.nlp2cmd.core.core_transform.NLP2CMD._normalize_entities_kubernetes, src.nlp2cmd.core.core_transform.NLP2CMD._normalize_entities_dql, src.nlp2cmd.core.core_transform.NLP2CMD._normalize_shell_entities

### tools.schema.comprehensive_command_scanner.ComprehensiveCommandScanner
> Scanner that extracts ALL command options.
- **Methods**: 23
- **Key Methods**: tools.schema.comprehensive_command_scanner.ComprehensiveCommandScanner.__init__, tools.schema.comprehensive_command_scanner.ComprehensiveCommandScanner.scan_command, tools.schema.comprehensive_command_scanner.ComprehensiveCommandScanner._parse_all_options, tools.schema.comprehensive_command_scanner.ComprehensiveCommandScanner._parse_options_from_text, tools.schema.comprehensive_command_scanner.ComprehensiveCommandScanner._parse_option_line, tools.schema.comprehensive_command_scanner.ComprehensiveCommandScanner._detect_option_type, tools.schema.comprehensive_command_scanner.ComprehensiveCommandScanner._detect_relationships, tools.schema.comprehensive_command_scanner.ComprehensiveCommandScanner._create_parameters_from_options, tools.schema.comprehensive_command_scanner.ComprehensiveCommandScanner._map_option_type_to_param_type, tools.schema.comprehensive_command_scanner.ComprehensiveCommandScanner._generate_comprehensive_examples

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

### src.nlp2cmd.generation.semantic_matcher_optimized.OptimizedSemanticMatcher
> Optimized semantic similarity matcher using sentence embeddings.

Features:
- Handles typos and para
- **Methods**: 20
- **Key Methods**: src.nlp2cmd.generation.semantic_matcher_optimized.OptimizedSemanticMatcher.__init__, src.nlp2cmd.generation.semantic_matcher_optimized.OptimizedSemanticMatcher._preload_models, src.nlp2cmd.generation.semantic_matcher_optimized.OptimizedSemanticMatcher._get_model, src.nlp2cmd.generation.semantic_matcher_optimized.OptimizedSemanticMatcher._get_polish_model, src.nlp2cmd.generation.semantic_matcher_optimized.OptimizedSemanticMatcher._load_model, src.nlp2cmd.generation.semantic_matcher_optimized.OptimizedSemanticMatcher.add_intent, src.nlp2cmd.generation.semantic_matcher_optimized.OptimizedSemanticMatcher.add_intents_batch, src.nlp2cmd.generation.semantic_matcher_optimized.OptimizedSemanticMatcher._encode_text, src.nlp2cmd.generation.semantic_matcher_optimized.OptimizedSemanticMatcher._encode_batch, src.nlp2cmd.generation.semantic_matcher_optimized.OptimizedSemanticMatcher._encode_with_cache

### src.nlp2cmd.generation.evolutionary_cache.EvolutionaryCache
> Manages the .nlp2cmd/ learned schema cache.

Usage:
    cache = EvolutionaryCache()
    result = cac
- **Methods**: 20
- **Key Methods**: src.nlp2cmd.generation.evolutionary_cache.EvolutionaryCache.__init__, src.nlp2cmd.generation.evolutionary_cache.EvolutionaryCache._ensure_dir, src.nlp2cmd.generation.evolutionary_cache.EvolutionaryCache._load, src.nlp2cmd.generation.evolutionary_cache.EvolutionaryCache.save, src.nlp2cmd.generation.evolutionary_cache.EvolutionaryCache.lookup, src.nlp2cmd.generation.evolutionary_cache.EvolutionaryCache._ask_teacher, src.nlp2cmd.generation.evolutionary_cache.EvolutionaryCache._clean, src.nlp2cmd.generation.evolutionary_cache.EvolutionaryCache._try_template_pipeline, src.nlp2cmd.generation.evolutionary_cache.EvolutionaryCache._try_english_pipeline, src.nlp2cmd.generation.evolutionary_cache.EvolutionaryCache._try_polish_template

### src.nlp2cmd.parsing.toon_parser.ToonParser
> Unified TOON format parser with hierarchical access
- **Methods**: 20
- **Key Methods**: src.nlp2cmd.parsing.toon_parser.ToonParser.__init__, src.nlp2cmd.parsing.toon_parser.ToonParser.parse_file, src.nlp2cmd.parsing.toon_parser.ToonParser.parse_content, src.nlp2cmd.parsing.toon_parser.ToonParser._parse_lines, src.nlp2cmd.parsing.toon_parser.ToonParser._parse_array_node, src.nlp2cmd.parsing.toon_parser.ToonParser._parse_object_node, src.nlp2cmd.parsing.toon_parser.ToonParser._parse_key_value, src.nlp2cmd.parsing.toon_parser.ToonParser._parse_value, src.nlp2cmd.parsing.toon_parser.ToonParser._extract_categories, src.nlp2cmd.parsing.toon_parser.ToonParser.get_category

### src.nlp2cmd.automation.step_validator.StepValidator
> Validates pre/post conditions for ActionPlan steps.

Checks clipboard state, DOM elements, environme
- **Methods**: 19
- **Key Methods**: src.nlp2cmd.automation.step_validator.StepValidator.__init__, src.nlp2cmd.automation.step_validator.StepValidator.metrics, src.nlp2cmd.automation.step_validator.StepValidator.start_step, src.nlp2cmd.automation.step_validator.StepValidator.finish_step, src.nlp2cmd.automation.step_validator.StepValidator.get_clipboard, src.nlp2cmd.automation.step_validator.StepValidator.set_clipboard, src.nlp2cmd.automation.step_validator.StepValidator.snapshot_clipboard, src.nlp2cmd.automation.step_validator.StepValidator.clipboard_changed, src.nlp2cmd.automation.step_validator.StepValidator.validate_pre_navigate, src.nlp2cmd.automation.step_validator.StepValidator.validate_pre_check_session

### src.nlp2cmd.automation.mouse_controller.MouseController
> Advanced mouse control via Playwright with human-like movements.

Supports:
- Click, double-click, r
- **Methods**: 19
- **Key Methods**: src.nlp2cmd.automation.mouse_controller.MouseController.__init__, src.nlp2cmd.automation.mouse_controller.MouseController._jitter, src.nlp2cmd.automation.mouse_controller.MouseController._human_delay, src.nlp2cmd.automation.mouse_controller.MouseController.click, src.nlp2cmd.automation.mouse_controller.MouseController.double_click, src.nlp2cmd.automation.mouse_controller.MouseController.right_click, src.nlp2cmd.automation.mouse_controller.MouseController.move_to, src.nlp2cmd.automation.mouse_controller.MouseController.drag, src.nlp2cmd.automation.mouse_controller.MouseController._compute_bezier, src.nlp2cmd.automation.mouse_controller.MouseController.bezier_move

### src.nlp2cmd.generation.fuzzy_schema_matcher_class.FuzzySchemaMatcher
> Language-agnostic fuzzy matcher using JSON schemas.

Works with any language by using character-leve
- **Methods**: 19
- **Key Methods**: src.nlp2cmd.generation.fuzzy_schema_matcher_class.FuzzySchemaMatcher.__init__, src.nlp2cmd.generation.fuzzy_schema_matcher_class.FuzzySchemaMatcher.load_schema, src.nlp2cmd.generation.fuzzy_schema_matcher_class.FuzzySchemaMatcher.add_phrase, src.nlp2cmd.generation.fuzzy_schema_matcher_class.FuzzySchemaMatcher.add_phrases_from_dict, src.nlp2cmd.generation.fuzzy_schema_matcher_class.FuzzySchemaMatcher._build_index, src.nlp2cmd.generation.fuzzy_schema_matcher_class.FuzzySchemaMatcher._index_phrase, src.nlp2cmd.generation.fuzzy_schema_matcher_class.FuzzySchemaMatcher._normalize, src.nlp2cmd.generation.fuzzy_schema_matcher_class.FuzzySchemaMatcher._remove_spaces, src.nlp2cmd.generation.fuzzy_schema_matcher_class.FuzzySchemaMatcher._get_ngrams, src.nlp2cmd.generation.fuzzy_schema_matcher_class.FuzzySchemaMatcher._ngram_similarity

### src.nlp2cmd.adapters.dynamic.DynamicAdapter
> Dynamic adapter that uses extracted schemas instead of hardcoded patterns.

This adapter can work wi
- **Methods**: 19
- **Key Methods**: src.nlp2cmd.adapters.dynamic.DynamicAdapter.__init__, src.nlp2cmd.adapters.dynamic.DynamicAdapter.check_safety, src.nlp2cmd.adapters.dynamic.DynamicAdapter._load_common_commands, src.nlp2cmd.adapters.dynamic.DynamicAdapter.register_schema_source, src.nlp2cmd.adapters.dynamic.DynamicAdapter.generate, src.nlp2cmd.adapters.dynamic.DynamicAdapter._find_matching_commands, src.nlp2cmd.adapters.dynamic.DynamicAdapter._generate_from_schema, src.nlp2cmd.adapters.dynamic.DynamicAdapter._generate_make_command, src.nlp2cmd.adapters.dynamic.DynamicAdapter._generate_web_dql, src.nlp2cmd.adapters.dynamic.DynamicAdapter._generate_from_template
- **Inherits**: BaseDSLAdapter

## Data Transformation Functions

Key functions that process and transform data:

### examples.05_advanced_features.dynamic_schemas.demo_intelligent_nlp2cmd.IntelligentNLP2CMD.transform
> Transform natural language to command with version detection.

Args:
    query: Natural language que
- **Output to**: ActionIR, self.base_nlp.transform_ir, self.generator.generate_command, ActionIR, test_nlp2cmd_commands.print

### examples.03_integrations.web_development._demo_helpers._run_subprocess
- **Output to**: subprocess.run

### examples.03_integrations.web_development.nl_command_parser.NLCommandParser.parse
> Parse natural language command.
- **Output to**: text.lower, self._detect_intent, self._detect_service_type, self._extract_entities

### examples.03_integrations.web_development.web_app_example.process_command
> Przetwarzaj komendę z języka naturalnego.
- **Output to**: app.post, CommandResponse, nlp_api.process_command, HTTPException, HTTPException

### examples.03_integrations.web_development.nlp2_cmd_web_api.NLP2CMDWebAPI.process_command
> Process command from web interface.

Returns JSON-serializable result.
- **Output to**: self.controller.execute, None.isoformat, datetime.now, None.isoformat, str

### examples.03_integrations.toon_format.comparison_demo.SimpleToonParser._parse_file
> Parse TOON file
- **Output to**: content.split, self.file_path.exists, test_nlp2cmd_commands.print, open, f.read

### examples.03_integrations.toon_format.comparison_demo.demonstrate_llm_friendly_format
> Show how TOON format is LLM-friendly
- **Output to**: test_nlp2cmd_commands.print, test_nlp2cmd_commands.print, test_nlp2cmd_commands.print, test_nlp2cmd_commands.print, test_nlp2cmd_commands.print

### examples.03_integrations.toon_format.14_batch_processing.demo.batch_validate
> Walidacja wsadowa komend.
- **Output to**: None.append, None.append, cmd.get

### examples.03_integrations.toon_format.08_memory_usage.demo.format_size
> Formatuje rozmiar w bajtach na czytelną formę.

### examples.03_integrations.pipelines.infrastructure_health.mock_process_list
> Mock: System process list.

### examples.01_basics.shell_fundamentals._environment_sections.format_size

### examples.01_basics.docker_basics.file_repair.validate_file
> Validate a file and print results.
- **Output to**: path.read_text, test_nlp2cmd_commands.print, test_nlp2cmd_commands.print, examples._example_helpers.print_rule, registry.validate

### examples.09_online_drawing.04_object_database.run.parse_objects_from_scene
> Parse object names from a scene description.
- **Output to**: None.replace, None.lower, None.replace, parts.split, p.strip

### examples.09_online_drawing.06_visual_validator.run.draw_and_validate
> Draw a shape using 3-skill pipeline and validate with Qwen VL.
- **Output to**: time.time, async_playwright, test_nlp2cmd_commands.print, DrawNavigationSkill, test_nlp2cmd_commands.print

### examples.09_online_drawing.06_visual_validator.run.validate_screenshot
> Validate an existing screenshot without drawing.
- **Output to**: test_nlp2cmd_commands.print, test_nlp2cmd_commands.print, TaskPlan, DrawValidationSkill.plan_from_description, DrawValidationSkill

### examples.04_domain_specific.polish_llm_integration.mock_test_polish_llm.MockPolishNLP2CMD.process_query
> Process Polish query and optionally execute (mock).
- **Output to**: test_nlp2cmd_commands.print, test_nlp2cmd_commands.print, test_nlp2cmd_commands.print, self.llm_client.generate_plan, test_nlp2cmd_commands.print

### examples.04_domain_specific.data_science.dsl_demo.demo_process_management
> Demonstracja zarządzania procesami.
- **Output to**: examples.04_domain_specific.data_science.dsl_demo.run_query_group

### examples.04_domain_specific.debugging.validation.ShellCommandValidator.validate_command
> Waliduje pojedynczą komendę.
- **Output to**: time.time, self._calculate_similarity, self.generator.generate, hasattr, hasattr

### examples.04_domain_specific.debugging.validation.ShellCommandValidator.validate_all
> Waliduje wszystkie komendy.
- **Output to**: self.get_test_cases, test_nlp2cmd_commands.print, test_nlp2cmd_commands.print, examples._example_helpers.print_rule, enumerate

### examples.04_domain_specific.debugging.10_advanced_validation.demo.AdvancedValidator.validate
- **Output to**: self._calculate_similarity, ValidationResult, self.results.append

### src.nlp2cmd.schema_driven.SchemaDrivenNLP2CMD.transform
- **Output to**: self._select_action, self._extract_params, self._render_dsl, str, ActionIR

### src.nlp2cmd.pipeline_runner_shell.ShellExecutionMixin._parse_shell_command
- **Output to**: command.strip, cmd.lower, any, any, re.search

### src.nlp2cmd.monitoring.resources.ResourceMonitor._process_cpu_time_seconds
> Return process CPU time in seconds (user+system).
- **Output to**: self.process.cpu_times, float, float, getattr, getattr

### src.nlp2cmd.monitoring.resources.ResourceMonitor.format_metrics
> Format metrics for display.
- **Output to**: None.join, lines.append

### src.nlp2cmd.monitoring.resources.format_last_metrics
> Format metrics from last execution for display.
- **Output to**: src.nlp2cmd.monitoring.resources.get_last_metrics, _monitor.format_metrics

## Public API Surface

Functions exposed as public API (no underscore prefix):

- `src.nlp2cmd.cli.commands.run.handle_run_mode` - 270 calls
- `src.nlp2cmd.pipeline_runner_plans.PlanExecutionMixin.execute_action_plan` - 219 calls
- `examples.10_online_code_editors.03_adaptive_code.main` - 133 calls
- `examples.10_online_code_editors.02_mycompiler_run.main` - 116 calls
- `src.nlp2cmd.cli.main.main` - 115 calls
- `src.nlp2cmd.execution.runner.ExecutionRunner.run_command` - 109 calls
- `docker.novnc.demos.demo_desktop_gui.run_demo` - 103 calls
- `examples.09_online_drawing._old.03_adaptive_drawing.main` - 93 calls
- `examples.05_advanced_features.schema_driven_architecture.end_to_end_demo.main` - 87 calls
- `examples.10_online_code_editors.01_codepen_live.main` - 87 calls
- `src.nlp2cmd.generation.train_model.train_all_models` - 86 calls
- `src.nlp2cmd.web_schema.form_handler.FormHandler.detect_form_fields` - 83 calls
- `examples.10_online_code_editors.04_jsfiddle_frontend.main` - 82 calls
- `examples.01_basics.sql_basics.workflows.main` - 81 calls
- `examples.04_domain_specific.debugging.validation.ShellCommandValidator.get_test_cases` - 79 calls
- `examples.show_metrics.main` - 77 calls
- `examples.03_integrations.toon_format.usage_example.main` - 77 calls
- `benchmarks.llm_benchmark.generate_html` - 77 calls
- `src.nlp2cmd.web_schema.site_explorer.SiteExplorer.find_form` - 77 calls
- `scripts.maintenance.refactoring_summary.print_summary` - 72 calls
- `src.app2schema.extract.extract_schema` - 70 calls
- `examples.03_integrations.validation.config_validation.main` - 68 calls
- `src.nlp2cmd.cli.commands.generate.handle_generate_query` - 68 calls
- `examples.02_benchmarks.sequential_testing.benchmark.main` - 67 calls
- `examples.09_online_drawing._old.04_object_database_drawing.main` - 66 calls
- `src.nlp2cmd.adapters.browser.BrowserAdapter.generate` - 66 calls
- `examples.09_online_drawing.05_autonomous.run.run_autonomous` - 65 calls
- `src.nlp2cmd.skills.drawing.svg_path_parser.parse_svg_path` - 64 calls
- `examples.09_online_drawing.06_visual_validator.run.draw_and_validate` - 62 calls
- `examples.01_basics.sql_basics.advanced.main` - 60 calls
- `src.nlp2cmd.web_schema.site_explorer.SiteExplorer.find_content` - 60 calls
- `examples.03_integrations.pipelines.infrastructure_health.main` - 59 calls
- `examples.09_online_drawing._old.05_autonomous_drawing.run_autonomous` - 59 calls
- `benchmarks.llm_benchmark.run_benchmark` - 57 calls
- `src.nlp2cmd.generation.evolutionary_cache.EvolutionaryCache.lookup` - 57 calls
- `src.nlp2cmd.cli.debug_info.show_schema_info` - 57 calls
- `tools.schema.update_schemas.update_all_schemas` - 57 calls
- `examples.05_advanced_features.dynamic_schemas.demo_schema_flow.demonstrate_schema_flow` - 56 calls
- `src.nlp2cmd.cli.debug_info.show_decision_tree_info` - 56 calls
- `benchmarks.llm_benchmark.generate_command_errors_report` - 55 calls

## System Interactions

How components interact:

```mermaid
graph TD
```

## Reverse Engineering Guidelines

1. **Entry Points**: Start analysis from the entry points listed above
2. **Core Logic**: Focus on classes with many methods
3. **Data Flow**: Follow data transformation functions
4. **Process Flows**: Use the flow diagrams for execution paths
5. **API Surface**: Public API functions reveal the interface

## Context for LLM

Maintain the identified architectural patterns and public API surface when suggesting changes.