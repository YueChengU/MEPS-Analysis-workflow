# MEPS Activity Data Workflow

This script provides a basic workflow for reading a CSV, exploring its contents, and preparing a separate working copy for later cleaning. It does not recode values, remove rows, or otherwise clean the data.

## Requirements

Use Python 3.10 or later with pandas and NumPy installed:

```powershell
python -m pip install pandas numpy
```

Keep `MEPS activity.py` and `meps_activity_data - final.csv` in the same folder, or update `DATA_FILE` in the script to point to the CSV.

## Run the Full Workflow

From this folder, run:

```powershell
python "MEPS activity.py"
```

The main block runs these steps in order:

1. `load_data()` reads the CSV and stores it as `raw_data`.
2. `explore_data()` prints column names, data types, sample rows, summary statistics, missing-value counts, and duplicate-row count.
3. `prepare_for_cleaning()` creates a separate copy in `working_data` and checks whether the configured column names exist.

## Configure the File and Variables

At the top of `MEPS activity.py`, update `DATA_FILE` to select a different CSV. `VARIABLE_MAPPING` maps readable names to the column names used in that file:

```python
VARIABLE_MAPPING = {
    "person_id": "pid",
    "age": "age",
    "total_expenses": "exptot",
}
```

The keys are descriptive names and the values are original CSV headers. `prepare_for_cleaning()` prints a table showing whether each source column was found, then renames matching columns in `working_data`. `raw_data` retains the original headers and values. Use the descriptive names from the mapping in workflow methods after preparation.

## Call Methods Individually

Since the script filename contains a space, load it with `importlib` when using its class from another Python file or an interactive session:

```python
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

script_path = Path("MEPS activity.py")
spec = spec_from_file_location("meps_activity", script_path)
if spec is None or spec.loader is None:
    raise ImportError(f"Could not load {script_path}")

meps_activity = module_from_spec(spec)
spec.loader.exec_module(meps_activity)

workflow = meps_activity.MEPSDataWorkflow(
    meps_activity.DATA_FILE,
    meps_activity.VARIABLE_MAPPING,
)
```

Then run only the methods you need:

```python
raw_data = workflow.load_data()
workflow.explore_data()
working_data = workflow.prepare_for_cleaning()
```

Call `load_data()` before either `explore_data()` or `prepare_for_cleaning()`. `raw_data` keeps the CSV as read; `working_data` is a separate copy with mapped descriptive column names where future cleaning steps can be applied.

## Summarize and Rank Groups

Use `summarize_and_rank()` after `prepare_for_cleaning()`. Explicitly list continuous and categorical variables. Continuous variables produce mean, standard deviation, and non-missing count. Categorical variables produce one row per category with count and percentage within its group. An optional `condition_query` filters rows before summarization:

```python
summary = workflow.summarize_and_rank(
    group_by="survey_year",
    continuous="annual_total_pay",
    categorical="depression_2w",
    condition_query="health == 1",
    rank_by="annual_total_pay",
)
print(summary)
```

The result is a long-form table with the grouping columns plus `variable`, `variable_type`, `category`, `count`, `percentage`, `mean`, and `sd`. `rank_by` is optional; when provided, continuous variables rank by mean and categorical variables by category percentage. Set `ascending=True` for low-to-high ranking. Query expressions use the descriptive column names created by `prepare_for_cleaning()`.

For a simple frequency table without aggregation or ranking, use `summarize_row_counts()`. It accepts one grouping column or a list and returns `row_count` and each group's percentage of all rows:

```python
insurance_health = workflow.summarize_row_counts(["medicaid_or_chip", "health"])
print(insurance_health)
```

## Add a Weighted Variable

For a continuous measure such as expenditures, `add_weighted_variable()` adds a row-level weighted contribution equal to the value multiplied by its weight. The original columns are kept:

```python
workflow.add_weighted_variable(
    value_column="annual_total_pay",
    weight_column="person_weight",
    new_column="weighted_annual_total_pay",
)
```

Choose the weight appropriate to the variable and analysis period according to the MEPS documentation. This product is a weighted contribution, not by itself a complete survey estimate. For a weighted mean, divide the sum of weighted values by the sum of the corresponding weights.

To calculate a weighted mean directly, use `calculate_weighted_mean()`. It excludes rows where the value or weight is missing and accepts an optional query filter:

```python
mean_annual_pay_2020 = workflow.calculate_weighted_mean(
    value_column="annual_total_pay",
    weight_column="person_weight",
    condition_query="survey_year == 2020",
)
print(mean_annual_pay_2020)
```

For a categorical variable, do not multiply its numeric codes by the weight. Use `weighted_category_distribution()` to sum weights within each category and calculate the category's percentage of total included weight:

```python
weighted_phqdep_distribution = workflow.weighted_category_distribution(
    category_column="depression_2w",
    weight_column="questionnaire_weight",
    condition_query="survey_year == 2020",
)
print(weighted_phqdep_distribution)
```

The result includes the category, `weighted_population`, and `weighted_percentage`. The optional query filters records before summing weights, so the percentage denominator is the sum of weights in the filtered data. Confirm that the selected MEPS weight is appropriate for the variable and year in your analysis.

## Count Distinct Values Under a Condition

Use `count_unique_values()` with a pandas query expression to filter rows, then count distinct values in the requested column. For example, count distinct people who have `health == 1` and are at least 18 but under 65:

```python
unique_people = workflow.count_unique_values(
    column="unique_meps_id",
    condition_query="health == 1 and age_years >= 18 and age_years < 65",
)
```

Use backticks around column names containing spaces, for example ``condition_query="`health status` == 1"``. Only use query text that you wrote and trust. Call the method after `prepare_for_cleaning()`; the return value is an integer. Use `dropna=False` if missing values in the counted column should count as one distinct value.

To also return the percentage of rows that match the query, set `include_percentage=True`. The method returns `(unique_count, percentage)`: `unique_count` is the number of distinct selected-column values in matching rows, while `percentage` is matching rows divided by all rows in that selected column (0 to 100):

```python
unique_people, percent_of_people = workflow.count_unique_values(
    column="unique_meps_id",
    condition_query="health == 1",
    include_percentage=True,
)
print(f"{unique_people} unique people ({percent_of_people:.1f}%)")
```

If the working data has no rows, the percentage is `nan` because it cannot be calculated. The percentage counts matching rows, including rows where the selected column's value is missing; `dropna` only affects the distinct-value count.

## Create Categories

For numeric variables, use `create_threshold_categories()` with explicit interval boundaries and one label per interval. With the default `right=False`, intervals include their lower bound and exclude their upper bound. Use negative and positive infinity to include values outside finite thresholds:

```python
workflow.create_threshold_categories(
    column="age",
    bins=[-float("inf"), 18, 65, float("inf")],
    labels=["under 18", "18 to under 65", "65 or older"],
)
```

This creates `age_category` without replacing the original `age` column. You can choose a different output column with `new_column`. Set `include_percentage=True` to return a table of category counts and each category's percentage of all rows, including missing/out-of-range values:

```python
age_distribution = workflow.create_threshold_categories(
    column="age",
    bins=[-float("inf"), 18, 65, float("inf")],
    labels=["under 18", "18 to under 65", "65 or older"],
    include_percentage=True,
)
```

For categorical variables or selected coded values, use `map_categories()`. Confirm the codes and meanings in the relevant data dictionary before defining the mapping:

```python
workflow.map_categories(
    column="sex",
    category_map={1: "category 1 label", 2: "category 2 label"},
)
```

This creates `sex_category`; values not listed in the mapping and missing values are preserved as they were. Replace the example labels with definitions from the data documentation. `map_categories()` also accepts `include_percentage=True` to return the same category count/percentage table. Both category methods update only `working_data` and should be called after `prepare_for_cleaning()`.
