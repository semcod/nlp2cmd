"""
Automatic and interactive form detection and filling.

Detects form fields on a page and fills them using:
1. Environment variables from .env
2. JSON data from data/ folder
3. Interactive input (fallback)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from rich.console import Console

from nlp2cmd.web_schema.form_data_loader import FormDataLoader


@dataclass
class FormField:
    """Represents a form field."""
    selector: str
    field_type: str  # text, email, password, textarea, select, checkbox, radio
    name: Optional[str] = None
    id: Optional[str] = None
    label: Optional[str] = None
    placeholder: Optional[str] = None
    required: bool = False
    options: list[str] = field(default_factory=list)  # For select/radio
    
    def get_display_name(self) -> str:
        """Get human-readable field name."""
        for candidate in (self.label, self.placeholder, self.name, self.id):
            if isinstance(candidate, str):
                v = candidate.strip()
                if v:
                    return v
        return "Unnamed field"


@dataclass
class FormData:
    """Collected form data."""
    fields: dict[str, str] = field(default_factory=dict)
    submit_selector: Optional[str] = None


class FormHandler:
    """
    Handles form detection and interactive filling.
    """
    
    def __init__(self, console: Optional[Console] = None, *, use_markdown: bool = False):
        self.console = console or Console()
        self.use_markdown = use_markdown
    
    def _print(self, renderable: Any, *, language: str = "text") -> None:
        """Helper to optionally wrap output in markdown code blocks."""
        if self.use_markdown:
            from nlp2cmd.cli.markdown_output import print_markdown_block
            print_markdown_block(renderable, language=language, console=self.console)
        else:
            self.console.print(renderable)

    def _print_yaml(self, data: Any) -> None:
        if self.use_markdown:
            from nlp2cmd.cli.markdown_output import print_yaml_block
            print_yaml_block(data, console=self.console)
        else:
            from nlp2cmd.utils.yaml_compat import yaml
            self.console.print(yaml.safe_dump(data, sort_keys=False, allow_unicode=True).rstrip())
    
    def detect_form_fields(self, page) -> list[FormField]:
        """
        Detect all form fields on a page.
        
        Args:
            page: Playwright page object
        
        Returns:
            List of FormField objects
        """
        fields = []
        
        # Debug: Show all input fields found
        all_inputs = page.query_selector_all('input')
        self._print_yaml({"status": "form_inputs_total", "count": len(all_inputs)})
        
        # Detect input fields
        inputs = page.query_selector_all('input:not([type="hidden"]):not([type="submit"]):not([type="button"])')
        self._print_yaml({"status": "form_inputs_visible", "count": len(inputs)})
        
        for inp in inputs:
            try:
                inp_type = inp.get_attribute('type') or 'text'
                name = inp.get_attribute('name')
                inp_id = inp.get_attribute('id')
                placeholder = inp.get_attribute('placeholder')
                required = inp.get_attribute('required') is not None
                
                # Debug output
                self._print_yaml(
                    {
                        "status": "form_input_detected",
                        "type": inp_type,
                        "name": name,
                        "id": inp_id,
                        "placeholder": placeholder,
                    }
                )
                
                # Try to find label
                label = None
                if inp_id:
                    label_elem = page.query_selector(f'label[for="{inp_id}"]')
                    if label_elem:
                        label = label_elem.inner_text().strip()
                
                # Generate selector
                if inp_id:
                    selector = f'#{inp_id}'
                elif name:
                    selector = f'input[name="{name}"]'
                else:
                    continue
                
                fields.append(FormField(
                    selector=selector,
                    field_type=inp_type,
                    name=name,
                    id=inp_id,
                    label=label,
                    placeholder=placeholder,
                    required=required,
                ))
            except Exception:
                continue
        
        # Detect textareas
        textareas = page.query_selector_all('textarea')
        self._print_yaml({"status": "form_textareas", "count": len(textareas)})
        
        for ta in textareas:
            try:
                name = ta.get_attribute('name')
                ta_id = ta.get_attribute('id')
                placeholder = ta.get_attribute('placeholder')
                required = ta.get_attribute('required') is not None
                
                # Debug output
                self._print_yaml(
                    {
                        "status": "form_textarea_detected",
                        "name": name,
                        "id": ta_id,
                        "placeholder": placeholder,
                    }
                )
                
                # Try to find label
                label = None
                if ta_id:
                    label_elem = page.query_selector(f'label[for="{ta_id}"]')
                    if label_elem:
                        label = label_elem.inner_text().strip()
                
                # Generate selector
                if ta_id:
                    selector = f'#{ta_id}'
                elif name:
                    selector = f'textarea[name="{name}"]'
                else:
                    continue
                
                fields.append(FormField(
                    selector=selector,
                    field_type='textarea',
                    name=name,
                    id=ta_id,
                    label=label,
                    placeholder=placeholder,
                    required=required,
                ))
            except Exception:
                continue
        
        # Detect contenteditable divs (often used as rich text editors)
        content_editables = page.query_selector_all('[contenteditable="true"]')
        self._print_yaml({"status": "form_contenteditable", "count": len(content_editables)})
        
        for ce in content_editables:
            try:
                ce_id = ce.get_attribute('id')
                ce_class = ce.get_attribute('class')
                
                # Debug output
                self._print_yaml(
                    {
                        "status": "form_contenteditable_detected",
                        "id": ce_id,
                        "class": ce_class,
                    }
                )
                
                # Try to find label by looking for preceding text or label
                label = None
                if ce_id:
                    label_elem = page.query_selector(f'label[for="{ce_id}"]')
                    if label_elem:
                        label = label_elem.inner_text().strip()
                
                # Generate selector
                if ce_id:
                    selector = f'#{ce_id}'
                elif ce_class:
                    selector = f'.{ce_class.replace(" ", ".")}'
                else:
                    continue
                
                fields.append(FormField(
                    selector=selector,
                    field_type='contenteditable',
                    name=None,
                    id=ce_id,
                    label=label,
                    placeholder=None,
                    required=False,
                ))
            except Exception:
                continue
        
        # Detect divs with form-like attributes (common in custom form builders)
        div_inputs = page.query_selector_all('div[role="textbox"], div[data-input], div[data-field]')
        self._print_yaml({"status": "form_div_inputs", "count": len(div_inputs)})
        
        for div in div_inputs:
            try:
                div_id = div.get_attribute('id')
                div_role = div.get_attribute('role')
                data_input = div.get_attribute('data-input')
                data_field = div.get_attribute('data-field')
                
                # Debug output
                self._print_yaml(
                    {
                        "status": "form_div_input_detected",
                        "id": div_id,
                        "role": div_role,
                        "data_input": data_input,
                        "data_field": data_field,
                    }
                )
                
                # Generate selector
                if div_id:
                    selector = f'#{div_id}'
                elif data_input:
                    selector = f'[data-input="{data_input}"]'
                elif data_field:
                    selector = f'[data-field="{data_field}"]'
                else:
                    continue
                
                fields.append(FormField(
                    selector=selector,
                    field_type='div-input',
                    name=data_input or data_field,
                    id=div_id,
                    label=None,
                    placeholder=None,
                    required=False,
                ))
            except Exception:
                continue
        
        # Detect selects
        selects = page.query_selector_all('select')
        
        for sel in selects:
            try:
                name = sel.get_attribute('name')
                sel_id = sel.get_attribute('id')
                required = sel.get_attribute('required') is not None
                
                # Get options
                options = []
                option_elems = sel.query_selector_all('option')
                for opt in option_elems:
                    opt_text = opt.inner_text().strip()
                    if opt_text:
                        options.append(opt_text)
                
                # Try to find label
                label = None
                if sel_id:
                    label_elem = page.query_selector(f'label[for="{sel_id}"]')
                    if label_elem:
                        label = label_elem.inner_text().strip()
                
                # Generate selector
                if sel_id:
                    selector = f'#{sel_id}'
                elif name:
                    selector = f'select[name="{name}"]'
                else:
                    continue
                
                fields.append(FormField(
                    selector=selector,
                    field_type='select',
                    name=name,
                    id=sel_id,
                    label=label,
                    required=required,
                    options=options,
                ))
            except Exception:
                continue
        
        return fields
    
    def detect_submit_button(self, page, data_loader: Optional[FormDataLoader] = None) -> Optional[str]:
        """Detect form submit button."""
        loader = data_loader or FormDataLoader()
        submit_selectors = loader.get_submit_selectors()
        
        for selector in submit_selectors:
            try:
                elem = page.query_selector(selector)
                if elem:
                    return selector
            except Exception:
                continue
        
        return None
    
    def automatic_fill(
        self,
        fields: list[FormField],
        data_loader: Optional[FormDataLoader] = None,
    ) -> FormData:
        """
        Automatically fill form using data from .env and data/*.json files.
        
        Args:
            fields: List of detected form fields
            data_loader: Optional pre-configured FormDataLoader
        
        Returns:
            FormData with values from configuration files
        """
        loader = data_loader or FormDataLoader()
        form_data = FormData()
        
        # Skip internal/hidden-like fields
        skip_fields = loader.get_skip_fields()
        
        self._print("📋 Auto-filling form fields:", language="text")

        filled_rows: list[dict[str, Any]] = []

        def _looks_like_honeypot_or_search(field: FormField) -> bool:
            name = (field.name or "").strip().lower()
            fid = (field.id or "").strip().lower()
            label = (field.label or "").strip().lower()
            placeholder = (field.placeholder or "").strip().lower()
            field_type = (field.field_type or "").strip().lower()

            # Common search widgets
            if field_type == "search":
                return True
            if name in {"s", "q", "search", "query"}:
                return True
            if "search" in placeholder or "search" in label:
                return True
            if "type your search" in placeholder:
                return True

            # Honeypots / anti-bot traps
            if "honeypot" in name or "honeypot" in fid:
                return True
            if name.endswith("[hp]") or "[hp]" in name or "-hp" in name or "_hp" in name:
                return True

            # Captcha
            if "captcha" in name or "captcha" in fid:
                return True
            if "recaptcha" in name or "recaptcha" in fid:
                return True
            if "h-captcha" in name or "h-captcha" in fid:
                return True
            if "g-recaptcha" in name or "g-recaptcha" in fid:
                return True

            return False
        
        for f in fields:
            field_name_lower = (f.name or "").lower()
            
            # Skip internal/hidden-like fields
            if field_name_lower in skip_fields:
                continue

            # Skip fields that are very likely search widgets / honeypots / captchas
            if _looks_like_honeypot_or_search(f):
                continue
            
            # Handle checkbox fields (consent, RODO, etc.)
            if f.field_type == 'checkbox':
                # Check if we should auto-check this checkbox
                consent_value = loader.get_value_for_field(
                    field_name=f.name,
                    field_id=f.id,
                    field_label=f.label,
                    field_placeholder=f.placeholder,
                    field_type='checkbox',
                )
                # Also check for generic FORM_CONSENT
                if not consent_value:
                    consent_value = loader.get_env_value('FORM_CONSENT')
                
                if consent_value and consent_value.lower() in ('true', '1', 'yes', 'tak'):
                    form_data.fields[f.selector] = '__checkbox__'
                    filled_rows.append(
                        {
                            "field": f.get_display_name(),
                            "selector": f.selector,
                            "type": "checkbox",
                            "value": True,
                            "source": ".env / data/",
                        }
                    )
                continue
            
            # Skip radio buttons for now
            if f.field_type == 'radio':
                continue
            
            # Get value from loader
            value = loader.get_value_for_field(
                field_name=f.name,
                field_id=f.id,
                field_label=f.label,
                field_placeholder=f.placeholder,
                field_type=f.field_type,
            )
            
            if value:
                form_data.fields[f.selector] = value
                filled_rows.append(
                    {
                        "field": f.get_display_name(),
                        "selector": f.selector,
                        "type": f.field_type,
                        "value": value,
                        "source": ".env / data/",
                    }
                )
        
        if form_data.fields:
            self._print_yaml(
                {
                    "status": "auto_fill",
                    "filled_count": len(filled_rows),
                    "filled": filled_rows,
                }
            )
        else:
            self._print("No matching data found in .env or data/ files", language="text")
            self._print("Create .env with FORM_NAME, FORM_EMAIL, etc. or data/form_data.json", language="text")
        
        return form_data
    
    def interactive_fill(
        self,
        fields: list[FormField],
        prefill: Optional[dict[str, str]] = None,
    ) -> FormData:
        """
        Interactively collect form data from user.
        
        Args:
            fields: List of detected form fields
            prefill: Optional prefilled values
        
        Returns:
            FormData with collected values
        """
        prefill = prefill or {}
        
        self.console.print("\n[cyan]📋 Form fields detected:[/cyan]\n")

        self._print_yaml(
            {
                "status": "form_fields_detected",
                "count": len(fields),
                "fields": [
                    {
                        "index": i,
                        "field": f.get_display_name(),
                        "type": f.field_type,
                        "required": bool(f.required),
                        "selector": f.selector,
                        "name": f.name,
                        "id": f.id,
                    }
                    for i, f in enumerate(fields, 1)
                ],
            }
        )
        
        # Collect values
        form_data = FormData()
        
        self.console.print("\n[yellow]Enter values for each field (press Enter to skip):[/yellow]\n")
        
        for f in fields:
            field_name = f.get_display_name()
            
            # Check for prefill
            default = prefill.get(f.name or "") or prefill.get(f.id or "") or ""
            
            if f.field_type == 'select' and f.options:
                self.console.print(f"[dim]Options: {', '.join(f.options[:5])}[/dim]")
            
            prompt = f"[bold]{field_name}[/bold]"
            if f.required:
                prompt += " [red]*[/red]"
            if default:
                prompt += f" [{default}]"
            prompt += ": "
            
            value = self.console.input(prompt).strip()
            
            if not value and default:
                value = default
            
            if value:
                form_data.fields[f.selector] = value
        
        return form_data
    
    def fill_form(
        self,
        page,
        form_data: FormData,
        submit: bool = False,
    ) -> bool:
        """
        Fill form fields on page.
        
        Args:
            page: Playwright page object
            form_data: Form data to fill
            submit: Whether to submit the form
        
        Returns:
            True if successful
        """
        for selector, value in form_data.fields.items():
            try:
                elem = page.query_selector(selector)
                if not elem:
                    self.console.print(f"[yellow]Field not found: {selector}[/yellow]")
                    continue
                
                tag = elem.evaluate('el => el.tagName.toLowerCase()')
                inp_type = elem.get_attribute('type') or ''
                
                # Handle checkbox
                if inp_type == 'checkbox' or value == '__checkbox__':
                    is_checked = elem.is_checked()
                    if not is_checked:
                        elem.click()
                    page.wait_for_timeout(200)
                    self.console.print(f"[green]✓[/green] Checked: {selector}")
                    continue
                
                if tag == 'select':
                    elem.select_option(label=value)
                elif tag in ('input', 'textarea'):
                    # Prefer fill without click to avoid pointer interception by overlays/icons.
                    try:
                        elem.fill(value)
                    except Exception:
                        # Fallback: scroll and force-click, then type.
                        try:
                            elem.scroll_into_view_if_needed()
                        except Exception:
                            pass
                        try:
                            elem.click(force=True)
                        except Exception:
                            pass
                        try:
                            elem.fill('')
                        except Exception:
                            pass
                        elem.type(value, delay=30)
                elif tag == 'div' or elem.get_attribute('contenteditable') == 'true':
                    # Handle contenteditable divs and div-based inputs
                    try:
                        elem.fill(value)
                    except Exception:
                        try:
                            elem.scroll_into_view_if_needed()
                        except Exception:
                            pass
                        try:
                            elem.click(force=True)
                        except Exception:
                            pass
                        try:
                            elem.fill('')  # Clear existing content
                        except Exception:
                            pass
                        elem.type(value, delay=30)
                else:
                    # Fallback for other element types
                    try:
                        elem.fill(value)
                    except Exception:
                        try:
                            elem.scroll_into_view_if_needed()
                        except Exception:
                            pass
                        try:
                            elem.click(force=True)
                        except Exception:
                            pass
                        try:
                            elem.fill('')
                        except Exception:
                            pass
                        elem.type(value, delay=30)
                
                page.wait_for_timeout(200)
                self.console.print(f"[green]✓[/green] Filled: {selector}")
                
            except Exception as e:
                self._print_yaml(
                    {
                        "status": "form_fill_error",
                        "selector": selector,
                        "error": str(e),
                    }
                )
                return False
        
        if submit and form_data.submit_selector:
            try:
                page.click(form_data.submit_selector)
                page.wait_for_timeout(1000)
                self.console.print("[green]✓[/green] Form submitted")
            except Exception as e:
                self._print_yaml(
                    {
                        "status": "form_submit_error",
                        "submit_selector": form_data.submit_selector,
                        "error": str(e),
                    }
                )
                return False
        
        return True
