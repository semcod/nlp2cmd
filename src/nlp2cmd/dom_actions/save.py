"""Save data DOM action handlers."""

from __future__ import annotations
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from .base import DomAction, ActionContext, ActionResult
from .registry import register_action

if TYPE_CHECKING:
    pass


@register_action("save_to_file")
class SaveToFileAction(DomAction):
    """Save extracted data to a text file."""
    
    def execute(self, ctx: ActionContext) -> ActionResult:
        """Save extracted data to a file with optional clipboard copy."""
        try:
            filename = ctx.action_spec.get("filename", "extracted_data.txt")
            also_copy = bool(ctx.action_spec.get("also_copy") or ctx.action_spec.get("copy_to_clipboard"))
            also_print = bool(ctx.action_spec.get("also_print") or ctx.action_spec.get("print_to_terminal"))
            
            self._debug(f"save_to_file: saving {len(ctx.extracted_data)} items to {filename}")
            
            if not ctx.extracted_data:
                ctx.console.print("⚠️  No data to save", language="text")
                return ActionResult(success=True)  # Not an error, just no data
            
            filepath = Path(filename)
            lines = self._extract_lines(ctx.extracted_data)
            
            if not lines:
                ctx.console.print("⚠️  No valid data to save", language="text")
                return ActionResult(success=True)
            
            filepath.write_text("\n".join(lines) + "\n", encoding="utf-8")
            
            ctx.console.print(f"💾 Saved {len(lines)} entries to {filepath.resolve()}", language="text")
            
            if also_print:
                try:
                    ctx.console.print("\n".join(lines), language="text")
                except Exception as pe:
                    self._debug(f"save_to_file: print failed: {pe}")
            
            if also_copy:
                self._copy_to_clipboard(ctx, lines)
            
            return ActionResult(
                success=True,
                data={"filename": str(filepath.resolve()), "entries": len(lines)}
            )
            
        except Exception as e:
            return ActionResult(
                success=False,
                error=f"Save to file failed: {e}"
            )
    
    def _extract_lines(self, extracted_data: list) -> list[str]:
        """Extract valid lines from data."""
        seen: set[str] = set()
        lines: list[str] = []
        
        has_website_field = any("website" in it for it in extracted_data if isinstance(it, dict))
        has_real_websites = False
        
        if has_website_field:
            for it in extracted_data:
                if isinstance(it, dict):
                    w = str(it.get("website") or "").strip()
                    if w and not self._is_bad_website(w):
                        has_real_websites = True
                        break
        
        for item in extracted_data:
            candidate = self._extract_candidate(item, has_website_field, has_real_websites)
            if not candidate:
                continue
            
            key = candidate.lower()
            if key in seen:
                continue
            seen.add(key)
            lines.append(candidate)
        
        return lines
    
    def _extract_candidate(self, item: dict, has_website_field: bool, has_real_websites: bool) -> str:
        """Extract candidate URL from item."""
        if isinstance(item, dict):
            candidate = ""
            if has_website_field:
                if has_real_websites:
                    if item.get("website"):
                        candidate = str(item.get("website") or "").strip()
                else:
                    # Fallback: use profile URLs
                    if item.get("oferteo_url"):
                        candidate = str(item.get("oferteo_url") or "").strip()
                    elif item.get("url"):
                        candidate = str(item.get("url") or "").strip()
            elif item.get("url"):
                candidate = str(item.get("url") or "").strip()
            elif item.get("oferteo_url"):
                candidate = str(item.get("oferteo_url") or "").strip()
            else:
                candidate = " ".join(str(v) for v in item.values()).strip()
            
            if has_website_field and has_real_websites and self._is_bad_website(candidate):
                return ""
            
            return candidate
        else:
            return str(item).strip()
    
    def _is_bad_website(self, url: str) -> bool:
        """Check if URL is a bad/irrelevant website."""
        low = (url or "").strip().lower()
        if not low:
            return True
        if not (low.startswith("http://") or low.startswith("https://")):
            return True
        
        bad = [
            "oferteo.pl", "apps.apple.com", "play.google.com", "itunes.apple.com",
            "facebook.com", "instagram.com", "linkedin.com", "twitter.com",
            "x.com", "youtube.com", "tiktok.com",
            "business.safety.google", "policies.google.com",
        ]
        return any(b in low for b in bad)
    
    def _copy_to_clipboard(self, ctx: ActionContext, lines: list[str]) -> None:
        """Copy lines to clipboard using available tools."""
        payload = ("\n".join(lines) + "\n").encode("utf-8")
        copied = False
        
        # Try wl-copy (Wayland)
        try:
            p = subprocess.Popen(
                ["wl-copy"],
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
            p.communicate(payload, timeout=3)
            copied = p.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        
        # Try xclip
        if not copied:
            try:
                p = subprocess.Popen(
                    ["xclip", "-selection", "clipboard"],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                )
                p.communicate(payload, timeout=3)
                copied = p.returncode == 0
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass
        
        # Try xsel
        if not copied:
            try:
                p = subprocess.Popen(
                    ["xsel", "--clipboard", "--input"],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                )
                p.communicate(payload, timeout=3)
                copied = p.returncode == 0
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass
        
        if copied:
            ctx.console.print(f"📋 Copied {len(lines)} lines to clipboard", language="text")


@register_action("save_to_csv")
class SaveToCsvAction(DomAction):
    """Save extracted data to a CSV file."""
    
    def execute(self, ctx: ActionContext) -> ActionResult:
        """Save extracted data to a CSV file."""
        try:
            import csv
            
            filename = ctx.action_spec.get("filename", "companies.csv")
            self._debug(f"save_to_csv: saving {len(ctx.extracted_data)} items to {filename}")
            
            if not ctx.extracted_data:
                ctx.console.print("⚠️  No data to save", language="text")
                return ActionResult(success=True)
            
            filepath = Path(filename)
            
            # Determine fieldnames from first item
            fieldnames = list(ctx.extracted_data[0].keys()) if ctx.extracted_data else ["name", "website"]
            
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for item in ctx.extracted_data:
                    if isinstance(item, dict):
                        writer.writerow(item)
            
            ctx.console.print(f"💾 Saved {len(ctx.extracted_data)} entries to CSV: {filepath.resolve()}", language="text")
            
            return ActionResult(
                success=True,
                data={"filename": str(filepath.resolve()), "entries": len(ctx.extracted_data)}
            )
            
        except Exception as e:
            return ActionResult(success=False, error=f"Save to CSV failed: {e}")
