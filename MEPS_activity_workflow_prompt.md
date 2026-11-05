# Prompt: Recreate the MEPS Activity Data Workflow

You are a coding agent working in a VS Code workspace. Build a simple, well-documented Python workflow for reading, exploring, summarizing, and preparing MEPS activity CSV data using pandas and NumPy.

## Workspace Inputs

- Main script: `MEPS activity.py`
- User guide: `README.md`
- Example data: `meps_activity_data - final.csv`
- The CSV headers should be read from the actual file before implementing or changing the mapping. Do not assume friendly names are already CSV headers.

## Requirements

1. Use an object-oriented design centered on a `MEPSDataWorkflow` class. Keep the implementation straightforward and appropriate for a beginner to read.
2. Define a configurable `DATA_FILE` and a `VARIABLE_MAPPING` dictionary at the top of the script. Map descriptive names to original CSV headers, for example `"survey_year": "year"`, `"annual_total_pay": "exptot"`, and `"person_weight": "perweight"`. Confirm each source header in the CSV before relying on it.
3. `load_data()` should read the CSV into `raw_data` and report its dimensions. `explore_data()` should display column names, data types, a sample, descriptive summaries, missing values, and duplicate rows.
4. `prepare_for_cleaning()` should print the variable mapping as a table with descriptive name, source header, and found/missing status. Create a separate `working_data` copy with source headers renamed to descriptive names. Preserve `raw_data` exactly as loaded.
5. Implement a grouped summary method with explicit `group_by`, `continuous`, and `categorical` inputs. For continuous variables, report non-missing count, mean, and standard deviation. For categorical variables, report count and percentage within the relevant group, including missing categories when practical. Allow an optional pandas query string to filter observations before summarizing. Ranking may be optional; define clearly which statistic is ranked for continuous and categorical variables.
6. Provide a simple grouped row-frequency summary with row counts and percentages of the relevant input rows.
7. Provide a method to create a row-level weighted contribution for continuous variables as `value * weight`, without overwriting the source variable.
8. Provide a weighted-mean method using the sum of `value * weight` divided by the sum of weights over rows where both are non-missing. Allow an optional query filter. Handle a zero denominator with a clear error.
9. Provide a separate weighted categorical distribution method. Do not multiply numeric category codes by weights. Instead, sum the selected survey weight within each category and calculate each category's percentage of total included weight. Allow an optional query filter and preserve missing categories where possible.
10. Keep category recoding tools straightforward: numeric thresholds should create a new labeled category column; explicit code-to-label mappings should be configurable and must not invent MEPS code meanings. Any percentage table should clearly state its denominator.
11. Provide a distinct-value count under an optional filtering query. If it reports a percentage, document whether the denominator is rows or distinct identifiers and make the result match that definition.
12. Put runnable examples under `if __name__ == "__main__":`. Examples must use the descriptive column names after `prepare_for_cleaning()`, valid columns present in the mapping, and consistent indentation. Avoid examples that accidentally use the same variable as both a grouping and summary field.
13. Update `README.md` to cover installation, running the script, the mapping/renaming behavior, each method's purpose and arguments, denominator definitions, examples, and the distinction between unweighted results, weighted contributions, weighted means, and weighted categorical distributions.
14. Do not claim that a weighted result is a full MEPS survey estimate unless the required survey design and weight are correctly specified. Tell the user to confirm the appropriate MEPS weight and code interpretation in the data dictionary.

## Implementation and Validation

- Inspect the current workspace files before editing; preserve unrelated user changes.
- Prefer the existing project's pandas/NumPy approach and keep edits scoped.
- Check that mapping source headers exist in the CSV and that examples use renamed working columns.
- Validate Python syntax and editor diagnostics after changes. Run a focused data check if a Python interpreter and dependencies are available; otherwise state that runtime validation could not be performed.
- Do not commit or push changes unless the user specifically asks for GitHub publication. If asked, inspect the configured repository and current changes first, stage only the requested files, and report the resulting commit/push status honestly.
