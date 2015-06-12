from __future__ import division

import pandas as pd
import numpy as np
import scipy as sp
import scipy.stats as stats
import scipy.signal as signal

import statsmodels.api as sm

import datetime

# timeseries manipulation functions


def var_cov_var_normal(P, c, mu=0, sigma=1, **kwargs):
    """
    Variance-Covariance calculation of daily Value-at-Risk
    using confidence level c, with mean of returns mu
    and standard deviation of returns sigma, on a portfolio
    of value P.
    """
    alpha = sp.stats.norm.ppf(1 - c, mu, sigma)
    return P - P * (alpha + 1)


def rolling_metric_stat(ret_ts, metric, stat_func=np.mean,
                        window=63, sample_freq=21,
                        return_all_values=False):
    roll_results = pd.rolling_apply(ret_ts, window, metric).dropna()
    roll_results_sample = roll_results[
        np.sort(
            range(
                len(roll_results) - 1, 0, -sample_freq))]

    if return_all_values:
        return roll_results_sample
    else:
        temp_f = lambda x: stat_func(x)
        return temp_f(roll_results_sample)


def normalize(df, withStartingValue=1):
    if withStartingValue > 1:
        return withStartingValue * (df / df.iloc[0])
    else:
        return df / df.iloc[0]


def cum_returns(df, withStartingValue=None):
    if withStartingValue is None:
        return np.exp(np.log(1 + df).cumsum()) - 1
    else:
        return np.exp(np.log(1 + df).cumsum()) * withStartingValue


def aggregate_returns(df_daily_rets, convert_to):
    cumulate_returns = lambda x: cum_returns(x)[-1]
    if convert_to == 'daily':
        return df_daily_rets
    elif convert_to == 'weekly':
        return df_daily_rets.groupby(
            [lambda x: x.year, lambda x: x.month, lambda x: x.isocalendar()[1]]).apply(cumulate_returns)
    elif convert_to == 'monthly':
        return df_daily_rets.groupby(
            [lambda x: x.year, lambda x: x.month]).apply(cumulate_returns)
    elif convert_to == 'yearly':
        return df_daily_rets.groupby(
            [lambda x: x.year]).apply(cumulate_returns)
    else:
        ValueError('convert_to must be daily, weekly, monthly or yearly')


def detrend_TS(theTS):
    return pd.Series(
        data=signal.detrend(
            theTS.values),
        index=theTS.index.values)


def append_series(ts1, ts2):
    '''
    @params
      ts1: <pd.Series>
          The 1st Series
      ts2: <pd.Series>
          The 2nd Series to be appended below 1st timeseries
    '''
    return pd.Series(
        data=np.concatenate([ts1, ts2]), index=np.concatenate([ts1.index, ts2.index]))


def dfTS(df, dateColumnLabel='Date'):
    # e.g.: takes a dataframe from a yahoo finance price csv and returns a df
    # with datetime64 index
    colNames = df.columns
    tempDF = df.copy()
    indexDates = map(np.datetime64, df.ix[:, dateColumnLabel].values)
    # tempDF = pd.DataFrame(data=df.values , index=map(pd.to_datetime,
    # indexDates))
    tempDF = pd.DataFrame(data=df.values, index=indexDates)
    tempDF.columns = colNames

    return tempDF.drop(axis=1, labels=dateColumnLabel).sort_index()


def multi_TS_to_DF_from_dict(
        tsDictInput,
        asPctChange=False,
        startDate=None,
        endDate=None,
        dropNA=False,
        ffillNA=False,
        fillNAvalue=None):
    tempDict = {}

    for i in tsDictInput.keys():
        if asPctChange:
            # print(i)
            # print(tsDictInput.get(i).head())
            tempDict[i] = slice_TS(
                tsDictInput.get(i).pct_change().dropna(),
                startDate=startDate,
                endDate=endDate)
        else:
            tempDict[i] = slice_TS(
                tsDictInput.get(i),
                startDate=startDate,
                endDate=endDate)
    tempDF = pd.DataFrame(tempDict)
    if dropNA:
        tempDF = tempDF.dropna()
    elif ffillNA:
        tempDF = tempDF.fillna(method="ffill")
    elif fillNAvalue is not None:
        tempDF = tempDF.fillna(fillNAvalue)

    return tempDF


def multi_TS_to_DF(
        tsSeriesList,
        tsSeriesNamesArr,
        asPctChange=False,
        startDate=None,
        endDate=None,
        dropNA=False,
        ffillNA=False,
        fillNAvalue=None):
    tempDict = {}

    for i in range(0, len(tsSeriesNamesArr)):
        if asPctChange:
            tempDict[
                tsSeriesNamesArr[i]] = slice_TS(
                tsSeriesList[i].pct_change().dropna(),
                startDate=startDate,
                endDate=endDate)
        else:
            tempDict[tsSeriesNamesArr[i]] = tsSeriesList[i]
    tempDF = pd.DataFrame(tempDict)
    if dropNA:
        tempDF = tempDF.dropna()
    elif ffillNA:
        tempDF = tempDF.fillna(method="ffill")
    elif fillNAvalue is not None:
        tempDF = tempDF.fillna(fillNAvalue)

    return tempDF


def slice_TS(
        theTS,
        startDate=None,
        endDate=None,
        inclusive_start=False,
        inclusive_end=False):

    if (startDate is None) and (endDate is None):
        return theTS

    if startDate is None:
        if inclusive_end:
            return theTS[:endDate]
        else:
            return theTS[:endDate][:-1]

    if endDate is None:
        if inclusive_start:
            return theTS[startDate:]
        else:
            return theTS[startDate:][1:]

    if inclusive_start & inclusive_end:
        return theTS[startDate:endDate]

    if inclusive_start & ~inclusive_end:
        return theTS[startDate:endDate][:-1]
    elif ~inclusive_start & inclusive_end:
        return theTS[startDate:endDate][1:]
    elif ~inclusive_start & ~inclusive_end:
        return theTS[startDate:endDate][1:-1]

    return pd.Series()


# timeseries manipulation functions


# Strategy Performance statistics & timeseries analysis functions

def max_drawdown(ts, inputIsNAV=True):
    if ts.size < 1:
        return np.nan

    if inputIsNAV:
        temp_ts = ts
    else:
        temp_ts = cum_returns(ts, withStartingValue=100)

    MDD = 0
    DD = 0
    peak = -99999
    for value in temp_ts:
        if (value > peak):
            peak = value
        else:
            DD = (peak - value) / peak
        if (DD > MDD):
            MDD = DD
    return -1 * MDD


def annual_return(ts, inputIsNAV=True, style='calendar'):
    # if style == 'compound' then return will be calculated in geometric terms: (1+mean(all_daily_returns))^252 - 1
    # if style == 'calendar' then return will be calculated as ((last_value - start_value)/start_value)/num_of_years
    # if style == 'arithmetic' then return is simply
    # mean(all_daily_returns)*252
    if ts.size < 1:
        return np.nan

    if inputIsNAV:
        tempReturns = ts.pct_change().dropna()
        if style == 'calendar':
            num_years = len(tempReturns) / 252
            start_value = ts[0]
            end_value = ts[-1]
            return ((end_value - start_value) / start_value) / num_years
        if style == 'compound':
            return pow((1 + tempReturns.mean()), 252) - 1
        else:
            return tempReturns.mean() * 252
    else:
        if style == 'calendar':
            num_years = len(ts) / 252
            temp_NAV = cum_returns(ts, withStartingValue=100)
            start_value = temp_NAV[0]
            end_value = temp_NAV[-1]
            return ((end_value - start_value) / start_value) / num_years
        if style == 'compound':
            return pow((1 + ts.mean()), 252) - 1
        else:
            return ts.mean() * 252


def annual_volatility(ts, inputIsNAV=True):
    if ts.size < 2:
        return np.nan
    if inputIsNAV:
        tempReturns = ts.pct_change().dropna()
        return tempReturns.std() * np.sqrt(252)
    else:
        return ts.std() * np.sqrt(252)


def calmer_ratio(ts, inputIsNAV=True, returns_style='calendar'):
    temp_max_dd = max_drawdown(ts=ts, inputIsNAV=inputIsNAV)
    # print(temp_max_dd)
    if temp_max_dd < 0:
        if inputIsNAV:
            temp = annual_return(ts=ts,
                                 inputIsNAV=True,
                                 style=returns_style) / abs(max_drawdown(ts=ts,
                                                                         inputIsNAV=True))
        else:
            tempNAV = cum_returns(ts, withStartingValue=100)
            temp = annual_return(ts=tempNAV,
                                 inputIsNAV=True,
                                 style=returns_style) / abs(max_drawdown(ts=tempNAV,
                                                                         inputIsNAV=True))
        # print(temp)
    else:
        return np.nan

    if np.isinf(temp):
        return np.nan
    else:
        return temp


def sharpe_ratio(ts, inputIsNAV=True, returns_style='calendar'):
    return annual_return(ts,
                         inputIsNAV=inputIsNAV,
                         style=returns_style) / annual_volatility(ts,
                                                                  inputIsNAV=inputIsNAV)


def stability_of_timeseries(ts, logValue=True, inputIsNAV=True):
    if ts.size < 2:
        return np.nan

    if logValue:
        if inputIsNAV:
            tempValues = np.log10(ts.values)
            tsLen = ts.size
        else:
            temp_ts = cum_returns(ts, withStartingValue=100)
            tempValues = np.log10(temp_ts.values)
            tsLen = temp_ts.size
    else:
        if inputIsNAV:
            tempValues = ts.values
            tsLen = ts.size
        else:
            temp_ts = cum_returns(ts, withStartingValue=100)
            tempValues = temp_ts.values
            tsLen = temp_ts.size

    X = range(0, tsLen)
    X = sm.add_constant(X)

    model = sm.OLS(tempValues, X).fit()

    return model.rsquared


def calc_multifactor(df_rets, factors):
    import statsmodels.api as sm
    factors = factors.loc[df_rets.index]
    factors = sm.add_constant(factors)
    factors = factors.dropna(axis=0)
    results = sm.OLS(df_rets[factors.index], factors).fit()

    return results.params


def rolling_multifactor_beta(ser, multi_factor_df, rolling_window=63):
    results = [calc_multifactor(ser[beg:end], multi_factor_df) for beg, end in zip(
        ser.index[0:-rolling_window], ser.index[rolling_window:])]

    return pd.DataFrame(index=ser.index[rolling_window:], data=results)


def multi_factor_alpha(
        factors_ts_list,
        single_ts,
        factor_names_list,
        input_is_returns=False,
        annualized=False,
        annualize_factor=252,
        show_output=False):

    factors_ts = [i.asfreq(freq='D', normalize=True) for i in factors_ts_list]
    dep_var = single_ts.asfreq(freq='D', normalize=True)

    if not input_is_returns:
        factors_ts = [i.pct_change().dropna() for i in factors_ts]
        dep_var = dep_var.pct_change().dropna()

    factors_align = pd.DataFrame(factors_ts).T.dropna()
    factors_align.columns = factor_names_list

    if show_output:
        print factors_align.head(5)
        print dep_var.head(5)

    if dep_var.shape[0] < 2:
        return np.nan
    if factors_align.shape[0] < 2:
        return np.nan

    factor_regress = pd.ols(y=dep_var, x=factors_align, intercept=True)

    factor_alpha = factor_regress.summary_as_matrix.intercept.beta

    if show_output:
        print factor_regress.resid
        print factor_regress.summary_as_matrix

    if annualized:
        return factor_alpha * annualize_factor
    else:
        return factor_alpha


def calc_alpha_beta(df_rets, benchmark_rets, startDate=None, endDate=None,
                    return_beta_only=False, inputs_are_returns=True,
                    normalize=False, remove_zeros=False):
    if not inputs_are_returns:
        df_rets = df_rets.pct_change().dropna()
        benchmark_rets = benchmark_rets.pct_change().dropna()

    if startDate is not None:
        df_rets = df_rets[startDate:]

    if endDate is not None:
        df_rets = df_rets[:endDate]

    if df_rets.ndim == 1:
        if remove_zeros:
            df_rets = df_rets[df_rets != 0]

        if normalize:
            ret_index = df_rets.index.normalize()
        else:
            ret_index = df_rets.index

        beta, alpha = sp.stats.linregress(benchmark_rets.loc[ret_index].values,
                                          df_rets.values)[:2]

    if df_rets.ndim == 2:
        beta = pd.Series(index=df_rets.columns)
        alpha = pd.Series(index=df_rets.columns)
        for algo_id in df_rets:
            df = df_rets[algo_id]
            if remove_zeros:
                df = df[df != 0]
            if normalize:
                ret_index = df.index.normalize()
            else:
                ret_index = df.index
            beta[algo_id], alpha[algo_id] = sp.stats.linregress(
                benchmark_rets.loc[ret_index].values, df.values)[
                :2]
        alpha.name = 'alpha'
        beta.name = 'beta'

    if return_beta_only:
        return beta
    else:
        return alpha * 252, beta


def rolling_beta(ser, benchmark_rets, rolling_window=63):
    results = [calc_alpha_beta(ser[beg:end],
                               benchmark_rets,
                               return_beta_only=True,
                               normalize=True) for beg,
               end in zip(ser.index[0:-rolling_window],
                          ser.index[rolling_window:])]

    return pd.Series(index=ser.index[rolling_window:], data=results)


def out_of_sample_vs_in_sample_returns_kde(
        bt_ts,
        oos_ts,
        transform_style='scale',
        return_zero_if_exception=True):

    bt_ts_pct = bt_ts.pct_change().dropna()
    oos_ts_pct = oos_ts.pct_change().dropna()

    bt_ts_r = bt_ts_pct.reshape(len(bt_ts_pct), 1)
    oos_ts_r = oos_ts_pct.reshape(len(oos_ts_pct), 1)

    if transform_style == 'raw':
        bt_scaled = bt_ts_r
        oos_scaled = oos_ts_r
    if transform_style == 'scale':
        bt_scaled = preprocessing.scale(bt_ts_r, axis=0)
        oos_scaled = preprocessing.scale(oos_ts_r, axis=0)
    if transform_style == 'normalize_L2':
        bt_scaled = preprocessing.normalize(bt_ts_r, axis=1)
        oos_scaled = preprocessing.normalize(oos_ts_r, axis=1)
    if transform_style == 'normalize_L1':
        bt_scaled = preprocessing.normalize(bt_ts_r, axis=1, norm='l1')
        oos_scaled = preprocessing.normalize(oos_ts_r, axis=1, norm='l1')

    X_train = bt_scaled
    X_test = oos_scaled

    X_train = X_train.reshape(len(X_train))
    X_test = X_test.reshape(len(X_test))

    x_axis_dim = np.linspace(-4, 4, 100)
    kernal_method = 'scott'

    try:
        scipy_kde_train = stats.gaussian_kde(
            X_train,
            bw_method=kernal_method)(x_axis_dim)
        scipy_kde_test = stats.gaussian_kde(
            X_test,
            bw_method=kernal_method)(x_axis_dim)
    except:
        if return_zero_if_exception:
            return 0.0
        else:
            return np.nan

    kde_diff = sum(abs(scipy_kde_test - scipy_kde_train)) / \
        (sum(scipy_kde_train) + sum(scipy_kde_test))

    return kde_diff


def perf_stats(
        ts,
        inputIsNAV=True,
        returns_style='compound',
        return_as_dict=False):
    all_stats = {}
    all_stats['annual_return'] = annual_return(
        ts,
        inputIsNAV=inputIsNAV,
        style=returns_style)
    all_stats['annual_volatility'] = annual_volatility(
        ts,
        inputIsNAV=inputIsNAV)
    all_stats['sharpe_ratio'] = sharpe_ratio(
        ts,
        inputIsNAV=inputIsNAV,
        returns_style=returns_style)
    all_stats['calmar_ratio'] = calmer_ratio(
        ts,
        inputIsNAV=inputIsNAV,
        returns_style=returns_style)
    all_stats['stability'] = stability_of_timeseries(ts, inputIsNAV=inputIsNAV)
    all_stats['max_drawdown'] = max_drawdown(ts, inputIsNAV=inputIsNAV)

    if return_as_dict:
        return all_stats
    else:
        all_stats_df = pd.DataFrame(
            index=all_stats.keys(),
            data=all_stats.values())
        all_stats_df.columns = ['perf_stats']
        return all_stats_df


def get_max_draw_down_underwater(underwater):
    valley = np.argmax(underwater)  # end of the period
    # Find first 0
    peak = underwater[:valley][underwater[:valley] == 0].index[-1]
    # Find last 0
    recovery = underwater[valley:][underwater[valley:] == 0].index[0]
    return peak, valley, recovery


def get_max_draw_down(df_rets):
    df_rets = df_rets.copy()
    df_cum = cum_returns(df_rets)
    running_max = np.maximum.accumulate(df_cum)
    underwater = running_max - df_cum
    return get_max_draw_down_underwater(underwater)


def get_top_draw_downs(df_rets, top=10):
    df_rets = df_rets.copy()
    df_cum = cum_returns(df_rets)
    running_max = np.maximum.accumulate(df_cum)
    underwater = running_max - df_cum

    drawdowns = []
    for t in range(top):
        peak, valley, recovery = get_max_draw_down_underwater(underwater)
        # Slice out draw-down period
        underwater = pd.concat(
            [underwater.loc[:peak].iloc[:-1], underwater.loc[recovery:].iloc[1:]])
        drawdowns.append((peak, valley, recovery))
        if len(df_rets) == 0:
            break
    return drawdowns


def gen_drawdown_table(df_rets, top=10):
    df_cum = cum_returns(df_rets, 1)
    drawdown_periods = get_top_draw_downs(df_rets, top=top)
    df_drawdowns = pd.DataFrame(index=range(top), columns=['net drawdown in %',
                                                           'peak date',
                                                           'valley date',
                                                           'recovery date',
                                                           'duration'])
    for i, (peak, valley, recovery) in enumerate(drawdown_periods):
        df_drawdowns.loc[
            i,
            'duration'] = len(
            pd.date_range(
                peak,
                recovery,
                freq='B'))
        df_drawdowns.loc[i, 'peak date'] = peak
        df_drawdowns.loc[i, 'valley date'] = valley
        df_drawdowns.loc[i, 'recovery date'] = recovery
        # df_drawdowns.loc[i, 'net drawdown in %'] = (df_cum.loc[peak] - df_cum.loc[valley]) * 100
        df_drawdowns.loc[
            i,
            'net drawdown in %'] = (
            (df_cum.loc[peak] - df_cum.loc[valley]) / df_cum.loc[peak]) * 100

    df_drawdowns['peak date'] = pd.to_datetime(
        df_drawdowns['peak date'],
        unit='D')
    df_drawdowns['valley date'] = pd.to_datetime(
        df_drawdowns['valley date'],
        unit='D')
    df_drawdowns['recovery date'] = pd.to_datetime(
        df_drawdowns['recovery date'],
        unit='D')

    return df_drawdowns


def rolling_sharpe(df_rets, rolling_sharpe_window):
    return pd.rolling_mean(df_rets,
                           rolling_sharpe_window) / pd.rolling_std(df_rets,
                                                                   rolling_sharpe_window) * np.sqrt(252)


def cone_rolling(
        input_rets,
        num_stdev=1.5,
        warm_up_days_pct=0.5,
        std_scale_factor=252,
        update_std_oos_rolling=False,
        cone_fit_end_date=None,
        extend_fit_trend=True,
        create_future_cone=True):

    # if specifying 'cone_fit_end_date' please use a pandas compatible format,
    # e.g. '2015-8-4', 'YYYY-MM-DD'

    warm_up_days = int(warm_up_days_pct * input_rets.size)

    # create initial linear fit from beginning of timeseries thru warm_up_days
    # or the specified 'cone_fit_end_date'
    if cone_fit_end_date is None:
        df_rets = input_rets[:warm_up_days]
    else:
        df_rets = input_rets[input_rets.index < cone_fit_end_date]

    perf_ts = cum_returns(df_rets, 1)

    X = range(0, perf_ts.size)
    X = sm.add_constant(X)
    sm.OLS(perf_ts, range(0, len(perf_ts)))
    line_ols = sm.OLS(perf_ts.values, X).fit()
    fit_line_ols_coef = line_ols.params[1]
    fit_line_ols_inter = line_ols.params[0]

    x_points = range(0, perf_ts.size)
    x_points = np.array(x_points) * fit_line_ols_coef + fit_line_ols_inter

    perf_ts_r = pd.DataFrame(perf_ts)
    perf_ts_r.columns = ['perf']

    warm_up_std_pct = np.std(perf_ts.pct_change().dropna())
    std_pct = warm_up_std_pct * np.sqrt(std_scale_factor)

    perf_ts_r['line'] = x_points
    perf_ts_r['sd_up'] = perf_ts_r['line'] * (1 + num_stdev * std_pct)
    perf_ts_r['sd_down'] = perf_ts_r['line'] * (1 - num_stdev * std_pct)

    std_pct = warm_up_std_pct * np.sqrt(std_scale_factor)

    last_backtest_day_index = df_rets.index[-1]
    cone_end_rets = input_rets[input_rets.index > last_backtest_day_index]
    new_cone_day_scale_factor = int(1)
    oos_intercept_shift = perf_ts_r.perf[-1] - perf_ts_r.line[-1]

    # make the cone for the out-of-sample/live papertrading period
    for i in cone_end_rets.index:
        df_rets = input_rets[:i]
        perf_ts = cum_returns(df_rets, 1)

        if extend_fit_trend:
            line_ols_coef = fit_line_ols_coef
            line_ols_inter = fit_line_ols_inter
        else:
            X = range(0, perf_ts.size)
            X = sm.add_constant(X)
            sm.OLS(perf_ts, range(0, len(perf_ts)))
            line_ols = sm.OLS(perf_ts.values, X).fit()
            line_ols_coef = line_ols.params[1]
            line_ols_inter = line_ols.params[0]

        x_points = range(0, perf_ts.size)
        x_points = np.array(x_points) * line_ols_coef + \
            line_ols_inter + oos_intercept_shift

        temp_line = x_points
        if update_std_oos_rolling:
            #std_pct = np.sqrt(std_scale_factor) * np.std(perf_ts.pct_change().dropna())
            std_pct = np.sqrt(new_cone_day_scale_factor) * \
                np.std(perf_ts.pct_change().dropna())
        else:
            std_pct = np.sqrt(new_cone_day_scale_factor) * warm_up_std_pct

        temp_sd_up = temp_line * (1 + num_stdev * std_pct)
        temp_sd_down = temp_line * (1 - num_stdev * std_pct)

        new_daily_cone = pd.DataFrame(index=[i],
                                      data={'perf': perf_ts[i],
                                            'line': temp_line[-1],
                                            'sd_up': temp_sd_up[-1],
                                            'sd_down': temp_sd_down[-1]})

        perf_ts_r = perf_ts_r.append(new_daily_cone)
        new_cone_day_scale_factor += 1

    if create_future_cone:
        extend_ahead_days = 252
        future_cone_dates = pd.date_range(
            cone_end_rets.index[-1], periods=extend_ahead_days, freq='B')

        future_cone_intercept_shift = perf_ts_r.perf[-1] - perf_ts_r.line[-1]

        future_days_scale_factor = np.linspace(
            1,
            extend_ahead_days,
            extend_ahead_days)
        std_pct = np.sqrt(future_days_scale_factor) * warm_up_std_pct

        x_points = range(perf_ts.size, perf_ts.size + extend_ahead_days)
        x_points = np.array(x_points) * line_ols_coef + line_ols_inter + \
            oos_intercept_shift + future_cone_intercept_shift
        temp_line = x_points
        temp_sd_up = temp_line * (1 + num_stdev * std_pct)
        temp_sd_down = temp_line * (1 - num_stdev * std_pct)

        future_cone = pd.DataFrame(
            index=map(
                np.datetime64,
                future_cone_dates),
            data={
                'perf': temp_line,
                'line': temp_line,
                'sd_up': temp_sd_up,
                'sd_down': temp_sd_down})

        perf_ts_r = perf_ts_r.append(future_cone)

    return perf_ts_r
