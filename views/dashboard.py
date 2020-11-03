import pickle
import copy
import pathlib
import urllib.request
import dash
import math
import datetime as dt
import pytz
from datetime import datetime, timedelta
import pandas as pd
from dash.dependencies import Input, Output, State, ClientsideFunction
import dash_core_components as dcc
import dash_html_components as html
import plotly.express as px
import dateparser
import ahocorasick
import warnings
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output

from server import app
from brain import load_labels, load_keywords, load_svc

localtz = pytz.timezone("America/New_York") # TODO

# Create controls
terms = [{"label": term, "value": term } for term in ["All"] + list(range(1,10))]
weeks = [{"label": week, "value": week } for week in ["All"] + list(range(1,26))]

# Create app layout
layout = html.Div(
    [
        dcc.Store(id="aggregate_data"),
        dcc.Store(id="data_source_loaded"),
        # empty Div to trigger javascript file for graph resizing
        html.Div(id="output-clientside"),
        html.Div(
            [
                html.Div(
                    [
                        html.P("Data source:", className="control_label"),
                        dcc.Dropdown(
                            id="data_source",
                            options=[
                                { "label": "Labeled Sessions", "value": "labels" },
                                { "label": "Keyword Matching", "value": "keywords" },
                                { "label": "Support Vector Classifier", "value": "svc" },
                            ],
                            value="labels",
                            className="dcc_control",
                        ),
                        html.P("College:", className="control_label"),
                        dcc.Dropdown(
                            id="college",
                            options=[
                                { "label": "College of I.T.", "value": "it" },
                            ],
                            disabled=True,
                            value="it",
                            className="dcc_control",
                        ),
                        html.P("Program:", className="control_label"),
                        dcc.Dropdown(
                            id="program",
                            options=[
                                { "label": "Computer Science – B.S.", "value": "cs" }
                            ],
                            disabled=True,
                            value="cs",                            
                            className="dcc_control",
                        ),
                        html.P("Enrollment date:", className="control_label"),
                        dcc.DatePickerSingle(
                            id='enrollment_date',                                           
                            className="dcc_control",
                            date=datetime(2020, 6, 1)
                        ),
                        html.P("Term:", className="control_label"),
                        dcc.Dropdown(
                            id="term",
                            options=terms,
                            value="1",                         
                            className="dcc_control",
                        ),
                        html.P("Week:", className="control_label"),
                        dcc.Dropdown(
                            id="week",
                            options=weeks,
                            value="All",                        
                            className="dcc_control",
                        ),
                    ],
                    className="pretty_container four columns",
                    id="cross-filter-options",
                ),
                html.Div(
                    [
                        html.Div(
                            [
                                html.Div(
                                    [html.H6(id="no_days_text"), html.P("No. of days")],
                                    className="mini_container",
                                ),
                                html.Div(
                                    [html.H6(id="no_sessions_text"), html.P("No. of sessions")],
                                    className="mini_container",
                                ),
                                html.Div(
                                    [html.H6(id="total_time_text"), html.P("Total time")],
                                    className="mini_container",
                                ),
                                html.Div(
                                    [html.H6(id="weekly_time_text"), html.P("Weekly average")],
                                    className="mini_container",
                                ),
                            ],
                            id="info-container",
                            className="row container-display",
                        ),
                        
                        html.Div(
                            [dcc.Graph(id="bar_figure")],
                            id="countGraphContainer",
                            className="pretty_container",
                        ),
                    ],
                    id="right-column",
                    className="eight columns",
                ),
            ],
            className="row flex-display",
        ),
        html.Div(
            [
                html.Div(
                    [dcc.Graph(id="gantt_figure")],
                    className="pretty_container eight columns",
                ),
                html.Div(
                    [dcc.Graph(id="sunburst_figure")],
                    className="pretty_container four columns",
                ),
            ],
            className="row flex-display",
        ),
    ],
    id="mainContainer",
    style={"display": "flex", "flex-direction": "column"},
)

app.clientside_callback(
    ClientsideFunction(namespace="clientside", function_name="resize"),
    Output("output-clientside", "children"),
    [Input("bar_figure", "figure")],
)

@app.callback(
    [
        Output("data_source_loaded", "data"),
    ],
    [
        Input("data_source", "value"),
    ]
)
def update_data_source(data_source):
    print("UPDATE DATA SOURCE")

    if data_source not in data_sources:
        if data_source == "labels":
            data_sources[data_source] = load_labels()
        elif data_source == "keywords":
            data_sources[data_source] = load_keywords()
        elif data_source == "svc":
            data_sources[data_source] = load_svc()
        else:
            return None # TODO

    print("LOADED DATA SOURCE")
    return [data_source]


@app.callback(
    [
        Output("week", "value"),
        Output("week", "disabled"),
    ],
    [
        Input("term", "value"),
    ],
    [State("week", "value")]
)
def update_week_dropdown(term, week):
    week = "All" if term == "All" else week
    isweekdisabled = term == "All"
    return [week, isweekdisabled]

@app.callback(
    [
        Output("aggregate_data", "data"),
    ],
    [
        Input("data_source", "value"),
        Input("enrollment_date", "date"),
        Input("term", "value"),
        Input("week", "value"),
        Input("data_source_loaded", "data")
    ],
)
def update_aggregate_data(data_source, enrollment_date, term, week, test):
    enrollment_date = dateparser.parse(enrollment_date)
    start = enrollment_date.replace(tzinfo=localtz) # TODO
    if term == "All":
        end = datetime.now().replace(tzinfo=localtz)
    else:
        start = start + timedelta(weeks=26*(int(term)-1))
        end = start + timedelta(weeks=26)
    
        if week == "All":
            pass
        else:
            start = start + timedelta(weeks=week-1)
            end = start + timedelta(weeks=1)

    return [{"start": start, "end": end, "data_source": data_source}]

data_sources = {}

def filter_df(data):
    data_source = data["data_source"]
    start = data["start"]
    end = data["end"]

    df = data_sources[data_source] if data_source in data_sources else None
    if df is None:
        return None

    df["start"] = df["start"].dt.tz_convert(localtz)
    df["end"] = df["end"].dt.tz_convert(localtz)
    
    df = df[(df.start >= start) & (df.end <= end)] # TODO: global_df?
    
    return df

@app.callback(
    [
        Output("no_days_text", "children"),
        Output("no_sessions_text", "children"),
        Output("total_time_text", "children"),
        Output("weekly_time_text", "children"),
    ],
    [Input("aggregate_data", "data")],
)
def update_text(data):
    try:
        df = filter_df(data)
        
        days = math.ceil((df["end"].max() - df["start"].min()).total_seconds() / 60 / 60 / 24)
        sessions = len(df)
        total = math.ceil((df["end"] - df["start"]).sum().total_seconds() / 60 / 60)
        weekly = math.ceil(total / days * 7) if days >= 7 else total

        return [
            str(days),
            str(sessions), 
            str(total) + " hours",
            str(weekly) + " hours"
        ]
    except:
        return "-", "-", "-", "-"
        
def make_placeholder():
    return {
        "layout": {
            "xaxis": {
                "visible": False
            },
            "yaxis": {
                "visible": False
            },
            "annotations": [
                {
                    "text": "No matching data found",
                    "xref": "paper",
                    "yref": "paper",
                    "showarrow": False,
                    "font": {
                        "size": 28
                    }
                }
            ]
        }
    }

@app.callback(
    Output("bar_figure", "figure"),
    [Input("aggregate_data", "data")],
)
def make_bar_figure(data):
    try:
        df = filter_df(data)
        df["duration"] = df["end"] - df["start"]
        df["Study time"] = df["duration"].apply(lambda duration: duration.total_seconds() / 60 / 60)
        df["Day"] = (df["start"] - timedelta(hours=4)).dt.date
        df = df.groupby("Day").sum().reset_index()
        fig = px.bar(df, x="Day", y="Study time", title='Study time per day')
        fig.update_layout(title_x=0.5)
        fig.update_layout(xaxis_title="", yaxis_title="Hours")
        return fig
    except:
        return make_placeholder()

@app.callback(
    Output("gantt_figure", "figure"), 
    [Input("aggregate_data", "data")]
)
def make_gantt_figure(data):
    try:
        df = filter_df(data)
        df["Course"] = df["main_topic_long"]
        fig = px.timeline(df, x_start="start", x_end="end", y="Course", color="Course", title="Activities")
        fig.update_yaxes(autorange="reversed")
        fig.update_layout(title_x=0.5, showlegend=False)
        fig.update_layout(xaxis_title="", yaxis_title="")
        return fig
    except:
        return make_placeholder()

@app.callback(
    Output("sunburst_figure", "figure"),
    [Input("aggregate_data", "data")],
)
def make_sunburst_figure(data):
    try:
        df = filter_df(data)

        df["duration_hours"] = (df["end"] - df["start"]).apply(lambda duration: duration.total_seconds() / 60 / 60)

        df = df.groupby("main_topic").agg({
            "parent": "first",
            "main_topic_long": "first",
            "main_topic_short": "first",
            "duration_hours": "sum",
        }).reset_index()

        if df.empty:
            raise Exception()

        fig = px.sunburst(
            df,
            names='main_topic_short',
            parents="parent",
            values='duration_hours',
            hover_name="main_topic_long",
            title="Courses"
        )
        fig.update_layout(title_x=0.5)
        return fig
    except:
        return make_placeholder()