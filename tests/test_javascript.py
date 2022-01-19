import pandas as pd
import pytest

from itables import javascript


@pytest.fixture()
def test_df():
    return pd.DataFrame([1, 2])


def test_datatables_repr_max_columns_none(test_df):
    with pd.option_context("display.max_columns", None):
        html = javascript._datatables_repr_(test_df)
        assert html


def test_ag_grid_repr(test_df):
    html = javascript._ag_grid_repr_(test_df)
    assert html
