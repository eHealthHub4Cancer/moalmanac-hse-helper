import argparse
import json
import pandas as pd
import requests
from bs4 import BeautifulSoup


class Hash:
    @staticmethod
    def hash_rows(dataframe, include_index_in_hash=False):
        return pd.util.hash_pandas_object(dataframe, index=include_index_in_hash)

    @classmethod
    def compare_dataframes(cls, old_dataframe, new_dataframe):
        hashed_old_dataframe = cls.hash_rows(old_dataframe)
        hashed_new_dataframe = cls.hash_rows(new_dataframe)

        new_rows_index = cls.series_difference(hashed_new_dataframe, hashed_old_dataframe)
        new_rows = new_dataframe.loc[new_rows_index, :]

        missing_rows_index = cls.series_difference(hashed_old_dataframe, hashed_new_dataframe)
        missing_rows = old_dataframe.loc[missing_rows_index, :]

        return new_rows, missing_rows

    @staticmethod
    def series_difference(series_1, series_2):
        idx_matching = series_1.isin(series_2)
        return series_1.loc[~idx_matching].index


class Read:
    @staticmethod
    def json(file):
        with open(file) as fp:
            data = json.load(fp)
        return data

    @staticmethod
    def tsv(file):
        return pd.read_csv(file, sep='\t')


class Soup:
    @staticmethod
    def get_page(url):
        response = requests.get(url, allow_redirects=True)
        return BeautifulSoup(response.content, "html.parser")

    @classmethod
    def get_tables(cls, soup, find_text='tbody'):
        tables = soup.find_all(find_text)
        if len(tables) == 0:
            title = soup.find("meta", property="og:title")["content"]
            print(f'Unable to find tables for {title} page.')

        table_dataframes = []
        for table in tables:
            table_data = []
            for row in table.find_all('tr'):
                cells = row.find_all('td')
                if cells:
                    row_data = [cls.replace_special_characters(cell.get_text(strip=True)) for cell in cells]
                    table_data.append(row_data)
            table_dataframe = pd.DataFrame(table_data)
            table_dataframes.append(table_dataframe)
        return pd.concat(table_dataframes, ignore_index=True)

    @staticmethod
    def reheader_soup_table(dataframe, columns):
        df = dataframe[~dataframe.loc[:, 0].eq(columns[0])]
        df.columns = columns
        return df.reset_index(drop=True)

    @staticmethod
    def remove_empty_rows(dataframe, columns):
        idx = dataframe.loc[:, columns].replace('', pd.NA).isnull().all(axis=1)
        return dataframe[~idx]

    @classmethod
    def replace_special_characters(cls, text):
        special_characters_dictionary = {
            '®': '',
            '≥': '>=',
            '≤': '<=',
            'é': 'e',
            '\xa0': ' ',
            '¬≠': '',
            'ï': 'i',
            '–': '-',
            'ü': 'u',
            '&nbsp;': '',
            '&lt;': '<',
            ' ': ' ',
            '  ': ' ',
            '   ': ' ',
            '’': '\'',
            'ö': 'o',
            '\u2010': '-',
            '\u2011': '-',
            '\u00b1': '+/-',
            '\u03b1': 'a'
        }
        for key, value in special_characters_dictionary.items():
            text = text.replace(key, value)
            text = ' '.join(text.split())
        return text


class CancerDrugsApprovedforReimbursement(Soup):
    columns = [
        'Drug',
        'Effective date for reimbursement',
        'Funding stream',
        'Approved Indications'
    ]

    @staticmethod
    def find_last_updated(soup):
        return soup.find('p', string=lambda t: t and 'Last updated' in t)

    @staticmethod
    def format_last_updated_date(element):
        split = (
            str(element)
            .replace('<p>Last updated ', '')
            .replace('</p>', '')
            .split('/')
        )
        return {
            'year': int(split[2]),
            'month': int(split[1]),
            'day': int(split[0])
        }

    @classmethod
    def get_last_updated_date(cls, soup):
        last_updated_element = cls.find_last_updated(soup)
        return cls.format_last_updated_date(last_updated_element)

    @classmethod
    def main(cls, dictionary):
        file = dictionary['output']
        label = dictionary['label']
        cached = pd.DataFrame(dictionary['indications'])

        soup = cls.get_page(dictionary['url'])
        last_updated = cls.get_last_updated_date(soup)
        print(f"{label} last updated: {last_updated}")

        current = cls.get_tables(soup=soup, find_text='tbody')
        current = cls.reheader_soup_table(dataframe=current, columns=cls.columns)
        current = cls.remove_empty_rows(dataframe=current, columns=cls.columns)

        comparison_columns = ['Drug', 'Approved Indications']
        new_rows, revised_rows = Hash.compare_dataframes(
            old_dataframe=cached.loc[:, comparison_columns],
            new_dataframe=current.loc[:, comparison_columns]
        )
        Write.new_rows(dataframe=new_rows, label=label, file=file)
        Write.revised_rows(dataframe=revised_rows, label=label, file=file)


class NationalSACTRegimens(Soup):
    columns = [
        'Regimen label',
        'Regimen Name',
        'Indication'
    ]

    @classmethod
    def main(cls, dictionary):
        file = dictionary['output']
        label = dictionary['label']
        cached = pd.DataFrame(dictionary['indications'])

        tables = []
        for regimen in dictionary['regimens']:
            regimen_label = regimen['label']
            print(f"Getting soup for {regimen_label}")

            soup = cls.get_page(regimen['url'])
            table = cls.get_tables(soup=soup, find_text='tbody')
            table = cls.reheader_soup_table(dataframe=table, columns=cls.columns[1:])
            table = cls.remove_empty_rows(dataframe=table, columns=cls.columns[1:])
            table['Regimen label'] = regimen_label
            tables.append(table.loc[:, cls.columns])
        current = pd.concat(tables, ignore_index=True).fillna('')

        comparison_columns = ['Regimen label', 'Regimen Name', 'Indication']
        new_rows, revised_rows = Hash.compare_dataframes(
            old_dataframe=cached.loc[:, comparison_columns],
            new_dataframe=current.loc[:, comparison_columns]
        )
        Write.new_rows(dataframe=new_rows, label=label, file=file)
        Write.revised_rows(dataframe=revised_rows, label=label, file=file)


class Write:
    @staticmethod
    def json(dictionary, file):
        json_object = json.dumps(dictionary, indent=4)
        with open(file, "w") as outfile:
            outfile.write(json_object)

    @classmethod
    def new_rows(cls, dataframe, label, file):
        if dataframe.empty:
            print(f'No new rows found for {label}.')
        else:
            print(f'{dataframe.shape[0]} edited or new rows found in the {label} table(s).')
            dictionary = dataframe.to_dict(orient='records')
            output_filename = f"{file}_edited_or_new_rows.json"
            cls.json(dictionary=dictionary, file=output_filename)

    @classmethod
    def revised_rows(cls, dataframe, label, file):
        if dataframe.empty:
            print(f'No rows are have been edited or removed from the {label} page.')
        else:
            print(f'{dataframe.shape[0]} rows edited or removed from the {label} table(s).')
            dictionary = dataframe.to_dict(orient='records')
            output_filename = f"{file}_edited_or_removed_rows.json"
            cls.json(dictionary=dictionary, file=output_filename)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="Check for updates from HSE NCCP",
        description="Check for updates from HSE's NCCP Cancer Drugs for Reimbursement and National SACT Regimens"
    )
    parser.add_argument(
        '--cache', '-c',
        help='JSON file detailing web page labels, urls, and currently curated indications',
        type=str
    )
    args = parser.parse_args()

    cache = Read.json(args.cache)
    CancerDrugsApprovedforReimbursement.main(dictionary=cache['cancer-drugs-approved-for-reimbursement'])
    NationalSACTRegimens.main(dictionary=cache['national-sact-regimens'])
