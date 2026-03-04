# System Architecture Analysis

## Overview

- **Project**: .
- **Analysis Mode**: static
- **Total Functions**: 37265
- **Total Classes**: 5837
- **Modules**: 3215
- **Entry Points**: 0

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

## Process Flows

Key execution flows identified:

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

### nlp2cmd.generation.template_generator.TemplateGenerator
> Generate DSL commands from templates.

Uses predefined templates filled with extracted entities.
Fal
- **Methods**: 100
- **Key Methods**: nlp2cmd.generation.template_generator.TemplateGenerator.__init__, nlp2cmd.generation.template_generator.TemplateGenerator._load_defaults_from_json, nlp2cmd.generation.template_generator.TemplateGenerator._load_templates_from_json, nlp2cmd.generation.template_generator.TemplateGenerator._get_default, nlp2cmd.generation.template_generator.TemplateGenerator.generate, nlp2cmd.generation.template_generator.TemplateGenerator._find_alternative_template, nlp2cmd.generation.template_generator.TemplateGenerator._get_intent_aliases, nlp2cmd.generation.template_generator.TemplateGenerator._prepare_entities, nlp2cmd.generation.template_generator.TemplateGenerator._prepare_sql_entities, nlp2cmd.generation.template_generator.TemplateGenerator._prepare_shell_entities

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

### fresh_env.lib.python3.13.site-packages.matplotlib.category.StrCategoryConverter.convert
> Convert strings in *value* to floats using mapping information stored
in the *unit* object.

Paramet
- **Output to**: StrCategoryConverter._validate_unit, np.atleast_1d, unit.update, ValueError, np.array

### fresh_env.lib.python3.13.site-packages.matplotlib.category.StrCategoryConverter._validate_unit
- **Output to**: hasattr, ValueError

### fresh_env.lib.python3.13.site-packages.matplotlib.category.StrCategoryFormatter.format_ticks
- **Output to**: self._text, r_mapping.get, self._units.items, fresh_env.lib.python3.13.site-packages.fontTools.colorLib.geometry.Circle.round

### fresh_env.lib.python3.13.site-packages.matplotlib.category.UnitData._str_is_convertible
> Helper method to check whether a string can be parsed as float or date.
- **Output to**: float, dateutil.parser.parse

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

## Public API Surface

Functions exposed as public API (no underscore prefix):

- `src.nlp2cmd.pipeline_runner_plans.PlanExecutionMixin.execute_action_plan` - 261 calls
- `src.nlp2cmd.cli.commands.run.handle_run_mode` - 261 calls
- `nlp2cmd.pipeline_runner_plans.PlanExecutionMixin.execute_action_plan` - 261 calls
- `nlp2cmd.cli.commands.run.handle_run_mode` - 261 calls
- `fresh_env.lib.python3.13.site-packages.networkx.generators.social.les_miserables_graph` - 256 calls
- `networkx-3.6.1-py3-none-any.networkx.generators.social.les_miserables_graph` - 256 calls
- `fresh_env.lib.python3.13.site-packages.numpy.f2py.crackfortran.analyzeline` - 237 calls
- `fresh_env.lib.python3.13.site-packages.code2logic.cli.main` - 209 calls
- `src.nlp2cmd.adapters.canvas.CanvasAdapter.execute_drawing_plan` - 193 calls
- `nlp2cmd.adapters.canvas.CanvasAdapter.execute_drawing_plan` - 193 calls
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
- `nlp2cmd-repo.examples.shell.environment_analysis.main` - 143 calls
- `examples.01_basics.shell_fundamentals.environment_analysis.main` - 139 calls
- `fresh_env.lib.python3.13.site-packages.matplotlib.axes._axes.Axes.hist` - 134 calls
- `examples.10_online_code_editors.03_adaptive_code.main` - 133 calls
- `fresh_env.lib.python3.13.site-packages.charset_normalizer.api.from_bytes` - 126 calls
- `fresh_env.lib.python3.13.site-packages.matplotlib.backends.backend_pdf.PdfFile.embedTTF` - 118 calls
- `examples.10_online_code_editors.02_mycompiler_run.main` - 116 calls
- `src.nlp2cmd.cli.main.main` - 115 calls
- `nlp2cmd.cli.main.main` - 115 calls
- `fresh_env.lib.python3.13.site-packages.numpy.f2py.f90mod_rules.buildhooks` - 114 calls
- `fresh_env.lib.python3.13.site-packages.numpy.f2py.symbolic._FromStringWorker.process` - 113 calls
- `fresh_env.lib.python3.13.site-packages.matplotlib.axes._axes.Axes.hexbin` - 113 calls
- `fresh_env.lib.python3.13.site-packages.matplotlib.backends.qt_editor.figureoptions.figure_edit` - 113 calls
- `src.nlp2cmd.execution.runner.ExecutionRunner.run_command` - 109 calls
- `nlp2cmd.execution.runner.ExecutionRunner.run_command` - 109 calls
- `webops.nlp2cmd-repo.examples.devops.demo.demo_nlp_commands` - 108 calls
- `nlp2cmd-repo.examples.devops.demo.demo_nlp_commands` - 108 calls
- `fresh_env.lib.python3.13.site-packages.fontTools.varLib.interpolatablePlot.InterpolatablePlot.draw_glyph` - 107 calls
- `examples.03_integrations.web_development.demo.demo_nlp_commands` - 106 calls

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