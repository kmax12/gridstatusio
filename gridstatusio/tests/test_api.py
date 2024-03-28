import os

import pandas as pd
import pytest

import gridstatusio as gs
from gridstatusio.version import version_is_higher

client = gs.GridStatusClient(api_key=os.getenv("GRIDSTATUS_API_KEY_TEST"))


@pytest.mark.parametrize(
    "latest, current, expected",
    [
        ("1.0.0", "0.9.9", True),
        ("0.9.9", "1.0.0", False),
        ("1.0.0", "1.0.0", False),
        ("1.0.1", "1.0.0", True),
        ("1.0.0", "1.0.1", False),
        ("1.1.0", "1.0.9", True),
    ],
)
def test_version_is_higher(latest, current, expected):
    assert version_is_higher(latest, current) == expected


def test_invalid_api_key():
    client = gs.GridStatusClient(api_key="invalid")
    try:
        client.get_dataset(dataset="isone_fuel_mix", verbose=True)
    except Exception as e:
        assert "Invalid API key" in str(e)


def test_uses_columns():
    dataset = "ercot_sced_gen_resource_60_day"
    one_column = "resource_name"
    columns = ["interval_start_utc", "interval_end_utc", one_column]
    limit = 100
    df = client.get_dataset(
        dataset=dataset,
        columns=columns,
        verbose=True,
        limit=limit,
    )
    _check_dataframe(df, columns=columns, length=limit)

    # time columns always included
    # even if not specified
    df = client.get_dataset(
        dataset=dataset,
        columns=[one_column],
        verbose=True,
        limit=limit,
    )
    _check_dataframe(df, columns=columns, length=limit)

    # no columns specified
    ncols = 29
    df = client.get_dataset(dataset=dataset, verbose=True, limit=limit)
    assert df.shape == (limit, ncols), "Expected all columns"


def test_handles_unknown_columns():
    dataset = "ercot_fuel_mix"

    with pytest.raises(Exception) as e:
        client.get_dataset(
            dataset=dataset,
            columns=["invalid_column"],
            verbose=True,
        )

    assert "Column invalid_column not found in dataset" in str(e.value)

    with pytest.raises(Exception) as e:
        client.get_dataset(
            dataset=dataset,
            columns=["invalid_column"],
            resample="1 hour",
            verbose=True,
        )

    assert "Column invalid_column not found in dataset" in str(e.value)


def test_list_datasets():
    datasets = client.list_datasets(return_list=True)
    assert isinstance(datasets, list), "Expected a list of datasets"
    assert len(datasets) > 0, "Expected at least one dataset"


def test_list_datasets_filter():
    filter_term = "fuel_mix"
    min_results = 7
    # run once without printing things out
    client.list_datasets(filter_term=filter_term, return_list=False)
    datasets = client.list_datasets(filter_term=filter_term, return_list=True)
    assert (
        len(datasets) >= min_results
    ), f"Expected at least {min_results} results with filter term '{filter_term}'"


def _check_dataframe(df, length=None, columns=None):
    assert isinstance(df, pd.DataFrame)
    assert len(df) > 0

    # todo should really on be either utc or local
    # possible datetime columns
    datetime_columns = [
        "interval_start_utc",
        "interval_end_utc",
        "interval_start_local",
        "interval_end_local",
    ]
    for c in datetime_columns:
        if c in df.columns:
            assert pd.api.types.is_datetime64_any_dtype(df[c])

    if columns is not None:
        assert df.columns.to_list() == columns

    if length is not None:
        assert len(df) == length
    assert df.index.is_unique


def test_set_api_works():
    client = gs.GridStatusClient(api_key="test")
    assert client.api_key == "test"


# todo test require_only_kwargs
def test_get_dataset_date_range():
    start = "2023-01-01"
    end = "2023-01-05"
    df = client.get_dataset(
        dataset="isone_fuel_mix",
        start=start,
        end=end,
        verbose=True,
    )

    _check_dataframe(df)

    # make sure min of interval_start_utc equals start
    assert df["interval_start_utc"].min().strftime("%Y-%m-%d") == start
    assert df["interval_end_utc"].max().strftime("%Y-%m-%d") == end


def test_index_unique_multiple_pages():
    start = "2023-01-01"
    end = "2023-01-02"
    df = client.get_dataset(
        dataset="isone_fuel_mix",
        start=start,
        end=end,
        verbose=True,
        limit=100,
    )

    _check_dataframe(df)


def test_filter_operator():
    dataset = "caiso_curtailment"
    limit = 100
    category_column = "curtailment_type"
    category_value = "Economic"
    category_values = ["Economic", "SelfSchCut", "ExDispatch"]
    numeric_column = "curtailment_mw"
    numeric_value = 100

    df = client.get_dataset(
        dataset=dataset,
        filter_column=category_column,
        filter_value=category_value,
        filter_operator="=",
        limit=limit,
        verbose=True,
    )
    _check_dataframe(df)
    assert df["curtailment_type"].unique() == [category_value]

    df = client.get_dataset(
        dataset=dataset,
        filter_column=category_column,
        filter_value=category_value,
        filter_operator="!=",
        limit=limit,
        verbose=True,
    )
    _check_dataframe(df)
    assert set(df["curtailment_type"].unique()) == set(category_values) - {
        category_value,
    }

    df = client.get_dataset(
        dataset=dataset,
        filter_column=category_column,
        filter_value=category_values,
        filter_operator="in",
        limit=limit,
        verbose=True,
    )
    _check_dataframe(df)
    assert set(df["curtailment_type"].unique()) == set(category_values)

    # test numeric operators = ["<", "<=", ">", ">=", "="]

    df = client.get_dataset(
        dataset=dataset,
        filter_column=numeric_column,
        filter_value=numeric_value,
        filter_operator="<",
        limit=limit,
        verbose=True,
    )

    _check_dataframe(df)
    assert df["curtailment_mw"].max() < numeric_value

    df = client.get_dataset(
        dataset=dataset,
        filter_column=numeric_column,
        filter_value=numeric_value,
        filter_operator="<=",
        limit=limit,
        verbose=True,
    )

    _check_dataframe(df)
    assert df["curtailment_mw"].max() <= numeric_value

    df = client.get_dataset(
        dataset=dataset,
        filter_column=numeric_column,
        filter_value=numeric_value,
        filter_operator=">",
        limit=limit,
        verbose=True,
    )

    _check_dataframe(df)
    assert df["curtailment_mw"].min() > numeric_value

    df = client.get_dataset(
        dataset=dataset,
        filter_column=numeric_column,
        filter_value=numeric_value,
        filter_operator=">=",
        limit=limit,
        verbose=True,
    )

    _check_dataframe(df)
    assert df["curtailment_mw"].min() >= numeric_value

    df = client.get_dataset(
        dataset=dataset,
        filter_column=numeric_column,
        filter_value=numeric_value,
        filter_operator="=",
        limit=limit,
        verbose=True,
    )

    _check_dataframe(df)
    assert df["curtailment_mw"].unique() == [numeric_value]


def test_filter_operator_in():
    locations = ["LZ_WEST", "LZ_HOUSTON"]
    df = client.get_dataset(
        dataset="ercot_spp_day_ahead_hourly",
        filter_column="location",
        filter_value=locations,
        filter_operator="in",
        start=pd.Timestamp("2023-09-07"),
        limit=10,
        verbose=True,
    )
    assert set(df["location"].unique()) == set(locations)
    _check_dataframe(df)


def test_get_dataset_verbose(capsys):
    # make sure nothing print to stdout
    client.get_dataset(
        dataset="isone_fuel_mix",
        start="2023-01-01",
        end="2023-01-05",
        limit=1,
        verbose=False,
    )

    captured = capsys.readouterr()
    assert captured.out == ""

    # test debug
    client.get_dataset(
        dataset="isone_fuel_mix",
        start="2023-01-01",
        end="2023-01-05",
        limit=1,
        verbose="debug",
    )

    captured = capsys.readouterr()
    assert captured.out != ""
    # make sure the params are printed
    assert "Done in" in captured.out
    assert "Params: {" in captured.out

    # make sure something prints to stdout
    # but not the params
    client.get_dataset(
        dataset="isone_fuel_mix",
        start="2023-01-01",
        end="2023-01-05",
        limit=1,
        verbose=True,
    )

    captured = capsys.readouterr()
    assert captured.out != ""
    assert "Done in" in captured.out
    assert "Params: {" not in captured.out

    # same as verbose=True
    client.get_dataset(
        dataset="isone_fuel_mix",
        start="2023-01-01",
        end="2023-01-05",
        limit=1,
        verbose="info",
    )

    captured = capsys.readouterr()
    assert captured.out != ""
    assert "Done in" in captured.out
    assert "Params: {" not in captured.out


def test_handles_all_nan_columns():
    # these are dates with no btm solar data
    start = "2020-01-01"
    end = "2020-01-02"
    btm_col = "btm_solar.capitl"
    time_columns = ["interval_start_utc", "interval_end_utc"]
    time_columns_local = ["interval_start_local", "interval_end_local"]

    # with time zone
    df = client.get_dataset(
        "nyiso_standardized_5_min",
        start=start,
        end=end,
        tz="America/New_York",
        columns=time_columns + [btm_col],
    )

    assert set(time_columns_local + [btm_col]) == set(df.columns)
    assert pd.api.types.is_datetime64_any_dtype(df[time_columns_local[0]])
    assert pd.api.types.is_datetime64_any_dtype(df[time_columns_local[1]])
    assert df[btm_col].dtype == "object"

    # without timezone
    df = client.get_dataset(
        "nyiso_standardized_5_min",
        start=start,
        end=end,
        columns=time_columns + [btm_col],
    )

    assert set(time_columns + [btm_col]) == set(df.columns)
    assert pd.api.types.is_datetime64_any_dtype(df[time_columns[0]])
    assert pd.api.types.is_datetime64_any_dtype(df[time_columns[1]])
    assert df[btm_col].dtype == "object"


def test_handles_no_results():
    btm_col = "capitl"
    time_columns = ["interval_start_utc", "interval_end_utc"]
    time_columns_local = ["interval_start_local", "interval_end_local"]

    # no data, with time zone
    df = client.get_dataset(
        "nyiso_btm_solar",
        start="2020-01-01",
        end="2020-01-02",
        tz="America/New_York",
        columns=time_columns + [btm_col],
    )

    assert set(time_columns_local + [btm_col]) == set(df.columns)
    assert pd.api.types.is_datetime64_any_dtype(df[time_columns_local[0]])
    assert pd.api.types.is_datetime64_any_dtype(df[time_columns_local[1]])
    assert df[btm_col].dtype == "object"

    # no data, without timezone
    df = client.get_dataset(
        "nyiso_btm_solar",
        start="2020-01-01",
        end="2020-01-02",
        columns=time_columns + [btm_col],
    )

    assert set(time_columns + [btm_col]) == set(df.columns)
    assert pd.api.types.is_datetime64_any_dtype(df[time_columns[0]])
    assert pd.api.types.is_datetime64_any_dtype(df[time_columns[1]])
    assert df[btm_col].dtype == "object"

    # this date range crosses from no data to data, with timezone
    df = client.get_dataset(
        "nyiso_btm_solar",
        start="2020-11-16",
        end="2020-11-18",
        tz="America/New_York",
        columns=time_columns + [btm_col],
    )

    assert set(time_columns_local + [btm_col]) == set(df.columns)
    assert pd.api.types.is_datetime64_any_dtype(df[time_columns_local[0]])
    assert pd.api.types.is_datetime64_any_dtype(df[time_columns_local[1]])
    assert df[btm_col].dtype == "float64"

    # this date range crosses from no data to data, without timezone
    df = client.get_dataset(
        "nyiso_btm_solar",
        start="2020-11-16",
        end="2020-11-18",
        columns=time_columns + [btm_col],
    )

    assert set(time_columns + [btm_col]) == set(df.columns)
    assert pd.api.types.is_datetime64_any_dtype(df[time_columns[0]])
    assert pd.api.types.is_datetime64_any_dtype(df[time_columns[1]])
    assert df[btm_col].dtype == "float64"


def test_resample_frequency():
    # test with interval_start_utc
    df = client.get_dataset(
        dataset="isone_fuel_mix",
        start="2023-01-01",
        end="2023-01-02",
        resample="hour",
        verbose=True,
    )

    assert df.shape[0] == 24
    _check_dataframe(
        df,
        columns=[
            "interval_start_utc",
            "interval_end_utc",
            "coal",
            "hydro",
            "landfill_gas",
            "natural_gas",
            "nuclear",
            "oil",
            "other",
            "refuse",
            "solar",
            "wind",
            "wood",
        ],
    )

    # test with columns
    # should always return time columns
    df = client.get_dataset(
        dataset="isone_fuel_mix",
        start="2023-01-01",
        end="2023-01-02",
        columns=["coal"],
        resample="hour",
        verbose=True,
    )
    assert df.shape[0] == 24
    _check_dataframe(
        df,
        columns=[
            "interval_start_utc",
            "interval_end_utc",
            "coal",
        ],
    )

    # test with time_utc column only
    df = client.get_dataset(
        dataset="ercot_real_time_as_monitor",
        start="2023-08-01",
        end="2023-08-02",
        # we don't have to provide time_utc
        # but will for testing purposes
        # to make sure it works
        columns=["time_utc", "prc"],
        resample="5 minutes",
        verbose=True,
    )

    _check_dataframe(
        df,
        length=288,
        columns=[
            "time_utc",
            "interval_start_utc",
            "interval_end_utc",
            "resample_frequency",
            "prc",
        ],
    )

    # assert resample_frequency is 5 minute
    assert df["resample_frequency"].unique() == ["5 MINUTES"]

    # test with time_utc column only, dont need to specify plural
    df = client.get_dataset(
        dataset="ercot_real_time_as_monitor",
        start="2023-08-01",
        end="2023-08-02",
        # we will skip time_utc
        # since we used it above
        columns=["prc"],
        # dont need to specify plural
        resample="4 hour",
        verbose=True,
    )

    _check_dataframe(
        df,
        length=6,
        columns=[
            "time_utc",
            "interval_start_utc",
            "interval_end_utc",
            "resample_frequency",
            "prc",
        ],
    )

    # assert resample_frequency is 5 minute
    assert df["resample_frequency"].unique() == ["4 HOUR"]


def test_resample_by():
    # test with interval_start_utc
    df = client.get_dataset(
        dataset="eia_ba_interchange_hourly",
        start="Sep 1, 2023",
        end="Sep 3, 2023",
        resample="1 day",
        resample_by=["interval_start_utc", "to_ba", "from_ba"],
    )

    _check_dataframe(
        df,
        # number of pairs times number of days
        length=df[["to_ba", "from_ba"]].drop_duplicates().shape[0] * 2,
        columns=["interval_start_utc", "interval_end_utc", "to_ba", "from_ba", "mw"],
    )

    # check that time_col is requeired

    with pytest.raises(Exception) as e:
        client.get_dataset(
            dataset="eia_ba_interchange_hourly",
            start="Sep 1, 2023",
            end="Sep 3, 2023",
            resample="1 day",
            resample_by=["to_ba", "from_ba"],
        )

    assert "resample_by must include the time column: interval_start_utc." in str(
        e.value,
    )


def test_resample_function():
    # test with interval_start_utc
    df_max = client.get_dataset(
        dataset="caiso_load",
        start="Sep 1, 2023",
        end="Sep 3, 2023",
        resample="1 day",
        resample_function="max",
    )

    _check_dataframe(
        df_max,
        length=2,
        columns=["interval_start_utc", "interval_end_utc", "load"],
    )

    df_min = client.get_dataset(
        dataset="caiso_load",
        start="Sep 1, 2023",
        end="Sep 3, 2023",
        resample="1 day",
        resample_function="min",
    )

    _check_dataframe(
        df_min,
        length=2,
        columns=["interval_start_utc", "interval_end_utc", "load"],
    )

    # interval_start_utc and interval_end_utc should be the same
    # load max should be higher than load min

    assert df_max["interval_start_utc"].equals(df_min["interval_start_utc"])
    assert df_max["interval_end_utc"].equals(df_min["interval_end_utc"])
    assert (df_max["load"] > df_min["load"]).all()


def test_publish_time_latest():
    today = pd.Timestamp.now(tz="UTC").floor("D")

    df = client.get_dataset(
        dataset="ercot_hourly_resource_outage_capacity_reports",
        start=today - pd.Timedelta(days=2),
        end=today,
        publish_time="latest",
        verbose=True,
    )

    assert df["publish_time_utc"].nunique() > 1, "Expected multiple publish times"
    assert (
        df["interval_start_utc"].value_counts() == 1
    ).all(), "Expected each interval to only occur once"


def test_publish_time_and_resample():
    today = pd.Timestamp.now(tz="UTC").ceil("D")

    # because no publish time is provided
    # this is resampled by unique publish time
    df = client.get_dataset(
        dataset="ercot_hourly_resource_outage_capacity_reports",
        start=today - pd.Timedelta(days=2),
        end=today,
        resample="1 day",
        verbose=True,
    )
    assert df["publish_time_utc"].nunique() > 1, "Expected multiple publish times"

    # make sure it still works if a column is provided
    df = client.get_dataset(
        dataset="ercot_hourly_resource_outage_capacity_reports",
        start=today - pd.Timedelta(days=2),
        end=today,
        columns=["total_resource_mw_zone_south"],
        resample="1 day",
        verbose=True,
    )
    assert df["publish_time_utc"].nunique() > 1, "Expected multiple publish times"

    # because of resampling and provided publish time option
    # there is no longer a single publish time value for each row
    # so it should be removed
    df = client.get_dataset(
        dataset="ercot_hourly_resource_outage_capacity_reports",
        start=today - pd.Timedelta(days=2),
        end=today,
        publish_time="latest",
        resample="1 day",
        verbose=True,
    )
    assert "publish_time_utc" not in df.columns, "Expected publish time to be removed"
    assert (
        df["interval_start_utc"].value_counts() == 1
    ).all(), "Expected each interval to only occur once"

    # make sure it still works if a column is provided
    df = client.get_dataset(
        dataset="ercot_hourly_resource_outage_capacity_reports",
        start=today - pd.Timedelta(days=2),
        end=today,
        publish_time="latest",
        columns=["total_resource_mw_zone_south"],
        resample="1 day",
        verbose=True,
    )
    assert "publish_time_utc" not in df.columns, "Expected publish time to be removed"
    assert (
        df["interval_start_utc"].value_counts() == 1
    ).all(), "Expected each interval to only occur once"


def test_publish_time_latest_report():
    df = client.get_dataset(
        dataset="ercot_hourly_resource_outage_capacity_reports",
        publish_time="latest_report",
        verbose=True,
    )

    assert df["publish_time_utc"].nunique() == 1, "Expected one publish time"
    assert (
        df["interval_start_utc"].value_counts() == 1
    ).all(), "Expected each interval to only occur once"


def test_publish_time_specific_time():
    publish_time = "2023-10-04 04:02:52+00:00"

    df = client.get_dataset(
        dataset="ercot_hourly_resource_outage_capacity_reports",
        publish_time=publish_time,
        verbose=True,
    )

    assert (df["publish_time_utc"] == publish_time).all(), "Expected one publish time"
    assert (
        df["interval_start_utc"].value_counts() == 1
    ).all(), "Expected each interval to only occur once"


def test_pagination():
    dataset = "isone_fuel_mix"

    # return 100 rows
    df = client.get_dataset(
        dataset=dataset,
        limit=100,
    )

    assert len(df) == 100

    # test multiple pages
    df = client.get_dataset(
        dataset=dataset,
        limit=100,
        page_size=25,
    )
    assert len(df) == 100

    # test limit less than page size
    df = client.get_dataset(
        dataset=dataset,
        limit=25,
        page_size=100,
    )
    assert len(df) == 25

    # test no limit, no page size
    df = client.get_dataset(
        dataset=dataset,
        start=pd.Timestamp.now(tz="UTC") - pd.Timedelta(hours=1),
    )
    assert len(df) > 0

    # test no limit, with page size
    df = client.get_dataset(
        dataset=dataset,
        start=pd.Timestamp.now(tz="UTC") - pd.Timedelta(minutes=30),
        # 5 minute data so at most 12 rows
        page_size=1,
    )
    assert len(df) > 0

    # test too large of page size errors
    with pytest.raises(Exception):
        client.get_dataset(
            dataset=dataset,
            page_size=10**10,
        )
