"""Load, inspect, and prepare MEPS activity data before cleaning."""

from pathlib import Path

import numpy as np
import pandas as pd


# Update these settings when using a different file or dataset.
DATA_FILE = Path(__file__).with_name("meps_activity_data - final.csv")
VARIABLE_MAPPING = {
    # Identifiers and survey structure
    "survey_year": "year",
    "number_household": "pernum",
    "id_duwell": "duid",
    "number_duwell": "pid",
    "unique_meps_id": "mepsid",
    "meps_panel": "panel",
    "year_entered": "panelyr",
    "year_within_panel": "relyr",

    # Survey design variables
    "annual_primary_sampling_unit": "psuann",
    "annual_variance_stratum": "stratann",
    "pooled_primary_sampling_unit": "psupld",
    "pooled_variance_stratum": "stratapld",

    # Survey weights
    "person_weight": "perweight",
    "questionnaire_weight": "saqweight",
    "diabetes_weight": "diabweight",

    # Demographic characteristics
    "age_years": "age",
    "sex": "sex",
    "race": "racea",

    # Health status and access to care
    "health": "health",
    "has_usual_care": "usualpl",

    # Health insurance coverage
    "no_insurance": "hinotcov",
    "private_insurance": "hiprivate",
    "medicaid_or_chip": "himachip",

    # Chronic-condition history
    "arthritis_history": "arthglupev",
    "cancer_history": "cancerev",
    "chd_history": "cheartdiev",
    "diabetes_history": "diabeticev",
    "heartattack_history": "heartattev",

    # Depression and functional health measures
    "depression_2w": "phqdep",
    "depression_score": "phq2",
    "less_accomplished_4w": "adpals",

    # Health care utilization and expenditures
    "annual_total_pay": "exptot",
    "annual_emergency_pay": "erexptot",
    "annual_discharge": "hptotdis",
    "annual_dental_pay": "dvexptot",
}




class MEPSDataWorkflow:
	"""Basic workflow for inspecting a CSV before making cleaning decisions."""

	def __init__(
		self,
		file_path: str | Path,
		variable_mapping: dict[str, str] | None = None,
	) -> None:
		self.file_path = Path(file_path)
		self.variable_mapping = variable_mapping or {}
		self.raw_data: pd.DataFrame | None = None
		self.working_data: pd.DataFrame | None = None

	def load_data(self) -> pd.DataFrame:
		"""Read the CSV and retain it unchanged as the raw dataset."""
		self.raw_data = pd.read_csv(self.file_path)
		print(f"Loaded: {self.file_path.name}")
		print(f"Rows: {self.raw_data.shape[0]:,}; columns: {self.raw_data.shape[1]:,}")
		return self.raw_data

	def explore_data(self) -> None:
		"""Print basic structure, summaries, missingness, and duplicate counts."""
		data = self._require_raw_data()

		print("\nColumn names:")
		print(data.columns.tolist())

		print("\nData types and non-null counts:")
		data.info()

		print("\nFirst five rows:")
		print(data.head())

		print("\nSummary statistics:")
		print(data.describe(include="all").transpose())

		# NumPy's numeric dtype selector limits this summary to numeric columns.
		numeric_columns = data.select_dtypes(include=np.number).columns
		print("\nMissing values by column:")
		print(data.isna().sum().sort_values(ascending=False))

		print(f"\nDuplicate rows: {data.duplicated().sum():,}")
		print(f"Numeric columns: {len(numeric_columns):,}")

	def prepare_for_cleaning(self) -> pd.DataFrame:
		"""Create a descriptively named working copy and display mapping status."""
		data = self._require_raw_data()
		mapping_table = pd.DataFrame(
			[
				{
					"friendly_name": friendly_name,
					"original_name": original_name,
					"status": "found" if original_name in data.columns else "NOT FOUND",
				}
				for friendly_name, original_name in self.variable_mapping.items()
			]
		)
		print("\nVariable mapping:")
		print(mapping_table.to_string(index=False) if not mapping_table.empty else "No variable mappings configured.")

		rename_columns = {
			original_name: descriptive_name
			for descriptive_name, original_name in self.variable_mapping.items()
			if original_name in data.columns
		}
		self.working_data = data.rename(columns=rename_columns).copy()

		print("\nA renamed working copy is ready. Raw data has not been changed or cleaned.")
		return self.working_data

	def summarize_and_rank(
		self,
		group_by: str | list[str],
		continuous: str | list[str] | None = None,
		categorical: str | list[str] | None = None,
		condition_query: str | None = None,
		rank_by: str | None = None,
		ascending: bool = False,
	) -> pd.DataFrame:
		"""Summarize continuous and categorical columns within optional groups."""
		data = self._require_working_data()
		groups = [group_by] if isinstance(group_by, str) else group_by
		continuous_columns = [] if continuous is None else ([continuous] if isinstance(continuous, str) else continuous)
		categorical_columns = [] if categorical is None else ([categorical] if isinstance(categorical, str) else categorical)
		selected_columns = [*continuous_columns, *categorical_columns]

		if not groups or not selected_columns:
			raise ValueError("Provide at least one grouping column and one summary column.")
		if len(set(selected_columns)) != len(selected_columns):
			raise ValueError("A summary column cannot be listed more than once or in both types.")
		if set(groups).intersection(selected_columns):
			raise ValueError("Summary columns must not also be grouping columns.")
		if rank_by is not None and rank_by not in selected_columns:
			raise ValueError("rank_by must be one of the selected continuous or categorical columns.")

		requested_columns = list(dict.fromkeys([*groups, *selected_columns]))
		missing_columns = [column for column in requested_columns if column not in data.columns]
		if missing_columns:
			raise KeyError(f"Columns not found in working data: {missing_columns}")
		for column in continuous_columns:
			if not pd.api.types.is_numeric_dtype(data[column]):
				raise TypeError(f"Continuous summary column must be numeric: {column}")

		analysis_data = data.query(condition_query) if condition_query else data
		rows: list[dict[str, object]] = []
		for group_values, subset in analysis_data.groupby(groups, dropna=False, sort=False):
			values = group_values if isinstance(group_values, tuple) else (group_values,)
			group_info = dict(zip(groups, values))

			for column in continuous_columns:
				values = subset[column]
				rows.append({
					**group_info,
					"variable": column,
					"variable_type": "continuous",
					"category": pd.NA,
					"count": int(values.count()),
					"percentage": np.nan,
					"mean": values.mean(),
					"sd": values.std(),
				})

			for column in categorical_columns:
				category_counts = subset[column].value_counts(dropna=False, sort=False)
				for category, count in category_counts.items():
					rows.append({
						**group_info,
						"variable": column,
						"variable_type": "categorical",
						"category": category,
						"count": int(count),
						"percentage": count / len(subset) * 100,
						"mean": np.nan,
						"sd": np.nan,
					})

		result = pd.DataFrame(rows)
		if rank_by is not None and not result.empty:
			rank_metric = "mean" if rank_by in continuous_columns else "percentage"
			rank_mask = result["variable"] == rank_by
			result["rank_order"] = pd.Series(pd.NA, index=result.index, dtype="Int64")
			result.loc[rank_mask, "rank_order"] = (
				result.loc[rank_mask, rank_metric]
				.rank(method="dense", ascending=ascending)
				.astype("Int64")
			)
			result = result.sort_values(
				"rank_order",
				ascending=True,
				na_position="last",
			).reset_index(drop=True)
		return result

	def summarize_row_counts(self, group_by: str | list[str]) -> pd.DataFrame:
		"""Count rows for each group and report each group's share of all rows."""
		data = self._require_working_data()
		groups = [group_by] if isinstance(group_by, str) else group_by

		if not groups:
			raise ValueError("group_by must not be empty.")
		missing_columns = [column for column in groups if column not in data.columns]
		if missing_columns:
			raise KeyError(f"Columns not found in working data: {missing_columns}")

		result = (
			data.groupby(groups, dropna=False)
			.size()
			.reset_index(name="row_count")
		)
		result["percentage"] = (
			result["row_count"] / len(data) * 100 if len(data) else float("nan")
		)
		return result

	def add_weighted_variable(
		self,
		value_column: str,
		weight_column: str,
		new_column: str,
	) -> pd.Series:
		"""Add a weighted contribution column as value multiplied by weight."""
		data = self._require_working_data()
		for column in (value_column, weight_column):
			if column not in data.columns:
				raise KeyError(f"Column not found in working data: {column}")
			if not pd.api.types.is_numeric_dtype(data[column]):
				raise TypeError(f"Weighted variable inputs must be numeric: {column}")

		data[new_column] = data[value_column] * data[weight_column]
		return data[new_column]

	def calculate_weighted_mean(
		self,
		value_column: str,
		weight_column: str,
		condition_query: str | None = None,
	) -> float:
		"""Calculate a weighted mean over rows with non-missing values and weights."""
		data = self._require_working_data()
		for column in (value_column, weight_column):
			if column not in data.columns:
				raise KeyError(f"Column not found in working data: {column}")
			if not pd.api.types.is_numeric_dtype(data[column]):
				raise TypeError(f"Weighted mean inputs must be numeric: {column}")

		analysis_data = data.query(condition_query) if condition_query else data
		valid_rows = analysis_data[[value_column, weight_column]].dropna()
		total_weight = valid_rows[weight_column].sum()
		if total_weight == 0:
			raise ValueError("Cannot calculate weighted mean: valid weights sum to zero.")

		return float(
			(valid_rows[value_column] * valid_rows[weight_column]).sum() / total_weight
		)

	def weighted_category_distribution(
		self,
		category_column: str,
		weight_column: str,
		condition_query: str | None = None,
	) -> pd.DataFrame:
		"""Sum survey weights by category and calculate weighted percentages."""
		data = self._require_working_data()
		for column in (category_column, weight_column):
			if column not in data.columns:
				raise KeyError(f"Column not found in working data: {column}")
		if not pd.api.types.is_numeric_dtype(data[weight_column]):
			raise TypeError(f"Weight column must be numeric: {weight_column}")

		analysis_data = data.query(condition_query) if condition_query else data
		distribution = (
			analysis_data.groupby(category_column, dropna=False, sort=False)[weight_column]
			.sum()
			.reset_index(name="weighted_population")
		)
		total_weight = distribution["weighted_population"].sum()
		distribution["weighted_percentage"] = (
			distribution["weighted_population"] / total_weight * 100
			if total_weight != 0
			else np.nan
		)
		return distribution

	def create_threshold_categories(
		self,
		column: str,
		bins: list[float],
		labels: list[str],
		new_column: str | None = None,
		right: bool = False,
		include_percentage: bool = False,
	) -> pd.Series | pd.DataFrame:
		"""Add labeled numeric intervals; by default each bin includes its lower bound."""
		data = self._require_working_data()
		if column not in data.columns:
			raise KeyError(f"Column not found in working data: {column}")
		if len(labels) != len(bins) - 1:
			raise ValueError("Provide exactly one label for each interval in bins.")

		category_column = new_column or f"{column}_category"
		data[category_column] = pd.cut(
			data[column],
			bins=bins,
			labels=labels,
			right=right,
			include_lowest=True,
		)
		if include_percentage:
			return self._category_distribution(data[category_column])
		return data[category_column]

	def map_categories(
		self,
		column: str,
		category_map: dict[object, object],
		new_column: str | None = None,
		include_percentage: bool = False,
	) -> pd.Series | pd.DataFrame:
		"""Create readable labels for selected values, preserving unmapped values."""
		data = self._require_working_data()
		if column not in data.columns:
			raise KeyError(f"Column not found in working data: {column}")

		category_column = new_column or f"{column}_category"
		mapped_values = data[column].map(category_map)
		data[category_column] = mapped_values.where(mapped_values.notna(), data[column])
		if include_percentage:
			return self._category_distribution(data[category_column])
		return data[category_column]

	def _category_distribution(self, categories: pd.Series) -> pd.DataFrame:
		"""Summarize category frequencies and their percentage of all rows."""
		distribution = (
			categories.value_counts(dropna=False, sort=False)
			.rename_axis("category")
			.reset_index(name="count")
		)
		distribution["percentage"] = (
			distribution["count"] / len(categories) * 100
			if len(categories)
			else float("nan")
		)
		return distribution

	def count_unique_values(
		self,
		column: str,
		condition_query: str,
		dropna: bool = True,
		include_percentage: bool = False,
	) -> int | tuple[int, float]:
		"""Count matching distinct values and optionally the matching-row percentage."""
		data = self._require_working_data()
		if column not in data.columns:
			raise KeyError(f"Column not found in working data: {column}")

		matching_rows = data.query(condition_query)[column]
		unique_count = int(matching_rows.nunique(dropna=dropna))
		if not include_percentage:
			return unique_count

		total_rows = len(data[column])
		percentage = (
			len(matching_rows) / total_rows * 100
			if total_rows
			else float("nan")
		)
		return unique_count, percentage

	def _require_raw_data(self) -> pd.DataFrame:
		"""Ensure the CSV has been loaded before another workflow step runs."""
		if self.raw_data is None:
			raise RuntimeError("Call load_data() before exploring or preparing data.")
		return self.raw_data

	def _require_working_data(self) -> pd.DataFrame:
		"""Ensure the working copy exists before summarizing or recoding it."""
		if self.working_data is None:
			raise RuntimeError("Call prepare_for_cleaning() before this operation.")
		return self.working_data


if __name__ == "__main__":
	# Run the standard read, inspect, and cleaning-preparation steps.
	workflow = MEPSDataWorkflow(DATA_FILE, VARIABLE_MAPPING)
	workflow.load_data()
	workflow.explore_data()
	workflow.prepare_for_cleaning()

	summary1 = workflow.summarize_and_rank(
		group_by="survey_year",
		continuous="annual_total_pay",
		rank_by="annual_total_pay",
	)
	print("Question 1")
	print(summary1)

	summary2 = workflow.summarize_and_rank(
		group_by= ["survey_year", "depression_2w"],
		continuous="annual_total_pay",
		rank_by="annual_total_pay",
	)

	summary2_1 = workflow.summarize_and_rank(
		group_by= "survey_year",
		continuous="annual_total_pay",
	    condition_query="depression_2w == 3",
		rank_by="annual_total_pay",
	)

	print("Question 2")
	print(summary2)
	print(summary2_1)

	summary3 = workflow.summarize_and_rank(
		group_by="survey_year",
		categorical="no_insurance",
		rank_by="no_insurance",
	)
	print("Question 3")
	print(summary3)


	summary4 = workflow.summarize_and_rank(
		group_by= ["survey_year", "medicaid_or_chip"],
		categorical="health",
		rank_by="health",
	)

	summary4_1 = workflow.summarize_and_rank(
		group_by="survey_year",
		categorical="health",
		condition_query="medicaid_or_chip == 2",
		rank_by="health",
	)
	print("Question 4")
	print(summary4)
	print(summary4_1)

	summary5 = workflow.summarize_and_rank(
		group_by= ["survey_year", "private_insurance"],
		categorical="health",
		rank_by="health",
	)

	summary5_1 = workflow.summarize_and_rank(
		group_by="survey_year",
		categorical="health",
		condition_query="private_insurance == 2",
		rank_by="health",
	)
	print("Question 5")
	print(summary5)
	print(summary5_1)	

	print("weighted version of answers")

	workflow.add_weighted_variable(
    value_column="annual_total_pay",
    weight_column="person_weight",
    new_column="weighted_annual_total_pay",
	)


	summary1_weighted = workflow.calculate_weighted_mean(
    value_column="annual_total_pay",
    weight_column="person_weight",
    condition_query="survey_year == 2020",
)
	print("Question 1 weighted")
	print(summary1_weighted)


	summary2_weighted = workflow.calculate_weighted_mean(
		value_column="annual_total_pay",
		weight_column="person_weight",
		condition_query="survey_year == 2020 and depression_2w == 3",
	)

	print("Question 2")
	print(summary2_weighted)


	summary3_weighted = workflow.weighted_category_distribution(
		category_column="no_insurance",
		weight_column="questionnaire_weight",
		condition_query="survey_year == 2020",
	)

	print("Question 3")
	print(summary3_weighted)


	summary4_weighted = workflow.weighted_category_distribution(
		category_column="health",
		weight_column="questionnaire_weight",
		condition_query="survey_year == 2020 and medicaid_or_chip == 2",
	)
	print("Question 4")
	print(summary4_weighted)

	summary5_weighted = workflow.weighted_category_distribution(
		category_column="health",
		weight_column="questionnaire_weight",
		condition_query="survey_year == 2020 and private_insurance == 2",
	)
	print("Question 5")
	print(summary5_weighted)

