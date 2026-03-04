# MOAlmanac HSE helper
Helper scripts for staying up-to-date on reimbursement approvals from the [Republic of Ireland's Health Service Executive](https://healthservice.hse.ie/staff/information-healthcare-workers/nccp/national-sact-regimens/) for the [Molecular Oncology Almanac's](https://ie.moalmanac.org) [database](https://github.com/vanallenlab/moalmanac-db)

The HSE has been in the process of revamping their website and **this workflow is currently broken**.

## Current (broken) workflow
_Text taken from another repo_.

Updating approvals for reimbursement from the HSE requires scraping both the [NCCP Cancer Drugs Approved for Reimbursement](https://www.hse.ie/eng/services/list/5/cancer/profinfo/medonc/cdmp/new.html) and the [NCCP National SACT Regimens](https://www.hse.ie/eng/services/list/5/cancer/profinfo/chemoprotocols/) by tumor group. We've written a single script, `check-for-updates.py`, to do both of these.
1. Run the python script, `check-for-updates.py`, to scrape both sources of approvals for reimbursement and provide the configuration file. For example, `python check-for-updates.py --config hse-cache.json`
2. For both cancer drugs approved for reimbursement and national sact regimens, files with extensions `_edited_or_removed_rows.json` and `_new_rows.json` will be produced. With these files, update `hse-cache.json` manually, and **also reflect these changes in [hse-indications.json](hse-indications.json)**. Annotate new entries in [hse-cache.json](hse-cache.json) with "1" for the biomarker key, if the entry contains at least 1 biomarker, and set the "cataloged" key to be 1 after it has been added to [hse-indications.json](hse-indications.json). 
3. Derive new relationships in [hse.json](hse.json) from hse-indications.json. The notebook [check-for-new indications](check-for-new-indications.ipynb) can be used to identify discrepancies between [hse-indications.json](hse-indications.json) and [hse.json](hse.json).

Step 2 is a huge point of friction in the current process. Figuring out a nice reference and de-referenced framework would be helpful.

## Installation
### Download
This repository can be downloaded through GitHub by either using the website or terminal. To download on the website, navigate to the top of this page, click the green `Clone or download` button, and select `Download ZIP` to download this repository in a compressed format. To install using GitHub on terminal, type:

```bash
git clone https://github.com/eHealthHub4Cancer/moalmanac-hse-helper.git
cd moalmanac-hse-helper
```

### Python dependencies
This repository uses Python 3.12. We recommend using a [virtual environment](https://docs.python.org/3/tutorial/venv.html) and running Python with a Conda distribution such as [Miniforge](https://github.com/conda-forge/miniforge), which uses the community-maintained [conda-forge](https://conda-forge.org) package channel.

Run the following from this repository's directory to create a virtual environment and install dependencies with a Conda distribution:
```bash
conda create -y -n moalmanac-hse-helper python=3.12 --channels conda-forge
conda activate moalmanac-hse-helper
pip install -r requirements.txt
```

Or, if using base Python: 
```bash
python -m venv venv
source activate venv/bin/activate
pip install -r requirements.txt
```

To make the virtual environment available to jupyter notebooks, execute the following code while the virtual environment is activated:
```bash
pip install notebook
ipython kernel install --user --name=moalmanac-hse-helper
```
