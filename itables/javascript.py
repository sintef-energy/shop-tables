"""HTML/js representation of Pandas dataframes"""

import io
import itertools
import json
import logging
import os
import uuid
import warnings

import numpy as np
import pandas as pd
import pandas.io.formats.format as fmt
from IPython.core.display import HTML, Javascript, display

import itables.options as opt

from .downsample import downsample

logging.basicConfig()
logger = logging.getLogger(__name__)

_JS_LIBRARY = "ag-grid"
_ORIGINAL_DATAFRAME_REPR_HTML = pd.DataFrame._repr_html_


def read_package_file(*path):
    current_path = os.path.dirname(__file__)
    with io.open(os.path.join(current_path, *path), encoding="utf-8") as fp:
        return fp.read()


def init_notebook_mode(all_interactive=False, js_library=_JS_LIBRARY):
    """Load the datatables.net library and the corresponding css, and if desired (all_interactive=True),
    activate the datatables representation for all the Pandas DataFrames and Series.

    Make sure you don't remove the output of this cell, otherwise the interactive tables won't work when
    your notebook is reloaded.
    """
    nonlocal _JS_LIBRARY
    _JS_LIBRARY = check_js_library(js_library)

    if all_interactive:
        pd.DataFrame._repr_html_ = _interactive_table_repr_
        pd.Series._repr_html_ = _interactive_table_repr_
    else:
        pd.DataFrame._repr_html_ = _ORIGINAL_DATAFRAME_REPR_HTML
        if hasattr(pd.Series, "_repr_html_"):
            del pd.Series._repr_html_

    # TODO: remove this #51
    if js_library == "datatables.net":
        display(Javascript(read_package_file("require_config.js")))


def check_js_library(js_library):
    assert js_library in {"ag-grid", "datatables.net"}, js_library
    return js_library


def _formatted_values(df):
    """Return the table content as a list of lists for DataTables"""
    formatted_df = df.copy()
    for col in formatted_df:
        x = formatted_df[col]
        if x.dtype.kind in ["b", "i", "s"]:
            continue

        if x.dtype.kind == "O":
            formatted_df[col] = formatted_df[col].astype(str)
            continue

        formatted_df[col] = np.array(fmt.format_array(x.values, None))
        if x.dtype.kind == "f":
            try:
                formatted_df[col] = formatted_df[col].astype(np.float)
            except ValueError:
                pass

    return formatted_df.values.tolist()


def _table_header(df, table_id, show_index, classes):
    """This function returns the HTML table header. Rows are not included."""
    thead = ""
    if show_index:
        thead = "<th></th>" * len(df.index.names)

    for column in df.columns:
        thead += f"<th>{column}</th>"

    loading = "<td>Loading... (need <a href=https://github.com/mwouts/itables/#table-not-loading>help</a>?)</td>"
    tbody = f"<tr>{loading}</tr>"

    return f'<table id="{table_id}" class="{classes}"><thead>{thead}</thead><tbody>{tbody}</tbody></table>'


def _column_names(df, show_index):
    """Return the column names"""
    if show_index:
        for name in df.index.names:
            yield name

    for column in df.columns:
        yield column


def eval_functions_dumps(obj):
    """
    This is a replacement for json.dumps that
    does not quote strings that start with 'function', so that
    these functions are evaluated in the HTML code.
    """
    if isinstance(obj, str):
        if obj.lstrip().startswith("function"):
            return obj
    if isinstance(obj, list):
        return "[" + ", ".join(eval_functions_dumps(i) for i in obj) + "]"
    if isinstance(obj, dict):
        return (
            "{"
            + ", ".join(
                f'"{key}": {eval_functions_dumps(value)}' for key, value in obj.items()
            )
            + "}"
        )
    return json.dumps(obj)


def replace_value(template, pattern, value, count=1):
    """Set the given pattern to the desired value in the template,
    after making sure that the pattern is found exactly once."""
    assert isinstance(template, str)
    assert template.count(pattern) == count
    return template.replace(pattern, value)


def _datatables_repr_(df=None, tableId=None, **kwargs):
    """Return an HTML output with a datatables.net
    representation of the table"""

    # Default options
    for option in dir(opt):
        if option not in kwargs and not option.startswith("__"):
            kwargs[option] = getattr(opt, option)

    # These options are used here, not in DataTable
    classes = kwargs.pop("classes")
    showIndex = kwargs.pop("showIndex")
    maxBytes = kwargs.pop("maxBytes", 0)
    maxRows = kwargs.pop("maxRows", 0)
    maxColumns = kwargs.pop("maxColumns", pd.get_option("display.max_columns") or 0)
    eval_functions = kwargs.pop("eval_functions", None)

    if isinstance(df, (np.ndarray, np.generic)):
        df = pd.DataFrame(df)

    if isinstance(df, pd.Series):
        df = df.to_frame()

    df = downsample(df, max_rows=maxRows, max_columns=maxColumns, max_bytes=maxBytes)

    # Do not show the page menu when the table has fewer rows than min length menu
    if "paging" not in kwargs and len(df.index) <= kwargs.get("lengthMenu", [10])[0]:
        kwargs["paging"] = False

    # Load the HTML template
    output = read_package_file("datatables_template.html")

    tableId = tableId or str(uuid.uuid4())
    if isinstance(classes, list):
        classes = " ".join(classes)

    if showIndex == "auto":
        showIndex = df.index.name is not None or not isinstance(df.index, pd.RangeIndex)

    if not showIndex:
        df = df.set_index(pd.RangeIndex(len(df.index)))

    table_header = _table_header(df, tableId, showIndex, classes)
    output = replace_value(
        output,
        '<table id="table_id"><thead><tr><th>A</th></tr></thead></table>',
        table_header,
    )
    output = replace_value(output, "#table_id", f"#{tableId}", count=2)

    # Export the DT args to JSON
    if eval_functions:
        dt_args = eval_functions_dumps(kwargs)
    else:
        dt_args = json.dumps(kwargs)
        if eval_functions is None and _any_function(kwargs):
            warnings.warn(
                "One of the arguments passed to datatables starts with 'function'. "
                "To evaluate this function, use the option 'eval_functions=True'. "
                "To silence this warning, use 'eval_functions=False'."
            )

    output = replace_value(
        output, "let dt_args = {};", f"let dt_args = {dt_args};", count=2
    )

    # Export the table data to JSON and include this in the HTML
    data = _formatted_values(df.reset_index() if showIndex else df)
    dt_data = json.dumps(data)
    output = replace_value(output, "const data = [];", f"const data = {dt_data};")

    return output


def _ag_grid_repr_(df=None, tableId=None, **kwargs):
    """Return an HTML output with an ag-grid
    representation of the table"""

    # Default options
    for option in dir(opt):
        if option not in kwargs and not option.startswith("__"):
            kwargs[option] = getattr(opt, option)

    # These options are used here, not in DataTable
    showIndex = kwargs.pop("showIndex")
    maxBytes = kwargs.pop("maxBytes", 0)
    maxRows = kwargs.pop("maxRows", 0)
    maxColumns = kwargs.pop("maxColumns", pd.get_option("display.max_columns") or 0)
    eval_functions = kwargs.pop("eval_functions", None)
    if eval_functions is not None:
        raise NotImplementedError("eval_functions is not implemented yet for ag-grid")

    if isinstance(df, (np.ndarray, np.generic)):
        df = pd.DataFrame(df)

    if isinstance(df, pd.Series):
        df = df.to_frame()

    df = downsample(df, max_rows=maxRows, max_columns=maxColumns, max_bytes=maxBytes)

    # Load the HTML template
    output = read_package_file("ag-grid_template.html")

    tableId = tableId or str(uuid.uuid4())

    if showIndex == "auto":
        showIndex = df.index.name is not None or not isinstance(df.index, pd.RangeIndex)

    if not showIndex:
        df = df.set_index(pd.RangeIndex(len(df.index)))

    output = replace_value(output, "table_id", tableId, count=2)

    gridOptions = kwargs
    gridOptions["columnDefs"] = [
        {"field": str(col_id), "headerName": col, "sortable": True, "filter": True}
        for col_id, col in zip(
            itertools.count(), _column_names(df, show_index=showIndex)
        )
    ]

    # Export the table data to JSON and include this in the HTML
    data = _formatted_values(df.reset_index() if showIndex else df)

    # ag-grid wants a list of dict, not a list of lists like datatables.net
    gridOptions["rowData"] = [
        {col_id: value for col_id, value in zip(itertools.count(), row)} for row in data
    ]

    gridOptions = json.dumps(gridOptions)
    output = replace_value(
        output,
        "const gridOptions = {columnDefs: columnDefs, rowData: rowData};",
        f"const gridOptions = {gridOptions};",
    )

    return output


def _any_function(value):
    """Does a value or nested value starts with 'function'?"""
    if isinstance(value, str) and value.lstrip().startswith("function"):
        return True
    elif isinstance(value, list):
        for nested_value in value:
            if _any_function(nested_value):
                return True
    elif isinstance(value, dict):
        for key, nested_value in value.items():
            if _any_function(nested_value):
                return True
    return False


def _interactive_table_repr_(df, js_library=None, **kwargs):
    if js_library is None:
        js_library = _JS_LIBRARY

    check_js_library(js_library)
    if js_library == "ag-grid":
        return _ag_grid_repr_(df, **kwargs)
    if js_library == "datatables.net":
        return _datatables_repr_(df, **kwargs)


def show(df=None, js_library=None, **kwargs):
    """Display a Pandas DataFrame (or a series, or a numpy array) as an interactive table"""
    html = _interactive_table_repr_(df, js_library=js_library, **kwargs)
    display(HTML(html))
