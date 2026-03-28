"""
qeanalysis/export.py
=====================
LaTeX table generation and bulk export utilities.

All functions operate on regular pandas DataFrames and write .tex / .csv files.
"""

import math
from pathlib import Path
from typing import Dict, Optional, Tuple

import pandas as pd


# ── Single table ─────────────────────────────────────────────────────────────────

def _fmt_cell(val, float_fmt: str) -> str:
    """Format a single cell value as a LaTeX-safe string."""
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return '—'
    if isinstance(val, float):
        return f'{val:{float_fmt}}'
    if isinstance(val, bool):
        return 'True' if val else 'False'
    return str(val).replace('_', '\\_').replace('%', '\\%').replace('&', '\\&')


def df_to_latex(df: pd.DataFrame,
                caption: str = '',
                label: str = '',
                float_fmt: str = '.3f',
                index: bool = True) -> str:
    """Convert a DataFrame to a publication-ready LaTeX table string.

    Uses booktabs formatting (\\toprule, \\midrule, \\bottomrule).
    Written without relying on pandas.to_latex() to avoid jinja2 dependency.

    Args:
        df:        The DataFrame to convert.
        caption:   LaTeX table caption text.
        label:     LaTeX table label (for \\ref{label}).
        float_fmt: Format string for float columns (default '.3f').
        index:     Whether to include the DataFrame index as a column.

    Returns:
        LaTeX string ready to paste into a .tex file.
    """
    # Build header row
    if index:
        header_cells = [str(df.index.name or '')] + [str(c) for c in df.columns]
    else:
        header_cells = [str(c) for c in df.columns]

    n_cols = len(header_cells)
    col_fmt = 'l' + 'r' * (n_cols - 1)

    # Escape header
    def _esc(s):
        return s.replace('_', '\\_').replace('%', '\\%').replace('&', '\\&')

    header_row = ' & '.join(_esc(h) for h in header_cells) + ' \\\\'

    # Build data rows
    data_rows = []
    for idx, row in df.iterrows():
        if index:
            cells = [_esc(str(idx))] + [_fmt_cell(v, float_fmt) for v in row]
        else:
            cells = [_fmt_cell(v, float_fmt) for v in row]
        data_rows.append(' & '.join(cells) + ' \\\\')

    body = '\n'.join(data_rows)

    caption_line = f'  \\caption{{{caption}}}\n' if caption else ''
    label_line   = f'  \\label{{{label}}}\n' if label else ''

    return (
        '\\begin{table}[htbp]\n'
        '  \\centering\n'
        f'{caption_line}'
        f'{label_line}'
        f'  \\begin{{tabular}}{{{col_fmt}}}\n'
        '    \\toprule\n'
        f'    {header_row}\n'
        '    \\midrule\n'
        f'{body}\n'
        '    \\bottomrule\n'
        '  \\end{tabular}\n'
        '\\end{table}\n'
    )


# ── Bulk export ──────────────────────────────────────────────────────────────────

def export_tables(tables_dict: Dict[str, Tuple],
                  output_dir) -> None:
    """Write multiple DataFrames as both .csv and .tex files.

    Args:
        tables_dict: {stem: (df, caption, label)} where stem is the
                     filename without extension (e.g. 'overall_summary').
        output_dir:  Directory to write files into (created if absent).
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for stem, payload in tables_dict.items():
        if len(payload) == 3:
            df, caption, label = payload
        else:
            df, caption, label = payload[0], '', ''

        # CSV
        csv_path = output_dir / f'{stem}.csv'
        df.to_csv(csv_path)

        # LaTeX
        tex_str = df_to_latex(df, caption=caption, label=label)
        tex_path = output_dir / f'{stem}.tex'
        with open(tex_path, 'w') as f:
            f.write(tex_str)
