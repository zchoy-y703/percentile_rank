from datetime import datetime
import asyncio
import io
from pyscript import document, window # https://docs.pyscript.net/2026.3.1/example-apps/overview/

import numpy as np
import pandas as pd
from scipy.stats import percentileofscore


async def process_files(event):
    # 1. Grab DOM elements
    btn = document.getElementById("process-btn")
    status_msg = document.getElementById("status-msg")
    download_container = document.getElementById("download-container")
    download_link = document.getElementById("download-link")

    # Reset UI state
    status_msg.classList.add("hidden")
    download_container.classList.add("hidden")
    btn.disabled = True

    try:
        # 2. Get the uploaded files
        targ_input = document.getElementById("targetFile").files
        ref_input = document.getElementById("refFile").files
        data_input = document.getElementById("dataFile").files

        if targ_input.length == 0 or ref_input.length == 0 or data_input.length == 0:
            raise ValueError("Please upload all three TSV files.")

        # Extract the actual File objects
        targ_file = targ_input.item(0)
        ref_file = ref_input.item(0)
        data_file = data_input.item(0)

        # 3. Read file contents asynchronously (browser native API)
        targ_text = await targ_file.text()
        ref_text = await ref_file.text()
        data_text = await data_file.text()

        # Convert the string content to a Pandas DataFrame
        targs = [line.rstrip() for line in targ_text.splitlines()]
        ref_df = pd.read_csv(io.StringIO(ref_text), sep='\t', skiprows=1, index_col=0)
        data_df = pd.read_csv(io.StringIO(data_text), sep='\t', skiprows=1, index_col=0)

        # 4. Compute the output
        result_df = compute_custom_logic(targs, ref_df, data_df)
        tsv_string = result_df.to_csv(sep='\t')

        # 5. Create a Blob and generate a download URL
        # We use window.Blob and window.URL to access JavaScript APIs from Python
        blob = window.Blob.new([tsv_string], {"type": "text/tab-separated-values"})
        url = window.URL.createObjectURL(blob)

        # 6. Update the download link and reveal it
        now = datetime.now()
        download_link.href = url
        download_link.download = f"output_percentile_rank_{now.strftime('%Y%m%d-%H%M%S')}.tsv"
        download_container.classList.remove("hidden")

    except ValueError as ve:
        status_msg.innerText = str(ve)
        status_msg.classList.remove("hidden")
    except Exception as e:
        status_msg.innerText = f"An error occurred: {str(e)}"
        status_msg.classList.remove("hidden")
    finally:
        btn.disabled = False
    return


def reset_page(event):
    try:
        # Clear files
        document.getElementById("targetFile").value = ""
        document.getElementById("refFile").value = ""
        document.getElementById("dataFile").value = ""
        
        # Reset UI
        document.getElementById("download-container").classList.add("hidden")
        document.getElementById("status-msg").classList.add("hidden")
        document.getElementById("preview-container").classList.add("hidden")
        
        # Reset Button state
        btn = document.getElementById("process-btn")
        btn.disabled = False
        
    except Exception as e:
        print(f"Error during reset: {e}")
    return

def preview_df(df):
    html_table = df.head().to_html(classes="min-w-full text-sm text-left text-slate-600", index=True)
        
    preview_div = document.getElementById("preview-table")
    preview_div.innerHTML = html_table
        
    document.getElementById("preview-container").classList.remove("hidden")
    return

def compute_custom_logic(targs, ref_df, data_df):
    ref = ref_df.transpose()
    data = data_df.transpose()

    if len(targs) == 0:
        raise ValueError("Target list is empty.")
    
    if ref_df.empty:
        raise ValueError("Reference Database is empty.")
    
    if data_df.empty:
        raise ValueError("Input Data is empty.")
    
    ref_abs_targs = [t for t in targs if t not in ref.columns]
    if len(ref_abs_targs) > 0:
        raise ValueError(f"Target(s) {', '.join(ref_abs_targs)} not found in reference DataFrame.")

    absent_targs = [t for t in targs if t not in data.columns]
    incl_targs = list(set(targs) - set(absent_targs))

    ref = ref[incl_targs]
    data = data[incl_targs]

    ps = []
    for t in incl_targs:
        tmp = data[t].values
        r = ref[t].values
        ps.append([percentileofscore(r, x) for x in tmp])
    tdf = pd.DataFrame(ps, index=data.columns, columns=data.index)
    tdf = tdf.transpose()
    tdf = tdf.assign(**{t: np.nan for t in absent_targs})
    #tdf.to_csv(outpath, sep='\t')
    return tdf