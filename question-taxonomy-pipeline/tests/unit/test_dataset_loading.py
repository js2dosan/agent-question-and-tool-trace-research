from pathlib import Path

from infrastructure.io.datasets import read_table


def test_read_txt_as_question_table(tmp_path: Path) -> None:
    path = tmp_path / "questions.txt"
    path.write_text("First question?\n\n Second question? \n", encoding="utf-8")

    df = read_table(path, ["question"])

    assert list(df.columns) == ["question"]
    assert df["question"].tolist() == ["First question?", "Second question?"]
