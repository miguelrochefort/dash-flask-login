# index page
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output

from server import app, server
from flask_login import logout_user, current_user
from views import login, dashboard

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

header = html.Div(
            [
                # html.Div(
                #     [
                #         # html.Img(
                #         #     src=app.get_asset_url("dash-logo.png"),
                #         #     id="plotly-image",
                #         #     style={
                #         #         "height": "60px",
                #         #         "width": "auto",
                #         #         "margin-bottom": "25px",
                #         #     },
                #         # )
                #     ],
                #     className="one-third column",
                # ),
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
                # html.Div(
                #     [
                #         html.A(
                #             html.Button("Logout", id="learn-more-button"),
                #             href="/logout",
                #         )
                #     ],
                #     className="one-third column",
                #     id="logout",
                # ),
            ],
            id="header",
            className="row flex-display",
            style={"margin-bottom": "25px"},
        )

# header = html.Div(
#     className='header',
#     children=html.Div(
#         className='container-width',
#         style={'height': '100%'},
#         children=[
#             html.Div(children=[
#                 html.H3(
#                     "WGU Time Tracker",
#                     style={"margin-bottom": "0px"},
#                 ),
#                 html.H5(
#                     "Powered by ActivityWatch", style={"margin-top": "0px"}
#                 ),
#             ]),
#             # html.Img(
#             #     src='assets/dash-logo-stripe.svg',
#             #     className='logo'
#             # ),
#             html.Div(className='links', children=[
#                 html.Div(id='user-name', className='link'),
#                 html.Div(id='logout', className='link')
#             ])
#         ]
#     )
# )

# header = html.Div(
#     className='header',
#     children=html.Div(
#         className='container-width',
#         style={'height': '100%'},
#         children=[
#             html.Img(
#                 src='assets/dash-logo-stripe.svg',
#                 className='logo'
#             ),
#             html.Div(className='links', children=[
#                 html.Div(id='user-name', className='link'),
#                 html.Div(id='logout', className='link')
#             ])
#         ]
#     )
# )

app.layout = html.Div(
    [
        header,
        html.Div([
            html.Div(
                html.Div(id='page-content')#, className='content')#,
                # className='content-container'
            )
        ]),
        dcc.Location(id='url', refresh=False),
    ]
)




@app.callback(Output('page-content', 'children'),
              [Input('url', 'pathname')])
def display_page(pathname):
    if pathname == '/' or pathname == '/login' or pathname == '/dashboard':
        if current_user.is_authenticated:
            return dashboard.layout
        else:
            return login.layout
    elif pathname == '/logout':
        if current_user.is_authenticated:
            logout_user()
        return login.layout
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
