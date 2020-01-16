from midas.midas_algebra.dataframe import MidasDataFrame
from datascience import Table
import numpy as np
from math import log10, pow
from pandas import notnull

from .errors import InternalLogicalError
from midas.constants import IS_OVERVIEW_FIELD_NAME
from midas.vis_types import FilterLabelOptions


def get_chart_title(df_name: str):
    # one level of indirection in case we need to change in the future
    return df_name


MAX_BINS = 20


def snap_to_nice_number(n: float):
    # print("Nice nubmer", n)
    if n == np.inf:
        raise InternalLogicalError("Should not have gotten infinity")
    if n <= 0:
        raise InternalLogicalError(f"Got {n}")
    if (n <= 1):
        zeroes = pow(10, abs(int(log10(n))) + 1)
        new_num = snap_to_nice_number(n * zeroes)
        return new_num/zeroes
        # if it's less than 1, make it as big as one and then call the same function and return
    if (n <= 2):
        return 2
    elif (n <= 5):
        return 5
    elif (n <= 10):
        return 10
    # bigger than 10, just zero out the digits
    zeroes = pow(10, int(log10(n)))
    return (int(n / zeroes) + 1) * zeroes



# TODO: we need to test this...
# taken from ipyvega
def sanitize_dataframe(df: Table):
    """Sanitize a DataFrame to prepare it for serialization.
    
    copied from the ipyvega project
    * Make a copy
    * Convert categoricals to strings.
    * Convert np.bool_ dtypes to Python bool objects
    * Convert np.int dtypes to Python int objects
    * Convert floats to objects and replace NaNs/infs with None.
    * Convert DateTime dtypes into appropriate string representations
    """
    import numpy as np

    if df is None:
        return None
        # raise InternalLogicalError("Cannot sanitize empty df")

    df = df.copy()

    def to_list_if_array(val):
        if isinstance(val, np.ndarray):
            return val.tolist()
        else:
            return val

    for col_name in df.labels:
        dtype = df.column(col_name).dtype
        if str(dtype) == 'category':
            # XXXX: work around bug in to_json for categorical types
            # https://github.com/pydata/pandas/issues/10778
            df[col_name] = df[col_name].astype(str)
        elif str(dtype) == 'bool':
            # convert numpy bools to objects; np.bool is not JSON serializable
            df[col_name] = df[col_name].astype(object)
        elif np.issubdtype(dtype, np.integer):
            # convert integers to objects; np.int is not JSON serializable
            df[col_name] = df[col_name].astype(object)
        elif np.issubdtype(dtype, np.floating):
            # For floats, convert to Python float: np.float is not JSON serializable
            # Also convert NaN/inf values to null, as they are not JSON serializable
            col = df[col_name]
            bad_values = np.isnan(col) | np.isinf(col)
            df[col_name] = np.where(bad_values, None, col).astype(object)
            # col.astype(object)[~bad_values]= None
        elif str(dtype).startswith('datetime'):
            # Convert datetimes to strings
            # astype(str) will choose the appropriate resolution
            new_column = df[col_name].astype(str)
            new_column[new_column == 'NaT'] = ''
            df[col_name] = new_column
        elif dtype == object:
            # Convert numpy arrays saved as objects to lists
            # Arrays are not JSON serializable
            col = np.vectorize(to_list_if_array)(df[col_name])
            df[col_name] = np.where(notnull(col), col, None).astype(object)
    return df


def dataframe_to_dict(df: MidasDataFrame, include_filter_label: FilterLabelOptions):
    """[summary]
    
    Keyword Arguments:
        include_filter_label {bool} -- whether we should insert another column indicating (default: {False})
    """
    clean_df = sanitize_dataframe(df.table)
    if clean_df is None:
        return []

    def s(x):
        k = {}
        for i, v in enumerate(x):
            k[clean_df.labels[i]] = v
        if include_filter_label != FilterLabelOptions.none:
            k[IS_OVERVIEW_FIELD_NAME] = include_filter_label.value
        return k
    return list(map(s, clean_df.rows))
