# index page
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output

from server import app, server
from flask_login import logout_user, current_user

from views import login, dashboard, login_fd

header = html.Div(
            [
                html.Div(
                    [
                        html.Div(
                            [
                                html.H3(
                                    "WGU Time Tracker",
                                    style={"margin-bottom": "0px"},
                                ),
                                html.H5(
                                    "Powered by ActivityWatch", style={"margin-top": "0px"}
                                ),
                            ]
                        )
                    ],
                    id="title",
                ),
                html.A("Logout", id="logout", href="/logout"),
            ],
            id="header",
            className="row flex-display",
            style={"margin-bottom": "25px"},
        )

app.layout = html.Div(
    [
        header,
        html.Div(id='page-content'),
        dcc.Location(id='url', refresh=False),
    ]
)



@app.callback(Output('page-content', 'children'),
              [Input('url', 'pathname')])
def display_page(pathname):
    if pathname == '/' or pathname == '/login':
        if current_user.is_authenticated:
            return dashboard.layout
        else:
            return login.layout
    elif pathname == "/dashboard":
        if current_user.is_authenticated:
            return dashboard.layout
        else:
            return login_fd.layout  
    elif pathname == '/logout':
        if current_user.is_authenticated:
            logout_user()
        return login_fd.layout
    else:
        return '404'


@app.callback(
    Output('user-name', 'children'),
    [Input('page-content', 'children')])
def cur_user(input1):
    if current_user.is_authenticated:
        return html.Div('Current user: ' + current_user.username)
        # 'User authenticated' return username in get_id()
    else:
        return ''


@app.callback(
    Output('logout', 'children'),
    [Input('page-content', 'children')])
def user_logout(input1):
    if current_user.is_authenticated:
        return html.A('Logout', href='/logout')
    else:
        return ''


if __name__ == '__main__':
    app.run_server(debug=True)
