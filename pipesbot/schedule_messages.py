import asyncio
import os
import datetime
import discord
import time
import pandas as pd
import matplotlib.pyplot as plt
from pipesbot import db_handler
from pipesbot import pollen
from pipesbot import gas
from pipesbot import PIPEEEEEES_DISCORD_ID
#from pipesbot import PIPES_SERVER_GENERAL_ID
from pipesbot import STEEBON_ATL_STATION_ID
from pipesbot import weather
import traceback
from pipesbot import urban_dict

pipesbot_dir = 'pipesbot'
pickle_subdir = 'pickles'
images_subdir = 'images'
plots_subdir = 'plots'
its_gone_rain_file = 'its-gon-rain.jpg'
pickle_file = 'gas_prices_ga.pkl'
pollen_pickle_file = 'pollen.pkl'
forecasted_rain_plot_file = 'forecasted_rain.png'
gas_historical_plot_file = 'gas_historical.png'

forecasted_rain_plot_file_path = os.path.join(pipesbot_dir, plots_subdir, forecasted_rain_plot_file)
its_gone_rain_file_path = os.path.join(pipesbot_dir, images_subdir, its_gone_rain_file)
ga_gas_pickle_path = os.path.join(pipesbot_dir, pickle_subdir, pickle_file)
ga_gas_historical_plot_path = os.path.join(pipesbot_dir, plots_subdir, gas_historical_plot_file)
pollen_pickle_path = os.path.join(pipesbot_dir, pickle_subdir, pollen_pickle_file)
pollen_historical_plot_path = os.path.join(pipesbot_dir, plots_subdir, 'pollen_historical.png')

class MessageScheduler:
    def __init__(self, client):
        self.client = client
        self.scheduled_messages = []

    async def schedule_message(self, channel_id, message, date, time):
        scheduled_time = datetime.datetime.combine(date, time)
        self.scheduled_messages.append((channel_id, message, scheduled_time))
    
    async def unschedule_message(self, channel_id, message):
        self.scheduled_messages = [(c, m, t) for (c, m, t) in self.scheduled_messages if not (c == channel_id and m == message)]

    async def check_scheduled_messages(self):
        now = datetime.datetime.now()
        for (channel_id, message, scheduled_time) in self.scheduled_messages:
            if now >= scheduled_time:
                channel = await self.client.fetch_channel(channel_id)
                await channel.send(message)
                self.scheduled_messages.remove((channel_id, message, scheduled_time))

    async def morning_report(self, channel_id=STEEBON_ATL_STATION_ID):
        # Compose the message
        message_string = ''
        clear_rain_plot()
        daily_update_gas_prices()

        message_string = message_string + morning_report_message()

        # Channel check
        if channel_id == PIPEEEEEES_DISCORD_ID:
            user = await self.client.fetch_user(PIPEEEEEES_DISCORD_ID)
            channel = await user.create_dm()
        else:
            channel = await self.client.fetch_channel(channel_id)

        # Send checker
        if message_string != '':
            await channel.send(message_string)

            """
            if 'It will rain today' in message_string:
                await channel.send(file=discord.File(r'pipesbot/images/its-gon-rain.jpg'))
            """

            # send a rain plot if one was generated
            """
            if check_rain_plot():
                try:
                    await channel.send(file=discord.File(forecasted_rain_plot_file_path))
                except:
                    pass
                clear_rain_plot()
            """
                
            # if the day is monday, send the gas prices historical plot
            if datetime.datetime.now().weekday() == 0:
                outcome = plot_gas_prices_historical(number_of_days=14, zero_out=False)
                if outcome:
                    await channel.send(file=discord.File(ga_gas_historical_plot_path))
                    clear_gas_prices_historical_plot()

            # if the day is the first of the month, send the gas prices historical plot with 60 days
            if datetime.datetime.now().day == 1:
                outcome = plot_gas_prices_historical(number_of_days=60, zero_out=False)
                if outcome:
                    await channel.send(file=discord.File(ga_gas_historical_plot_path))
                    clear_gas_prices_historical_plot()

            await asyncio.sleep(65) 
    
    async def word_of_the_day(self, channel_id=STEEBON_ATL_STATION_ID):
        # Compose the message
        message_string = word_of_the_day_message()

        # Channel check
        if channel_id == PIPEEEEEES_DISCORD_ID:
            user = await self.client.fetch_user(PIPEEEEEES_DISCORD_ID)
            channel = await user.create_dm()
        else:
            channel = await self.client.fetch_channel(channel_id)

        # Send checker
        if message_string != '':
            await channel.send(message_string)
            if channel_id != PIPEEEEEES_DISCORD_ID:
                await asyncio.sleep(65)
        
    async def pollen_report(self, channel_id=STEEBON_ATL_STATION_ID):
        # send plot of pollen count for the last 14 days
        outcome = plot_pollen_historical(number_of_days=14, zero_out=False)
        if outcome:
            if channel_id == PIPEEEEEES_DISCORD_ID:
                user = await self.client.fetch_user(PIPEEEEEES_DISCORD_ID)
                channel = await user.create_dm()
            else:
                channel = await self.client.fetch_channel(channel_id)
            await channel.send(file=discord.File('pollen_historical.png'))
            clear_pollen_historical_plot()
            await asyncio.sleep(65)
        else:
            # send "failed to generate pollen plot" message
            await channel.send('Failed to generate pollen plot. Way to go, @pipeeeeees.')
            await asyncio.sleep(65)

    # Start the scheduler loop
    async def start(self):
        counter = 0
        min_flag = False
        time.sleep(1)
        while True:
            now = datetime.datetime.now()

            # check for reminder messages
            await self.check_scheduled_messages()

            # every day at 9:00 AM
            if now.hour == 9 and now.minute == 00 and min_flag == False:
                min_flag = True
                await self.morning_report()
            """
            # every day at noon
            if now.hour == 12 and now.minute == 00 and min_flag == False:
                min_flag = True
                await self.word_of_the_day()
            """

            # every day at 11:30 AM, update the pollen count
            if now.hour == 11 and now.minute == 30 and min_flag == False:
                min_flag = True
                daily_update_pollen()

            # every monday at 12:00 PM during March, April, and May
            if now.weekday() == 0 and now.hour == 12 and now.minute == 00 and min_flag == False and now.month in [3,4,5]:
                min_flag = True
                await self.pollen_report()

            # check every n seconds
            n = 30
            await asyncio.sleep(n) 
            counter += 1

            # 5 minute counter 
            if counter >= ((60*5/n) - 1):
                db_handler.clear_old_reminders()
                min_flag = False
                counter = 0

    # Stop the scheudler loop
    async def stop(self):
        # No urge to implement this yet
        pass

scheduler = None

def scheduler_setup(client):
    global scheduler
    scheduler = MessageScheduler(client)

def word_of_the_day_message():
    message_string = ''
    word, definition = urban_dict.random_popular_word()
    if word and definition:
        message_string = message_string + f'Good afternoon! The Word of the Day is: ```{word}```Definition: ```{definition}```'
    else:
        message_string = message_string + f'Unable to retrieve the word of the day. Please complain to @pipeeeeees'
    return message_string

def morning_report_message(plot=False):
    message_string = ''

    try:
        message_string = message_string + f"Here is your Atlanta Morning Report for {datetime.datetime.now().strftime('%A, %B %d, %Y')}:"
        
        pollen_cnt = pollen.get_atl_pollen_count()
        if type(pollen_cnt) == int:
            message_string = message_string + f'\n- The pollen count for today is {pollen_cnt} ' + chr(0x1F333)
        else:
            #message_string = message_string + f'\n- The pollen count is not available at this time.'
            pass

        reg, mid, prem, die = gas.get_gas('GA')
        reg = float(reg.removeprefix('$'))
        mid = float(mid.removeprefix('$'))
        prem = float(prem.removeprefix('$'))
        die = float(die.removeprefix('$'))
        diff_reg = 0
        diff_mid = 0
        diff_prem = 0
        if check_gas_prices_historical():
            gas_prices = get_gas_prices_historical()
            if len(gas_prices) > 1:
                last_reg_price = float(gas_prices['Regular'].iloc[-2].removeprefix('$'))
                diff_reg = reg - last_reg_price
                #message_string = message_string + f'{reg} - {type(reg)}'
                #message_string = message_string + f'{last_reg_price} - {type(last_reg_price)}'

                last_mid_price = float(gas_prices['Midgrade'].iloc[-2].removeprefix('$'))
                diff_mid = mid - last_mid_price
                #message_string = message_string + f'{mid} - {type(mid)}'
                #message_string = message_string + f'{last_mid_price} - {type(last_mid_price)}'

                last_prem_price = float(gas_prices['Premium'].iloc[-2].removeprefix('$'))
                diff_prem = prem - last_prem_price
                #message_string = message_string + f'{prem} - {type(prem)}'
                #message_string = message_string + f'{last_prem_price} - {type(last_prem_price)}'
                
                # GAS PRICES
                message_string = message_string + f'\n- In Georgia, the state-wide average gas prices are:'
                if diff_reg > 0:
                    message_string = message_string + f'\n\t\tRegular: ${reg} ' + chr(0x2197) + f' (${diff_reg:+.3f})'
                elif diff_reg < 0:
                    message_string = message_string + f'\n\t\tRegular: ${reg} ' + chr(0x2198) + f' (${diff_reg:.3f})'
                else:
                    message_string = message_string + f'\n\t\tRegular: ${reg} ' + chr(0x2192) + f' (${diff_reg:.3f})'
                if diff_mid > 0:
                    message_string = message_string + f'\n\t\tMidgrade: ${mid} ' + chr(0x2197) + f' (${diff_mid:+.3f})'
                elif diff_mid < 0:
                    message_string = message_string + f'\n\t\tMidgrade: ${mid} ' + chr(0x2198) + f' (${diff_mid:.3f})'
                else:
                    message_string = message_string + f'\n\t\tMidgrade: ${mid} ' + chr(0x2192) + f' (${diff_mid:.3f})'
                if diff_prem > 0:
                    message_string = message_string + f'\n\t\tPremium: ${prem} ' + chr(0x2197) + f' (${diff_prem:+.3f})'
                elif diff_prem < 0:
                    message_string = message_string + f'\n\t\tPremium: ${prem} ' + chr(0x2198) + f' (${diff_prem:.3f})'
                else:
                    message_string = message_string + f'\n\t\tPremium: ${prem} ' + chr(0x2192) + f' (${diff_prem:.3f})'
            else:
                message_string = message_string + f'\n- In Georgia, the state-wide average gas prices are:\n\t\tRegular: {reg}\n\t\tMidgrade: {mid}\n\t\tPremium: {prem}'
        else:
            message_string = message_string + f'\n- In Georgia, the state-wide average gas prices are:\n\t\tRegular: {reg}\n\t\tMidgrade: {mid}\n\t\tPremium: {prem}'

        # WEATHER
        short_message_string = message_string
        message_string = message_string + weather.real_time_weather_report(plot=True)

        # SUNSET
        sunset = weather.get_sun_time(0, "sunset")
        sunset_string = f"\n- Sunset is at {sunset} 🌅"
        sunrise = weather.get_sun_time(1, "sunrise")
        sunrise_string = f"\n- Sunrise tomorrow is at {sunrise} 🌅"
        message_string = message_string + sunset_string
        message_string = message_string + sunrise_string

        # if message string is 2000 chars or more, send the short version
        if len(message_string) >= 2000:
            message_string = short_message_string
        
    except Exception as e:
        exception_traceback = traceback.format_exc()
        message_string = f'An error occurred while trying to compose the morning report.\n'
        message_string = f'```{e}```\n```{exception_traceback}```'

    return message_string

def morning_report_command(channel_id=PIPEEEEEES_DISCORD_ID):
    global scheduler
    asyncio.ensure_future(scheduler.morning_report(channel_id))

def clear_rain_plot():
    if check_rain_plot():
        os.remove(forecasted_rain_plot_file_path)
        return True
    else:
        return False

def daily_update_gas_prices():
    now = datetime.datetime.now()
    reg, mid, prem, die = gas.get_gas('GA')
    append_gas_prices_historical(reg,mid,prem,die,now)
    return reg,mid,prem,die,now

def daily_update_pollen():
    now = datetime.datetime.now()
    pollen_cnt = pollen.get_atl_pollen_count()
    # check if the pollen count is an integer
    if type(pollen_cnt) == int:
        append_pollen_historical(pollen_cnt, now)
        return pollen_cnt, now

def create_gas_prices_historical():
    if not check_gas_prices_historical():
        gas_prices = pd.DataFrame(columns=['Regular','Midgrade','Premium','Diesel'])
        gas_prices.to_pickle(ga_gas_pickle_path)
        return True
    else:
        return False
    
def create_pollen_historical():
    if not check_pollen_historical():
        pollen = pd.DataFrame(columns=['Pollen Count'])
        pollen.to_pickle(pollen_pickle_path)
        return True
    else:
        return False

def check_rain_plot():
    if os.path.exists(forecasted_rain_plot_file_path):
        return True
    else:
        return False

def check_gas_prices_historical():
    if os.path.exists(ga_gas_pickle_path):
        return True
    else:
        return False
    
def check_pollen_historical():
    if os.path.exists(pollen_pickle_path):
        return True
    else:
        return False

def get_gas_prices_historical():
    if os.path.exists(ga_gas_pickle_path):
        gas_prices = pd.read_pickle(ga_gas_pickle_path)
        return gas_prices
    else:
        return None
    
def get_pollen_historical():
    if os.path.exists(pollen_pickle_path):
        pollen = pd.read_pickle(pollen_pickle_path)
        return pollen
    else:
        return None

def append_gas_prices_historical(reg,mid,prem,die,datetime):
    # append to the pickle file. if the new data is on the same day as the last entry, overwrite it
    # otherwise, append it
    if check_gas_prices_historical():
        gas_prices = pd.read_pickle(ga_gas_pickle_path)
        if len(gas_prices) > 0:
            if gas_prices.index[-1].date() == datetime.date():
                gas_prices.loc[gas_prices.index[-1]] = [reg,mid,prem,die]
            else:
                gas_prices.loc[datetime] = [reg,mid,prem,die]
            gas_prices.to_pickle(ga_gas_pickle_path)
            return True
        else:
            gas_prices.loc[datetime] = [reg,mid,prem,die]
            gas_prices.to_pickle(ga_gas_pickle_path)
    else:
        return False
    
def append_pollen_historical(pollen_count, datetime):
    # append to the pickle file. if the new data is on the same day as the last entry, overwrite it
    # otherwise, append it
    if check_pollen_historical():
        pollen = pd.read_pickle(pollen_pickle_path)
        if len(pollen) > 0:
            if pollen.index[-1].date() == datetime.date():
                pollen.loc[pollen.index[-1]] = [pollen_count]
            else:
                pollen.loc[datetime] = [pollen_count]
            pollen.to_pickle(pollen_pickle_path)
            return True
        else:
            pollen.loc[datetime] = [pollen_count]
            pollen.to_pickle(pollen_pickle_path)
    else:
        return False
    
def get_string_gas_prices_historical():
    if check_gas_prices_historical():
        gas_prices = pd.read_pickle(ga_gas_pickle_path)
        return f'```{gas_prices}```'
    else:
        return None

def get_string_pollen_historical():
    if check_pollen_historical():
        pollen = pd.read_pickle(pollen_pickle_path)
        return f'```{pollen}```'
    else:
        return None

# plot the last 7 entries of gas prices
def plot_gas_prices_historical(number_of_days=7, zero_out=True):
    if check_gas_prices_historical():
        gas_prices = pd.read_pickle(ga_gas_pickle_path)

        # if number of entries is less than number_of_days, set number_of_days to the number of entries
        if len(gas_prices) < number_of_days:
            number_of_days = len(gas_prices)

        gas_prices_reg = gas_prices['Regular']
        gas_prices_reg = gas_prices_reg.iloc[-number_of_days:]
        gas_prices_reg = gas_prices_reg.str.replace('$','')
        gas_prices_reg = gas_prices_reg.astype(float)

        gas_prices_mid = gas_prices['Midgrade']
        gas_prices_mid = gas_prices_mid.iloc[-number_of_days:]
        gas_prices_mid = gas_prices_mid.str.replace('$','')
        gas_prices_mid = gas_prices_mid.astype(float)

        gas_prices_prem = gas_prices['Premium']
        gas_prices_prem = gas_prices_prem.iloc[-number_of_days:]
        gas_prices_prem = gas_prices_prem.str.replace('$','')
        gas_prices_prem = gas_prices_prem.astype(float)

        gas_prices_die = gas_prices['Diesel']
        gas_prices_die = gas_prices_die.iloc[-number_of_days:]
        gas_prices_die = gas_prices_die.str.replace('$','')
        gas_prices_die = gas_prices_die.astype(float)

        gas_prices_dates = gas_prices.index
        gas_prices_dates = gas_prices_dates[-number_of_days:]
        if number_of_days <= 10:
            gas_prices_dates = [date.strftime('%A\n%m/%d') for date in gas_prices_dates]
        else:
            gas_prices_dates = [date.strftime('%m/%d') for date in gas_prices_dates]

        # plot all in one plot
        fig, ax = plt.subplots()
        #ax.plot(gas_prices_dates, gas_prices_die, label='Diesel')
        ax.plot(gas_prices_dates, gas_prices_prem, label='Premium')
        ax.plot(gas_prices_dates, gas_prices_mid, label='Midgrade')
        ax.plot(gas_prices_dates, gas_prices_reg, label='Regular')
        if zero_out:
            ax.set_ylim(ymin=0)
        ax.set_xlabel('Date Recorded')
        ax.set_ylabel('Price per Gallon ($)')
        ax.set_title(f'Georgia Avg Gas Prices (last {number_of_days} entries)')
        # dont show all x labels, just 9 of them if there are more than 9 entries
        if number_of_days > 9:
            ax.set_xticks(gas_prices_dates[::(number_of_days//9)])
        ax.legend(loc='upper left')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.grid()
        plt.savefig(ga_gas_historical_plot_path) 
        return True
    else:
        return False
    

def plot_pollen_historical(number_of_days=7, zero_out=True):
    if check_pollen_historical():
        pollen_pkl = pd.read_pickle(pollen_pickle_path)
        if len(pollen_pkl) < number_of_days:
            number_of_days = len(pollen_pkl)
        pollen_pkl = pollen_pkl.iloc[-number_of_days:]
        pollen_dates = pollen_pkl.index
        pollen_dates = pollen_dates[-number_of_days:]
        pollen_pkl = pollen_pkl['Pollen Count']
        
        # Calculate the rolling average with a minimum of 3 periods for the first window
        rolling_avg = pollen_pkl.rolling(window=3, min_periods=1).mean()
        
        fig, ax = plt.subplots()
        ax.plot(pollen_dates, pollen_pkl, label='Pollen Count')
        ax.plot(pollen_dates, rolling_avg, color='red', label='3-"day" Rolling Average')  # Add red line for rolling average
        if zero_out:
            ax.set_ylim(ymin=0)
        ax.set_xlabel('Date Recorded')
        ax.set_ylabel('Pollen Count')
        ax.set_title(f'Atlanta Pollen Count (last {number_of_days} entries)')
        # dont show all x labels, just 9 of them if there are more than 9 entries
        if number_of_days > 9:
            ax.set_xticks(pollen_dates[::(number_of_days//9)])
        ax.legend(loc='upper left')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.grid()
        plt.savefig(pollen_historical_plot_path) 
        return True
    else:
        return False


# delete the gas prices historical plot
def clear_gas_prices_historical_plot():
    if check_gas_prices_historical():
        os.remove(ga_gas_historical_plot_path)
        return True
    else:
        return False

def clear_pollen_historical_plot():
    if check_pollen_historical():
        os.remove('pollen_historical.png')
        return True
    else:
        return False

if __name__ == '__main__':
    print(morning_report_message())