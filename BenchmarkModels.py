#!/usr/bin/env python
# coding: utf-8

# # Benchmark model generation: A script with all the functions used in the Prediction Competition 2023

# Imports
## Basics
import random
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.cbook as cbook
import os
from functools import partial

## Views 3
import views_runs
from viewser.operations import fetch
from views_forecasts.extensions import *
from viewser import Queryset, Column


# Auxilliary functions

## Extract sc predictions for a given calendar year

def extract_sc_predictions(year,ss_predictions):
    ''' Extract sc predictions if necessary, split into calendar years '''
    first_month = (year - 1980)*12 + 1
    months=list(range(first_month,first_month+12))
    df = ss_predictions.loc[months].copy()
    if 'prediction' in ss_predictions:
        df = pd.DataFrame(df['prediction'])
    else:
        df['prediction'] = 0
        for month in range(1,12+1):
            this_month = first_month + month - 1
            df_temp = df.loc[this_month]
            this_col = 'step_pred_' + str(month+2)

            df_temp['prediction'] = np.expm1(df_temp[this_col].values) 
            df['prediction'].loc[this_month] = df_temp['prediction'].values
    #        print(month, this_col, this_month)
    #        print(df_temp[this_col].values)
    return pd.DataFrame(df['prediction'])


def extract_year(year, df):
    """
    Extract data from input dataframe in year-chunks
    """
    first_month = (year - 1980)*12 + 1
    last_month = first_month + 11
    return pd.DataFrame(df.loc[first_month:last_month])


def describe_expanded(df, df_expanded, month, country):
    # Verify that the distribution is right
    this_month = 457 # the month is not a variable
    this_country = 57 # the country is not a variable
    print("Mean and std of original predictions, all rows:")
    print(df.describe())
    print("Mean and std of expanded predictions, all rows:")
    print(df_expanded.describe())
    print("Mean and std of original predictions, one cm:")
    print(df.loc[this_month,this_country].describe())
    print("Mean and std of expanded predictions, one cm:")
    print(df_expanded.loc[this_month,this_country].describe())
    print("Variance:",df_expanded.loc[this_month,this_country].var())


def sample_poisson_row(row: pd.DataFrame, ndraws:int = 100) -> np.ndarray:
    """Given a dataframe row, produce ndraws poisson draws from the prediction column in the row.
    Attention, this is a row vectorized approach, should be used with apply.
    :return an np array. Should be exploded for long df.
    """
    row.prediction = 0 if row.prediction <= 0 else row.prediction
    return np.random.poisson(row.prediction, size=ndraws)


def sample_uniform_row(row: pd.DataFrame, ndraws:int = 100) -> np.ndarray:
    """Given a dataframe row, produce ndraws poisson draws from the prediction column in the row.
    Attention, this is a row vectorized approach, should be used with apply.
    :return an np array. Should be exploded for long df.
    """
    row.prediction = 0 if row.prediction <= 0 else row.prediction
    return np.random.uniform(low=row.prediction, high=row.prediction, size=ndraws)

def sample_bootstrap_row(row: pd.DataFrame, draw_from: np.array, ndraws: int = 100) -> np.ndarray:
    """Given a dataframe row, produce ndraws draws from the prediction column in the df.
    Attention, this is a row vectorized approach, should be used with apply.
    :return an np array. Should be exploded for long df.
    """
    return np.random.choice(draw_from, size=ndraws, replace=True)


def expanded_df_distribution(df, ndraws=1000, level='cm', distribution = 'poisson'):
    if distribution == 'poisson':
        function_with_draws = partial(sample_poisson_row, ndraws=ndraws)
    if distribution == 'uniform':
        function_with_draws = partial(sample_uniform_row, ndraws=ndraws)
    df['draws'] = df.apply(function_with_draws, axis=1)
    exploded_df = df.explode('draws').astype('int32')
    if level == 'cm':
        exploded_df['draw'] = exploded_df.groupby(['month_id', 'country_id']).cumcount()
    if level == 'pgm':
        exploded_df['draw'] = exploded_df.groupby(['month_id', 'priogrid_gid']).cumcount()
    exploded_df.drop(columns=['prediction'], inplace=True)
    exploded_df.rename(columns={'draws':'outcome'}, inplace=True)
    exploded_df.set_index('draw', append=True, inplace=True)
    return exploded_df


def expanded_df_bootstrap(df, ndraws=1000, draw_from=None, level='cm'):
    function_with_draws = partial(sample_bootstrap_row, draw_from=draw_from, ndraws=ndraws)
    df['draws'] = df.apply(function_with_draws, axis=1)
    exploded_df = df.explode('draws').astype('int32')
    if level == 'cm':
        exploded_df['draw'] = exploded_df.groupby(['month_id', 'country_id']).cumcount()
    if level == 'pgm':
        exploded_df['draw'] = exploded_df.groupby(['month_id', 'priogrid_gid']).cumcount()
    exploded_df.drop(columns=['ln_ged_sb_dep'], inplace=True)
    exploded_df.rename(columns={'draws':'outcome'}, inplace=True)
    exploded_df.set_index('draw', append=True, inplace=True)
    return exploded_df

def expanded_df_poisson(df, ndraws=1000,level='cm'):
    function_with_draws = partial(sample_poisson_row, ndraws=ndraws)
    df['draws'] = df.apply(function_with_draws, axis=1)
    exploded_df = df.explode('draws')
    if level=='cm':
        exploded_df['draw'] = exploded_df.groupby(['month_id','country_id']).cumcount()
    if level=='pgm':
        exploded_df['draw'] = exploded_df.groupby(['month_id','priogrid_gid']).cumcount()
    exploded_df.drop(columns=['prediction'],inplace=True)
    exploded_df.rename(columns={'draws':'outcome'},inplace=True)
    exploded_df.set_index('draw', append=True,inplace=True)
    return(exploded_df)

def expanded_df(df, function, ndraws=1000,level='cm'):
    function_with_draws = function(ndraws=ndraws)
    df['draws'] = df.apply(function_with_draws, axis=1)
    exploded_df = df.explode('draws')
    if level=='cm':
        exploded_df['draw'] = exploded_df.groupby(['month_id','country_id']).cumcount()
    if level=='pgm':
        exploded_df['draw'] = exploded_df.groupby(['month_id','priogrid_gid']).cumcount()
    try:
        exploded_df.drop(columns=['prediction'],inplace=True)
    except:
        pass
    try:
        exploded_df.drop(columns=['ln_ged_sb_dep'],inplace=True)
    except:
        pass
    exploded_df.rename(columns={'draws':'outcome'},inplace=True)
    exploded_df.set_index('draw', append=True,inplace=True)
    return exploded_df

# cm level
## Based on ensemble; expanded using a Poisson draw with mean=variance=\hat{y}_{it}


# Assembling benchmark based on VIEWS ensemble predictions

def distribution_expand_single_point_predictions(predictions_df,level,year_list,draws=1000,distribution='poisson'):
    ''' Expands an input prediction df with one prediction per unit to n draws from the point predictions 
    assuming a poisson distribution with mean and variance equal to the point prediction, and returns a list of 
    dictionaries with prediction and metadata for all years in year_list '''

    sc_predictions_ensemble = []
    
    for year in year_list:
        sc_dict = {
            'year': year,
            'prediction_df': extract_sc_predictions(year=year,ss_predictions=predictions_df)
        }
        sc_predictions_ensemble.append(sc_dict)

    # Expanding by drawing n draws from Poisson distribution   

    for year_record in sc_predictions_ensemble:
        print(year_record['year'])
        df = year_record.get('prediction_df')
        year_record['expanded_df'] = expanded_df_distribution(df,ndraws=draws,level=level,distribution=distribution)
    return sc_predictions_ensemble


def bootstrap_expand_single_point_predictions(ensemble_df, draw_from_column, level, year_list, draws=1000):
    """
    Expands an input prediction df with one prediction per unit to n draws from the 'draw_from' array,
    bootstrap-fashion, and returns a list of dictionaries with prediction and metadata for all years in year_list
    """

    actuals = np.expm1(ensemble_df[draw_from_column].fillna(0))
    actuals_by_year = []
    for year in year_list:
        actuals_dict = {
            'year': year,
            'actuals_df': extract_year(year=year, df=actuals)
        }
        actuals_by_year.append(actuals_dict)

    # Expanding by drawing n draws from specified draw_from array

    for year_record in actuals_by_year:
        print(year_record['year'])
        df = year_record.get('actuals_df')
        year_record['expanded_df'] = expanded_df_bootstrap(df, ndraws=draws, draw_from=df[draw_from_column],
                                                           level=level)
    return actuals_by_year

  
def distribution_expand_multiple_point_predictions(ModelList,level,year_list,draws=1000,distribution='poisson'):
    ''' Expands an input prediction df with multiple prediction per unit to n draws from the point predictions 
    assuming a poisson distribution with mean and variance equal to each point prediction. 
    The function then merges all these draws, and returns a list of 
    dictionaries with prediction and metadata for all years in year_list '''

    draws_per_model = np.floor_divide(draws,len(ModelList))
    
    # Drawing from the specified distribution for each of the models in model list
    for model in ModelList:
        print(model['modelname'])

        model['sc_predictions_constituent'] = []
        for year in year_list:
            sc_dict = {
                'year': year,
                'prediction_df': extract_sc_predictions(year=year,ss_predictions=model['predictions_test_df'])
            }
            model['sc_predictions_constituent'].append(sc_dict)

            
        # Expanding by drawing n draws from Poisson distribution   
        for year_record in model['sc_predictions_constituent']:
            print(year_record['year'])
            df = year_record.get('prediction_df')
            year_record['expanded_df'] = expanded_df_distribution(df,draws_per_model,level='cm',distribution=distribution)

    # Assembling benchmark based on the list of expanded model predictions

    sc_predictions_constituent = []

    for year in year_list:
        print(year)
        print(ModelList[0]['modelname'])
        merged_expanded_df = ModelList[0]['sc_predictions_constituent'][year-2018]['expanded_df']
    #    print(expanded_df.describe())
        i = 0
        for model in ModelList[1:]:
            print(model['modelname'])
            merged_expanded_df = pd.concat([merged_expanded_df,model['sc_predictions_constituent'][year-2018]['expanded_df']])
    #        print(expanded_df.describe())

        sc_dict = {
            'year': year,
            'expanded_df': merged_expanded_df
        }
        sc_predictions_constituent.append(sc_dict)
        i = i + 1

    return(sc_predictions_constituent)


def save_models(level,model_names,model_list, filepath):
    ''' Saves the models to dropbox '''
    
    i = 0
    for bm_model in model_list:
        for record in bm_model:
            year_record = record # First part of record list is list of yearly predictions, second is string name for benchmark model
            print(year_record['year'])
            filename = filepath + 'bm_' + level + '_' + model_names[i] + '_expanded_' + str(year_record['year']) + '.parquet'
            print(filename)
            year_record['expanded_df'].to_parquet(filename)
        i = i + 1

def save_actuals(level, df, filepath, year_list):
    ''' Saves the actuals from the given prediction file '''
    # Dataframe with actuals
    df_actuals = pd.DataFrame(df['ln_ged_sb_dep'])
    actuals = df_actuals
    actuals['outcome'] = np.expm1(actuals['ln_ged_sb_dep'])
    actuals.drop(columns=['ln_ged_sb_dep'], inplace=True)
    print(actuals.head())
    print(actuals.tail())
    print(actuals.describe())

    # Annual dataframes with actuals, saved to disk
    for year in year_list:
        first_month = (year - 1980)*12 + 1
        last_month = (year - 1980 + 1)*12
        df_annual = actuals.loc[first_month:last_month]
        filename = filepath + level + '_actuals_' + str(year) + '.parquet'
        print(year, first_month, last_month, filename)
        print(df_annual.head())
        df_annual.to_parquet(filename)
    # For all four years
    filename = filepath + level + '_actuals_allyears.parquet'
    actuals.to_parquet(filename)


def bootstrap_preddraws_inner(pred, resids, bins,bin_borders,n_bins,n_draws,lb = 0, ub = float('inf')):
    obs_bin = pd.cut([pred], bins = bin_borders, labels = range(1,n_bins+1))
    resids = np.array(resids)
    resids = resids[bins == obs_bin[0]]
    sampled_resids = random.choices(resids,k=n_draws)
    draws = pred + np.array(sampled_resids)
    draws[draws<lb] = lb
    draws[draws>ub] = ub
    out = pd.DataFrame({'draw_id': range(1,n_draws + 1),
                       'draw': draws})
    return(out)


# A function for bootstrapped binned draws taking a df with actuals-predictions , 
# an optional df with only predictions (if you want to use the actual-predictions from one set and make draws for another), 
# n_bins och n_draws. It  returns a df with index  month_id, country_id, and draw_id.

def boot_preddraws(actuals_pred, preds = None, n_bins = 5, n_draws = 1, lb = 0, ub = float('inf')):
    resids = actuals_pred.iloc[:,1] - actuals_pred.iloc[:,0]
    bins = pd.qcut(x=actuals_pred.iloc[:,1],q=n_bins,labels=range(1,n_bins+1),retbins=True)
    bin_borders = bins[1]
    bins = bins[0]
    bin_borders[0] = lb
    bin_borders[-1] = ub
    if preds is not None:
        preds = preds.reset_index()
        output = pd.DataFrame()
        for i in range(0,len(preds)):
            tmp = bootstrap_preddraws_inner(preds.iloc[i,2],resids,bins,bin_borders,n_bins,n_draws,lb,ub)
            tmp['month_id'] = np.repeat(preds.iloc[i,0],n_draws)
            tmp['country_id'] = np.repeat(preds.iloc[i,1],n_draws)
            output = pd.concat([output,tmp],axis = 0)
    else:
        actuals_pred = actuals_pred.reset_index()
        output = pd.DataFrame()
        for i in range(0,len(actuals_pred)):
            tmp = bootstrap_preddraws_inner(actuals_pred.iloc[i,3],resids,bins,bin_borders,n_bins,n_draws,lb,ub)
            tmp['month_id'] = np.repeat(actuals_pred.iloc[i,0],n_draws)
            tmp['country_id'] = np.repeat(actuals_pred.iloc[i,1],n_draws)
            output = pd.concat([output,tmp],axis = 0)
        
    output = output.set_index(['month_id','country_id','draw_id'])
    return(output)

# End of file
'''
# New functions from Benchmark_models

def reshape_df_cm(df, draw):
    #Drops steps we will not need in the benchmark model. 
    #Another round of drops are done below 
    steps_to_drop = ['ln_ged_sb_dep','step_pred_25','step_pred_26','step_pred_27','step_pred_28','step_pred_29','step_pred_30',
                     'step_pred_31','step_pred_32','step_pred_33','step_pred_34','step_pred_35','step_pred_36',]
    df = df.drop(steps_to_drop,axis=1)
    df.reset_index(inplace=True)
    df['draw'] = draw
    df_long = pd.wide_to_long(df, 'step_pred_', i = ['month_id', 'country_id'], j = 'step')
    df_long.reset_index(inplace=True)
    df_long.set_index(['month_id','country_id','step','draw'],inplace=True)
    return(df_long)

def make_dfcopy_cm(df_in, step, shifted_step, repetition):
    #Makes a 'copy' of the df with a shifted step 
#    print(step, shifted_step, repetition)
    df = pd.DataFrame(df_in[df_in.index.get_level_values('step').isin([shifted_step])]).copy()
    df.reset_index(inplace = True)
    df['step'].replace(shifted_step, step, inplace = True)
#    print(df.describe())
    df['draw'] = (df['draw'] + len(ModelList_cm) * repetition)
#    print(df.describe())
    df.set_index(['month_id', 'country_id', 'step', 'draw'], inplace=True)
    return(df)

def from_ss48_to_sc12(df, level,firstmonth,years):
    #Converts a dataframe in long format from one including all VIEWS ss predictions 
    #   into a set of dataframes containing only sc predictions for 12 months 
    df_list = []
    for year in range(1,years+1):
        this_firstmonth = firstmonth + (year-1)*12
        print(year, this_firstmonth)
#        this_df = df.query(f'month_id >= {this_firstmonth} and month_id <= {this_firstmonth+12-1}')
        month_df_list = []
        for step in range(3,14+1):
            select_month = this_firstmonth + step - 3
#            print('retaining month',select_month,'step',step)
            month_df = df.query(f'month_id == {select_month} and step == {step}')
            month_df_list.append(month_df)
        year_df = pd.concat(month_df_list)
        df_list.append(year_df)
    return(df_list)

def reshape_df_pgm(df, draw):
    #Drops steps we will not need in the benchmark model. 
    #nother round of drops are done below 
    steps_to_drop = ['ln_ged_sb_dep','step_pred_23','step_pred_24',
                     'step_pred_25','step_pred_26','step_pred_27','step_pred_28','step_pred_29','step_pred_30',
                     'step_pred_31','step_pred_32','step_pred_33','step_pred_34','step_pred_35','step_pred_36',]
    df = df.drop(steps_to_drop,axis=1)
    df.reset_index(inplace=True)
    df['draw'] = draw
    df_long = pd.wide_to_long(df, 'step_pred_', i = ['month_id', 'priogrid_gid', 'draw'], j = 'step')
    return(df_long)

def retrieve_qs(qs_to_retrieve=qs,rerun=True,filename=''):
    if rerun:
        df = qs_to_retrieve.publish().fetch().loc[445:492]    
        df.to_parquet(filename)
    else:
        df = pd.read_parquet(filename)
    return(df)

def aggregate_and_categorize(df, level):
    #This function aggregates the input df across all draws, and returns summary statistics for the prediction model 
    if level == 'cm':
        index = ['month_id','country_id']
    if level == 'pgm':
        index = ['month_id', 'priogrid_gid']
    if level == 'pgm2':
        index = ['month_id', 'priogrid_gid']
    df_to_aggregate = df.copy()
    df_to_aggregate['log_prediction'] = np.log1p(df_to_aggregate['prediction'] )

    # Proportion of draws in fatality categories
    #for cutoffs in [0,1,10,100,1000,10000]:
    bins = pd.IntervalIndex.from_tuples([(-1, 0), (1, 10), (11, 100), (101, 1000), (1001, 10000), (10001,100000000)])
    df_to_aggregate['categorical'] = pd.cut(df_to_aggregate['prediction'],bins)
    df_to_aggregate_dummies = pd.get_dummies(df_to_aggregate['categorical'],prefix='cat')
    df_to_aggregate = pd.concat([df_to_aggregate,df_to_aggregate_dummies],axis=1)

    # Mean and standard deviation of log predictions
    df_aggregated = pd.DataFrame(df_to_aggregate['log_prediction'].groupby(level=index).mean())
    df_aggregated.rename(columns={'log_prediction':'mean_log_prediction'},inplace=True)
    df_aggregated['std_log_prediction'] = df_to_aggregate['log_prediction'].groupby(level=index).std()
    for col in ('cat_(-1, 0]','cat_(1, 10]','cat_(11, 100]','cat_(101, 1000]','cat_(1001, 10000]','cat_(10001, 100000000]'):
        df_aggregated[col] = df_to_aggregate[col].groupby(level=index).mean()
    return(df_aggregated)

def make_dfcopy_pgm(df_in, step, shifted_step, repetition):
    #Makes a 'copy' of the df with a shifted step 
#    print(step, shifted_step, repetition)
    df = pd.DataFrame(df_in[df_in.index.get_level_values('step').isin([shifted_step])]).copy()
    df.reset_index(inplace = True)
    df['step'].replace(shifted_step, step, inplace = True)
#    print(df.describe())
    df['draw'] = (df['draw'] + len(ModelList_pgm) * repetition)
#    print(df.describe())
    df.set_index(['month_id', 'priogrid_gid', 'step', 'draw'], inplace=True)
    return(df)

'''