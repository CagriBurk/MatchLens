import pandas as pd
import sqlite3

conn = sqlite3.connect("database/matchlens.db")

matches_df=pd.read_sql_query("SELECT * FROM matches",conn)
team_mapping_df= pd.read_sql_query("SELECT * FROM team_mapping",conn)
tm_clubs = pd.read_sql_query("SELECT * FROM tm_clubs",conn)
tm_team_form = pd.read_sql_query("SELECT * FROM tm_team_form",conn)

matches_df['date'] = pd.to_datetime(matches_df['date'])
tm_team_form['date'] = pd.to_datetime(tm_team_form['date'])

matches_df['date'] = matches_df['date'].dt.tz_localize(None)
tm_team_form['date'] = tm_team_form['date'].dt.tz_localize(None)

matches_df = matches_df.sort_values('date')
tm_team_form = tm_team_form.sort_values('date')

matches_df = pd.merge(
    matches_df,
    team_mapping_df[['api_id', 'tm_id']], 
    left_on='home_team_id',     
    right_on='api_id',     
    how='left'                  
)
matches_df = matches_df.rename(columns={'tm_id': 'home_tm_id'})
matches_df = matches_df.drop(columns=['api_id'])

matches_df = pd.merge(
    matches_df,
    team_mapping_df[['api_id', 'tm_id']], 
    left_on='away_team_id',     
    right_on='api_id',     
    how='left'                  
)
matches_df = matches_df.rename(columns={'tm_id': 'away_tm_id'})
matches_df = matches_df.drop(columns=['api_id'])


conn.close()

matches_df = pd.merge_asof(
    left=matches_df,
    right=tm_team_form,
    left_on='date',              
    right_on='date',             
    left_by='home_tm_id',        
    right_by='team_id',         
    direction='backward',     
    suffixes=('', '_home')       
)


