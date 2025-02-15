# -*- coding: utf-8 -*-
"""
@File: xdataframe
@Author: ltw
@Time: 2022/8/4
"""
import functools
import json
from bisect import bisect_left
import pandas as pd
import numpy as np


def empty_df(columns=None):
    """
    :param columns:
    :return:
    """
    if not columns:
        return pd.DataFrame()
    return pd.DataFrame(columns=columns)


def df_col2row_idx(_df, index_keys, data_key):
    """
    # df 列转行索引
    #
    #           day      player_id   money
    # 0    20210527  1508277000053     6.0
    # 1    20210527  1508277000058     6.0
    # 3    20210528  1508277000058     12.0
    #
    # res_df = df_col2row_idx(res_df, ['player_id', 'day'], 'money')
    #
    #         player_id  20210527  20210528
    # 0    1508277000053       6.0       NaN
    # 1    1508277000058       6.0       12.0
    """
    df_index = _df.set_index(index_keys)[data_key]
    _df = df_index.unstack()
    _df = _df.rename_axis(None, axis="columns").reset_index()
    return _df


def cut_bins(val, bins, concat="-"):
    """
    :param val:
    :param bins:
    :param concat:
    :return:
    """
    if not val:
        return val

    if val > bins[-1]:
        val = bins[-1]

    position = bisect_left(bins, val)
    labels = f"{bins[position - 1] + 1}{concat}{ bins[position]}"
    return labels, bins[position]


def df_cut_bins(_df, key, bins, insert_zero=True):
    """
    :param _df:
    :param key:
    :param bins:
    :param insert_zero:
    :return:
    """

    def prefix_bins(_bins):
        """
        排序
        :param _bins:
        :return:
        """
        _bins = sorted(map(int, _bins))
        if insert_zero and _bins[0] != 0:
            _bins.insert(0, 0)
        return _bins

    bins = prefix_bins(bins)
    return _df[key].apply(cut_bins, bins=bins)


def cal_round_rate(data, precision=2, suffix="%", invalid_value="-"):
    """
    :param data:
    :param precision:
    :param suffix:
    :param invalid_value:
    :return:
    """
    if isinstance(data, pd.DataFrame):
        return data.apply(cal_round_rate, args=(precision, suffix), axis=0)
    if isinstance(data, pd.Series):
        if str(invalid_value).isdigit():
            data = data.fillna(invalid_value)
        data = data.astype(float).round(precision)
        if precision == 0:
            data = data.astype(int)
        return data.apply(
            lambda d: invalid_value if (d == np.inf or np.isnan(d)) else f"{d}{suffix}"
        )
    if isinstance(data, (int, float)):
        if np.isnan(data) or data == np.inf:
            return invalid_value
        if precision == 0:
            return str(int(data)) + suffix
        return str(round(data, precision)) + suffix
    return invalid_value


def func_cal_round_rate(func, **kw):
    """
    用于快速构造用agg或apply传递的cal_round_rate函数
    :param func:
    :param kw:
    :return:
    """

    @functools.wraps(func)
    def wrapper(data, *args, **kwargs):
        if isinstance(func, str):
            data = getattr(data, func)()
        else:
            data = func(data)
        return cal_round_rate(data, **kw)

    return wrapper


def dict_to_json(data):
    """用于es对象转json,并且正常显示中文"""
    if not data:
        if not isinstance(data, (str, bytes)):
            data = str(data)
        return data
    if isinstance(data, float) and pd.isna(data):
        return ""
    return json.dumps(data, ensure_ascii=False)


def df_json_normalize(_df, columns, prefixes=None, sep=".", column_prefix=False):
    """
    df: 原df数据
    record_paths: 需要解析的列名list
    record_prefixes: 需要填充前缀list
    sep: 填充前缀的分隔符
    column_prefix: 使用字段名作为前缀
    """
    for idx, record_column in enumerate(columns):
        if record_column not in _df.columns:
            continue
        tmp_df = pd.DataFrame(_df[record_column].apply(fill_dict).tolist())
        record_prefix = None
        if column_prefix:
            record_prefix = record_column
        elif prefixes is not None:
            record_prefix = prefixes[idx]
        if record_prefix:
            tmp_df.columns = [f"{record_prefix}{sep}{col}" for col in tmp_df.columns]
        _df[tmp_df.columns] = tmp_df
        _df = _df.drop(columns=record_column)
    return _df


def df_fill_columns(_df, columns, default="", tpe=None):
    """
    填充列,以确保列存在
    """
    if isinstance(columns, (list, tuple)):
        for column in columns:
            if column not in _df.columns:
                _df[column] = default
            elif tpe:
                _df[column] = _df[column].fillna(default).astype(tpe)
            else:
                _df[column] = _df[column].fillna(default)

    elif isinstance(columns, dict):
        for column, val in columns.items():
            if column not in _df.columns:
                _df[column] = val
            elif tpe:
                _df[column] = _df[column].fillna(default).astype(tpe)
            else:
                _df[column] = _df[column].fillna(default)
    else:
        if columns not in _df.columns:
            _df[columns] = default
        elif tpe:
            _df[columns] = _df[columns].fillna(default).astype(tpe)
        else:
            _df[columns] = _df[columns].fillna(default)
    return _df


def df_rm_columns(_df, columns):
    """
    安全删除列
    :param _df:dataframe or series
    :param columns:需删除的列或index
    :return:新的dataframe or series
    """
    if isinstance(_df, pd.Series):
        rm_columns = [column for column in columns if column in _df.index]
        if rm_columns:
            _df = _df.drop(rm_columns)
    else:
        rm_columns = [column for column in columns if column in _df.columns]
        if rm_columns:
            _df = _df.drop(columns=rm_columns)
    return _df


def fill_dict(data):
    """填充{}到nan"""
    return {} if not isinstance(data, dict) and pd.isna(data) else data


def fill_list(data):
    """填充[]到nan"""
    return [] if not isinstance(data, list) and pd.isna(data) else data


def div_rate(data_df: pd.DataFrame, top_key, bottom_key, precision=2) -> pd.Series:
    """
    dataframe div函数计算百分比 top_key / bottom_key
    example:
        data_df["pay_rate"] = div_rate(data_df, "pid_cnt", "act_player_cnt")
    :return:
    """
    fmt_show = f"%0.{precision}f"
    if isinstance(top_key, list):
        return (
            data_df[top_key]
            .div(data_df[bottom_key], axis=0)
            .round(precision + 2)
            .fillna(0)
            .applymap(lambda x: f"{ fmt_show % round(x * 100, precision) }%")
        )
    return (
        data_df[top_key]
        .div(data_df[bottom_key], axis=0)
        .round(precision + 2)
        .fillna(0)
        .apply(lambda x: f"{fmt_show % round(x * 100, precision) }%")
    )


def div_round(data_df: pd.DataFrame, top_key, bottom_key, precision=2) -> pd.Series:
    """
    dataframe div函数 top_key / bottom_key
    example:
        data_df["pay_rate"] = div_round(data_df, "pid_cnt", "act_player_cnt")
    :return:
    """
    return data_df[top_key].div(data_df[bottom_key], axis=0).round(precision)


def concat_cols(data_df: pd.DataFrame, cols: list, concat_by="|") -> pd.Series:
    """
    合将列，汇总后的列为：recharge_cnt|recharge_type_id
    example:
        data_df["show_pid_cnt"] = concat_cols(data_df, ["pid_cnt", "pid_rate"]) -> 98|10.0%
    """
    res = None
    for col in cols:
        if res is None:
            res = data_df[col].astype(str)
        else:
            res = res + data_df[col].astype(str)
        if col == cols[-1]:
            continue
        res = res + concat_by
    return res


def df_astype(_df: pd.DataFrame, columns=(), excludes=(), tpe=str):
    """
    dataframe转类型,可指定列进行转换,也可反向排除某些列,进行转换
    主要用于某些数据列,仅少数列无需转,多数列需要转时,需要列举所有的列,此举可减少编写
    columns:需转换的列
    excludes:除了excludes外的列将进行转换(优先级更高)
    tpe:需转换的类型
    """
    if excludes:
        df_columns = _df.columns.tolist()
        columns = list(set(df_columns) - set(excludes))
    if columns:
        _df[columns] = _df[columns].astype(tpe)
    return _df


def show_range_labels(_df, key, bins, insert_zero=True, max_label_fmt=None):
    """
    # money_df ####
    # player_id, money
    # 19296,  0
    # 21169,  8
    # 24003,  98
    money_df[["money_label", "label_rank"]] = show_range_labels(
        money_df, "money", bins=[0, 8, 41], max_label_fmt="{}+"
    ) =>
    # player_id, money, money_label, label_rank
    # 19296,    0,  "",    -1
    # 21169,    8,  "1-8",    8
    # 24003,    98, "41+”,    41
    insert_zero : 是否在bins最前面插入0
    :return:
    """

    def prefix_bins(_bins):
        _bins = sorted(map(int, _bins))
        if insert_zero and _bins[0] != 0:
            _bins.insert(0, 0)
        return _bins

    bins = prefix_bins(bins)
    concat = "-"

    def cut_bins(row):
        val = row[key]
        if not val:
            return "", -1

        if val > bins[-1]:
            val = bins[-1]

        position = bisect_left(bins, val)
        if position <= 0:
            return "", -1
        left_val = bins[position - 1] + 1
        right_val = bins[position]
        labels = f"{left_val}{concat}{right_val}"
        if position == len(bins) - 1 and max_label_fmt is not None:
            labels = max_label_fmt.format(left_val)
        return labels, bins[position]

    return _df.apply(cut_bins, axis=1, result_type="expand")
