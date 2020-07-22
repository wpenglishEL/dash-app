import datetime
import argparse
import logging
import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_table
import pandas as pd
import plotly
from dash.dependencies import Input, Output
from flask import send_file
from github import Github
import json
 
logging.basicConfig(
    format="%(levelname)s - %(asctime)s - %(message)s",
    level=logging.DEBUG
)
 
external_stylesheets = external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
	 
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
server = app.server
 
app.config.update({
    'routes_pathname_prefix': './',
    'requests_pathname_prefix': './'
})

symptom_list=["fever", "cough", "muscle aches", "shortness of breath", "fatigue",
              "loss of taste or smell", "headache", "congestion", "nausea"]
app.layout = html.Div(children=[
    html.Img(
        src="https://upload.wikimedia.org/wikipedia/commons/thumb/2/2b/Eli_Lilly_and_Company.svg/1200px-Eli_Lilly_and_Company.svg.png",
        style={
            'height': 40,
            'width': 70,
        }
        ),
    html.H1("COVID-19 Recovery Questionnaire"),
    html.H3("At Eli Lilly and Company, we care about your well-being. \n Please "+
            "answer a few questions for us to determine your next steps \n "+
            "during these tough times."),
    html.H5("To help with results tracking, we ask that you come up with a unique username. "+
            "make sure that your username contains both letters and numbers (no special characters) "+
            "and is at least 8 digits long."),
    # this div below is to track the button status - is it running a
    # function, is it done, when should we disable the button?
    html.Div(id='trigger', children=0, style=dict(display="none")),
    html.Div(id='return_user_trigger', children=0, style=dict(display="none")),
    html.Button('I am a Returning User', id='return_user_button', disabled=False),
    html.Div("Welcome Back! Please continue to enter your username and complete the form below.", id='welcome_back_message', hidden=True),
    html.Br(),
    html.Div(id='questionnaire', children=[
        html.H5("What is your username?"),
        html.Div(id='name_input', children=
            dcc.Input(
                id="user_name",
                placeholder="Enter your unique username here...",
                type="text",
                size="50",
                required=True)
        ),
        html.Br(),
        html.H5("What is your current body temperature in Fahrenheit?"),
        html.Div(id='temperature_input', children=
            dcc.Input(
                id="temperature",
                placeholder="Enter your current body temperature in Fahrenheit...",
                type="number",
                size="50",
                min=70,
                required=True)
        ),
        html.Br(),
        html.H5("What are your current symptoms? Select from dropdown below."),
        html.Div(id="symptom_select", children=
            dcc.Dropdown(id='symptoms', placeholder='Select Applicable Symptoms...', 
                        multi=True, options=[{'label': i, 'value': i} for i in symptom_list])
        ),
        html.Br(),
        html.H5("How well are you feeling? Select 1 for extremely sick and 10 for a near full recovery."),
        html.Div(id='feeling_rating_input', children=
            dcc.Input(
                id="feeling_rating",
                placeholder="Enter your rating...",
                type="number",
                size="50",
                min=1,
                max=10,
                required=True)
        ),
        html.Br(),
        html.H5("How many cups of water have you had today?"),
        html.Div(id='water_intake_input', children=
            dcc.Input(
                id="water_intake",
                placeholder="Enter your water intake in ounces...",
                type="number",
                size="50",
                min=1,
                required=True)
        ),
        html.Br(),
        html.H5("Any other thoughts?"),
        html.Div(id='soup_input', children=
            dcc.Input(
                id="soup",
                placeholder="Enter some notes...",
                type="text",
                size="50",
                required=True)
        ),
    ]
    ),
    html.Br(),
    dcc.Markdown('**Click to submit** - please wait a moment for a response',
               id='submit-label'),
    html.Button('Submit', id='button', disabled=False, style={'BackgroundColor':'white'}),
    html.Div(id='input_return', hidden=True),
    dcc.Store(id='data_entered', data=False),
    dcc.Store(id="display_results", data=False),
    dcc.Store(id="is_returning_user", data=False),
    html.Br(),
    html.Div("Thank you for filling out the questionnaire! \n"+
             "Keep your username in a safe place. To view your results, \n"+
             "navigate to the \"View Your Progress\" page and enter the same \n"+
             "username you used to fill out this form." id='view_results'
    ),
]
)

@app.callback(
    dash.dependencies.Output("button", "disabled"),
    [dash.dependencies.Input("button", "n_clicks"),
     dash.dependencies.Input("trigger", "children")]
)
def trigger_function(n_clicks, trigger):
    context = dash.callback_context.triggered[0]['prop_id'].split('.')[0]
    if context == "button":
        # only if the button clicked do we consider disabling
        if n_clicks and n_clicks > 0:
            # let's immediately disable if it was clicked
            return True
        else:
            # don't disable on startup
            return False
    else:
        # on startup or something else triggered besides the button,
        # don't disable
        return False

@app.callback(
    dash.dependencies.Output("return_user_button", "disabled"),
    [dash.dependencies.Input("return_user_button", "n_clicks"),
     dash.dependencies.Input("return_user_trigger", "children")]
)
def trigger_function(n_clicks, return_user_trigger):
    context = dash.callback_context.triggered[0]['prop_id'].split('.')[0]
    if context == "return_user_button":
        # only if the button clicked do we consider disabling
        if n_clicks and n_clicks > 0:
            # let's immediately disable if it was clicked
            return True
        else:
            # don't disable on startup
            return False
    else:
        # on startup or something else triggered besides the button,
        # don't disable
        return False

@app.callback(
    [dash.dependencies.Output('is_returning_user', "data"),
     dash.dependencies.Output('welcome_back_message', "hidden")],
    [dash.dependencies.Input('return_user_button', 'n_clicks')]
)
def return_user(n_clicks):
    if not n_clicks or n_clicks == 0:
        # don't return anything initially
        return False, True
    return True, False

@app.callback(
    dash.dependencies.Output('display_results', "data"),
    [dash.dependencies.Input('button', 'n_clicks')],
    # this list below will create the ordered args into our callback to
    # collect all the form inputs
    [dash.dependencies.State("user_name", "value"),
     dash.dependencies.State("temperature", "value"),
     dash.dependencies.State("symptoms", "value"),
     dash.dependencies.State("feeling_rating", "value"),
     dash.dependencies.State("water_intake", "value"),
     dash.dependencies.State("soup", "value")]
)
def enter_word(
        n_clicks,
        user_name,
        temperature,
        symptoms,
        feeling_rating,
        water_intake,
        soup
        ):
    if not n_clicks or n_clicks == 0:
        # don't return anything initially
        return False
    required_inputs = {
        "required_singletons": {
            "User Name": user_name,
            "Temperature": temperature,
            "Symptoms": symptoms,
            "Feeling Rating": feeling_rating,
            "Water Intake": water_intake,
            "Soup": soup
        }
    }
    return True

@app.callback(
    dash.dependencies.Output('view_results', "hidden"),
    [dash.dependencies.Input('display_results', 'data'),
     dash.dependencies.Input('is_returning_user', 'data')],
    # this list below will create the ordered args into our callback to
    # collect all the form inputs
    [dash.dependencies.State("user_name", "value"),
     dash.dependencies.State("temperature", "value"),
     dash.dependencies.State("symptoms", "value"),
     dash.dependencies.State("feeling_rating", "value"),
     dash.dependencies.State("water_intake", "value"),
     dash.dependencies.State("soup", "value")]
)
def generate_results(
        display_results,
        is_returning_user,
        user_name,
        temperature,
        symptoms,
        feeling_rating,
        water_intake,
        soup
        ):
    if display_results:
        print(user_name)
        repo = "wpenglish/trackingJSON"
        g = Github("730b20add" + "112f61ecc5" + "b89fa43fd" + "d8123fb4bb44")
        repo = g.get_repo(repo)
        num_sym = len(symptoms)
        if is_returning_user:
            contents = repo.get_contents(user_name + ".json")
            person = json.loads(contents.decoded_content)
            person['temp'].append(temperature)
            person['symptoms'].append(symptoms)
            person['rating'].append(feeling_rating)
            person['water_intake'].append(water_intake)
            person['num_sym'].append(num_sym)
            person['Soup'].append(soup)
            person = json.dumps(person)
            repo.update_file(contents.path, user_name + " data", person, contents.sha)
        else:
            data_set = {"name": user_name, "temp": [temperature], "symptoms":[symptoms], "num_sym":[num_sym], "rating":[feeling_rating], "water_intake": [water_intake], "Soup":[soup]}
            json_dump = json.dumps(data_set)
            repo.create_file(user_name + ".json", user_name + " data", json_dump)
        return False
    return True

if __name__ == '__main__':
    app.run_server(debug=True)
