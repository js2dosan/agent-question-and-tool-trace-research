from pathlib import Path

from infrastructure.config.models import DataColumnsConfig, RunConfig


def test_include_subcategory_in_icl_demo_is_ignored_when_include_icl_demo_false() -> None:
    cfg = RunConfig(
        model="dummy-model",
        test_file_path=Path("data/test.csv"),
        columns=DataColumnsConfig(
            test_question_col="question",
            test_category_col=None,
            test_subcategory_col=None,
            icl_demo_question_col=None,
            icl_demo_category_col=None,
            icl_demo_subcategory_col=None,
        ),
        include_icl_demo=False,
        include_subcategory_in_icl_demo=True,  # should be forced off by validator
        label_subcategories=False,  # avoids requiring test_subcategory_col
    )

    assert cfg.include_subcategory_in_icl_demo is False


def test_label_subcategories_can_run_without_human_subcategory_labels() -> None:
    cfg = RunConfig(
        model="dummy-model",
        test_file_path=Path("data/test.csv"),
        columns=DataColumnsConfig(
            test_question_col="question",
            test_category_col=None,
            test_subcategory_col=None,
            icl_demo_question_col=None,
            icl_demo_category_col=None,
            icl_demo_subcategory_col=None,
        ),
        include_icl_demo=False,
        label_subcategories=True,
    )

    assert cfg.label_subcategories is True
    assert cfg.columns.test_subcategory_col is None


def test_row_range_validation_accepts_resume_slice() -> None:
    cfg = RunConfig(
        model="dummy-model",
        test_file_path=Path("data/test.csv"),
        columns=DataColumnsConfig(test_question_col="question"),
        include_icl_demo=False,
        label_subcategories=False,
        row_start=1000,
        row_end=2000,
    )

    assert cfg.row_start == 1000
    assert cfg.row_end == 2000


def test_row_range_validation_rejects_empty_slice() -> None:
    try:
        RunConfig(
            model="dummy-model",
            test_file_path=Path("data/test.csv"),
            columns=DataColumnsConfig(test_question_col="question"),
            include_icl_demo=False,
            label_subcategories=False,
            row_start=20,
            row_end=20,
        )
    except ValueError as e:
        assert "row_start must be less than row_end" in str(e)
    else:
        raise AssertionError("Expected invalid row range to raise ValueError")
