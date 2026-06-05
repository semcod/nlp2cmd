"""Re-exports from split fuzzy_schema_matcher.py module."""

from pathlib import Path
from typing import Optional

from nlp2cmd.generation.match_result import MatchResult
from nlp2cmd.generation.phrase_schema import PhraseSchema
from nlp2cmd.generation.fuzzy_schema_matcher_config import FuzzySchemaMatcherConfig
from nlp2cmd.generation.fuzzy_schema_matcher_class import FuzzySchemaMatcher

__all__ = ['MatchResult', 'PhraseSchema', 'FuzzySchemaMatcherConfig', 'FuzzySchemaMatcher']



# Convenience function for quick matching
def create_multilingual_matcher(
    phrases_dict: Optional[dict] = None,
    schema_path: Optional[Path] = None,
) -> FuzzySchemaMatcher:
    """
    Create a fuzzy matcher with default multilingual phrases.
    
    Args:
        phrases_dict: Optional dict of {domain: {intent: [phrases]}}
        schema_path: Optional path to JSON schema file
    """
    matcher = FuzzySchemaMatcher()
    
    if schema_path and Path(schema_path).exists():
        matcher.load_schema(Path(schema_path))
    
    if phrases_dict:
        matcher.add_phrases_from_dict(phrases_dict)
    
    # Add default multilingual phrases if no input provided
    if not matcher.phrases:
        default_phrases = {
            "shell": {
                "list": [
                    "list files", "lista plików", "liste dateien", "lister fichiers",
                    "listar archivos", "elenco file", "列出文件", "ファイル一覧",
                ],
                "find": [
                    "find file", "znajdź plik", "datei finden", "trouver fichier",
                    "buscar archivo", "cerca file", "查找文件", "ファイル検索",
                ],
                "delete": [
                    "delete file", "usuń plik", "datei löschen", "supprimer fichier",
                    "eliminar archivo", "elimina file", "删除文件", "ファイル削除",
                ],
                "copy": [
                    "copy file", "kopiuj plik", "datei kopieren", "copier fichier",
                    "copiar archivo", "copia file", "复制文件", "ファイルコピー",
                ],
                "move": [
                    "move file", "przenieś plik", "datei verschieben", "déplacer fichier",
                    "mover archivo", "sposta file", "移动文件", "ファイル移動",
                ],
                "show_processes": [
                    "show processes", "pokaż procesy", "prozesse anzeigen", "afficher processus",
                    "mostrar procesos", "mostra processi", "显示进程", "プロセス表示",
                ],
            },
            "sql": {
                "select": [
                    "select from", "wybierz z", "auswählen aus", "sélectionner de",
                    "seleccionar de", "seleziona da", "选择从", "選択する",
                ],
                "insert": [
                    "insert into", "wstaw do", "einfügen in", "insérer dans",
                    "insertar en", "inserisci in", "插入到", "挿入する",
                ],
                "delete": [
                    "delete from", "usuń z", "löschen aus", "supprimer de",
                    "eliminar de", "elimina da", "删除从", "削除する",
                ],
            },
        }
        matcher.add_phrases_from_dict(default_phrases)
    
    return matcher
