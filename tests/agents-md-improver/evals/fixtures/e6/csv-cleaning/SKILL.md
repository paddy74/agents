---
name: csv-cleaning
description: I can clean up messy CSV files for you. You can use me when a CSV has bad headers, duplicate rows or mixed date formats, or when the user asks to tidy, normalize or dedupe a spreadsheet export.
---

# CSV cleaning

## What is a CSV file?

CSV stands for "comma-separated values". It is a plain-text format where each
line is a record and fields are separated by commas. The first line is often a
header row. CSV files are very common and are exported by spreadsheet programs
such as Excel and Google Sheets. Python has a built-in `csv` module for reading
and writing them, and pandas can read them with `pandas.read_csv`.

## Why cleaning matters

Messy data leads to wrong results. Cleaning data before analysis is an
important step that many people skip. It is always a good idea to clean data.

## Workflow

1. Run `python scripts/clean.py input.csv output.csv` to normalize headers,
   drop exact duplicate rows and convert dates to ISO 8601.
2. Open the output and check the row count against the input.
3. If dates still look wrong, see [advanced options](references/advanced.md).

As of March 2025, use the `--dayfirst` flag for European exports.

## Example

Input header: ` First Name ,DOB ` → output header: `first_name,dob`.
