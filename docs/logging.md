# Experiment Logging Design

There are two ways to perform the analysis:

- M1: selections vs. coding
- M2: what methods were invoked
- M3: insight

The schema for the log will contain the following columns:

- `action`
- `seconds_since_start`
- `optional_metadata`

In order to perform M1, look for the following two values in `action`:

- coding: `code_execution`
- ui : all of the UI operations, or focus on `ui_selection`

M2 offers more detailed information, and contains the following functions:

API

- `load_data`
- `add_join_info`

UI

- `snapshot_single`
- `snapshot_all`
- `move_chart`
- `resize_midas_area`
- `hide_midas`,
- `show_midas`
- `hide_columns_pane`
- `show_columns_pane`
- `show_chart` (previously, `toggle_chart`)
- `hide_chart`
- `column_click`
- `ui_selection`
- `get_code`
- `remove_df`
- `navigate_to_definition_cell` (previously, `change_visual`)
- `hide_midas` (previously, `toggle_midas`)
- `show_midas`
- `show_selection_cells`
- `hide_selection_cells`
- `navigate_to_original_cell`

Note that we will also have `code_selection` calls, note that all `ui_selection`s are followed by `code_selection`, but not all `code_selection`s are preceded by a `ui_selection`, in that case, the selection was triggered by the user.

M3 is pretty straightforward, it's captured as a markdown cell being ran,

- `markdown-rendered`
