# System Architecture Analysis

## Overview

- **Project**: /home/tom/github/wronai/nlp2cmd
- **Analysis Mode**: static
- **Total Functions**: 32234
- **Total Classes**: 4869
- **Modules**: 2689
- **Entry Points**: 27234

## Architecture by Module

### fresh_env.lib.python3.13.site-packages.regex._regex_core
- **Functions**: 353
- **Classes**: 61
- **File**: `_regex_core.py`

### fresh_env.lib.python3.13.site-packages.astroid.nodes.node_classes
- **Functions**: 283
- **Classes**: 76
- **File**: `node_classes.py`

### fresh_env.lib.python3.13.site-packages.pyparsing.core
- **Functions**: 262
- **Classes**: 56
- **File**: `core.py`

### fresh_env.lib.python3.13.site-packages.pip._vendor.pkg_resources
- **Functions**: 256
- **Classes**: 33
- **File**: `__init__.py`

### fresh_env.lib.python3.13.site-packages.numpy.ma.core
- **Functions**: 240
- **Classes**: 18
- **File**: `core.py`

### fresh_env.lib.python3.13.site-packages.fontTools.ttLib.ttFont
- **Functions**: 232
- **Classes**: 2
- **File**: `ttFont.py`

### fresh_env.lib.python3.13.site-packages.fontTools.cffLib
- **Functions**: 215
- **Classes**: 47
- **File**: `__init__.py`

### fresh_env.lib.python3.13.site-packages.fontTools.feaLib.ast
- **Functions**: 200
- **Classes**: 68
- **File**: `ast.py`

### fresh_env.lib.python3.13.site-packages.matplotlib.patches
- **Functions**: 199
- **Classes**: 22
- **File**: `patches.py`

### fresh_env.lib.python3.13.site-packages.matplotlib.transforms
- **Functions**: 191
- **Classes**: 25
- **File**: `transforms.py`

### fresh_env.lib.python3.13.site-packages.matplotlib.widgets
- **Functions**: 184
- **Classes**: 22
- **File**: `widgets.py`

### fresh_env.lib.python3.13.site-packages.fontTools.ttLib.tables.otConverters
- **Functions**: 180
- **Classes**: 57
- **File**: `otConverters.py`

### fresh_env.lib.python3.13.site-packages.matplotlib.pyplot
- **Functions**: 179
- **File**: `pyplot.py`

### fresh_env.lib.python3.13.site-packages.matplotlib.backend_bases
- **Functions**: 179
- **Classes**: 20
- **File**: `backend_bases.py`

### fresh_env.lib.python3.13.site-packages.fontTools.misc.psCharStrings
- **Functions**: 171
- **Classes**: 9
- **File**: `psCharStrings.py`

### fresh_env.lib.python3.13.site-packages.fontTools.subset
- **Functions**: 168
- **Classes**: 2
- **File**: `__init__.py`

### fresh_env.lib.python3.13.site-packages.matplotlib.axes._base
- **Functions**: 168
- **Classes**: 4
- **File**: `_base.py`

### fresh_env.lib.python3.13.site-packages.matplotlib.axis
- **Functions**: 163
- **Classes**: 8
- **File**: `axis.py`

### fresh_env.lib.python3.13.site-packages.matplotlib.ticker
- **Functions**: 156
- **Classes**: 31
- **File**: `ticker.py`

### fresh_env.lib.python3.13.site-packages.PIL.Image
- **Functions**: 144
- **Classes**: 16
- **File**: `Image.py`

## Key Entry Points

Main execution flows into the system:

### src.nlp2cmd.pipeline_runner_plans.PlanExecutionMixin._execute_plan_step
> Execute a single ActionPlan step. Returns extracted value or None.
- **Calls**: self._resolve_plan_variables, Console, fresh_env.lib.python3.13.site-packages.code2logic.terminal.ShellRenderer.print, params.get, page.goto, page.wait_for_timeout, ValueError, url.startswith

### src.nlp2cmd.pipeline_runner_browser.BrowserExecutionMixin._run_dom_multi_action
> Execute multiple browser actions in sequence.
- **Calls**: payload.get, Console, _MarkdownConsoleWrapper, payload.get, RunnerResult, RunnerResult, sync_playwright, p.chromium.launch

### src.nlp2cmd.pipeline_runner_plans.PlanExecutionMixin.execute_action_plan
> Execute an ActionPlan step by step using Playwright.

Args:
    plan: ActionPlan instance with steps to execute
    dry_run: If True, only show the pl
- **Calls**: Console, frozenset, console.print, console.print, enumerate, None.strip, RunnerResult, fresh_env.lib.python3.13.site-packages.numpy._core.fromnumeric.any

### fresh_env.lib.python3.13.site-packages.networkx.generators.social.les_miserables_graph
> Returns coappearance network of characters in the novel Les Miserables.

References
----------
.. [1] D. E. Knuth, 1993.
   The Stanford GraphBase: a 
- **Calls**: nx._dispatchable, nx.Graph, G.add_edge, G.add_edge, G.add_edge, G.add_edge, G.add_edge, G.add_edge

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

### fresh_env.lib.python3.13.site-packages.code2logic.cli.main
- **Calls**: time.time, argparse.ArgumentParser, parser.add_argument, parser.add_argument, parser.add_argument, parser.add_argument, parser.add_argument, parser.add_argument

### fresh_env.lib.python3.13.site-packages.networkx.drawing.nx_pylab.display
> Draw the graph G.

Draw the graph as a collection of nodes connected by edges.
The exact details of what the graph looks like are controlled by the be
- **Calls**: kwargs.get, kwargs.get, isinstance, G.subgraph, kwargs.get, fresh_env.lib.python3.13.site-packages.astroid.bases.Instance.callable, kwargs.get, kwargs.get

### networkx-3.6.1-py3-none-any.networkx.drawing.nx_pylab.display
> Draw the graph G.

Draw the graph as a collection of nodes connected by edges.
The exact details of what the graph looks like are controlled by the be
- **Calls**: kwargs.get, kwargs.get, isinstance, G.subgraph, kwargs.get, fresh_env.lib.python3.13.site-packages.astroid.bases.Instance.callable, kwargs.get, kwargs.get

### fresh_env.lib.python3.13.site-packages.fontTools.varLib.interpolatable.main
> Test for interpolatability issues between fonts
- **Calls**: argparse.ArgumentParser, parser.add_argument, parser.add_argument, parser.add_argument, parser.add_argument, parser.add_argument, parser.add_argument, parser.add_argument

### networkx-3.6.1-py3-none-any.networkx.algorithms.similarity.optimize_edit_paths
> GED (graph edit distance) calculation: advanced interface.

Graph edit path is a sequence of node and edge edit operations
transforming graph G1 to gr
- **Calls**: nx._dispatchable, fresh_env.lib.python3.13.site-packages.matplotlib.animation.MovieWriterRegistry.list, fresh_env.lib.python3.13.site-packages.matplotlib.animation.MovieWriterRegistry.list, len, len, np.zeros, None.reshape, None.reshape

### fresh_env.lib.python3.13.site-packages.matplotlib.sankey.Sankey.add
> Add a simple Sankey diagram with flows at the same hierarchical level.

Parameters
----------
patchlabel : str
    Label to be placed at the center of
- **Calls**: fresh_env.lib.python3.13.site-packages.PIL.ImageStat.Stat.sum, fresh_env.lib.python3.13.site-packages.PIL.ImageStat.Stat.sum, enumerate, enumerate, np.iterable, np.zeros, np.zeros, enumerate

### networkx-3.6.1-py3-none-any.networkx.algorithms.matching.max_weight_matching
> Compute a maximum-weighted matching of G.

A matching is a subset of edges in which no node occurs more than once.
The weight of a matching is the sum
- **Calls**: fresh_env.lib.python3.13.site-packages.networkx.utils.decorators.not_implemented_for, fresh_env.lib.python3.13.site-packages.networkx.utils.decorators.not_implemented_for, nx._dispatchable, fresh_env.lib.python3.13.site-packages.matplotlib.animation.MovieWriterRegistry.list, G.edges, dict, dict, dict

### webops.nlp2cmd-repo.examples.shell.environment_analysis.main
- **Calls**: fresh_env.lib.python3.13.site-packages.code2logic.terminal.ShellRenderer.print, fresh_env.lib.python3.13.site-packages.code2logic.terminal.ShellRenderer.print, fresh_env.lib.python3.13.site-packages.code2logic.terminal.ShellRenderer.print, EnvironmentAnalyzer, fresh_env.lib.python3.13.site-packages.code2logic.terminal.ShellRenderer.print, fresh_env.lib.python3.13.site-packages.code2logic.terminal.ShellRenderer.print, fresh_env.lib.python3.13.site-packages.code2logic.terminal.ShellRenderer.print, analyzer.analyze

### examples.01_basics.shell_fundamentals.environment_analysis.main
- **Calls**: examples._example_helpers.print_separator, EnvironmentAnalyzer, examples._example_helpers.print_rule, fresh_env.lib.python3.13.site-packages.code2logic.terminal.ShellRenderer.print, examples._example_helpers.print_rule, analyzer.analyze, fresh_env.lib.python3.13.site-packages.code2logic.terminal.ShellRenderer.print, fresh_env.lib.python3.13.site-packages.code2logic.terminal.ShellRenderer.print

### fresh_env.lib.python3.13.site-packages.fontTools.pens.momentsPen.MomentsPen._curveToOne
- **Calls**: cython.locals, cython.locals, cython.locals, cython.locals, cython.locals, cython.locals, cython.locals, cython.locals

### fresh_env.lib.python3.13.site-packages.matplotlib.axes._axes.Axes.hist
> Compute and plot a histogram.

This method uses `numpy.histogram` to bin the data in *x* and count the
number of values in each bin, then draws the di
- **Calls**: _api.make_keyword_only, fresh_env.lib.python3.13.site-packages.matplotlib._preprocess_data, fresh_env.lib.python3.13.site-packages.matplotlib.cbook.normalize_kwargs, np.isscalar, fresh_env.lib.python3.13.site-packages.matplotlib._api.check_in_list, fresh_env.lib.python3.13.site-packages.matplotlib._api.check_in_list, fresh_env.lib.python3.13.site-packages.matplotlib._api.check_in_list, fresh_env.lib.python3.13.site-packages.matplotlib.cbook._reshape_2D

### fresh_env.lib.python3.13.site-packages.code2logic.cli._code2logic_llm_cli
- **Calls**: argparse.ArgumentParser, parser.add_subparsers, sub.add_parser, sub.add_parser, p_config.add_subparsers, config_sub.add_parser, sub.add_parser, p_set_provider.add_argument

### fresh_env.lib.python3.13.site-packages.matplotlib.backends.backend_pdf.PdfFile.embedTTF
> Embed the TTF font from the named file into the document.
- **Calls**: fresh_env.lib.python3.13.site-packages.matplotlib.font_manager.get_font, self._get_subsetted_psname, ps_name.encode, Name, self.reserveObject, self.reserveObject, self.reserveObject, self.reserveObject

### fresh_env.lib.python3.13.site-packages.code2logic.parsers.UniversalParser._parse_js_ts
> Parse JS/TS using regex patterns.
- **Calls**: re.finditer, re.finditer, re.finditer, re.finditer, re.finditer, re.finditer, re.finditer, re.finditer

### webops.nlp2cmd-repo.src.nlp2cmd.pipeline_runner.PipelineRunner._run_dom_multi_action
> Execute multiple browser actions in sequence.
- **Calls**: payload.get, Console, _MarkdownConsoleWrapper, payload.get, RunnerResult, RunnerResult, sync_playwright, p.chromium.launch

### src.nlp2cmd.cli.main.main
> NLP2CMD - Natural Language to Domain-Specific Commands.
- **Calls**: click.group, click.option, click.option, click.option, click.option, click.option, click.option, click.option

### fresh_env.lib.python3.13.site-packages.numpy.f2py.symbolic._FromStringWorker.process
> Parse string within the given context.

The context may define the result in case of ambiguous
expressions. For instance, consider expressions `f(x, y
- **Calls**: isinstance, isinstance, fresh_env.lib.python3.13.site-packages.numpy.f2py.symbolic.replace_parenthesis, r.strip, re.match, re.match, re.split, re.split

### fresh_env.lib.python3.13.site-packages.matplotlib.axes._axes.Axes.hexbin
> Make a 2D hexagonal binning plot of points *x*, *y*.

If *C* is *None*, the value of the hexagon is determined by the number
of points in the hexagon.
- **Calls**: _api.make_keyword_only, fresh_env.lib.python3.13.site-packages.matplotlib._preprocess_data, self._process_unit_info, fresh_env.lib.python3.13.site-packages.matplotlib.cbook.delete_masked_points, np.iterable, np.asarray, np.asarray, None.astype

### src.nlp2cmd.execution.runner.ExecutionRunner.run_command
> Execute a shell command with real-time output.

Args:
    command: Shell command to execute
    cwd: Working directory
    env: Environment variables

- **Calls**: time.time, self.print_markdown_block, ExecutionResult, self.execution_history.append, subprocess.Popen, None.join, None.join, subprocess.run

### fresh_env.lib.python3.13.site-packages.fontTools.subset.Subsetter._closure_glyphs
- **Calls**: fresh_env.lib.python3.13.site-packages.matplotlib.dates.rrulewrapper.set, font.getGlyphOrder, fresh_env.lib.python3.13.site-packages.matplotlib.dates.rrulewrapper.set, self.glyphs_requested.update, self.glyphs_requested.update, fresh_env.lib.python3.13.site-packages.matplotlib.dates.rrulewrapper.set, self.glyphs_missing.update, self.glyphs_missing.update

### fresh_env.lib.python3.13.site-packages.fontTools.varLib.interpolatablePlot.InterpolatablePlot.draw_glyph
- **Calls**: fresh_env.lib.python3.13.site-packages.numpy._core.fromnumeric.any, fresh_env.lib.python3.13.site-packages.matplotlib.dates.rrulewrapper.set, RecordingPen, glyph.draw, DecomposingRecordingPen, glyph.draw, ControlBoundsPen, decomposedRecording.replay

### examples.03_integrations.web_development.demo.demo_nlp_commands
> Interaktywna demonstracja poleceń NLP.
- **Calls**: NLP2CMDWebController, examples._example_helpers.print_separator, fresh_env.lib.python3.13.site-packages.code2logic.terminal.ShellRenderer.print, fresh_env.lib.python3.13.site-packages.code2logic.terminal.ShellRenderer.print, None.strip, fresh_env.lib.python3.13.site-packages.code2logic.terminal.ShellRenderer.print, examples._example_helpers.print_rule, fresh_env.lib.python3.13.site-packages.code2logic.terminal.ShellRenderer.print

### fresh_env.lib.python3.13.site-packages.matplotlib.axes._axes.Axes.bxp
> Draw a box and whisker plot from pre-computed statistics.

The box extends from the first quartile *q1* to the third
quartile *q3* of the data, with a
- **Calls**: _api.make_keyword_only, merge_kw_rc, merge_kw_rc, merge_kw_rc, merge_kw_rc, merge_kw_rc, fresh_env.lib.python3.13.site-packages.matplotlib._api.check_in_list, len

### webops.nlp2cmd-repo.src.nlp2cmd.registry.ActionRegistry._register_builtin_actions
> Register built-in actions.
- **Calls**: self.register, self.register, self.register, self.register, self.register, self.register, self.register, self.register

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
les_miserables_graph [fresh_env.lib.python3.13.site-packages.networkx.generators.social]
```

### Flow 5: _prepare_shell_entities
```
_prepare_shell_entities [webops.nlp2cmd-repo.src.nlp2cmd.generation.templates.TemplateGenerator]
```

### Flow 6: main
```
main [fresh_env.lib.python3.13.site-packages.code2logic.cli]
```

### Flow 7: display
```
display [fresh_env.lib.python3.13.site-packages.networkx.drawing.nx_pylab]
```

### Flow 8: optimize_edit_paths
```
optimize_edit_paths [networkx-3.6.1-py3-none-any.networkx.algorithms.similarity]
  └─ →> list
  └─ →> list
```

### Flow 9: add
```
add [fresh_env.lib.python3.13.site-packages.matplotlib.sankey.Sankey]
  └─ →> sum
      └─ →> range
          └─ →> reversed
          └─ →> list
  └─ →> sum
      └─ →> range
          └─ →> reversed
          └─ →> list
```

### Flow 10: max_weight_matching
```
max_weight_matching [networkx-3.6.1-py3-none-any.networkx.algorithms.matching]
  └─ →> not_implemented_for
      └─ →> set
  └─ →> not_implemented_for
      └─ →> set
  └─ →> list
```

## Key Classes

### fresh_env.lib.python3.13.site-packages.fontTools.ttLib.ttFont.TTFont
> Represents a TrueType font.

The object manages file input and output, and offers a convenient way o
- **Methods**: 213
- **Key Methods**: fresh_env.lib.python3.13.site-packages.fontTools.ttLib.ttFont.TTFont.__init__, fresh_env.lib.python3.13.site-packages.fontTools.ttLib.ttFont.TTFont.__enter__, fresh_env.lib.python3.13.site-packages.fontTools.ttLib.ttFont.TTFont.__exit__, fresh_env.lib.python3.13.site-packages.fontTools.ttLib.ttFont.TTFont.close, fresh_env.lib.python3.13.site-packages.fontTools.ttLib.ttFont.TTFont.save, fresh_env.lib.python3.13.site-packages.fontTools.ttLib.ttFont.TTFont._save, fresh_env.lib.python3.13.site-packages.fontTools.ttLib.ttFont.TTFont.saveXML, fresh_env.lib.python3.13.site-packages.fontTools.ttLib.ttFont.TTFont._saveXML, fresh_env.lib.python3.13.site-packages.fontTools.ttLib.ttFont.TTFont._tableToXML, fresh_env.lib.python3.13.site-packages.fontTools.ttLib.ttFont.TTFont.importXML
- **Inherits**: object

### fresh_env.lib.python3.13.site-packages.matplotlib.axes._base._AxesBase
- **Methods**: 162
- **Key Methods**: fresh_env.lib.python3.13.site-packages.matplotlib.axes._base._AxesBase._axis_map, fresh_env.lib.python3.13.site-packages.matplotlib.axes._base._AxesBase.__str__, fresh_env.lib.python3.13.site-packages.matplotlib.axes._base._AxesBase.__init__, fresh_env.lib.python3.13.site-packages.matplotlib.axes._base._AxesBase.__init_subclass__, fresh_env.lib.python3.13.site-packages.matplotlib.axes._base._AxesBase.__getstate__, fresh_env.lib.python3.13.site-packages.matplotlib.axes._base._AxesBase.__setstate__, fresh_env.lib.python3.13.site-packages.matplotlib.axes._base._AxesBase.__repr__, fresh_env.lib.python3.13.site-packages.matplotlib.axes._base._AxesBase.get_subplotspec, fresh_env.lib.python3.13.site-packages.matplotlib.axes._base._AxesBase.set_subplotspec, fresh_env.lib.python3.13.site-packages.matplotlib.axes._base._AxesBase.get_gridspec
- **Inherits**: martist.Artist

### fresh_env.lib.python3.13.site-packages.numpy.ma.core.MaskedArray
> An array class with possibly masked values.

Masked values of True exclude the corresponding element
- **Methods**: 104
- **Key Methods**: fresh_env.lib.python3.13.site-packages.numpy.ma.core.MaskedArray.__new__, fresh_env.lib.python3.13.site-packages.numpy.ma.core.MaskedArray._update_from, fresh_env.lib.python3.13.site-packages.numpy.ma.core.MaskedArray.__array_finalize__, fresh_env.lib.python3.13.site-packages.numpy.ma.core.MaskedArray.__array_wrap__, fresh_env.lib.python3.13.site-packages.numpy.ma.core.MaskedArray.view, fresh_env.lib.python3.13.site-packages.numpy.ma.core.MaskedArray.__getitem__, fresh_env.lib.python3.13.site-packages.numpy.ma.core.MaskedArray.__setitem__, fresh_env.lib.python3.13.site-packages.numpy.ma.core.MaskedArray.dtype, fresh_env.lib.python3.13.site-packages.numpy.ma.core.MaskedArray.dtype, fresh_env.lib.python3.13.site-packages.numpy.ma.core.MaskedArray.shape
- **Inherits**: ndarray

### fresh_env.lib.python3.13.site-packages.matplotlib.axis.Axis
> Base class for `.XAxis` and `.YAxis`.

Attributes
----------
isDefault_label : bool

axes : `~matplo
- **Methods**: 103
- **Key Methods**: fresh_env.lib.python3.13.site-packages.matplotlib.axis.Axis.__str__, fresh_env.lib.python3.13.site-packages.matplotlib.axis.Axis.__init__, fresh_env.lib.python3.13.site-packages.matplotlib.axis.Axis.isDefault_majloc, fresh_env.lib.python3.13.site-packages.matplotlib.axis.Axis.isDefault_majloc, fresh_env.lib.python3.13.site-packages.matplotlib.axis.Axis.isDefault_majfmt, fresh_env.lib.python3.13.site-packages.matplotlib.axis.Axis.isDefault_majfmt, fresh_env.lib.python3.13.site-packages.matplotlib.axis.Axis.isDefault_minloc, fresh_env.lib.python3.13.site-packages.matplotlib.axis.Axis.isDefault_minloc, fresh_env.lib.python3.13.site-packages.matplotlib.axis.Axis.isDefault_minfmt, fresh_env.lib.python3.13.site-packages.matplotlib.axis.Axis.isDefault_minfmt
- **Inherits**: martist.Artist

### src.nlp2cmd.generation.template_generator.TemplateGenerator
> Generate DSL commands from templates.

Uses predefined templates filled with extracted entities.
Fal
- **Methods**: 100
- **Key Methods**: src.nlp2cmd.generation.template_generator.TemplateGenerator.__init__, src.nlp2cmd.generation.template_generator.TemplateGenerator._load_defaults_from_json, src.nlp2cmd.generation.template_generator.TemplateGenerator._load_templates_from_json, src.nlp2cmd.generation.template_generator.TemplateGenerator._get_default, src.nlp2cmd.generation.template_generator.TemplateGenerator.generate, src.nlp2cmd.generation.template_generator.TemplateGenerator._find_alternative_template, src.nlp2cmd.generation.template_generator.TemplateGenerator._get_intent_aliases, src.nlp2cmd.generation.template_generator.TemplateGenerator._prepare_entities, src.nlp2cmd.generation.template_generator.TemplateGenerator._prepare_sql_entities, src.nlp2cmd.generation.template_generator.TemplateGenerator._prepare_shell_entities

### fresh_env.lib.python3.13.site-packages.fontTools.feaLib.parser.Parser
> Initializes a Parser object.

Example:

    .. code:: python

        from fontTools.feaLib.parser i
- **Methods**: 98
- **Key Methods**: fresh_env.lib.python3.13.site-packages.fontTools.feaLib.parser.Parser.__init__, fresh_env.lib.python3.13.site-packages.fontTools.feaLib.parser.Parser.parse, fresh_env.lib.python3.13.site-packages.fontTools.feaLib.parser.Parser.parse_anchor_, fresh_env.lib.python3.13.site-packages.fontTools.feaLib.parser.Parser.parse_anchor_marks_, fresh_env.lib.python3.13.site-packages.fontTools.feaLib.parser.Parser.parse_anchordef_, fresh_env.lib.python3.13.site-packages.fontTools.feaLib.parser.Parser.parse_anonymous_, fresh_env.lib.python3.13.site-packages.fontTools.feaLib.parser.Parser.parse_attach_, fresh_env.lib.python3.13.site-packages.fontTools.feaLib.parser.Parser.parse_enumerate_, fresh_env.lib.python3.13.site-packages.fontTools.feaLib.parser.Parser.parse_GlyphClassDef_, fresh_env.lib.python3.13.site-packages.fontTools.feaLib.parser.Parser.parse_glyphclass_definition_
- **Inherits**: object

### fresh_env.lib.python3.13.site-packages.astroid.nodes.as_string.AsStringVisitor
> Visitor to render an Astroid node as a valid python code string
- **Methods**: 98
- **Key Methods**: fresh_env.lib.python3.13.site-packages.astroid.nodes.as_string.AsStringVisitor.__init__, fresh_env.lib.python3.13.site-packages.astroid.nodes.as_string.AsStringVisitor.__call__, fresh_env.lib.python3.13.site-packages.astroid.nodes.as_string.AsStringVisitor._docs_dedent, fresh_env.lib.python3.13.site-packages.astroid.nodes.as_string.AsStringVisitor._stmt_list, fresh_env.lib.python3.13.site-packages.astroid.nodes.as_string.AsStringVisitor._precedence_parens, fresh_env.lib.python3.13.site-packages.astroid.nodes.as_string.AsStringVisitor._should_wrap, fresh_env.lib.python3.13.site-packages.astroid.nodes.as_string.AsStringVisitor.visit_await, fresh_env.lib.python3.13.site-packages.astroid.nodes.as_string.AsStringVisitor.visit_asyncwith, fresh_env.lib.python3.13.site-packages.astroid.nodes.as_string.AsStringVisitor.visit_asyncfor, fresh_env.lib.python3.13.site-packages.astroid.nodes.as_string.AsStringVisitor.visit_arguments

### fresh_env.lib.python3.13.site-packages.mpl_toolkits.mplot3d.axes3d.Axes3D
> 3D Axes object.

.. note::

    As a user, you do not instantiate Axes directly, but use Axes creati
- **Methods**: 94
- **Key Methods**: fresh_env.lib.python3.13.site-packages.mpl_toolkits.mplot3d.axes3d.Axes3D.__init__, fresh_env.lib.python3.13.site-packages.mpl_toolkits.mplot3d.axes3d.Axes3D.set_axis_off, fresh_env.lib.python3.13.site-packages.mpl_toolkits.mplot3d.axes3d.Axes3D.set_axis_on, fresh_env.lib.python3.13.site-packages.mpl_toolkits.mplot3d.axes3d.Axes3D.convert_zunits, fresh_env.lib.python3.13.site-packages.mpl_toolkits.mplot3d.axes3d.Axes3D.set_top_view, fresh_env.lib.python3.13.site-packages.mpl_toolkits.mplot3d.axes3d.Axes3D._init_axis, fresh_env.lib.python3.13.site-packages.mpl_toolkits.mplot3d.axes3d.Axes3D.get_zaxis, fresh_env.lib.python3.13.site-packages.mpl_toolkits.mplot3d.axes3d.Axes3D._transformed_cube, fresh_env.lib.python3.13.site-packages.mpl_toolkits.mplot3d.axes3d.Axes3D.set_aspect, fresh_env.lib.python3.13.site-packages.mpl_toolkits.mplot3d.axes3d.Axes3D._equal_aspect_axis_indices
- **Inherits**: Axes

### fresh_env.lib.python3.13.site-packages.jinja2.compiler.CodeGenerator
- **Methods**: 93
- **Key Methods**: fresh_env.lib.python3.13.site-packages.jinja2.compiler.CodeGenerator.__init__, fresh_env.lib.python3.13.site-packages.jinja2.compiler.CodeGenerator.optimized, fresh_env.lib.python3.13.site-packages.jinja2.compiler.CodeGenerator.fail, fresh_env.lib.python3.13.site-packages.jinja2.compiler.CodeGenerator.temporary_identifier, fresh_env.lib.python3.13.site-packages.jinja2.compiler.CodeGenerator.buffer, fresh_env.lib.python3.13.site-packages.jinja2.compiler.CodeGenerator.return_buffer_contents, fresh_env.lib.python3.13.site-packages.jinja2.compiler.CodeGenerator.indent, fresh_env.lib.python3.13.site-packages.jinja2.compiler.CodeGenerator.outdent, fresh_env.lib.python3.13.site-packages.jinja2.compiler.CodeGenerator.start_write, fresh_env.lib.python3.13.site-packages.jinja2.compiler.CodeGenerator.end_write
- **Inherits**: NodeVisitor

### fresh_env.lib.python3.13.site-packages.PIL.Image.Image
> This class represents an image object.  To create
:py:class:`~PIL.Image.Image` objects, use the appr
- **Methods**: 83
- **Key Methods**: fresh_env.lib.python3.13.site-packages.PIL.Image.Image.__init__, fresh_env.lib.python3.13.site-packages.PIL.Image.Image.im, fresh_env.lib.python3.13.site-packages.PIL.Image.Image.im, fresh_env.lib.python3.13.site-packages.PIL.Image.Image.width, fresh_env.lib.python3.13.site-packages.PIL.Image.Image.height, fresh_env.lib.python3.13.site-packages.PIL.Image.Image.size, fresh_env.lib.python3.13.site-packages.PIL.Image.Image.mode, fresh_env.lib.python3.13.site-packages.PIL.Image.Image.readonly, fresh_env.lib.python3.13.site-packages.PIL.Image.Image.readonly, fresh_env.lib.python3.13.site-packages.PIL.Image.Image._new

### fresh_env.lib.python3.13.site-packages.matplotlib.artist.Artist
> Abstract base class for objects that render into a FigureCanvas.

Typically, all visible elements in
- **Methods**: 79
- **Key Methods**: fresh_env.lib.python3.13.site-packages.matplotlib.artist.Artist.__init_subclass__, fresh_env.lib.python3.13.site-packages.matplotlib.artist.Artist._update_set_signature_and_docstring, fresh_env.lib.python3.13.site-packages.matplotlib.artist.Artist.__init__, fresh_env.lib.python3.13.site-packages.matplotlib.artist.Artist.__getstate__, fresh_env.lib.python3.13.site-packages.matplotlib.artist.Artist.remove, fresh_env.lib.python3.13.site-packages.matplotlib.artist.Artist.have_units, fresh_env.lib.python3.13.site-packages.matplotlib.artist.Artist.convert_xunits, fresh_env.lib.python3.13.site-packages.matplotlib.artist.Artist.convert_yunits, fresh_env.lib.python3.13.site-packages.matplotlib.artist.Artist.axes, fresh_env.lib.python3.13.site-packages.matplotlib.artist.Artist.axes

### fresh_env.lib.python3.13.site-packages.matplotlib.axes._axes.Axes
> An Axes object encapsulates all the elements of an individual (sub-)plot in
a figure.

It contains m
- **Methods**: 78
- **Key Methods**: fresh_env.lib.python3.13.site-packages.matplotlib.axes._axes.Axes.get_title, fresh_env.lib.python3.13.site-packages.matplotlib.axes._axes.Axes.set_title, fresh_env.lib.python3.13.site-packages.matplotlib.axes._axes.Axes.get_legend_handles_labels, fresh_env.lib.python3.13.site-packages.matplotlib.axes._axes.Axes.legend, fresh_env.lib.python3.13.site-packages.matplotlib.axes._axes.Axes._remove_legend, fresh_env.lib.python3.13.site-packages.matplotlib.axes._axes.Axes.inset_axes, fresh_env.lib.python3.13.site-packages.matplotlib.axes._axes.Axes.indicate_inset, fresh_env.lib.python3.13.site-packages.matplotlib.axes._axes.Axes.indicate_inset_zoom, fresh_env.lib.python3.13.site-packages.matplotlib.axes._axes.Axes.secondary_xaxis, fresh_env.lib.python3.13.site-packages.matplotlib.axes._axes.Axes.secondary_yaxis
- **Inherits**: _AxesBase

### fresh_env.lib.python3.13.site-packages.matplotlib.text.Text
> Handle storing and drawing of text in window or data coordinates.
- **Methods**: 73
- **Key Methods**: fresh_env.lib.python3.13.site-packages.matplotlib.text.Text.__repr__, fresh_env.lib.python3.13.site-packages.matplotlib.text.Text.__init__, fresh_env.lib.python3.13.site-packages.matplotlib.text.Text._reset_visual_defaults, fresh_env.lib.python3.13.site-packages.matplotlib.text.Text.update, fresh_env.lib.python3.13.site-packages.matplotlib.text.Text.__getstate__, fresh_env.lib.python3.13.site-packages.matplotlib.text.Text.contains, fresh_env.lib.python3.13.site-packages.matplotlib.text.Text._get_xy_display, fresh_env.lib.python3.13.site-packages.matplotlib.text.Text._get_multialignment, fresh_env.lib.python3.13.site-packages.matplotlib.text.Text._char_index_at, fresh_env.lib.python3.13.site-packages.matplotlib.text.Text.get_rotation
- **Inherits**: Artist

### fresh_env.lib.python3.13.site-packages.pyparsing.core.ParserElement
> Abstract base level parser element class.
- **Methods**: 73
- **Key Methods**: fresh_env.lib.python3.13.site-packages.pyparsing.core.ParserElement.set_default_whitespace_chars, fresh_env.lib.python3.13.site-packages.pyparsing.core.ParserElement.inline_literals_using, fresh_env.lib.python3.13.site-packages.pyparsing.core.ParserElement.using_each, fresh_env.lib.python3.13.site-packages.pyparsing.core.ParserElement.__init__, fresh_env.lib.python3.13.site-packages.pyparsing.core.ParserElement.mayReturnEmpty, fresh_env.lib.python3.13.site-packages.pyparsing.core.ParserElement.mayReturnEmpty, fresh_env.lib.python3.13.site-packages.pyparsing.core.ParserElement.suppress_warning, fresh_env.lib.python3.13.site-packages.pyparsing.core.ParserElement.visit_all, fresh_env.lib.python3.13.site-packages.pyparsing.core.ParserElement.copy, fresh_env.lib.python3.13.site-packages.pyparsing.core.ParserElement.set_results_name
- **Inherits**: ABC

### fresh_env.lib.python3.13.site-packages.numpy.polynomial._polybase.ABCPolyBase
> An abstract base class for immutable series classes.

ABCPolyBase provides the standard Python numer
- **Methods**: 72
- **Key Methods**: fresh_env.lib.python3.13.site-packages.numpy.polynomial._polybase.ABCPolyBase.symbol, fresh_env.lib.python3.13.site-packages.numpy.polynomial._polybase.ABCPolyBase.domain, fresh_env.lib.python3.13.site-packages.numpy.polynomial._polybase.ABCPolyBase.window, fresh_env.lib.python3.13.site-packages.numpy.polynomial._polybase.ABCPolyBase.basis_name, fresh_env.lib.python3.13.site-packages.numpy.polynomial._polybase.ABCPolyBase._add, fresh_env.lib.python3.13.site-packages.numpy.polynomial._polybase.ABCPolyBase._sub, fresh_env.lib.python3.13.site-packages.numpy.polynomial._polybase.ABCPolyBase._mul, fresh_env.lib.python3.13.site-packages.numpy.polynomial._polybase.ABCPolyBase._div, fresh_env.lib.python3.13.site-packages.numpy.polynomial._polybase.ABCPolyBase._pow, fresh_env.lib.python3.13.site-packages.numpy.polynomial._polybase.ABCPolyBase._val
- **Inherits**: abc.ABC

### fresh_env.lib.python3.13.site-packages.yaml.scanner.Scanner
- **Methods**: 71
- **Key Methods**: fresh_env.lib.python3.13.site-packages.yaml.scanner.Scanner.__init__, fresh_env.lib.python3.13.site-packages.yaml.scanner.Scanner.check_token, fresh_env.lib.python3.13.site-packages.yaml.scanner.Scanner.peek_token, fresh_env.lib.python3.13.site-packages.yaml.scanner.Scanner.get_token, fresh_env.lib.python3.13.site-packages.yaml.scanner.Scanner.need_more_tokens, fresh_env.lib.python3.13.site-packages.yaml.scanner.Scanner.fetch_more_tokens, fresh_env.lib.python3.13.site-packages.yaml.scanner.Scanner.next_possible_simple_key, fresh_env.lib.python3.13.site-packages.yaml.scanner.Scanner.stale_possible_simple_keys, fresh_env.lib.python3.13.site-packages.yaml.scanner.Scanner.save_possible_simple_key, fresh_env.lib.python3.13.site-packages.yaml.scanner.Scanner.remove_possible_simple_key

### fresh_env.lib.python3.13.site-packages.pip._vendor.rich.console.Console
> A high level console interface.

Args:
    color_system (str, optional): The color system supported 
- **Methods**: 71
- **Key Methods**: fresh_env.lib.python3.13.site-packages.pip._vendor.rich.console.Console.__init__, fresh_env.lib.python3.13.site-packages.pip._vendor.rich.console.Console.__repr__, fresh_env.lib.python3.13.site-packages.pip._vendor.rich.console.Console.file, fresh_env.lib.python3.13.site-packages.pip._vendor.rich.console.Console.file, fresh_env.lib.python3.13.site-packages.pip._vendor.rich.console.Console._buffer, fresh_env.lib.python3.13.site-packages.pip._vendor.rich.console.Console._buffer_index, fresh_env.lib.python3.13.site-packages.pip._vendor.rich.console.Console._buffer_index, fresh_env.lib.python3.13.site-packages.pip._vendor.rich.console.Console._theme_stack, fresh_env.lib.python3.13.site-packages.pip._vendor.rich.console.Console._detect_color_system, fresh_env.lib.python3.13.site-packages.pip._vendor.rich.console.Console._enter_buffer

### fresh_env.lib.python3.13.site-packages.matplotlib.markers.MarkerStyle
> A class representing marker types.

Instances are immutable. If you need to change anything, create 
- **Methods**: 64
- **Key Methods**: fresh_env.lib.python3.13.site-packages.matplotlib.markers.MarkerStyle.__init__, fresh_env.lib.python3.13.site-packages.matplotlib.markers.MarkerStyle._recache, fresh_env.lib.python3.13.site-packages.matplotlib.markers.MarkerStyle.__bool__, fresh_env.lib.python3.13.site-packages.matplotlib.markers.MarkerStyle.is_filled, fresh_env.lib.python3.13.site-packages.matplotlib.markers.MarkerStyle.get_fillstyle, fresh_env.lib.python3.13.site-packages.matplotlib.markers.MarkerStyle._set_fillstyle, fresh_env.lib.python3.13.site-packages.matplotlib.markers.MarkerStyle.get_joinstyle, fresh_env.lib.python3.13.site-packages.matplotlib.markers.MarkerStyle.get_capstyle, fresh_env.lib.python3.13.site-packages.matplotlib.markers.MarkerStyle.get_marker, fresh_env.lib.python3.13.site-packages.matplotlib.markers.MarkerStyle._set_marker

### fresh_env.lib.python3.13.site-packages.matplotlib.lines.Line2D
> A line - the line can have both a solid linestyle connecting all
the vertices, and a marker at each 
- **Methods**: 63
- **Key Methods**: fresh_env.lib.python3.13.site-packages.matplotlib.lines.Line2D.__str__, fresh_env.lib.python3.13.site-packages.matplotlib.lines.Line2D.__init__, fresh_env.lib.python3.13.site-packages.matplotlib.lines.Line2D.contains, fresh_env.lib.python3.13.site-packages.matplotlib.lines.Line2D.get_pickradius, fresh_env.lib.python3.13.site-packages.matplotlib.lines.Line2D.set_pickradius, fresh_env.lib.python3.13.site-packages.matplotlib.lines.Line2D.get_fillstyle, fresh_env.lib.python3.13.site-packages.matplotlib.lines.Line2D.set_fillstyle, fresh_env.lib.python3.13.site-packages.matplotlib.lines.Line2D.set_markevery, fresh_env.lib.python3.13.site-packages.matplotlib.lines.Line2D.get_markevery, fresh_env.lib.python3.13.site-packages.matplotlib.lines.Line2D.set_picker
- **Inherits**: Artist

### fresh_env.lib.python3.13.site-packages.numpy.lib._user_array_impl.container
> container(data, dtype=None, copy=True)

Standard container-class for easy multiple-inheritance.

Met
- **Methods**: 61
- **Key Methods**: fresh_env.lib.python3.13.site-packages.numpy.lib._user_array_impl.container.__init_subclass__, fresh_env.lib.python3.13.site-packages.numpy.lib._user_array_impl.container.__init__, fresh_env.lib.python3.13.site-packages.numpy.lib._user_array_impl.container.__repr__, fresh_env.lib.python3.13.site-packages.numpy.lib._user_array_impl.container.__array__, fresh_env.lib.python3.13.site-packages.numpy.lib._user_array_impl.container.__len__, fresh_env.lib.python3.13.site-packages.numpy.lib._user_array_impl.container.__getitem__, fresh_env.lib.python3.13.site-packages.numpy.lib._user_array_impl.container.__setitem__, fresh_env.lib.python3.13.site-packages.numpy.lib._user_array_impl.container.__abs__, fresh_env.lib.python3.13.site-packages.numpy.lib._user_array_impl.container.__neg__, fresh_env.lib.python3.13.site-packages.numpy.lib._user_array_impl.container.__add__

## Data Transformation Functions

Key functions that process and transform data:

### webops.voice_service.VoiceServiceManager.process_voice_command
> Process voice command and return response.
- **Output to**: fresh_env.lib.python3.13.site-packages.code2logic.terminal.ShellRenderer.print, fresh_env.lib.python3.13.site-packages.code2logic.terminal.ShellRenderer.print, fresh_env.lib.python3.13.site-packages.code2logic.terminal.ShellRenderer.print, fresh_env.lib.python3.13.site-packages.code2logic.terminal.ShellRenderer.print, self._normalize_cache_key

### webops.voice_service.VoiceServiceManager._process_with_mock_pipeline
> Process command using mock pipeline.
- **Output to**: self.pipeline.process, self.broadcast_log, self.executor.execute_command, execution_result.get, hasattr

### webops.voice_service.VoiceServiceManager._process_with_nlp2cmd_service
> Process command using NLP2CMD service.
- **Output to**: pipeline.process, execution_result.get, self._process_with_mock_pipeline, self.broadcast_log, self.executor.execute_command

### webops.voice_service.process_voice_command
> Process voice command and execute shell command.
- **Output to**: app.post, fresh_env.lib.python3.13.site-packages.code2logic.terminal.ShellRenderer.print, fresh_env.lib.python3.13.site-packages.code2logic.terminal.ShellRenderer.print, fresh_env.lib.python3.13.site-packages.code2logic.terminal.ShellRenderer.print, fresh_env.lib.python3.13.site-packages.code2logic.terminal.ShellRenderer.print

### webops.voice_service_clean.VoiceServiceManager.process_voice_command
> Process voice command and return response.
- **Output to**: fresh_env.lib.python3.13.site-packages.code2logic.terminal.ShellRenderer.print, fresh_env.lib.python3.13.site-packages.code2logic.terminal.ShellRenderer.print, fresh_env.lib.python3.13.site-packages.code2logic.terminal.ShellRenderer.print, fresh_env.lib.python3.13.site-packages.code2logic.terminal.ShellRenderer.print, fresh_env.lib.python3.13.site-packages.code2logic.terminal.ShellRenderer.print

### webops.voice_service_clean.process_voice_command
> Process voice command and execute shell command.
- **Output to**: app.post, fresh_env.lib.python3.13.site-packages.code2logic.terminal.ShellRenderer.print, fresh_env.lib.python3.13.site-packages.code2logic.terminal.ShellRenderer.print, fresh_env.lib.python3.13.site-packages.code2logic.terminal.ShellRenderer.print, fresh_env.lib.python3.13.site-packages.code2logic.terminal.ShellRenderer.print

### webops.docker_app.VoiceServiceManager.process_voice_command
> Process voice command and return response.
- **Output to**: self.pipeline.process, VoiceCommandResponse, VoiceCommandResponse, VoiceCommandResponse, VoiceCommandResponse

### webops.docker_app.process_voice_command
> Process voice command and execute shell command.
- **Output to**: app.post, voice_manager.process_voice_command

### demos.demo_intelligent_nlp2cmd.IntelligentNLP2CMD.transform
> Transform natural language to command with version detection.

Args:
    query: Natural language que
- **Output to**: ActionIR, self.base_nlp.transform_ir, self.generator.generate_command, ActionIR, fresh_env.lib.python3.13.site-packages.code2logic.terminal.ShellRenderer.print

### fresh_env.lib.python3.13.site-packages.matplotlib.category.StrCategoryConverter.convert
> Convert strings in *value* to floats using mapping information stored
in the *unit* object.

Paramet
- **Output to**: fresh_env.lib.python3.13.site-packages.matplotlib.category.StrCategoryConverter._validate_unit, np.atleast_1d, unit.update, ValueError, np.array

### fresh_env.lib.python3.13.site-packages.matplotlib.category.StrCategoryConverter._validate_unit
- **Output to**: hasattr, ValueError

### fresh_env.lib.python3.13.site-packages.matplotlib.category.StrCategoryFormatter.format_ticks
- **Output to**: self._text, r_mapping.get, self._units.items, fresh_env.lib.python3.13.site-packages.fontTools.colorLib.geometry.Circle.round

### fresh_env.lib.python3.13.site-packages.matplotlib.category.UnitData._str_is_convertible
> Helper method to check whether a string can be parsed as float or date.
- **Output to**: float, dateutil.parser.parse

### fresh_env.lib.python3.13.site-packages.matplotlib.spines.Spine._recompute_transform
> Notes
-----
This cannot be called until after this has been added to an Axes,
otherwise unit convers
- **Output to**: self.convert_xunits, self.convert_yunits, None.translate, self.convert_xunits, self.convert_yunits

### fresh_env.lib.python3.13.site-packages.matplotlib.spines.Spine.get_patch_transform
- **Output to**: self._recompute_transform, None.get_patch_transform, fresh_env.lib.python3.13.site-packages.jinja2.runtime.Context.super

### fresh_env.lib.python3.13.site-packages.matplotlib.spines.Spine.get_spine_transform
> Return the spine transform.
- **Output to**: self._ensure_position_is_set, isinstance, fresh_env.lib.python3.13.site-packages.matplotlib._api.check_in_list, len, self.axes.get_yaxis_transform

### fresh_env.lib.python3.13.site-packages.matplotlib.patches.Patch._process_radius
- **Output to**: isinstance, self.get_linewidth, self.get_edgecolor

### fresh_env.lib.python3.13.site-packages.matplotlib.patches.Patch.get_transform
> Return the `~.transforms.Transform` applied to the `Patch`.
- **Output to**: self.get_patch_transform, fresh_env.lib.python3.13.site-packages.matplotlib.artist.Artist.get_transform

### fresh_env.lib.python3.13.site-packages.matplotlib.patches.Patch.get_data_transform
> Return the `~.transforms.Transform` mapping data coordinates to
physical coordinates.
- **Output to**: fresh_env.lib.python3.13.site-packages.matplotlib.artist.Artist.get_transform

### fresh_env.lib.python3.13.site-packages.matplotlib.patches.Patch.get_patch_transform
> Return the `~.transforms.Transform` instance mapping patch coordinates
to data coordinates.

For exa
- **Output to**: transforms.IdentityTransform

### fresh_env.lib.python3.13.site-packages.matplotlib.patches.Patch._convert_xy_units
> Convert x and y units for a tuple (x, y).
- **Output to**: self.convert_xunits, self.convert_yunits

### fresh_env.lib.python3.13.site-packages.matplotlib.patches.Shadow._update_transform
- **Output to**: renderer.points_to_pixels, renderer.points_to_pixels, None.translate, self._shadow_transform.clear

### fresh_env.lib.python3.13.site-packages.matplotlib.patches.Shadow.get_patch_transform
- **Output to**: self.patch.get_patch_transform

### fresh_env.lib.python3.13.site-packages.matplotlib.patches.Rectangle._convert_units
> Convert bounds of the rectangle.
- **Output to**: self.convert_xunits, self.convert_yunits, self.convert_xunits, self.convert_yunits

### fresh_env.lib.python3.13.site-packages.matplotlib.patches.Rectangle.get_patch_transform
- **Output to**: self.get_bbox, transforms.BboxTransformTo, None.translate, None.scale, None.rotate_deg

## Behavioral Patterns

### recursion_plot_children
- **Type**: recursion
- **Confidence**: 0.90
- **Functions**: fresh_env.lib.python3.13.site-packages.matplotlib._layoutgrid.plot_children

### recursion_flatten
- **Type**: recursion
- **Confidence**: 0.90
- **Functions**: fresh_env.lib.python3.13.site-packages.matplotlib.cbook.flatten

### recursion_make_layoutgrids
- **Type**: recursion
- **Confidence**: 0.90
- **Functions**: fresh_env.lib.python3.13.site-packages.matplotlib._constrained_layout.make_layoutgrids

### recursion_make_layoutgrids_gs
- **Type**: recursion
- **Confidence**: 0.90
- **Functions**: fresh_env.lib.python3.13.site-packages.matplotlib._constrained_layout.make_layoutgrids_gs

### recursion_check_no_collapsed_axes
- **Type**: recursion
- **Confidence**: 0.90
- **Functions**: fresh_env.lib.python3.13.site-packages.matplotlib._constrained_layout.check_no_collapsed_axes

### recursion_make_layout_margins
- **Type**: recursion
- **Confidence**: 0.90
- **Functions**: fresh_env.lib.python3.13.site-packages.matplotlib._constrained_layout.make_layout_margins

### recursion_make_margin_suptitles
- **Type**: recursion
- **Confidence**: 0.90
- **Functions**: fresh_env.lib.python3.13.site-packages.matplotlib._constrained_layout.make_margin_suptitles

### recursion_match_submerged_margins
- **Type**: recursion
- **Confidence**: 0.90
- **Functions**: fresh_env.lib.python3.13.site-packages.matplotlib._constrained_layout.match_submerged_margins

### recursion_reposition_axes
- **Type**: recursion
- **Confidence**: 0.90
- **Functions**: fresh_env.lib.python3.13.site-packages.matplotlib._constrained_layout.reposition_axes

### recursion_detrend
- **Type**: recursion
- **Confidence**: 0.90
- **Functions**: fresh_env.lib.python3.13.site-packages.matplotlib.mlab.detrend

### recursion__normalize_stix_fontcodes
- **Type**: recursion
- **Confidence**: 0.90
- **Functions**: fresh_env.lib.python3.13.site-packages.matplotlib._mathtext_data._normalize_stix_fontcodes

### recursion_switch_backend
- **Type**: recursion
- **Confidence**: 0.90
- **Functions**: fresh_env.lib.python3.13.site-packages.matplotlib.pyplot.switch_backend

### recursion__py_expr_to_dotted_name
- **Type**: recursion
- **Confidence**: 0.90
- **Functions**: fresh_env.lib.python3.13.site-packages.code2logic.parsers._py_expr_to_dotted_name

### recursion_pformat
- **Type**: recursion
- **Confidence**: 0.90
- **Functions**: fresh_env.lib.python3.13.site-packages.jinja2.utils.pformat

### recursion_has_safe_repr
- **Type**: recursion
- **Confidence**: 0.90
- **Functions**: fresh_env.lib.python3.13.site-packages.jinja2.compiler.has_safe_repr

## Public API Surface

Functions exposed as public API (no underscore prefix):

- `src.nlp2cmd.pipeline_runner_plans.PlanExecutionMixin.execute_action_plan` - 261 calls
- `src.nlp2cmd.cli.commands.run.handle_run_mode` - 261 calls
- `fresh_env.lib.python3.13.site-packages.networkx.generators.social.les_miserables_graph` - 256 calls
- `networkx-3.6.1-py3-none-any.networkx.generators.social.les_miserables_graph` - 256 calls
- `fresh_env.lib.python3.13.site-packages.numpy.f2py.crackfortran.analyzeline` - 237 calls
- `fresh_env.lib.python3.13.site-packages.code2logic.cli.main` - 209 calls
- `src.nlp2cmd.adapters.canvas.CanvasAdapter.execute_drawing_plan` - 193 calls
- `fresh_env.lib.python3.13.site-packages.numpy.lib._npyio_impl.genfromtxt` - 192 calls
- `fresh_env.lib.python3.13.site-packages.networkx.drawing.nx_pylab.display` - 188 calls
- `networkx-3.6.1-py3-none-any.networkx.drawing.nx_pylab.display` - 188 calls
- `fresh_env.lib.python3.13.site-packages.fontTools.varLib.interpolatable.main` - 168 calls
- `fresh_env.lib.python3.13.site-packages.networkx.algorithms.similarity.optimize_edit_paths` - 168 calls
- `networkx-3.6.1-py3-none-any.networkx.algorithms.similarity.optimize_edit_paths` - 168 calls
- `fresh_env.lib.python3.13.site-packages.numpy.f2py.crackfortran.analyzevars` - 156 calls
- `fresh_env.lib.python3.13.site-packages.matplotlib.sankey.Sankey.add` - 151 calls
- `fresh_env.lib.python3.13.site-packages.networkx.algorithms.matching.max_weight_matching` - 150 calls
- `networkx-3.6.1-py3-none-any.networkx.algorithms.matching.max_weight_matching` - 150 calls
- `webops.nlp2cmd-repo.examples.shell.environment_analysis.main` - 143 calls
- `examples.01_basics.shell_fundamentals.environment_analysis.main` - 139 calls
- `fresh_env.lib.python3.13.site-packages.matplotlib.axes._axes.Axes.hist` - 134 calls
- `fresh_env.lib.python3.13.site-packages.charset_normalizer.api.from_bytes` - 126 calls
- `fresh_env.lib.python3.13.site-packages.matplotlib.backends.backend_pdf.PdfFile.embedTTF` - 118 calls
- `src.nlp2cmd.cli.main.main` - 115 calls
- `fresh_env.lib.python3.13.site-packages.numpy.f2py.f90mod_rules.buildhooks` - 114 calls
- `fresh_env.lib.python3.13.site-packages.numpy.f2py.symbolic._FromStringWorker.process` - 113 calls
- `fresh_env.lib.python3.13.site-packages.matplotlib.axes._axes.Axes.hexbin` - 113 calls
- `fresh_env.lib.python3.13.site-packages.matplotlib.backends.qt_editor.figureoptions.figure_edit` - 113 calls
- `src.nlp2cmd.execution.runner.ExecutionRunner.run_command` - 109 calls
- `webops.nlp2cmd-repo.examples.devops.demo.demo_nlp_commands` - 108 calls
- `fresh_env.lib.python3.13.site-packages.fontTools.varLib.interpolatablePlot.InterpolatablePlot.draw_glyph` - 107 calls
- `examples.03_integrations.web_development.demo.demo_nlp_commands` - 106 calls
- `fresh_env.lib.python3.13.site-packages.pip._vendor.rich.pretty.traverse` - 104 calls
- `fresh_env.lib.python3.13.site-packages.matplotlib.axes._axes.Axes.bxp` - 104 calls
- `docker.novnc.demos.demo_desktop_gui.run_demo` - 103 calls
- `fresh_env.lib.python3.13.site-packages.numpy.f2py.rules.buildmodule` - 101 calls
- `webops.nlp2cmd-repo.examples.devops.demo_batch.run_batch_demo` - 99 calls
- `fresh_env.lib.python3.13.site-packages.matplotlib.lines.Line2D.draw` - 97 calls
- `examples.03_integrations.web_development.demo_batch.run_batch_demo` - 95 calls
- `fresh_env.lib.python3.13.site-packages.PIL.PdfParser.PdfParser.get_value` - 94 calls
- `fresh_env.lib.python3.13.site-packages.code2logic.mcp_server.call_tool` - 92 calls

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
    main --> time
    main --> ArgumentParser
    main --> add_argument
    display --> get
    display --> isinstance
    display --> subgraph
    optimize_edit_paths --> _dispatchable
    optimize_edit_paths --> list
    optimize_edit_paths --> len
    add --> sum
    add --> enumerate
    add --> iterable
```

## Reverse Engineering Guidelines

1. **Entry Points**: Start analysis from the entry points listed above
2. **Core Logic**: Focus on classes with many methods
3. **Data Flow**: Follow data transformation functions
4. **Process Flows**: Use the flow diagrams for execution paths
5. **API Surface**: Public API functions reveal the interface

## Context for LLM

Maintain the identified architectural patterns and public API surface when suggesting changes.