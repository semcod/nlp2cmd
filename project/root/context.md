# System Architecture Analysis

## Overview

- **Project**: /home/tom/github/wronai/nlp2cmd
- **Primary Language**: python
- **Languages**: python: 2628, shell: 66, cpp: 26, c: 10, javascript: 5
- **Analysis Mode**: static
- **Total Functions**: 35429
- **Total Classes**: 4797
- **Modules**: 2736
- **Entry Points**: 27744

## Architecture by Module

### fresh_env.lib.python3.13.site-packages.fontTools.misc.bezierTools
- **Functions**: 7269
- **Classes**: 71
- **File**: `bezierTools.c`

### fresh_env.lib.python3.13.site-packages.fontTools.varLib.iup
- **Functions**: 3028
- **Classes**: 51
- **File**: `iup.c`

### fresh_env.lib.python3.13.site-packages.fontTools.feaLib.lexer
- **Functions**: 2735
- **Classes**: 6
- **File**: `lexer.c`

### fresh_env.lib.python3.13.site-packages.fontTools.qu2cu.qu2cu
- **Functions**: 2472
- **Classes**: 21
- **File**: `qu2cu.c`

### fresh_env.lib.python3.13.site-packages.fontTools.cu2qu.cu2qu
- **Functions**: 2272
- **Classes**: 12
- **File**: `cu2qu.c`

### fresh_env.lib.python3.13.site-packages.fontTools.pens.momentsPen
- **Functions**: 1536
- **Classes**: 6
- **File**: `momentsPen.c`

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

### fresh_env.lib.python3.13.site-packages.numpy._core.include.numpy.random.libdivide
- **Functions**: 208
- **Classes**: 29
- **File**: `libdivide.h`

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

### fresh_env.lib.python3.13.site-packages.numpy._core.include.numpy.npy_math
- **Functions**: 181
- **File**: `npy_math.h`

### fresh_env.lib.python3.13.site-packages.fontTools.ttLib.tables.otConverters
- **Functions**: 180
- **Classes**: 57
- **File**: `otConverters.py`

## Key Entry Points

Main execution flows into the system:

### src.nlp2cmd.pipeline_runner_plans.PlanExecutionMixin._execute_plan_step
> Execute a single ActionPlan step. Returns extracted value or None.
- **Calls**: self._resolve_plan_variables, Console, fresh_env.lib.python3.13.site-packages.code2logic.terminal.ShellRenderer.print, StepDispatcher.has_handler, params.get, page.goto, page.wait_for_timeout, StepDispatcher.dispatch

### src.nlp2cmd.pipeline_runner_browser.BrowserExecutionMixin._run_dom_multi_action
> Execute multiple browser actions in sequence.
- **Calls**: payload.get, Console, _MarkdownConsoleWrapper, payload.get, RunnerResult, RunnerResult, sync_playwright, p.chromium.launch

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

### src.nlp2cmd.pipeline_runner_plans.PlanExecutionMixin.execute_action_plan
> Execute an ActionPlan step by step using Playwright.

Args:
    plan: ActionPlan instance with steps to execute
    dry_run: If True, only show the pl
- **Calls**: Console, self._detect_desktop_steps, console.print, console.print, enumerate, None.strip, RunnerResult, console.print

### fresh_env.lib.python3.13.site-packages.code2logic.cli.main
- **Calls**: time.time, argparse.ArgumentParser, parser.add_argument, parser.add_argument, parser.add_argument, parser.add_argument, parser.add_argument, parser.add_argument

### src.nlp2cmd.adapters.canvas.CanvasAdapter.execute_drawing_plan
> Execute a canvas drawing plan on a Playwright page.

IMPROVED: Added detailed diagnostic logging for each step.
- **Calls**: plan.get, MouseController, enumerate, json.loads, step.get, step.get, fresh_env.lib.python3.13.site-packages.code2logic.terminal.ShellRenderer.print, fresh_env.lib.python3.13.site-packages.code2logic.terminal.ShellRenderer.print

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

### fresh_env.lib.python3.13.site-packages.matplotlib.sankey.Sankey.add
> Add a simple Sankey diagram with flows at the same hierarchical level.

Parameters
----------
patchlabel : str
    Label to be placed at the center of
- **Calls**: fresh_env.lib.python3.13.site-packages.PIL.ImageStat.Stat.sum, fresh_env.lib.python3.13.site-packages.PIL.ImageStat.Stat.sum, enumerate, enumerate, np.iterable, np.zeros, np.zeros, enumerate

### examples.01_basics.shell_fundamentals.environment_analysis.main
- **Calls**: examples._example_helpers.print_separator, EnvironmentAnalyzer, examples._example_helpers.print_rule, fresh_env.lib.python3.13.site-packages.code2logic.terminal.ShellRenderer.print, examples._example_helpers.print_rule, analyzer.analyze, fresh_env.lib.python3.13.site-packages.code2logic.terminal.ShellRenderer.print, fresh_env.lib.python3.13.site-packages.code2logic.terminal.ShellRenderer.print

### fresh_env.lib.python3.13.site-packages.fontTools.pens.momentsPen.MomentsPen._curveToOne
- **Calls**: cython.locals, cython.locals, cython.locals, cython.locals, cython.locals, cython.locals, cython.locals, cython.locals

### fresh_env.lib.python3.13.site-packages.matplotlib.axes._axes.Axes.hist
> Compute and plot a histogram.

This method uses `numpy.histogram` to bin the data in *x* and count the
number of values in each bin, then draws the di
- **Calls**: _api.make_keyword_only, fresh_env.lib.python3.13.site-packages.matplotlib._preprocess_data, cbook.normalize_kwargs, np.isscalar, _api.check_in_list, _api.check_in_list, _api.check_in_list, cbook._reshape_2D

### examples.10_online_code_editors.03_adaptive_code.main
- **Calls**: argparse.ArgumentParser, parser.add_argument, parser.add_argument, parser.add_argument, parser.add_argument, parser.add_argument, parser.add_argument, parser.parse_args

### fresh_env.lib.python3.13.site-packages.code2logic.cli._code2logic_llm_cli
- **Calls**: argparse.ArgumentParser, parser.add_subparsers, sub.add_parser, sub.add_parser, p_config.add_subparsers, config_sub.add_parser, sub.add_parser, p_set_provider.add_argument

### fresh_env.lib.python3.13.site-packages.matplotlib.backends.backend_pdf.PdfFile.embedTTF
> Embed the TTF font from the named file into the document.
- **Calls**: fresh_env.lib.python3.13.site-packages.matplotlib.font_manager.get_font, self._get_subsetted_psname, ps_name.encode, Name, self.reserveObject, self.reserveObject, self.reserveObject, self.reserveObject

### fresh_env.lib.python3.13.site-packages.fontTools.misc.bezierTools.__pyx_pymod_exec_bezierTools
- **Calls**: fresh_env.lib.python3.13.site-packages.fontTools.misc.bezierTools.PyErr_SetString, fresh_env.lib.python3.13.site-packages.fontTools.misc.bezierTools.__Pyx_NewRef, fresh_env.lib.python3.13.site-packages.fontTools.misc.bezierTools.Py_INCREF, fresh_env.lib.python3.13.site-packages.fontTools.misc.bezierTools.PyModule_Create, fresh_env.lib.python3.13.site-packages.fontTools.misc.bezierTools.unlikely, fresh_env.lib.python3.13.site-packages.fontTools.misc.bezierTools.__PYX_ERR, fresh_env.lib.python3.13.site-packages.fontTools.misc.bezierTools.__Pyx_State_AddModule, fresh_env.lib.python3.13.site-packages.fontTools.misc.bezierTools.PyUnstable_Module_SetGIL

### fresh_env.lib.python3.13.site-packages.code2logic.parsers.UniversalParser._parse_js_ts
> Parse JS/TS using regex patterns.
- **Calls**: re.finditer, re.finditer, re.finditer, re.finditer, re.finditer, re.finditer, re.finditer, re.finditer

### examples.10_online_code_editors.02_mycompiler_run.main
- **Calls**: argparse.ArgumentParser, parser.add_argument, parser.add_argument, parser.add_argument, parser.add_argument, parser.add_argument, parser.add_argument, parser.add_argument

### fresh_env.lib.python3.13.site-packages.numpy.f2py.f90mod_rules.buildhooks
- **Calls**: fresh_env.lib.python3.13.site-packages.numpy.f2py.auxfuncs.getuseblocks, fresh_env.lib.python3.13.site-packages.numpy.f2py.f90mod_rules.findf90modules, fresh_env.lib.python3.13.site-packages.numpy.f2py.auxfuncs.hasbody, None.keys, fresh_env.lib.python3.13.site-packages.numpy.f2py.crackfortran.outmess, capi_maps.modsign2map, cadd, dadd

### fresh_env.lib.python3.13.site-packages.numpy.f2py.symbolic._FromStringWorker.process
> Parse string within the given context.

The context may define the result in case of ambiguous
expressions. For instance, consider expressions `f(x, y
- **Calls**: isinstance, isinstance, fresh_env.lib.python3.13.site-packages.numpy.f2py.symbolic.replace_parenthesis, r.strip, re.match, re.match, re.split, re.split

### fresh_env.lib.python3.13.site-packages.matplotlib.axes._axes.Axes.hexbin
> Make a 2D hexagonal binning plot of points *x*, *y*.

If *C* is *None*, the value of the hexagon is determined by the number
of points in the hexagon.
- **Calls**: _api.make_keyword_only, fresh_env.lib.python3.13.site-packages.matplotlib._preprocess_data, self._process_unit_info, cbook.delete_masked_points, np.iterable, np.asarray, np.asarray, None.astype

### fresh_env.lib.python3.13.site-packages.matplotlib.backends.qt_editor.figureoptions.figure_edit
> Edit matplotlib figure options
- **Calls**: axes.get_lines, bool, bool, _formlayout.fedit, isinstance, fresh_env.lib.python3.13.site-packages.fontTools.varLib.avar.map.map, tuple, axis.get_converter

### fresh_env.lib.python3.13.site-packages.matplotlib._mathtext.Parser.__init__
- **Calls**: types.SimpleNamespace, Regex, None.leave_whitespace, csnames, Literal, fresh_env.lib.python3.13.site-packages.pyparsing.helpers.one_of, Forward, Forward

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

### fresh_env.lib.python3.13.site-packages.matplotlib.axes._axes.Axes.bxp
> Draw a box and whisker plot from pre-computed statistics.

The box extends from the first quartile *q1* to the third
quartile *q3* of the data, with a
- **Calls**: _api.make_keyword_only, merge_kw_rc, merge_kw_rc, merge_kw_rc, merge_kw_rc, merge_kw_rc, _api.check_in_list, len

### fresh_env.lib.python3.13.site-packages.numpy.f2py.rules.buildmodule
> Return
- **Calls**: fresh_env.lib.python3.13.site-packages.numpy.f2py.crackfortran.outmess, capi_maps.modsign2map, fresh_env.lib.python3.13.site-packages.numpy.f2py.auxfuncs.dictappend, common_rules.buildhooks, fresh_env.lib.python3.13.site-packages.numpy.f2py.auxfuncs.applyrules, fresh_env.lib.python3.13.site-packages.numpy.f2py.auxfuncs.dictappend, f90mod_rules.buildhooks, fresh_env.lib.python3.13.site-packages.numpy.f2py.auxfuncs.applyrules

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
les_miserables_graph [fresh_env.lib.python3.13.site-packages.networkx.generators.social]
```

### Flow 4: execute_action_plan
```
execute_action_plan [src.nlp2cmd.pipeline_runner_plans.PlanExecutionMixin]
```

### Flow 5: main
```
main [fresh_env.lib.python3.13.site-packages.code2logic.cli]
```

### Flow 6: execute_drawing_plan
```
execute_drawing_plan [src.nlp2cmd.adapters.canvas.CanvasAdapter]
```

### Flow 7: display
```
display [fresh_env.lib.python3.13.site-packages.networkx.drawing.nx_pylab]
```

### Flow 8: add
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

### Flow 9: _curveToOne
```
_curveToOne [fresh_env.lib.python3.13.site-packages.fontTools.pens.momentsPen.MomentsPen]
```

### Flow 10: hist
```
hist [fresh_env.lib.python3.13.site-packages.matplotlib.axes._axes.Axes]
  └─ →> _preprocess_data
      └─ →> list
```

## Key Classes

### fresh_env.lib.python3.13.site-packages.fontTools.qu2cu.qu2cu.__Pyx_CodeObjectCache
- **Methods**: 530
- **Key Methods**: fresh_env.lib.python3.13.site-packages.fontTools.qu2cu.qu2cu.__Pyx_CodeObjectCache.__pyx__insert_code_object, fresh_env.lib.python3.13.site-packages.fontTools.qu2cu.qu2cu.__Pyx_CodeObjectCache.__pyx_atomic_sub, fresh_env.lib.python3.13.site-packages.fontTools.qu2cu.qu2cu.__Pyx_CodeObjectCache.Py_DECREF, fresh_env.lib.python3.13.site-packages.fontTools.qu2cu.qu2cu.__Pyx_CodeObjectCache.PyErr_Clear, fresh_env.lib.python3.13.site-packages.fontTools.qu2cu.qu2cu.__Pyx_CodeObjectCache.PyErr_Fetch, fresh_env.lib.python3.13.site-packages.fontTools.qu2cu.qu2cu.__Pyx_CodeObjectCache.Py_DECREF, fresh_env.lib.python3.13.site-packages.fontTools.qu2cu.qu2cu.__Pyx_CodeObjectCache.__pyx_insert_code_object, fresh_env.lib.python3.13.site-packages.fontTools.qu2cu.qu2cu.__Pyx_CodeObjectCache.PyErr_Restore, fresh_env.lib.python3.13.site-packages.fontTools.qu2cu.qu2cu.__Pyx_CodeObjectCache.Py_XDECREF, fresh_env.lib.python3.13.site-packages.fontTools.qu2cu.qu2cu.__Pyx_CodeObjectCache.Py_XDECREF

### fresh_env.lib.python3.13.site-packages.fontTools.ttLib.ttFont.TTFont
> Represents a TrueType font.

The object manages file input and output, and offers a convenient way o
- **Methods**: 213
- **Key Methods**: fresh_env.lib.python3.13.site-packages.fontTools.ttLib.ttFont.TTFont.__init__, fresh_env.lib.python3.13.site-packages.fontTools.ttLib.ttFont.TTFont.__enter__, fresh_env.lib.python3.13.site-packages.fontTools.ttLib.ttFont.TTFont.__exit__, fresh_env.lib.python3.13.site-packages.fontTools.ttLib.ttFont.TTFont.close, fresh_env.lib.python3.13.site-packages.fontTools.ttLib.ttFont.TTFont.save, fresh_env.lib.python3.13.site-packages.fontTools.ttLib.ttFont.TTFont._save, fresh_env.lib.python3.13.site-packages.fontTools.ttLib.ttFont.TTFont.saveXML, fresh_env.lib.python3.13.site-packages.fontTools.ttLib.ttFont.TTFont._saveXML, fresh_env.lib.python3.13.site-packages.fontTools.ttLib.ttFont.TTFont._tableToXML, fresh_env.lib.python3.13.site-packages.fontTools.ttLib.ttFont.TTFont.importXML
- **Inherits**: object

### fresh_env.lib.python3.13.site-packages.fontTools.feaLib.lexer.__PYX_IS_UNSIGNED_IMPL
- **Methods**: 174
- **Key Methods**: fresh_env.lib.python3.13.site-packages.fontTools.feaLib.lexer.__PYX_IS_UNSIGNED_IMPL.__Pyx_init_co_variables, fresh_env.lib.python3.13.site-packages.fontTools.feaLib.lexer.__PYX_IS_UNSIGNED_IMPL.__Pyx_CyOrPyCFunction_GET_SELF, fresh_env.lib.python3.13.site-packages.fontTools.feaLib.lexer.__PYX_IS_UNSIGNED_IMPL.__Pyx__IsSameCFunction, fresh_env.lib.python3.13.site-packages.fontTools.feaLib.lexer.__PYX_IS_UNSIGNED_IMPL.PyCFunction_Check, fresh_env.lib.python3.13.site-packages.fontTools.feaLib.lexer.__PYX_IS_UNSIGNED_IMPL.PyCFunction_Check, fresh_env.lib.python3.13.site-packages.fontTools.feaLib.lexer.__PYX_IS_UNSIGNED_IMPL.Py_FatalError, fresh_env.lib.python3.13.site-packages.fontTools.feaLib.lexer.__PYX_IS_UNSIGNED_IMPL.__Pyx_PyType_GetSlot, fresh_env.lib.python3.13.site-packages.fontTools.feaLib.lexer.__PYX_IS_UNSIGNED_IMPL.__Pyx_PyDict_GetItemStr, fresh_env.lib.python3.13.site-packages.fontTools.feaLib.lexer.__PYX_IS_UNSIGNED_IMPL.__Pyx_PyDict_GetItemStrWithError, fresh_env.lib.python3.13.site-packages.fontTools.feaLib.lexer.__PYX_IS_UNSIGNED_IMPL.PyDict_GetItem

### fresh_env.lib.python3.13.site-packages.fontTools.cu2qu.cu2qu.__pyx_obj_9fontTools_5cu2qu_5cu2qu___pyx_scope_struct___split_cubic_into_n_gen
- **Methods**: 171
- **Key Methods**: fresh_env.lib.python3.13.site-packages.fontTools.cu2qu.cu2qu.__pyx_obj_9fontTools_5cu2qu_5cu2qu___pyx_scope_struct___split_cubic_into_n_gen.__Pyx_RefNannySetupContext, fresh_env.lib.python3.13.site-packages.fontTools.cu2qu.cu2qu.__pyx_obj_9fontTools_5cu2qu_5cu2qu___pyx_scope_struct___split_cubic_into_n_gen.__Pyx_RefNannyFinishContext, fresh_env.lib.python3.13.site-packages.fontTools.cu2qu.cu2qu.__pyx_obj_9fontTools_5cu2qu_5cu2qu___pyx_scope_struct___split_cubic_into_n_gen.__PYX_ERR, fresh_env.lib.python3.13.site-packages.fontTools.cu2qu.cu2qu.__pyx_obj_9fontTools_5cu2qu_5cu2qu___pyx_scope_struct___split_cubic_into_n_gen.__Pyx_GOTREF, fresh_env.lib.python3.13.site-packages.fontTools.cu2qu.cu2qu.__pyx_obj_9fontTools_5cu2qu_5cu2qu___pyx_scope_struct___split_cubic_into_n_gen.__PYX_ERR, fresh_env.lib.python3.13.site-packages.fontTools.cu2qu.cu2qu.__pyx_obj_9fontTools_5cu2qu_5cu2qu___pyx_scope_struct___split_cubic_into_n_gen.__Pyx_INCREF, fresh_env.lib.python3.13.site-packages.fontTools.cu2qu.cu2qu.__pyx_obj_9fontTools_5cu2qu_5cu2qu___pyx_scope_struct___split_cubic_into_n_gen.__Pyx_INCREF, fresh_env.lib.python3.13.site-packages.fontTools.cu2qu.cu2qu.__pyx_obj_9fontTools_5cu2qu_5cu2qu___pyx_scope_struct___split_cubic_into_n_gen.__Pyx_INCREF, fresh_env.lib.python3.13.site-packages.fontTools.cu2qu.cu2qu.__pyx_obj_9fontTools_5cu2qu_5cu2qu___pyx_scope_struct___split_cubic_into_n_gen.__Pyx_INCREF, fresh_env.lib.python3.13.site-packages.fontTools.cu2qu.cu2qu.__pyx_obj_9fontTools_5cu2qu_5cu2qu___pyx_scope_struct___split_cubic_into_n_gen.__Pyx_XGOTREF

### fresh_env.lib.python3.13.site-packages.matplotlib.axes._base._AxesBase
- **Methods**: 162
- **Key Methods**: fresh_env.lib.python3.13.site-packages.matplotlib.axes._base._AxesBase._axis_map, fresh_env.lib.python3.13.site-packages.matplotlib.axes._base._AxesBase.__str__, fresh_env.lib.python3.13.site-packages.matplotlib.axes._base._AxesBase.__init__, fresh_env.lib.python3.13.site-packages.matplotlib.axes._base._AxesBase.__init_subclass__, fresh_env.lib.python3.13.site-packages.matplotlib.axes._base._AxesBase.__getstate__, fresh_env.lib.python3.13.site-packages.matplotlib.axes._base._AxesBase.__setstate__, fresh_env.lib.python3.13.site-packages.matplotlib.axes._base._AxesBase.__repr__, fresh_env.lib.python3.13.site-packages.matplotlib.axes._base._AxesBase.get_subplotspec, fresh_env.lib.python3.13.site-packages.matplotlib.axes._base._AxesBase.set_subplotspec, fresh_env.lib.python3.13.site-packages.matplotlib.axes._base._AxesBase.get_gridspec
- **Inherits**: martist.Artist

### fresh_env.lib.python3.13.site-packages.fontTools.pens.momentsPen.PyModuleDef
- **Methods**: 139
- **Key Methods**: fresh_env.lib.python3.13.site-packages.fontTools.pens.momentsPen.PyModuleDef.sizeof, fresh_env.lib.python3.13.site-packages.fontTools.pens.momentsPen.PyModuleDef.PyInit_momentsPen, fresh_env.lib.python3.13.site-packages.fontTools.pens.momentsPen.PyModuleDef.PyInit_momentsPen, fresh_env.lib.python3.13.site-packages.fontTools.pens.momentsPen.PyModuleDef.PyModuleDef_Init, fresh_env.lib.python3.13.site-packages.fontTools.pens.momentsPen.PyModuleDef.__Pyx_GetCurrentInterpreterId, fresh_env.lib.python3.13.site-packages.fontTools.pens.momentsPen.PyModuleDef.PyErr_Clear, fresh_env.lib.python3.13.site-packages.fontTools.pens.momentsPen.PyModuleDef.Py_DECREF, fresh_env.lib.python3.13.site-packages.fontTools.pens.momentsPen.PyModuleDef.Py_DECREF, fresh_env.lib.python3.13.site-packages.fontTools.pens.momentsPen.PyModuleDef.Py_DECREF, fresh_env.lib.python3.13.site-packages.fontTools.pens.momentsPen.PyModuleDef.PySys_WriteStderr

### fresh_env.lib.python3.13.site-packages.fontTools.pens.momentsPen.__PYX_IS_UNSIGNED_IMPL
- **Methods**: 124
- **Key Methods**: fresh_env.lib.python3.13.site-packages.fontTools.pens.momentsPen.__PYX_IS_UNSIGNED_IMPL.__Pyx_init_co_variables, fresh_env.lib.python3.13.site-packages.fontTools.pens.momentsPen.__PYX_IS_UNSIGNED_IMPL.__Pyx_CyOrPyCFunction_GET_SELF, fresh_env.lib.python3.13.site-packages.fontTools.pens.momentsPen.__PYX_IS_UNSIGNED_IMPL.__Pyx__IsSameCFunction, fresh_env.lib.python3.13.site-packages.fontTools.pens.momentsPen.__PYX_IS_UNSIGNED_IMPL.PyCFunction_Check, fresh_env.lib.python3.13.site-packages.fontTools.pens.momentsPen.__PYX_IS_UNSIGNED_IMPL.PyCFunction_Check, fresh_env.lib.python3.13.site-packages.fontTools.pens.momentsPen.__PYX_IS_UNSIGNED_IMPL.Py_FatalError, fresh_env.lib.python3.13.site-packages.fontTools.pens.momentsPen.__PYX_IS_UNSIGNED_IMPL.__Pyx_PyType_GetSlot, fresh_env.lib.python3.13.site-packages.fontTools.pens.momentsPen.__PYX_IS_UNSIGNED_IMPL.__Pyx_PyDict_GetItemStr, fresh_env.lib.python3.13.site-packages.fontTools.pens.momentsPen.__PYX_IS_UNSIGNED_IMPL.__Pyx_PyDict_GetItemStrWithError, fresh_env.lib.python3.13.site-packages.fontTools.pens.momentsPen.__PYX_IS_UNSIGNED_IMPL.PyDict_GetItem

### fresh_env.lib.python3.13.site-packages.numpy._core.include.numpy.random.libdivide.libdivide_s64_branchfree_t
- **Methods**: 109
- **Key Methods**: fresh_env.lib.python3.13.site-packages.numpy._core.include.numpy.random.libdivide.libdivide_s64_branchfree_t.libdivide_s64_do, fresh_env.lib.python3.13.site-packages.numpy._core.include.numpy.random.libdivide.libdivide_s64_branchfree_t.libdivide_s64_branchfree_do, fresh_env.lib.python3.13.site-packages.numpy._core.include.numpy.random.libdivide.libdivide_s64_branchfree_t.libdivide_s64_recover, fresh_env.lib.python3.13.site-packages.numpy._core.include.numpy.random.libdivide.libdivide_s64_branchfree_t.libdivide_s64_branchfree_recover, fresh_env.lib.python3.13.site-packages.numpy._core.include.numpy.random.libdivide.libdivide_s64_branchfree_t.libdivide_s64_recover, fresh_env.lib.python3.13.site-packages.numpy._core.include.numpy.random.libdivide.libdivide_s64_branchfree_t.libdivide_u32_do_vector, fresh_env.lib.python3.13.site-packages.numpy._core.include.numpy.random.libdivide.libdivide_s64_branchfree_t.libdivide_s32_do_vector, fresh_env.lib.python3.13.site-packages.numpy._core.include.numpy.random.libdivide.libdivide_s64_branchfree_t.libdivide_u64_do_vector, fresh_env.lib.python3.13.site-packages.numpy._core.include.numpy.random.libdivide.libdivide_s64_branchfree_t.libdivide_s64_do_vector, fresh_env.lib.python3.13.site-packages.numpy._core.include.numpy.random.libdivide.libdivide_s64_branchfree_t.libdivide_u32_branchfree_do_vector

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

## Data Transformation Functions

Key functions that process and transform data:

### demos.demo_intelligent_nlp2cmd.IntelligentNLP2CMD.transform
> Transform natural language to command with version detection.

Args:
    query: Natural language que
- **Output to**: ActionIR, self.base_nlp.transform_ir, self.generator.generate_command, ActionIR, fresh_env.lib.python3.13.site-packages.code2logic.terminal.ShellRenderer.print

### webops.docker_app.VoiceServiceManager.process_voice_command
> Process voice command and return response.
- **Output to**: self.pipeline.process, VoiceCommandResponse, VoiceCommandResponse, VoiceCommandResponse, VoiceCommandResponse

### webops.docker_app.process_voice_command
> Process voice command and execute shell command.
- **Output to**: app.post, voice_manager.process_voice_command

### webops.voice_service_clean.VoiceServiceManager.process_voice_command
> Process voice command and return response.
- **Output to**: fresh_env.lib.python3.13.site-packages.code2logic.terminal.ShellRenderer.print, fresh_env.lib.python3.13.site-packages.code2logic.terminal.ShellRenderer.print, fresh_env.lib.python3.13.site-packages.code2logic.terminal.ShellRenderer.print, fresh_env.lib.python3.13.site-packages.code2logic.terminal.ShellRenderer.print, fresh_env.lib.python3.13.site-packages.code2logic.terminal.ShellRenderer.print

### webops.voice_service_clean.process_voice_command
> Process voice command and execute shell command.
- **Output to**: app.post, fresh_env.lib.python3.13.site-packages.code2logic.terminal.ShellRenderer.print, fresh_env.lib.python3.13.site-packages.code2logic.terminal.ShellRenderer.print, fresh_env.lib.python3.13.site-packages.code2logic.terminal.ShellRenderer.print, fresh_env.lib.python3.13.site-packages.code2logic.terminal.ShellRenderer.print

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
- **Output to**: self._ensure_position_is_set, isinstance, _api.check_in_list, len, self.axes.get_yaxis_transform

### fresh_env.lib.python3.13.site-packages.matplotlib.patches.Patch._process_radius
- **Output to**: isinstance, self.get_linewidth, self.get_edgecolor

### fresh_env.lib.python3.13.site-packages.matplotlib.patches.Patch.get_transform
> Return the `~.transforms.Transform` applied to the `Patch`.
- **Output to**: self.get_patch_transform, artist.Artist.get_transform

### fresh_env.lib.python3.13.site-packages.matplotlib.patches.Patch.get_data_transform
> Return the `~.transforms.Transform` mapping data coordinates to
physical coordinates.
- **Output to**: artist.Artist.get_transform

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

### fresh_env.lib.python3.13.site-packages.matplotlib.patches.RegularPolygon.get_patch_transform
- **Output to**: None.translate, None.rotate, None.scale, self._patch_transform.clear

### fresh_env.lib.python3.13.site-packages.matplotlib.patches.Arrow.get_patch_transform

### fresh_env.lib.python3.13.site-packages.matplotlib.patches.Ellipse._recompute_transform
> Notes
-----
This cannot be called until after this has been added to an Axes,
otherwise unit convers
- **Output to**: self.convert_xunits, self.convert_yunits, None.translate, self.convert_xunits, self.convert_yunits

### fresh_env.lib.python3.13.site-packages.matplotlib.patches.Ellipse.get_patch_transform
- **Output to**: self._recompute_transform

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

### recursion_reset_margins
- **Type**: recursion
- **Confidence**: 0.90
- **Functions**: fresh_env.lib.python3.13.site-packages.matplotlib._constrained_layout.reset_margins

### recursion__get_renderer
- **Type**: recursion
- **Confidence**: 0.90
- **Functions**: fresh_env.lib.python3.13.site-packages.matplotlib.figure.Figure._get_renderer

### recursion_reversed
- **Type**: recursion
- **Confidence**: 0.90
- **Functions**: fresh_env.lib.python3.13.site-packages.matplotlib.colors.LinearSegmentedColormap.reversed

### recursion_reversed
- **Type**: recursion
- **Confidence**: 0.90
- **Functions**: fresh_env.lib.python3.13.site-packages.matplotlib.colors.ListedColormap.reversed

### recursion_detrend
- **Type**: recursion
- **Confidence**: 0.90
- **Functions**: fresh_env.lib.python3.13.site-packages.matplotlib.mlab.detrend

### recursion__normalize_stix_fontcodes
- **Type**: recursion
- **Confidence**: 0.90
- **Functions**: fresh_env.lib.python3.13.site-packages.matplotlib._mathtext_data._normalize_stix_fontcodes

## Public API Surface

Functions exposed as public API (no underscore prefix):

- `src.nlp2cmd.cli.commands.run.handle_run_mode` - 261 calls
- `fresh_env.lib.python3.13.site-packages.networkx.generators.social.les_miserables_graph` - 256 calls
- `networkx-3.6.1-py3-none-any.networkx.generators.social.les_miserables_graph` - 256 calls
- `fresh_env.lib.python3.13.site-packages.numpy.f2py.crackfortran.analyzeline` - 237 calls
- `src.nlp2cmd.pipeline_runner_plans.PlanExecutionMixin.execute_action_plan` - 219 calls
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
- `examples.01_basics.shell_fundamentals.environment_analysis.main` - 139 calls
- `fresh_env.lib.python3.13.site-packages.matplotlib.axes._axes.Axes.hist` - 134 calls
- `examples.10_online_code_editors.03_adaptive_code.main` - 133 calls
- `fresh_env.lib.python3.13.site-packages.charset_normalizer.api.from_bytes` - 126 calls
- `fresh_env.lib.python3.13.site-packages.matplotlib.backends.backend_pdf.PdfFile.embedTTF` - 118 calls
- `examples.10_online_code_editors.02_mycompiler_run.main` - 116 calls
- `src.nlp2cmd.cli.main.main` - 115 calls
- `fresh_env.lib.python3.13.site-packages.numpy.f2py.f90mod_rules.buildhooks` - 114 calls
- `fresh_env.lib.python3.13.site-packages.numpy.f2py.symbolic._FromStringWorker.process` - 113 calls
- `fresh_env.lib.python3.13.site-packages.matplotlib.axes._axes.Axes.hexbin` - 113 calls
- `fresh_env.lib.python3.13.site-packages.matplotlib.backends.qt_editor.figureoptions.figure_edit` - 113 calls
- `src.nlp2cmd.execution.runner.ExecutionRunner.run_command` - 109 calls
- `fresh_env.lib.python3.13.site-packages.fontTools.varLib.interpolatablePlot.InterpolatablePlot.draw_glyph` - 107 calls
- `examples.03_integrations.web_development.demo.demo_nlp_commands` - 106 calls
- `fresh_env.lib.python3.13.site-packages.pip._vendor.rich.pretty.traverse` - 104 calls
- `fresh_env.lib.python3.13.site-packages.matplotlib.axes._axes.Axes.bxp` - 104 calls
- `docker.novnc.demos.demo_desktop_gui.run_demo` - 103 calls
- `fresh_env.lib.python3.13.site-packages.numpy.f2py.rules.buildmodule` - 101 calls
- `fresh_env.lib.python3.13.site-packages.matplotlib.lines.Line2D.draw` - 97 calls
- `examples.03_integrations.web_development.demo_batch.run_batch_demo` - 95 calls
- `fresh_env.lib.python3.13.site-packages.PIL.PdfParser.PdfParser.get_value` - 94 calls
- `examples.09_online_drawing._old.03_adaptive_drawing.main` - 93 calls
- `fresh_env.lib.python3.13.site-packages.code2logic.mcp_server.call_tool` - 92 calls

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
    main --> time
    main --> ArgumentParser
    main --> add_argument
    execute_drawing_plan --> get
    execute_drawing_plan --> MouseController
    execute_drawing_plan --> enumerate
    execute_drawing_plan --> loads
    display --> get
    display --> isinstance
    display --> subgraph
    add --> sum
    add --> enumerate
    add --> iterable
    main --> print_separator
```

## Reverse Engineering Guidelines

1. **Entry Points**: Start analysis from the entry points listed above
2. **Core Logic**: Focus on classes with many methods
3. **Data Flow**: Follow data transformation functions
4. **Process Flows**: Use the flow diagrams for execution paths
5. **API Surface**: Public API functions reveal the interface

## Context for LLM

Maintain the identified architectural patterns and public API surface when suggesting changes.