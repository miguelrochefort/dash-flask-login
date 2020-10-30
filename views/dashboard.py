# Import required libraries
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

import warnings
# Dash configuration
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output

from server import app

localtz = pytz.timezone("America/New_York") # TODO

# Multi-dropdown options
# from controls import COUNTIES, WELL_STATUSES, WELL_TYPES, WELL_COLORS

# get relative data folder
PATH = pathlib.Path(__file__).parent
DATA_PATH = PATH.joinpath("data").resolve() # TODO: Move out of Views

# app = dash.Dash(
#     __name__, meta_tags=[{"name": "viewport", "content": "width=device-width"}]
# )
# server = app.server












































df_inputs = pd.read_csv(DATA_PATH.joinpath("all.csv"), parse_dates=["start", "end"])#, converters={'topics': clean})
# df_inputs = pd.read_csv("/content/drive/My Drive/C964/all.csv", parse_dates=parse_dates)

# TODO: Remove long items probabyl daded by accident due to bug with AFK when screen turned off with AW
df_inputs = df_inputs[df_inputs.end - df_inputs.start < timedelta(hours=3)]

# TODO: Remove duplicate web browser events (Chrome)
df_inputs = df_inputs[~(df_inputs.title.astype(str).str.endswith("- Google Chrome"))]

df_inputs






def parse_topics():
  file = open(DATA_PATH.joinpath("activitywatch_wgu.txt"))

  indent = 0
  tree = (None, [])
  parents = [] # [None] * 4 * 10 # 10 level maximum
  for line in file.readlines():
    line = line.split("#")[0].rstrip() # Remove comments and right-side whitespace
    new_indent = len(line)-len(line.lstrip())
    line = line.strip()
    if line.isspace() or line == ' ' or line == '':
      continue
    
    node = (line.lower(), []) #{ "name": line, "children": [] } # TODO: Not lowercase

    parents = parents[0:new_indent]
    parent = [parent for parent in parents if parent is not None][-1] if parents else tree
    
    parent[1].append(node)

    parents = parents + [None] * (1 + new_indent - len(parents))
    parents[new_indent] = node

  return tree


topics = parse_topics()





import ahocorasick

def list_topics(topics, parent=None):
  result = []
  key = str(topics[0])
  value = key if topics[1] else parent
  result.append((key, value))
  for topic in topics[1]:
    result.extend(list_topics(topic, key))
  
  return result

topics = parse_topics()
names = dict(list(set(list_topics(topics))))

automaton = ahocorasick.Automaton()

for name in names:
    automaton.add_word(name, name)

automaton.make_automaton()

def findit_with_ahocorasick(element):
    try:
        return list(set([names[key[1]] for key in automaton.iter(element)]))
    except StopIteration:
        return []








# %%timeit
def collapse(df, gap, threshold, equality, gate=False): # TODO: Sessionize?
  # TODO: Assume, or check: start, end as datetime
  # TODO: Sort chronologically, ascending or descending, because inputs they don't all follow the same order

  if df is None or df.empty:
    return pd.DataFrame()

  df = df.sort_values("start")

  sessions = []

  if gate:
    for x in df.itertuples():
      start = x[1]
      end = x[2]

      if sessions:
        session = sessions[-1]
        delta = start - session["end"]
        # print(delta)
        if delta <= gap: #and (not equality or equality(session["children"][0], row)):
          # print("SUCCESS!!!!! MERGE")
          session["start"] = min(session["start"], start)
          session["end"] = max(session["end"], end)
          #session["children"].append(row)
          continue

      sessions.append({
        "start": start,
        "end": end,
        #"children": [row]
      })
  else:
    for idx, row in df.iterrows():
      start = row["start"]
      end = row["end"]
      if sessions:
        session = sessions[-1]
        delta = start - session["end"]
        if delta <= gap and (not equality or equality(session["children"][0], row)):
          #print("SUCCESS!!!!! MERGE")
          session["start"] = min(session["start"], start)
          session["end"] = max(session["end"], end)
          session["children"].append(row)
          continue

      sessions.append({
        "start": start,
        "end": end,
        "children": [row]
      })

  df = pd.DataFrame(sessions)
  
  if df.empty:
    return df
  
  df["duration"] = df["end"] - df["start"]

  if threshold:
    df = df[df["duration"] >= threshold]

  return df

# df1 = collapse(df, timedelta(minutes=5), timedelta(minutes=5), None, True)
# df2 = collapse(df, timedelta(minutes=5), timedelta(minutes=5), None, False)

# df2


#%%
def describe_tags(x):
    total = 0
  #try:
    tf = {}
    # tf2 = {}
    for child in x.children:
      tags = child["topics"]
    
      for tag in tags:
        if tag not in tf:
          tf[tag] = 0
        duration_seconds = (child.end - child.start).total_seconds()
        tf[tag] = tf[tag] + duration_seconds
        total = total + duration_seconds

        # print(child.duration.total_seconds())

      # title = str(child["title"])
      # title = title.replace("- Google Chrome", "")
      # title = title.lower()
      # title = title.replace("-", " ")
      # title = title.replace(",", " ")
      # title = title.replace("'", " ")
      # title = title.replace("\"", " ")
      # title = title.replace("_", " ")
      # title = title.replace(":", " ")
      # title = title.replace(".", " ")
      # title = title.replace("?", " ")
      # title = title.replace("(", " ")
      # title = title.replace(")", " ")
      # title = title.replace("[", " ")
      # title = title.replace("]", " ")
      # title = title.replace("|", " ")
      # for word in title.split(" "):
      #   if word not in tf2:
      #     tf2[word] = 0
      #   tf2[word] = tf2[word] + (child.end - child.start).total_seconds()


    # total = (x.end - x.start).total_seconds()
    # total = sum([child.duration.total_seconds() for child in x.children]) # Relative duration
    # print(sum([child.duration.total_seconds() for child in x.children]))
    if total == 0:
      return "ERROR!"
    #print(total)
    tf = [(tag, tf[tag] / total) for tag in tf]
    tf = list(sorted(tf, key=lambda t: t[1], reverse=True))

    #tf2 = [(tag, tf2[tag] / total) for tag in tf2]
    #tf2 = sorted(tf2, key=lambda t: t[1], reverse=True)
    
    #print(tf)
    #tf # ", ".join([t[0] + " (" + str(int(t[1] * 100)) + "%)" for t in tf])
    
    #print(tf)
    # print(tf2)
    #print()

    # TODO:

    # return [(topic, )]
    # return list(set([x[0] for x in tf]))

    return tf

  #except:
    print("ERROR")
    return []

def predict(df):
    print("PREDICTING A")
    print(len(df_inputs))
    df["topics"] = (df["app"].astype(str) + " " + df["title"].astype(str) + " " + df["url"].astype(str)).str.lower().apply(findit_with_ahocorasick)
    print("PREDICTING B")
    df = df[df["topics"].str.len() > 0]
    print(len(df))
    df = collapse(df, timedelta(minutes=5), timedelta(minutes=5), None)
    print(len(df))
    print("PREDICTING C")
    df["topics"] = df.apply(describe_tags, axis=1)
    df = df[["start", "end", "topics"]]
    print("PREDICTING D")
    return df

print("PREDICTING")







df_predictions = predict(df_inputs)
df_predictions

df = df_predictions




# # TODO: Remove this part
# def clean(x):
#   return [topic.replace("'", "").strip() for topic in x[1:-1].split(",")]

# def get_topic_ratio(topics):
#   num_topics = len(topics)
#   return [(topic, 1/num_topics) for topic in topics]

# df = pd.read_csv(DATA_PATH.joinpath("labels.csv"), parse_dates=["start", "end"], converters={'topics': clean})
# df["topics"] = df["topics"].apply(get_topic_ratio)
























topic_names = {
    "BSCS": "Bachelor of Computer Science ",
    "TOEFL": "English proficiency",
    "Study.com": "Study.com",
    "Sophia.org": "Sophia.org",
    "WGU": "Western Governors University",
    "ORA1": "Orientation",
    "C482": "Software I",
    "C683": "Natural Science Lab",
    "C950": "Data Structures and Algorithms II",
    "C867": "Scripting and Programming - Applications",
    "C195": "Software II - Advanced Java Concepts",
    "C455": "English Composition I",
    "C188": "Software Engineering",
    "C173": "Scripting and Programming - Foundations",
    "C955": "Applied Probability and Statistics",
    "C175": "Data Management - Foundations",
    "C993": "Structured Query Language",
    "C170": "Data Management - Applications",
    "C949": "Data Structures and Algorithms I",
    "C846": "Business of IT - Applications",
    "C779": "Web Development Foundations",
    "C165": "Integrated Physical Sciences",
    "C172": "Network and Security - Foundations",
    "C963": "American Politics and the US Constitution",
    "C958": "Calculus I",
    "C176": "Business of IT - Project Management",
    "C191": "Operating Systems for Programmers",
    "C952": "Computer Architecture",
    "C836": "Fundamentals of Information Security",
    "C959": "Discrete Mathematics I",
    "C960": "Discrete Mathematics II",
    "C182": "Introduction to IT",
    "C961": "Ethics in Technology",
    "C464": "Introduction to Communication",
    "C100": "Introduction to Humanities",
    "C255": "Introduction to Geography",
    "C857": "Software Quality Assurance",
    "C951": "Introduction to Artificial Intelligence",
    "C768": "Technical Communication",
    "C964": "Computer Science Capstone",
}
long_topic_names = dict(map(lambda x: (x.lower(), topic_names[x]), topic_names))
short_topic_names = dict(map(lambda x: (x.lower(), x), topic_names))

def beautify_topic_short(topic):
  try:
    return short_topic_names[topic]
  except:
    return topic

def beautify_topic_long(topic):
  try:
    return long_topic_names[topic]
  except:
    return topic

beautify_topic_long("wgu")

























wgu_courses = [
      "C455",
      "C952",
      "C195",
      "C960",
      "C191",
      "C867",
      "C683",
      "C950",
      "C482",
      "C959",
      "C949",
      "C172",
      "C961",
      "C779",
      "C836",
      "C173",
      "C182",
      "C857",
      "C464",
      "C100",
      "C255",
      "C188",
      "C846",
      "C951",
      "C768",
      "C964",
      "ORA1",
  ]

sophia_courses = [
               "C955",
               "C176",
               "C165",   
] 

study_courses = [
         "C958",
         "C963",
         "C993",
         "C175",
         "C170",   
]

schools = [
         "WGU",
         "Study.com",
         "Sophia.org",  
         "TOEFL",
]


def get_parent(tag):
  if tag in [x.lower() for x in wgu_courses]:
    return "wgu"
  if tag in [x.lower() for x in sophia_courses]:
    return "sophia.org"
  if tag in [x.lower() for x in study_courses]:
    return "study.com"
    
  if tag in [x.lower() for x in schools]:
    return "bscs"
  if tag == "wgu":
    return "bscs"
  return ""

# def get_parent(tag):
#   if tag in [x.lower() for x in wgu_courses]:
#     return "wgu"
#   if tag in [x.lower() for x in sophia_courses]:
#     return "wgu" #"sophia.org"
#   if tag in [x.lower() for x in study_courses]:
#     return "wgu" #"study.com"
#   if tag != "wgu":
#     return "wgu"
#   return ""


def topic_alias(topic):
  if topic in ["wgu", "sophia.org", "study.com", "bscs", "toefl"]:
    return "unknown"
  return topic




































































































terms = [{"label": term, "value": term } for term in ["All"] + list(range(1,10))]
weeks = [{"label": week, "value": week } for week in ["All"] + list(range(1,26))]

# # Create controls
# county_options = [
#     {"label": str(COUNTIES[county]), "value": str(county)} for county in COUNTIES
# ]

# well_status_options = [
#     {"label": str(WELL_STATUSES[well_status]), "value": str(well_status)}
#     for well_status in WELL_STATUSES
# ]

# well_type_options = [
#     {"label": str(WELL_TYPES[well_type]), "value": str(well_type)}
#     for well_type in WELL_TYPES
# ]




# # Load data
# df = pd.read_csv(
#     "https://github.com/plotly/datasets/raw/master/dash-sample-apps/dash-oil-and-gas/data/wellspublic.csv",
#     low_memory=False,
# )
# df["Date_Well_Completed"] = pd.to_datetime(df["Date_Well_Completed"])
# df = df[df["Date_Well_Completed"] > dt.datetime(1960, 1, 1)]

# trim = df[["API_WellNo", "Well_Type", "Well_Name"]]
# trim.index = trim["API_WellNo"]
# dataset = trim.to_dict(orient="index")


# Create global chart template
mapbox_access_token = "pk.eyJ1IjoicGxvdGx5bWFwYm94IiwiYSI6ImNrOWJqb2F4djBnMjEzbG50amg0dnJieG4ifQ.Zme1-Uzoi75IaFbieBDl3A"

# layout = dict(
#     autosize=True,
#     automargin=True,
#     margin=dict(l=30, r=30, b=20, t=40),
#     hovermode="closest",
#     plot_bgcolor="#F9F9F9",
#     paper_bgcolor="#F9F9F9",
#     legend=dict(font=dict(size=10), orientation="h"),
#     title="Satellite Overview",
#     mapbox=dict(
#         accesstoken=mapbox_access_token,
#         style="light",
#         center=dict(lon=-78.05, lat=42.54),
#         zoom=7,
#     ),
# )

# Create app layout
layout = html.Div(
    [
        dcc.Store(id="aggregate_data"),
        # empty Div to trigger javascript file for graph resizing
        html.Div(id="output-clientside"),
        # html.Div(
        #     [
        #         html.Div(
        #             [
        #                 # html.Img(
        #                 #     src=app.get_asset_url("dash-logo.png"),
        #                 #     id="plotly-image",
        #                 #     style={
        #                 #         "height": "60px",
        #                 #         "width": "auto",
        #                 #         "margin-bottom": "25px",
        #                 #     },
        #                 # )
        #             ],
        #             className="one-third column",
        #         ),
        #         html.Div(
        #             [
        #                 html.Div(
        #                     [
        #                         html.H3(
        #                             "WGU Time Tracker",
        #                             style={"margin-bottom": "0px"},
        #                         ),
        #                         html.H5(
        #                             "Powered by ActivityWatch", style={"margin-top": "0px"}
        #                         ),
        #                     ]
        #                 )
        #             ],
        #             className="one-third column",
        #             id="title",
        #         ),
        #         html.Div(
        #             [
        #                 # html.A(
        #                 #     html.Button("Learn More", id="learn-more-button"),
        #                 #     href="https://plot.ly/dash/pricing/",
        #                 # )
        #             ],
        #             className="one-third column",
        #             id="button",
        #         ),
        #     ],
        #     id="header",
        #     className="row flex-display",
        #     style={"margin-bottom": "25px"},
        # ),
        html.Div(
            [
                html.Div(
                    [
                        html.P("College:", className="control_label"),
                        dcc.Dropdown(
                            id="college",
                            options=[
                                { "label": "College of I.T.", "value": "it" },
                            ],
                            # disabled=True,
                            value="it",
                            className="dcc_control",
                        ),
                        html.P("Program:", className="control_label"),
                        dcc.Dropdown(
                            id="program",
                            options=[
                                { "label": "Computer Science – B.S.", "value": "cs" }
                            ],
                            # disabled=True,
                            value="cs",                            
                            className="dcc_control",
                        ),                        
                        # html.P("Time period type:", className="control_label"),
                        # dcc.RadioItems(
                        #     id="time",
                        #     options=[
                        #         { "label": "Standard", "value": "standard" },
                        #         { "label": "Custom", "value": "custom" },
                        #     ],
                        #     value="custom",                            
                        #     labelStyle={"display": "inline-block"},
                        #     className="dcc_control",
                        # ),
                        html.P("Enrollment date:", className="control_label"),
                        dcc.DatePickerSingle(
                            id='enrollment_date',                                           
                            className="dcc_control",
                            #min_date_allowed=date(1995, 8, 5),
                            #max_date_allowed=date(2017, 9, 19),
                            #initial_visible_month=date(2017, 8, 5),
                            date=datetime(2020, 9, 1)
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
                        # html.P("Time period:", className="control_label"),
                        # dcc.DatePickerRange(
                        #     id='my-date-picker-range',
                        #     #min_date_allowed=date(1995, 8, 5),
                        #     #max_date_allowed=date(2017, 9, 19),
                        #     #initial_visible_month=date(2017, 8, 5),
                        #     #date=date(2017, 8, 25)
                        # ),
                        # html.P("Week:", className="control_label"),
                        # dcc.RangeSlider(
                        #     id="year_slider",
                        #     min=1,
                        #     max=26,
                        #     value=[1, 26],
                        #     step=1,
                        #     className="dcc_control",
                        #     marks= dict([(x, str(x)) for x in range(1,26)]),
                        # ),







                        # html.P("Duration:", className="control_label"),
                        # dcc.DatePickerRange(
                        #     #min_date_allowed=date(1995, 8, 5),
                        #     #max_date_allowed=date(2017, 9, 19),
                        #     #initial_visible_month=date(2017, 8, 5),
                        #     #date=date(2017, 8, 25)
                        # ),
                        #                         html.P("Duration:", className="control_label"),
                        # dcc.DatePickerRange(
                        #     #min_date_allowed=date(1995, 8, 5),
                        #     #max_date_allowed=date(2017, 9, 19),
                        #     #initial_visible_month=date(2017, 8, 5),
                        #     #date=date(2017, 8, 25)
                        # ),

              


                        # html.P(
                        #     "Filter by construction date (or select range in histogram):",
                        #     className="control_label",
                        # ),
                        # dcc.RangeSlider(
                        #     id="year_slider",
                        #     min=1960,
                        #     max=2017,
                        #     value=[1990, 2010],
                        #     className="dcc_control",
                        # ),
                        # html.P("Filter by well status:", className="control_label"),
                        # dcc.RadioItems(
                        #     id="well_status_selector",
                        #     options=[
                        #         {"label": "All ", "value": "all"},
                        #         {"label": "Active only ", "value": "active"},
                        #         {"label": "Customize ", "value": "custom"},
                        #     ],
                        #     value="active",
                        #     labelStyle={"display": "inline-block"},
                        #     className="dcc_control",
                        # ),
                        # dcc.Dropdown(
                        #     id="well_statuses",
                        #     options=well_status_options,
                        #     multi=True,
                        #     value=list(WELL_STATUSES.keys()),
                        #     className="dcc_control",
                        # ),
                        # dcc.Checklist(
                        #     id="lock_selector",
                        #     options=[{"label": "Lock camera", "value": "locked"}],
                        #     className="dcc_control",
                        #     value=[],
                        # ),
                        # html.P("Filter by well type:", className="control_label"),
                        # dcc.RadioItems(
                        #     id="well_type_selector",
                        #     options=[
                        #         {"label": "All ", "value": "all"},
                        #         {"label": "Productive only ", "value": "productive"},
                        #         {"label": "Customize ", "value": "custom"},
                        #     ],
                        #     value="productive",
                        #     labelStyle={"display": "inline-block"},
                        #     className="dcc_control",
                        # ),
                        # dcc.Dropdown(
                        #     id="well_types",
                        #     options=well_type_options,
                        #     multi=True,
                        #     value=list(WELL_TYPES.keys()),
                        #     className="dcc_control",
                        # ),
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
                                # html.Div(
                                #     [html.H6(id="no_events_text"), html.P("No. of events")],
                                #     className="mini_container",
                                # ),
                                html.Div(
                                    [html.H6(id="no_sessions_text"), html.P("No. of sessions")],
                                    className="mini_container",
                                ),
                                html.Div(
                                    [html.H6(id="total_time_text"), html.P("Total time")],
                                    className="mini_container",
                                ),
                                # html.Div(
                                #     [html.H6(id="no_courses_text"), html.P("No. of courses")],
                                #     className="mini_container",
                                # ),
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

# Create callbacks
app.clientside_callback(
    ClientsideFunction(namespace="clientside", function_name="resize"),
    Output("output-clientside", "children"),
    [Input("bar_figure", "figure")],
)

import dateparser



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
        Input("enrollment_date", "date"),
        Input("term", "value"),
        Input("week", "value"),
    ],
)
def update_aggregate_data(enrollment_date, term, week):
    #df = df_labels
    #print(enrollment_date, type(enrollment_date))
    enrollment_date = dateparser.parse(enrollment_date)
    # enrollment_date = datetime.combine(enrollment_date.today(), datetime.min.time())
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

    return [{"start": start, "end": end}]
    #return [df[(df.start >= start) & (df.end <= end)]]

def filter_df(data):
    start = data["start"]
    end = data["end"]
    return df[(df.start >= start) & (df.end <= end)] # TODO: global_df?

    # Convert to local timezone
    # TODO: Do this somewhere else?
    df["start"] = df["start"].dt.tz_convert(localtz)
    df["end"] = df["end"].dt.tz_convert(localtz)

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

# Selectors -> count graph
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
        fig.update_layout(xaxis_title="", yaxis_title="Hours") # hide all the xticks
        return fig
    except:
        return make_placeholder()
# Main graph -> individual graph
@app.callback(
    Output("gantt_figure", "figure"), 
    [Input("aggregate_data", "data")]
)
def make_gantt_figure(data):
    try:
        df = filter_df(data)

        # week = 1
        # start_of_term = datetime(2020,9,1, tzinfo=pytz.utc)
        # start = start_of_term + timedelta(days=7*(week-1))
        # end = start + timedelta(days=7)
        # df = df[(df.start > start) & (df.end < end)]

        df["Course"] = df["topics"].apply(lambda x: x[0][0]).apply(beautify_topic_long) # TODO: Don't just take first, especially if WGU for most predictions

        fig2 = px.timeline(df, x_start="start", x_end="end", y="Course", color="Course", title="Activities")
        fig2.update_yaxes(autorange="reversed") # otherwise tasks are listed from the bottom up
        fig2.update_layout(title_x=0.5, showlegend=False)
        fig2.update_layout(xaxis_title="", yaxis_title="") # hide all the xticks
        return fig2
    except:
        return make_placeholder()

# Selectors -> main graph
@app.callback(
    Output("sunburst_figure", "figure"),
    [Input("aggregate_data", "data")],
)
def make_sunburst_figure(data):
    try:
        df = filter_df(data)

        df["duration_hours"] = (df["end"] - df["start"]).apply(lambda duration: duration.total_seconds() / 60 / 60)

        df["main_topic"] = df["topics"].apply(lambda x: x[0][0])
        # df["main_topic"] = df["main_topic"].apply(topic_alias)

        df = df[df["main_topic"] != "E"]
        df = df[df["main_topic"] != "database courses"]
        df = df.groupby("main_topic").sum().reset_index()
        df["parent"] = df["main_topic"].apply(get_parent)
        df

        data = dict(
            title=df["main_topic"].apply(beautify_topic_long),
            course=df["main_topic"].apply(beautify_topic_short), # TODO: use ratios
            parent=df["parent"].apply(beautify_topic_short),
            hours=df["duration_hours"],
        )

        fig3 = px.sunburst(
            data,
            names='course',
            parents="parent",
            values='hours',
            labels=topic_names,
            hover_name="title",
            title="Time spent on each course" # Course allocation?
        )
        fig3.update_layout(title_x=0.5)
        return fig3
    except:
        return make_placeholder()

# # Main
# if __name__ == "__main__":
#     app.run_server(host='127.0.0.1', port=8080, debug=True)#, port="8060", host="0.0.0.0")




# import Flask

# @app.route('/')
# def hello():
#     """Return a friendly HTTP greeting."""
#     return 'Hello World!'


# @app.errorhandler(500)
# def server_error(e):
#     return """
#     An internal error occurred: <pre>{}</pre>
#     See logs for full stacktrace.
#     """.format(e), 500


# if __name__ == '__main__':
#     # This is used when running locally. Gunicorn is used to run the
#     # application on Google App Engine. See entrypoint in app.yaml.
#     app.run(host='127.0.0.1', port=8080, debug=True)
# # [END gae_flex_quickstart]