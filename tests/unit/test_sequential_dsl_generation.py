import pytest

from nlp2cmd import NLP2CMD
from nlp2cmd.adapters import DockerAdapter, DQLAdapter, KubernetesAdapter, ShellAdapter, SQLAdapter


@pytest.mark.parametrize(
    ("adapter", "text", "assert_contains"),
    [
        (SQLAdapter(dialect="postgresql"), "Pokaż dane z tabeli users", "FROM users"),
        (ShellAdapter(), "Znajdź *.py w katalogu /tmp", "find"),
        (DockerAdapter(), "Pokaż logi kontenera myapp --tail 50", "docker logs"),
        (KubernetesAdapter(), "Pokaż pody w namespace default", "kubectl get"),
        (DQLAdapter(), "Pobierz encję User", "createQueryBuilder"),
    ],
)
def test_transform_sequential_all_dsls(adapter, text, assert_contains):
    nlp = NLP2CMD(adapter=adapter)
    result = nlp.transform(text)
    assert result.is_success
    assert assert_contains in result.command
