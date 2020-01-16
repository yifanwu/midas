from __future__ import absolute_import
from midas.midas_algebra.selection import SelectionValue, ColumnRef, EmptySelection, SelectionType
from IPython import get_ipython
from typing import Optional, List, Dict, Iterator
from datascience import Table

try:
    from IPython.display import display  # type: ignore
except ImportError as err:
    print("not in Notebook environment")
    display = lambda x: None
    logging = lambda x, y: None

from typing import Dict, List

from .midas_algebra.dataframe import MidasDataFrame, DFInfo, VisualizedDFInfo, get_midas_code
from .util.errors import InternalLogicalError
from .vis_types import SelectionEvent, EncodingSpec
from .state_types import DFName
from .ui_comm import UiComm
from midas.midas_algebra.dataframe import MidasDataFrame, DFInfo, JoinInfo, RuntimeFunctions, RelationalOp, VisualizedDFInfo
from midas.midas_algebra.context import Context

from midas.vis_types import SelectionEvent
from midas.state_types import DFName
from .ui_comm import UiComm
from .midas_magic import MidasMagic
from .util.instructions import HELP_INSTRUCTION
from .util.errors import UserError
from .util.utils import isnotebook, find_name, diff_selection_value
from .config import default_midas_config, MidasConfig


is_in_ipynb = isnotebook()


class Midas(object):
    """[summary]
    The Midas object holds the environment that controls different dataframes
    """
    magic: MidasMagic
    ui_comm: UiComm
    context: Context
    rt_funcs: RuntimeFunctions
    current_selection: List[SelectionValue]
    selection_history: List[List[SelectionValue]]
    assigned_name: str
    df_info_store: Dict[DFName, DFInfo]
    config: MidasConfig
    last_add_selection_df: str

    def __init__(self, config: MidasConfig=default_midas_config):
        assigned_name = find_name(True)
        if assigned_name is None:
            raise UserError("must assign a name")
        self.assigned_name = assigned_name
        ui_comm = UiComm(is_in_ipynb, assigned_name, self.get_df_info, self.remove_df, self.from_ops, self.add_selection, self.get_filtered_code)
        self.ui_comm = ui_comm
        self.df_info_store = {}
        self.context = Context(self.df_info_store, self.from_ops)
        self.selection_history = []
        self.config = config
        self.last_add_selection_df = ""
        self.current_selection = []
        if is_in_ipynb:
            ip = get_ipython()
            magics = MidasMagic(ip, ui_comm)
            ip.register_magics(magics)

        self.rt_funcs = RuntimeFunctions(
            self.add_df,
            self.show_df,
            self.show_df_filtered,
            self.show_profiler,
            self.context.apply_selection,
            self.add_join_info)


    def add_df(self, mdf: MidasDataFrame):
        if mdf.df_name is None:
            raise InternalLogicalError("df should have a name to be updated")
        self.df_info_store[mdf.df_name] = DFInfo(mdf)


    def show_profiler(self, mdf: MidasDataFrame):
        self.ui_comm.create_profile(mdf)


    def show_df_filtered(self, mdf: Optional[MidasDataFrame], df_name: DFName):
        if not self.has_df(df_name):
            raise InternalLogicalError("cannot add filter to charts not created")
        self.ui_comm.update_chart_filtered_value(mdf, df_name)
        self.df_info_store[df_name].update_df(mdf)


    def show_df(self, mdf: MidasDataFrame, spec: EncodingSpec):
        if mdf.df_name is None:
            raise InternalLogicalError("df should have a name to be updated")
        df_name = mdf.df_name
        # if this visualization has existed, we must remove the existing interactions
        # the equivalent of updating the selection with empty
        if self.has_df_chart(mdf.df_name):
            self.add_selection([EmptySelection(ColumnRef(spec.x, df_name))])
        self.df_info_store[df_name] = VisualizedDFInfo(mdf)
        self.ui_comm.create_chart(mdf, spec)
        # now we need to see if we need to apply selection,
        if len(self.current_selection) > 0:
            new_df = mdf.apply_selection(self.current_selection)
            new_df.filter_chart(df_name)


    def has_df_chart(self, df_name: DFName):
        return df_name in self.df_info_store and isinstance(self.df_info_store[df_name], VisualizedDFInfo)


    def has_df(self, df_name: DFName):
        return df_name in self.df_info_store


    def append_df_predicates(self, selection: SelectionEvent) -> DFInfo:
        df_name = selection.df_name
        df_info = self.df_info_store.get(df_name)
        if df_info and isinstance(df_info, VisualizedDFInfo):
            df_info.predicates.append(selection)
            return df_info
        else:
            raise InternalLogicalError(f"Df ({df_name}) should be defined and be visualized as a chart!")


    def get_df_info(self, df_name: DFName):
        return self.df_info_store.get(df_name)


    def get_df(self, df_name: DFName):
        r = self.df_info_store.get(df_name)
        if r:
            return r.df


    def remove_df(self, df_name: DFName):
        self.df_info_store.pop(df_name)

    def from_records(self, records):
        table = Table.from_records(records)
        df_name = find_name()
        return MidasDataFrame.create_with_table(table, df_name, self.rt_funcs)


    def read_table(self, filepath_or_buffer, *args, **vargs):
        table = Table.read_table(filepath_or_buffer, *args, **vargs)
        df_name = find_name()
        return MidasDataFrame.create_with_table(table, df_name, self.rt_funcs)


    def from_df(self, df):
        # a pandas df
        table = Table.from_df(df)
        df_name = find_name()
        return MidasDataFrame.create_with_table(table, df_name, self.rt_funcs)


    def from_ops(self, ops: RelationalOp):
        return MidasDataFrame(ops, self.rt_funcs)


    def with_columns(self, *labels_and_values, **formatter):
        table = Table().with_columns(*labels_and_values, **formatter)
        df_name = find_name()
        return MidasDataFrame.create_with_table(table, df_name, self.rt_funcs)


    def add_join_info(self, join_info: JoinInfo):
        self.context.add_join_info(join_info)
            

    def refresh_comm(self):
        self.ui_comm.set_comm(self.assigned_name)


    def get_df_info(self, df_name: DFName) -> Optional[DFInfo]:
        return self.df_info_store.get(df_name)


    def get_df_vis_info(self, df_name: str):
        return self.ui_comm.vis_spec.get(DFName(df_name))


    @staticmethod
    def help():
        print(HELP_INSTRUCTION)


    def get_current_selection(self):
        return self.current_selection

    # this function just modifies the current selection and returns it
    # this currently assume that all the selectionvalue are from one dataframe
    def add_selection(self, selection: List[SelectionValue]) -> List[SelectionValue]:
        df_name = DFName(selection[0].column.df_name)
        # date = datetime.now()
        # selection_event = SelectionEvent(date, selection, DFName(df_name))
        # self.append_df_predicates(selection_event)
        new_selection = list(filter(lambda v: v.column.df_name != df_name, self.current_selection))
        none_empty = list(filter(lambda s: s.selection_type != SelectionType.empty , selection))
        new_selection.extend(none_empty)
        self.current_selection = new_selection
        return self.current_selection


    def tick(self, all_predicate: Optional[List[SelectionValue]]=None):
        if all_predicate is None:
            # reset every df's filter
            for df_info in self.get_visualized_df_info():
                self.show_df_filtered(None, df_info.df_name)
        else:
            if self.config.linked:
                # debug_log("here are your predicates")
                # print(all_predicate)
                for df_info in self.get_visualized_df_info():
                    s = list(filter(lambda p: p.column.df_name != df_info.df_name, all_predicate))
                    if len(s) > 0:
                        new_df = df_info.original_df.apply_selection(s)
                        # debug_log(f"Filtering df {a_df_name}")
                        new_df.filter_chart(df_info.df_name)


    def get_visualized_df_info(self) -> Iterator[VisualizedDFInfo]:
        for df_name in list(self.df_info_store):
            df_info = self.df_info_store[df_name]
            if isinstance(df_info, VisualizedDFInfo):
                yield df_info


    # PUBLIC
    def make_selections(self, current_selections_array: List[Dict]):
        """this function is executed via python cells
        this function makes idempotentn modifications to state
        Keyword Arguments:
            current_selections_array {Optional[List[Dict]]} --
            note that the dict is Dict[DFName, SelectionValue] (default: {None})
        """
        df_involved = ""
        if len(current_selections_array) == 0:
            # this is a reset!
            self.current_selection = []
            self.tick()
        else:
            current_selection = []
            for v in current_selections_array:
                current_selection.extend(self.ui_comm.get_predicate_info(v)[0])

            # this check if for when there is no UI effect, but code effect
            diff = diff_selection_value(current_selection, self.current_selection)
            if len(diff) > 0:
                # either no change, or that
                # if there is only one diff, then we trigger with specific df
                dfs = set([d.column.df_name for d in diff])
                # debug_log("changed")
                df_involved = dfs.pop()
                self.current_selection = current_selection
            else:
                df_involved = self.last_add_selection_df
            self.tick(current_selection)

        self.ui_comm.after_selection(current_selections_array, df_involved)
        self.selection_history.append(self.current_selection)


    def get_filtered_code(self, df_name: str):
        return get_midas_code(self.df_info_store[DFName(df_name)].df.ops)


    def get_original_code(self, df_name: str):
        return get_midas_code(self.df_info_store[DFName(df_name)].original_df.ops)


__all__ = ['Midas']
