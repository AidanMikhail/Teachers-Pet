# Imports
import asyncio
import io
import os
import math
import random
import re
import discord

# API Key protection
from dotenv import load_dotenv
load_dotenv()

import datetime
from zoneinfo import ZoneInfo

# Discord Extensions
from discord import app_commands
from discord.ext import commands

# Image Recognition Extensions
from PIL import Image 
from pytesseract import pytesseract 

# Bot Setup
intents = discord.Intents.default()
intents.message_content = True
client = commands.Bot(command_prefix='!', intents=intents)

# Checks if the bot is active
@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')
    try:
        synced = await client.tree.sync()
        print(f"Synced {len(synced)} Commands")
    except Exception as e:
        print(e)

# Helps in converting written days (User input) to actual days (Bot output))
WeekDays = ["monday", "tuesday", "wednesday", "thursday", "friday","saturday","sunday"]
timezone = ZoneInfo('America/Toronto')

# Information Storing Lists
Channels = []
Guilds = []
Names = []
TimeSheets = []
freeMessages = {"":0}

# File paths
channelPath = "Storage/Channels.txt"
namesPath = "Storage/Names.txt"
sheetsPath = "Storage/TimeSheets.txt"
freePath = "Storage/freeMessages.txt"


# Update Guild & Channel lists from saved text file
if os.path.isfile(channelPath):
    file = open(channelPath,'r')

    for line in file.readlines(): # Iterate through the lines of the file
        if line != "":
            # Split the line into guild and channel ID
            lineSplit = line.split(",") 

            # Add the ID's to the Guild and Channel list accordingly
            Guilds.append(int(lineSplit[0]))
            Channels.append(int(lineSplit[1]))

# Update Names list from saved text file
if os.path.isfile(namesPath):
    file = open(namesPath,'r')

    for line in file.readlines(): # Iterate through the lines of the file
        if line != "":
            # Split the line into each name
            lineSplit = line.split(",")

            # Add each name to the list
            for i in range(len(lineSplit)):
                Names.append(lineSplit[i])

# Update TimeSheets list from saved text file
if os.path.isfile(sheetsPath):
    file = open(sheetsPath,'r')

    # Indexes
    lines = 0
    userIndex = 0
    dayIndex = 0
    lineSplit = []

    TimeSheets.append([])
    for line in file.readlines(): # Iterate through the lines of the file

        # After 7 lines ("New User" text), start updating the next user's timesheet
        if line == "New User\n":
            # Create the next user's timesheet & Update index
            TimeSheets.append([])
            userIndex += 1 

            # Reset Indexes
            dayIndex = 0
            classIndex = 0
        elif line != "\n": # Create the next day's array for each new line (if not empty)

            # Create the empty array to store the information
            TimeSheets[userIndex].append([]) 
            lineSplit = line[:-1].split(",") # Sepeate the infromation for each class
            for i in range(len(lineSplit)): 
                # Add "empty" timeslot
                TimeSheets[userIndex][dayIndex].append([0.0,0.0, "Class Name"])
                
                # Replace the start & end times with the correct times
                times = lineSplit[i].split(" ")
                TimeSheets[userIndex][dayIndex][i][0] = float(times[0])
                TimeSheets[userIndex][dayIndex][i][1] = float(times[1])
                TimeSheets[userIndex][dayIndex][i][2] = str(times[2])

            # Sort the day based on start time
            TimeSheets[userIndex][dayIndex] = sorted(TimeSheets[userIndex][dayIndex],key=lambda x: (x[0]))
            dayIndex += 1
        else: # Create an empty list if the day has no times
            TimeSheets[userIndex].append([])
            dayIndex += 1


# Update stored "Free" messages dictionary from saved text file
if os.path.isfile(freePath):
    file = open(freePath,'r')

    lineSplit = []
    for line in file.readlines(): # Iterate through the lines of the file
        line = line[:-1] # Remove the \n character from the line

        # Split the line into username and amount of messages & add to dictionary
        lineSplit = line.split(',')
        freeMessages.update({lineSplit[0]:int(lineSplit[1])})

# Dropdown menu / Stop function
class Answer(discord.ui.Select):
    def __init__(self, ans, user):
        self.ans = ans
        self.user = user
        options = [discord.SelectOption(label=f"{i + 1}") for i in range(25)]
        super().__init__(placeholder="What is X",max_values=1,min_values=1,options=options)

    async def callback(self, interaction: discord.Interaction):
        if int(self.values[0]) == self.ans:
            if self.user in freeMessages:
                i = 0
                while int(freeMessages[self.user]) < 10 and i < 5:
                    freeMessages[self.user] += 1
                    i += 1
            else:
                freeMessages.update({self.user:5})
            return await interaction.response.edit_message(content = "Huh, I guess you can be smart sometimes, i'll give you 5 free messages (max of 10)")
        else:
            return await interaction.response.edit_message(content = "Ha, you're dumb just like I thought. Now get back to studying")
class AnswerView(discord.ui.View):
    def __init__(self, ans, user, timeout = 100):
        super().__init__(timeout = timeout)
        self.add_item(Answer(ans, user))

# Functions
def between(min,max,num): #Check if a num is between min and max
    return min <= num <= max
def checksheet(TimeSheet, day, time): #Check if a time is in the sheet
    return any(between(i[0], i[1], time) for i in TimeSheet[day])
def convertTo24(time, half):
    hour = int(time.split(":")[0])
    min = time.split(":")[1]

    if half == "PM" and hour != 12:
        return f"{hour + 12}:{min}"
    elif half == "AM" and hour == 12:
        return f"0:{min}"
    else:
        return time
    
# Used to keep timer going on reminder
async def RemindUser(timeTo, yellMember):
    if timeTo > 0:
        await asyncio.sleep(timeTo)
        await yellMember.send(f"{yellMember.mention} GET TO CLASS BUDDY!!!! It's in 30 MINUTES")
    else:
        await yellMember.send(f"{yellMember.mention} GET TO CLASS BUDDY!!!! It's in {timeTo} MINUTES")
    
# Get text from image
async def getText (image):
    # Download the attachment as bytes
    image_bytes = await image.read()
    img = Image.open(io.BytesIO(image_bytes))
    
    return pytesseract.image_to_string(img)[:-1]

# Update timesheet file to store new time
async def TimeSheetToFile():
    sheetLine = ""
    with open(sheetsPath, 'w') as f:
        for user in range (len(TimeSheets)):
            for day in range (len(TimeSheets[user])):
                for classes in range (len(TimeSheets[user][day])):
                    sheetLine += f"{TimeSheets[user][day][classes][0]} {TimeSheets[user][day][classes][1]} {TimeSheets[user][day][classes][2]}," # Classses are seperated by commas ({start} {end} {name}, )
                if (len(TimeSheets[user][day])) >=   1:
                    f.write(sheetLine[:-1] + "\n") # Days are seperated with newlines
                else:
                    f.write("\n")
                sheetLine = ""
            f.write("New User\n") #Users are seperated with "New User"
async def NamesToFile():
    nameLine = ""
    with open(namesPath, 'w') as f:
        for user in range(len(Names)):
            nameLine += f"{Names[user]},"
        f.write(nameLine[:-1])
async def ChannelToFile():
    with open(channelPath, 'w') as f:
        for i in range(len(Guilds)):
            f.write(f"{Guilds[i]},{Channels[i]}\n")
async def FreeToFile():
    with open(freePath, 'w') as f:
        for user in freeMessages:
            f.write(f"{user},{freeMessages[user]}\n")




# Add a time to sheet (create one if none exists)
@client.tree.command(description = "Adds a time to your current timesheet. If a timesheet does not exist, creates one first", name = "add")
@app_commands.describe(weekday = "WeekDay that you would like to add the time to (In words)",starttime = "Starting time of the class in 24hour format seperated by : (ex: 1:59)",endtime = "Ending time of the class in 24hour format seperated by : (ex: 23:59)", classname = "The Name of your class (When using imageToSchedule names will be formatted like CIS*2500)")
async def add(interaction: discord.Interaction, weekday:str, starttime:str, endtime:str, classname:str = "No Name"):
    if (weekday.lower() in WeekDays): # Makes sure the user entered the correct weekday

        # if hour is 24 set to 0
        if starttime.split(":")[0] == "24":
            minuteString = starttime.split(":")[1]
            starttime = f"0:{minuteString}"
        if endtime.split(":")[0] == "24":
            minuteString = endtime.split(":")[1]
            endtime = f"0:{minuteString}"

        # Converts text input to numeric value
        date = WeekDays.index(weekday.lower())
        startnum = float(starttime.split(":")[0]) + float((int(starttime.split(":")[1])/60))
        endnum = float(endtime.split(":")[0]) + float((int(endtime.split(":")[1])/60))

        # Make sure the time is real (and the start and end times are not the same)
        if (float(starttime.split(":")[0]) < 0 or float(starttime.split(":")[0]) >= 24) or (float(endtime.split(":")[0]) < 0 or float(endtime.split(":")[0]) >= 24) or (float(starttime.split(":")[1]) < 0 or float(starttime.split(":")[1]) >= 60) or (float(endtime.split(":")[1]) < 0 or float(endtime.split(":")[1]) >= 60) or startnum == endnum:
            await interaction.response.send_message(f"Ummm ACTUALLY that's not a real time...",ephemeral = True)
            return

        # If user entered ending time before starting time switch
        if startnum > endnum:
            temp = startnum
            startnum = endnum
            endnum = temp

            tempWord = starttime
            starttime = endtime
            endtime = tempWord

        # Checks if user already has a TimeSheet if so, adds time to correct day on TimeSheet
        if str(interaction.user) in Names:
            # If that class intersects with another class stop it
            for times in TimeSheets[Names.index(str(interaction.user))][date]:
                if between(times[0],times[1],startnum) or between(times[0],times[1],endnum):
                    await interaction.response.send_message(f"Ok buddy, you already have a class at that time",ephemeral = True)
                    return

            # Add the timesheet & sort it
            TimeSheets[Names.index(str(interaction.user))][date].append([float(startnum), float(endnum), classname])
            TimeSheets[Names.index(str(interaction.user))][date] = sorted(TimeSheets[Names.index(str(interaction.user))][date],key=lambda x: (x[0]))
            
            # If the user entered a class name, include it in the message
            if classname != "No Name":
                await interaction.response.send_message(f"\nYeah, I Added the class {classname}: {starttime} - {endtime} on {weekday.capitalize()}",ephemeral = True)
            else:
                await interaction.response.send_message(f"\nYeah, I Added the time: {starttime} - {endtime} on {weekday.capitalize()}",ephemeral = True)
            
        else:
            # Creates time sheet for user if one does not exist
            message = ""
            Names.append(str(interaction.user))
            TimeSheets.append([[],[],[],[],[],[],[]])

            message += f"*Adjusts Glasses* I created a new time sheet for {str(interaction.user)}"

            # Update user file to store new user
            await NamesToFile()

            # Adds time to correct day on created TimeSheet & Sort it
            TimeSheets[Names.index(str(interaction.user))][date].append([float(startnum), float(endnum), classname])
            TimeSheets[Names.index(str(interaction.user))][date] = sorted(TimeSheets[Names.index(str(interaction.user))][date],key=lambda x: (x[0]))

            # If the user entered a class name, include it in the message
            if classname != "No Name":
                await interaction.response.send_message(message + f"\nYeah, I Added the class {classname}: {starttime} - {endtime} on {weekday.capitalize()}",ephemeral = True)
            else:
                await interaction.response.send_message(message + f"\nYeah, I Added the time: {starttime} - {endtime} on {weekday.capitalize()}",ephemeral = True)

        #Change text file to store updated Array
        await TimeSheetToFile()

    else: # Error handling for incorrect week spelling
        await interaction.response.send_message("Are you dumb? That's not a weekday",ephemeral = True)

# Remove a time from sheet
@client.tree.command(description = "Removes a time from your timesheet", name = "remove")
@app_commands.describe(weekday = "WeekDay that you would like to remove the time from (In words)",classname = "the Name of the class or the timeslot indicated with /schedule)")
async def remove(interaction: discord.Interaction, weekday:str, classname:str):
    
    if str(interaction.user) in Names: #Checks if user has a TimeSheet
        # Converts text input to floats
        Use = TimeSheets[Names.index(str(interaction.user))]

        if (weekday.lower() in WeekDays): # Make sure the user entered a correct weekday
            date = WeekDays.index(weekday.lower())

            if classname != "No Name" and any(classname in sublist for sublist in Use[date]):
                timeslot = 1
                for list in range (len(Use[date])):
                    if classname in Use[date][list][2]:
                        timeslot = list + 1
                        break
            elif classname.isdigit():
                timeslot = int(classname)
            else:
                await interaction.response.send_message("Hey buddy! That class doesn't exist!",ephemeral = True)
                return

            if (timeslot <= len(Use[date]) and timeslot > 0): # Make sure the timeslot exists

                # Find the written times (in order to post the time removed)
                hourS = math.floor(float(Use[date][int(timeslot) - 1][0]))
                minuteS = math.floor((float(Use[date][int(timeslot) - 1][0])%1)*60)
                hourE = math.floor(float(Use[date][int(timeslot) - 1][1]))
                minuteE = math.floor((float(Use[date][int(timeslot) - 1][1])%1)*60)
                
                # Remove the timeslot requested
                await interaction.response.send_message(f"ermm... this is awkward, I guess i'll remove the class from {hourS}:{str(minuteS).ljust(2,'0')} - {hourE}:{str(minuteE).ljust(2,'0')} on {str(weekday).capitalize()}",ephemeral = True)
                Use[date].pop(int(timeslot) - 1)

                #Change text file to store updated Array
                await TimeSheetToFile()

            else: # Error handling for non-existent timeslot
                await interaction.response.send_message("Hey buddy! That timeslot doesn't exist!",ephemeral = True)
        else: # Error handling for incorrect week spelling
            await interaction.response.send_message("Are you dumb? That's not a weekday",ephemeral = True)
    else: # Error handling for no time sheet
        await interaction.response.send_message("Listen buddy, You don't currently have a time sheet. Next time create one by adding a time with /add",ephemeral = True)

# Print schedule
@client.tree.command(description = "Prints the schedule of the user you selected", name = "schedule")
@app_commands.describe(person = "Mention the user you would like to check, default is yourself")
async def schedule(interaction: discord.Interaction, person: discord.User = None):
    
    # Set who to print the schedule of
    if person != None:
        check = str(person)
    else:
        check = str(interaction.user)

    if check in Names: # Checks if user has a TimeSheet
        CurSheet = TimeSheets[Names.index(check)] # Find correct TimeSheet to use
        schedule = ""
        schedule += f"----------{check}'s Schedule----------\n"

        # Loops through each day
        for day in range(len(CurSheet)):
            schedule += f"{WeekDays[day].capitalize()}:\n"
            for times in CurSheet[day]:

                # Get time in readable Format
                hourS = math.floor(float(times[0]))
                minuteS = round((float(times[0])%1)*60)
                hourE = math.floor(float(times[1]))
                minuteE = round((float(times[1])%1)*60)

                if times[2] != "No Name":
                    schedule += f"{times[2]}: {hourS}:{str(minuteS).ljust(2,'0')} - {hourE}:{str(minuteE).ljust(2,'0')}\n" # Add time to text
                else:
                    schedule += f"Slot {CurSheet[day].index(times) + 1}: {hourS}:{str(minuteS).ljust(2,'0')} - {hourE}:{str(minuteE).ljust(2,'0')}\n" # Add time to text
            schedule += "\n"

        await interaction.response.send_message(schedule,ephemeral = True)
    else: # Error handling for no TimeSheet
        await interaction.response.send_message(f"Listen buddy, {check} doesn't currently have a time sheet, tell them to add one with /add",ephemeral = True)

# Let user know how much time t'ill their next class
@client.tree.command(description = "Will tell you when the user's next class is in Days, Hours and Minutes", name = "next")
@app_commands.describe(person = "Mention the user you would like to check, default is yourself")
async def next(interaction: discord.Interaction, person: discord.User = None):

    # Chooses which user to check
    if person != None:
        check = str(person)
    else:
        check = str(interaction.user)
    
    # Create searching variables
    curTime = datetime.datetime.now(timezone).hour + (datetime.datetime.now(timezone).minute/60)
    dayTo = 0
    minTo = 0
    hourTo = 0

    if check in Names: # Checks if user has a TimeSheet
        CurSheet = TimeSheets[Names.index(check)]

        # The class is the same day
        for time in range(len(CurSheet[datetime.datetime.now(timezone).weekday()])): # Check each timeslot in the current day for a next class
            if CurSheet[datetime.datetime.now(timezone).weekday()][time][0] > curTime:
                nextClass = CurSheet[datetime.datetime.now(timezone).weekday()][time][0]
                dayTo = 0
                hourTo = int(nextClass) - int(curTime)
                
                if (nextClass % 1) >= (curTime % 1):
                    minTo = round((nextClass % 1) * 60) - round((curTime % 1) * 60)
                else:
                    if hourTo > 0:
                        hourTo -= 1
                    minTo = 60 - (round((curTime % 1) * 60) - round((nextClass % 1) * 60))
                
                await interaction.response.send_message(f"You should be in class like right now... It's only {hourTo} hours and {minTo} minutes away",ephemeral = True)
                return
            elif between(CurSheet[datetime.datetime.now(timezone).weekday()][time][0],CurSheet[datetime.datetime.now(timezone).weekday()][time][1],curTime):
                await interaction.response.send_message(f"You should be in class... right now. Wait t'ill the professor hears about this one",ephemeral = True)
                return
        
        for day in range(datetime.datetime.now(timezone).weekday() + 1, 7):
            for time in range(len(CurSheet[day])): # Check each timeslot (if they exist)
                nextClass = CurSheet[day][time][0]
                dayTo = day - datetime.datetime.now(timezone).weekday()

                if int(nextClass) >= int(curTime):
                    hourTo = int(nextClass) - int(curTime)
                else:
                    dayTo -= 1
                    hourTo = 24 - (int(curTime) - int(nextClass))
                
                if (nextClass % 1) >= (curTime % 1):
                    minTo = round((nextClass % 1) * 60) - round((curTime % 1) * 60)
                else:
                    if hourTo > 0:
                        hourTo -= 1
                    minTo = 60 - (round((curTime % 1) * 60) - round((nextClass % 1) * 60))

                await interaction.response.send_message(f"You should be in class like right now... It's only {dayTo} days, {hourTo} hours and {minTo} minutes away",ephemeral = True)
                return
        
        for day in range(datetime.datetime.now(timezone).weekday() + 1):
            for time in range(len(CurSheet[day])): # Check each timeslot (if they exist)
                nextClass = CurSheet[day][time][0]

                dayTo = 7 - (datetime.datetime.now(timezone).weekday() - day)

                if int(nextClass) >= int(curTime):
                    hourTo = int(nextClass) - int(curTime)
                else:
                    dayTo -= 1
                    hourTo = 24 - (int(curTime) - int(nextClass))
                
                if (nextClass % 1) >= (curTime % 1):
                    minTo = round((nextClass % 1) * 60) - round((curTime % 1) * 60)
                else:
                    if hourTo > 0:
                        hourTo -= 1

                    elif dayTo > 0:
                        dayTo -= 1
                        hourTo = 23
                    minTo = 60 - (round((curTime % 1) * 60) - round((nextClass % 1) * 60))

                await interaction.response.send_message(f"You should be in class like right now... It's only {dayTo} days, {hourTo} hours and {minTo} minutes away",ephemeral = True)
                return
                
        # TimeSheet exists but is empty
        await interaction.response.send_message(f"Erm... So {check} doesn't have any classes in their schedule right now, I would fix that if I were them buddy",ephemeral = True)

    else: # Error handling for no TimeSheet
        await interaction.response.send_message(f"Listen buddy, {check} doesn't currently have a time sheet",ephemeral = True)

# Clear the user's sheet
@client.tree.command(description = "Removes all times from your timesheet (does not delete the timesheet)",name = "clear")
async def clear(interaction: discord.Interaction):
    
    if str(interaction.user) in Names:

        # Remove all times from that user's timesheet
        CurSheet = TimeSheets[Names.index(str(interaction.user))]
        for day in range(len(CurSheet)):
            CurSheet[day].clear()

        #Change text file to store updated Array
        await TimeSheetToFile()

        await interaction.response.send_message("Wow buddy, why would you remove your schedule... classes are so fun! Ok... I'll do it",ephemeral = True)
    else:
        await interaction.response.send_message("Listen buddy, You don't currently have a time sheet. Next time create one by adding a time with $Add",ephemeral = True)

# Shut bot up
@client.tree.command(description = "Solve for x to gain 5 free messages, allowing you to send messages in class without repercussions", name = "shutup")
async def stop(interaction: discord.Interaction):
    
    # Create the equation
    ans = random.randint(1, 25)
    mult = random.randint(2, 45)
    add = random.randint(1, 100)

    view = AnswerView(ans, str(interaction.user))
    await interaction.response.send_message(f"Sorry I can't hear you, I only listen to people who can solve for x in:\n{mult}x + {add} = {(mult * ans) + add}", view=view, ephemeral = True)

# Tells the user how many "free" messages they have left
@client.tree.command(description = "Tells you how many messages during class until the bot can yell at the user", name = "free")
@app_commands.describe(person = "Mention the user you would like to check, default is yourself")
async def free(interaction: discord.Interaction, person: discord.User = None):
    if person != None:
        check = str(person)
    else:
        check = str(interaction.user)
    
    if check in freeMessages:
        await interaction.response.send_message(f"{check} has {freeMessages[check]} free messages, just wait",ephemeral = True)
    else:
        await interaction.response.send_message(f"I can yell at {check} whenever I want, no free messages for them",ephemeral = True)

# Lets admins choose what channel the bot will choose to yell at people in
@client.tree.command(description = "Select the channel that people will get yelled at in (only for admins of the server)", name = "yellchannel")
@app_commands.describe(chosenchannel = "The channel that you want the messages to be sent in")
@app_commands.checks.has_permissions(administrator=True) # Makes sure the user has administrator perms
async def yellChannel(interaction: discord.Interaction, chosenchannel: discord.TextChannel):
    # If the guild already has a channel chosenm change it
    if interaction.guild.id in Guilds:
        Channels[Guilds.index(interaction.guild.id)] = chosenchannel.id
    else: # Add the guild id and channel id to a list if the guild hasn't already been given a channel
        Guilds.append(interaction.guild.id)
        Channels.append(chosenchannel.id)

    # Update the text file to contain the new guild and channel id
    await ChannelToFile()
    
    await interaction.response.send_message(f"Changed channel that I will yell at people in to {chosenchannel.name}", ephemeral = True)

# Add Schedule from given image
@client.tree.command(description = "Automatically create your schedule from an image of your WebAdvisor schedule", name = "imagetoschedule")
@app_commands.describe(schedule = "The image of your schedule (PNG or JPEG)")
async def ScheduleFromImage(interaction: discord.Interaction, schedule: discord.Attachment): 
    text = await getText(schedule)
    lines = text.split("\n")

    i = 0
    date = None

    name = None
    classNames = []
    namesUsed = 0

    while i < len(lines):
        # Ignore all exams, DE classes, dates (/) or empty lines
        if "EXAM" in lines[i] or "Distance Education" in lines[i] or "/" in lines[i] or not lines[i]:
            i += 1 
        # If the line is a class code add it to a list of class codes (to be stored for later)
        elif "*" in lines[i]:
            classNames.append(re.sub("[a-z]", "", lines[i].split("*")[0] + "*" + lines[i].split("*")[1])) # Remove all non-uppercase letters (reading errors)
            i += 1
        # If it is a Lecture or Lab add it
        elif "LEC" in lines[i] or "LAB" in lines[i]:
            use = lines[i].split(" ") # Get each piece of information

            if "LEC" in lines[i]: # If it's a lecture set the name to the class code assosciated with that positio
                name = classNames[namesUsed] + " LEC"
                namesUsed += 1
            else: # If it's a lab set the name to the same as the previous (the lecture)
                name = classNames[namesUsed - 1] + " LAB"

            for day in range(len(use[1])): # Go through each day

                # Convert the letter to the actual date
                match(use[1][day]):
                    case "M": date = "Monday"
                    case "T": 
                        if day != len(use[1]) - 1 and use[1][day + 1] == "h":
                            date = "Thursday"
                        else:
                            date = "Tuesday"
                    case "W": date = "Wednesday"
                    case "F": date = "Friday"

                # If it's not a h (Thursdays) same time to timesheet
                if use[1][day] != "h":
                    await add(interaction, date, convertTo24(use[2],use[3]), convertTo24(use[5],use[6]), name)

            i += 1
        else:
            i += 1

# Remind the person of their next class 30 minutes before it starts
@client.tree.command(description = "Notify the user of their next class 30 minutes before it begins", name = "remindme")
@app_commands.describe(person = "The user who should be notified of their next class")
async def RemindMe(interaction: discord.Interaction, person: discord.User = None): 
    
    if person is None:
        check = str(interaction.user)
    else:
        check = str(person)

    # Create searching variables
    curTime = datetime.datetime.now(timezone).hour + (datetime.datetime.now(timezone).minute/60)
    dayTo = 0
    minTo = 0
    hourTo = 0

    foundTime = False

    if check in Names: # Checks if user has a TimeSheet
        CurSheet = TimeSheets[Names.index(check)]

        # The class is the same day
        for time in range(len(CurSheet[datetime.datetime.now(timezone).weekday()])): # Check each timeslot in the current day for a next class
            if CurSheet[datetime.datetime.now(timezone).weekday()][time][0] >= curTime:
                nextClass = CurSheet[datetime.datetime.now(timezone).weekday()][time][0]
                dayTo = 0
                hourTo = int(nextClass) - int(curTime)
                
                if (nextClass % 1) >= (curTime % 1):
                    minTo = round((nextClass % 1) * 60) - round((curTime % 1) * 60)
                else:
                    if hourTo > 0:
                        hourTo -= 1
                    minTo = 60 - (round((curTime % 1) * 60) - round((nextClass % 1) * 60))
                
                foundTime = True
        
        if not foundTime:
            for day in range(datetime.datetime.now(timezone).weekday() + 1, 7):
                for time in range(len(CurSheet[day])): # Check each timeslot (if they exist)
                    nextClass = CurSheet[day][time][0]
                    dayTo = day - datetime.datetime.now(timezone).weekday()

                    if int(nextClass) >= int(curTime):
                        hourTo = int(nextClass) - int(curTime)
                    else:
                        dayTo -= 1
                        hourTo = 24 - (int(curTime) - int(nextClass))
                    
                    if (nextClass % 1) >= (curTime % 1):
                        minTo = round((nextClass % 1) * 60) - round((curTime % 1) * 60)
                    else:
                        if hourTo > 0:
                            hourTo -= 1
                        minTo = 60 - (round((curTime % 1) * 60) - round((nextClass % 1) * 60))
                    
                    foundTime = True
        
        if not foundTime:
            for day in range(datetime.datetime.now(timezone).weekday() + 1):
                for time in range(len(CurSheet[day])): # Check each timeslot (if they exist)
                    nextClass = CurSheet[day][time][0]

                    dayTo = 7 - (datetime.datetime.now(timezone).weekday() - day)

                    if int(nextClass) >= int(curTime):
                        hourTo = int(nextClass) - int(curTime)
                    else:
                        dayTo -= 1
                        hourTo = 24 - (int(curTime) - int(nextClass))
                    
                    if (nextClass % 1) >= (curTime % 1):
                        minTo = round((nextClass % 1) * 60) - round((curTime % 1) * 60)
                    else:
                        if hourTo > 0:
                            hourTo -= 1

                        elif dayTo > 0:
                            dayTo -= 1
                            hourTo = 23
                        minTo = 60 - (round((curTime % 1) * 60) - round((nextClass % 1) * 60))
                    
                    foundTime = True
        
        if not foundTime:
            await interaction.response.send_message(f"Listen buddy, {check}'s schedule is empty... they should fix that",ephemeral = True)
            return
        
        timeTo = (dayTo * 86400) + (hourTo * 3600) + (minTo * 60)

        if person is None:
            yellMember = interaction.user
        else:
            yellMember = person

        await interaction.response.send_message(f"I'll send them a dm when they should get to class buddy",ephemeral = True)
        await RemindUser(timeTo, yellMember)

    else: # Error handling for no TimeSheet
        await interaction.response.send_message(f"Listen buddy, {check} doesn't currently have a time sheet",ephemeral = True)
        
# On message Events
@client.event
async def on_message(message):
    # No looping (Does not check own messages)
    if message.author == client.user:
        return
    
    # Check if the user has a class when a message is sent
    elif message.author.name in Names:
        # Get current time & day
        day = datetime.datetime.now(timezone).weekday()
        time = datetime.datetime.now(timezone).hour + (datetime.datetime.now(timezone).minute/60)
        Sheet = TimeSheets[Names.index(message.author.name)]

        # Check if user currently has class, if so yell at them
        if checksheet(Sheet,day,time):
            # If the user has free messages, decrease by one (remove if they have no more)
            if message.author.name in freeMessages and freeMessages[message.author.name] > 0:
                freeMessages[message.author.name] -= 1
                if freeMessages[message.author.name] == 0:
                    freeMessages.pop(message.author.name)

                # Update file
                await FreeToFile()
            else:
                # If the guild has a chosen channel (and that channel exists) yell in that channel
                if message.guild.id in Guilds and client.get_channel(Channels[Guilds.index(message.guild.id)]) != None:
                    channel = client.get_channel(Channels[Guilds.index(message.guild.id)])
                    await channel.send(f"{message.author.mention} UMMM!! I don't think you are supposed to be talking here, pay attention to class mister! :point_up: :nerd: {message.jump_url}")
                # Yell in the channel the message was sent to (inform the mods to use /yellchannel to choose a specifies channel)
                else:
                    await message.reply(f"{message.author.mention} UMMM!! I don't think you are supposed to be talking here, pay attention to class mister! :point_up: :nerd:\n(If you want to change the channel this message is sent in, use the /yellchannel command... MODS)")
                

    await client.process_commands(message)

# Runs the bot
secret = os.getenv("DISCORD_SECRET")
client.run(secret)