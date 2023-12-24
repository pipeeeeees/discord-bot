import asyncio
import os
import datetime
import discord
import time
import pandas as pd
from pipesbot import db_handler
from pipesbot import pollen
from pipesbot import gas
from pipesbot import PIPEEEEEES_DISCORD_ID
#from pipesbot import PIPES_SERVER_GENERAL_ID
from pipesbot import STEEBON_ATL_STATION_ID
from pipesbot import weather
import traceback

pipesbot_dir = 'pipesbot'
pickle_subdir = 'pickles'
images_subdir = 'images'
plots_subdir = 'plots'
its_gone_rain_file = 'its-gon-rain.jpg'
pickle_file = 'gas_prices_ga.pkl'
forecasted_rain_plot_file = 'forecasted_rain.png'

forecasted_rain_plot_file_path = os.path.join(pipesbot_dir, plots_subdir, forecasted_rain_plot_file)
its_gone_rain_file_path = os.path.join(pipesbot_dir, images_subdir, its_gone_rain_file)
ga_gas_pickle_path = os.path.join(pipesbot_dir, pickle_subdir, pickle_file)

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

            # send a rain plot if one was generated
            if check_rain_plot():
                try:
                    await channel.send(file=discord.File(forecasted_rain_plot_file_path))
                    time.sleep(15)
                    await channel.send(file=discord.File(its_gone_rain_file_path))
                except:
                    pass
                clear_rain_plot()
            await asyncio.sleep(60) 
        
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

def morning_report_message(plot=False):
    message_string = ''

    try:
        message_string = message_string + f"Good morning! Here is your Atlanta Morning Report for {datetime.datetime.now().strftime('%B %d, %Y')}:"
        
        pollen_cnt = pollen.get_atl_pollen_count()
        if type(pollen_cnt) == int:
            message_string = message_string + f'\n- The pollen count for today is {pollen_cnt} ' + chr(0x1F333)
        else:
            message_string = message_string + f'\n- The pollen count is not available at this time.'

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
                message_string = message_string + f'{reg} - {type(reg)}'
                message_string = message_string + f'{last_reg_price} - {type(last_reg_price)}'

                last_mid_price = float(gas_prices['Midgrade'].iloc[-2].removeprefix('$'))
                diff_mid = mid - last_mid_price
                message_string = message_string + f'{mid} - {type(mid)}'
                message_string = message_string + f'{last_mid_price} - {type(last_mid_price)}'

                last_prem_price = float(gas_prices['Premium'].iloc[-2].removeprefix('$'))
                diff_prem = prem - last_prem_price
                message_string = message_string + f'{prem} - {type(prem)}'
                message_string = message_string + f'{last_prem_price} - {type(last_prem_price)}'

                message_string = message_string + f'\n- In Georgia, the state-wide average gas prices are:'
                if diff_reg > 0:
                    message_string = message_string + f'\n\t\tRegular: {reg} ' + chr(0x2197)
                elif diff_reg < 0:
                    message_string = message_string + f'\n\t\tRegular: {reg} ' + chr(0x2198)
                else:
                    message_string = message_string + f'\n\t\tRegular: {reg} ' + chr(0x2192)
                if diff_mid > 0:
                    message_string = message_string + f'\n\t\tMidgrade: {mid} ' + chr(0x2197)
                elif diff_mid < 0:
                    message_string = message_string + f'\n\t\tMidgrade: {mid} ' + chr(0x2198)
                else:
                    message_string = message_string + f'\n\t\tMidgrade: {mid} ' + chr(0x2192)
                if diff_prem > 0:
                    message_string = message_string + f'\n\t\tPremium: {prem} ' + chr(0x2197)
                elif diff_prem < 0:
                    message_string = message_string + f'\n\t\tPremium: {prem} ' + chr(0x2198)
                else:
                    message_string = message_string + f'\n\t\tPremium: {prem} ' + chr(0x2192)
            else:
                message_string = message_string + f'\n- In Georgia, the state-wide average gas prices are:\n\t\tRegular: {reg}\n\t\tMidgrade: {mid}\n\t\tPremium: {prem}'
        else:
            message_string = message_string + f'\n- In Georgia, the state-wide average gas prices are:\n\t\tRegular: {reg}\n\t\tMidgrade: {mid}\n\t\tPremium: {prem}'

        #message_string = message_string + weather.real_time_weather_report(plot=True)
        message_string = message_string + f'\n- NOTE: The weather feature is in beta and may not be accurate yet. Please report any issues.'

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

def create_gas_prices_historical():
    if not check_gas_prices_historical():
        gas_prices = pd.DataFrame(columns=['Regular','Midgrade','Premium','Diesel'])
        gas_prices.to_pickle(ga_gas_pickle_path)
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

def get_gas_prices_historical():
    if os.path.exists(ga_gas_pickle_path):
        gas_prices = pd.read_pickle(ga_gas_pickle_path)
        return gas_prices
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
    
def get_string_gas_prices_historical():
    if check_gas_prices_historical():
        gas_prices = pd.read_pickle(ga_gas_pickle_path)
        return f'```{gas_prices}```'
    else:
        return None

if __name__ == '__main__':
    print(morning_report_message())