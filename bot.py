import telegram
from telegram.ext import Updater
from telegram.ext import CommandHandler
import os
from geopy.geocoders import Nominatim
import networkx as nx
from staticmap import StaticMap, Line
import pandas as pd
from pandas import DataFrame

# Import functions from external file.
from data import *


# ----------------------------- HELPER FUNCTIONS ------------------------------
# Sends the message 's' to the user.
def message(bot, update, s):
    bot.send_message(chat_id=update.message.chat_id, text=s)


# Sends the message 's' to the user in Markdown format.
def message_MD(bot, update, s):
    bot.send_message(chat_id=update.message.chat_id, text=s,
    parse_mode=telegram.ParseMode.MARKDOWN)


# Checks if x is an integer number.
def is_int(x):
    try:
        int(x)
        return True
    except ValueError:
        return False


# Checks if x is a float number.
def is_float(x):
    try:
        float(x)
        return True
    except ValueError:
        return False


# ------------------------------ BOT COMMANDS ---------------------------------

# Gives a welcoming message to the user.
def start(bot, update, user_data):
    # Saves username's first name.
    name = update.message.chat.first_name
    text = ("Hello, %s! Do you need something?") % (name)
    text2 = ''' I'm deBOTed 🤖 to /help you.'''
    message(bot, update, text)
    message_MD(bot, update, text2)

# Gives information about the authors of the bot.
def authors(bot, update):
    text = ('''My creators are Maria Prat and Max Balsells. 
Their emails are respectively maria.prat@est.fib.upc.edu and 
max.balsells.i@est.fib.upc.edu.''')
    message_MD(bot, update, text)

# Gives information about bot commands and short instructions to use them.
def help(bot, update):
    text = '''
🚲 Let me help you to use *Bicing* in Barcelona! 🚲
- Use /start to get a welcoming message. 😉
- Use /authors to get information about my authors. 
- Use /graph *<distance>* to initialize a new graph with up-to-date data.
You can choose the maximum distance between two stations or take the default 
value of 1000 m.
- Use /nodes to get the number of stations in the current graph.
- Use /edges to get the number of connections between stations in the current graph.
- Use /components to get the number of connected components in the current graph.
- Use /plotgraph to create a map 🗺️ with all the stations and connections between them. 
- Use /route *<origin>, <destination>* to create a map with the fastest route between two addresses.
- Use /valid\_route *<origin>, <destination>* to create a map with the fastest route between two addresses.
The first station has at least one bike and the last one has at least one empty dock.
- Use /distribute *<min_bikes>, <min_docks>* to find the minimum cost of transfering bikes
among connected stations so that each one has at least `min_bikes` bikes and `min_docks` empty 
docks, as well as the edge with maximum cost.
'''
    message_MD(bot, update, text)  


# Tells the user how many nodes has the current graph (if previously defined).
def nodes(bot, update, user_data):
    if 'G' in user_data:
        message(bot, update, "Number of nodes: " + str(user_data['G'].number_of_nodes()))
    else:
        message(bot, update, "❗You must first construct a geometric graph!")


# Tells the user how many connected components has the current graph
# (if previously defined).
def components(bot, update, user_data):
    if 'G' in user_data:
        message(bot, update, "Number of connected components: " +
                str(nx.number_connected_components(user_data['G'])))
    else:
        message(bot, update, "❗You must first construct a geometric graph!")


# Tells the user how many edges has the current graph (if previously defined).
def edges(bot, update, user_data):
    if 'G' in user_data:
        message(bot, update, "Number of edges: " + str(user_data['G'].number_of_edges()))
    else:
        message(bot, update, "❗You must first construct a geometric graph!")


# Plots the current graph over a map (if previously defined).
def plotgraph(bot, update, user_data):
    if 'G' in user_data:
        fitxer = "plotgraph_" + str(update.message.chat_id) + ".png"

        m = ploting(user_data['G'], user_data['position'])
        image = m.render(zoom=12)
        image.save(fitxer)

        bot.send_photo(chat_id=update.message.chat_id,
                       photo=open(fitxer, 'rb'))
        os.remove(fitxer)

    else:
        message(bot, update, "❗You must first construct a geometric graph!")


# Defines a new geometric graph over the stations with the desired distance in
# as meters argument. If it isn't specified, it takes 1000 m as the distance.
# And we store the dataframes that contain the bicing stations information.
def graph(bot, update, args, user_data):
    warning_num = "❗You should introduce a number!"
    warning_pos_num = "❗You should introduce a positive number!"
    try:
        if (len(args) == 0):
            dist = 1000
        else:
            dist = args[0]

        if (not is_float(dist)):
            message(bot, update, warning_num)

        elif (float(dist) <= 0):
            message(bot, update, warning_pos_num)
        else:
            # Import station data.
            url_info = ui = ('https://api.bsmsa.eu/ext/api/bsm/gbfs/'
                        'v2/en/station_information')
            url_status = us = ('https://api.bsmsa.eu/ext/api/bsm/gbfs/'
                          'v2/en/station_status')
            b1 = DataFrame.from_records(pd.read_json(ui)['data']['stations'], 
                                        index='station_id')
            b2 = DataFrame.from_records(pd.read_json(us)['data']['stations'], 
                                        index='station_id')
            bicing = b1[['address', 'lat', 'lon', 'capacity']]
            bikes = b2[['num_bikes_available', 'num_docks_available']]
            
            results = geometric_graph(float(dist), bicing)

            user_data['G'], user_data['position'] = results
            user_data['bikes'], user_data['bicing'] = bikes, bicing

            message(bot, update, "✅ Graph constructed successfully!")

    except Exception as e:
        print(e)
        text = "❗Unexpected error. Please, report this error to the authors 😊."
        message(bot, update, text)


# Shows a map with the fastest route between two valid adresses, moving with
# bicycle and on foot. It also returns the expected travelling time.
def route(bot, update, args, user_data):
    if 'G' in user_data:
        try:
            m, time = unchecked_route(" ".join(args), user_data['G'],
                                      user_data['position'])

            if (time == -1):
                bot.send_message(chat_id=update.message.chat_id, text=m)
            else:
                fitxer = "route_" + str(update.message.chat_id) + ".png"
                image = m.render()
                image.save(fitxer)

                bot.send_photo(chat_id=update.message.chat_id,
                               photo=open(fitxer, 'rb'))
                text = ("📍 This route will take you to your destination in "
                        "{} minutes. 🕒".format(time))
                message(bot, update, text)
                os.remove(fitxer)

        except Exception as e:
            print(e)
            text = ("❗Unexpected error. Please, report this error to the "
                    "authors 😊.")
            message(bot, update, text)

    else:
        message(bot, update, "❗You must first construct a geometric graph!")


# Returns the same as route. However, it checks that the first station has at
# least one bike and the last station has at least one free dock.
def valid_route(bot, update, args, user_data):
    if 'G' in user_data:
        try:
            m, time = true_route(" ".join(args), user_data['G'],
                            user_data['position'], user_data['bikes'])

            if (time == -1):
                bot.send_message(chat_id=update.message.chat_id, text=m)
            else:
                fitxer = "valid_route_" + str(update.message.chat_id) + ".png"
                image = m.render()
                image.save(fitxer)

                bot.send_photo(chat_id=update.message.chat_id,
                               photo=open(fitxer, 'rb'))
                text = ("📍 This route will take you to your destination in "
                        "{} minutes. 🕒".format(time))
                message(bot, update, text)
                os.remove(fitxer)

        except Exception as e:
            print(e)
            text = ("❗Unexpected error. Please, report this error to the "
                    "authors 😊.")
            message(bot, update, text)

    else:
        message(bot, update, "❗You must first construct a geometric graph!")


# Gets a minimum number of bikes and a minimum nomber of docks for each station
# as arguments. Both values must be integers. Returns the value of the minimum
# flow and the edge with the highest cost (with cost := distance * number of
# bicycles).
def distribute(bot, update, args, user_data):
    if 'G' in user_data:
        try:
            if (len(args) < 2):
                message(bot, update, "❗You should introduce two numbers!")
            elif (not is_int(args[0] or not is_int(arg[1]))):
                message(bot, update, "❗You should introduce two numbers!")
            elif (int(args[0]) < 0 or int(args[1]) < 0):
                message(bot, update,
                        "❗You should introduce two non negative numbers!")

            else:
                cost, information = distribution(int(args[0]),
                                                 int(args[1]),
                                                 user_data['G'],
                                                 user_data['bicing'],
                                                 user_data['bikes'])
                if (cost > 0):
                    text = ("🚛 Total cost of transferring bicycles: "
                            "{} km.".format(cost))
                    message(bot, update, text)
                message(bot, update, information)

        except Exception as e:
            print(e)
            text = ("❗Unexpected error. Please, report this error to the "
                    "authors 😊.")
            message(bot, update, text)

    else:
        message(bot, update, "❗You must first construct a geometric graph!")


TOKEN = open('token.txt').read().strip()

updater = Updater(token=TOKEN)
dispatcher = updater.dispatcher

# Command definitions.
dispatcher.add_handler(CommandHandler('start', start, pass_user_data=True))
dispatcher.add_handler(CommandHandler('help', help))
dispatcher.add_handler(CommandHandler('authors', authors))
dispatcher.add_handler(CommandHandler('nodes', nodes, pass_user_data=True))
dispatcher.add_handler(CommandHandler('edges', edges, pass_user_data=True))
dispatcher.add_handler(CommandHandler('plotgraph', plotgraph,
                                      pass_user_data=True))
dispatcher.add_handler(CommandHandler('components', components,
                                      pass_user_data=True))
dispatcher.add_handler(CommandHandler('graph', graph, pass_args=True,
                                      pass_user_data=True))
dispatcher.add_handler(CommandHandler('route', route, pass_args=True,
                                      pass_user_data=True))
dispatcher.add_handler(CommandHandler('valid_route', valid_route,
                                      pass_args=True, pass_user_data=True))
dispatcher.add_handler(CommandHandler('distribute', distribute,
                                      pass_args=True, pass_user_data=True))

updater.start_polling()
