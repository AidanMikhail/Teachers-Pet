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
import numpy as np
import easyocr


# Bot Setup
reader = easyocr.Reader(['en'])  
schedule = "C:\\Users\\aidan\\OneDrive\\Desktop\\Discord_bot\\Screenshot 2025-09-08 155954.png"

# Get text from image
async def getText(image):
    # Open image from file path
    img = Image.open(image).convert("RGB")

    # Run OCR
    results = reader.readtext(np.array(img), detail=0)

    # Join detected text into lines
    return "\n".join(results)

def convertTo24(time, half):
    time = time.replace(".", ":")  # Convert 11.30 → 11:30
    hour, minute = map(int, time.split(":"))

    if half == "PM" and hour != 12:
        hour += 12
    elif half == "AM" and hour == 12:
        hour = 0

    return f"{hour}:{minute:02d}"

async def maintfunc():
    i = 0
    date = None

    name = None
    classNames = []
    namesUsed = 0

    text = await getText(schedule)
    lines = text.split("\n")

    while i < len(lines):
        # print(lines[i])
        # Ignore all exams, DE classes, dates (/) or empty lines
        if "EXAM" in lines[i] or "Distance Education" in lines[i] or "/" in lines[i] or not lines[i]:
            i += 1 
        # If the line is a class code add it to a list of class codes (to be stored for later)
        elif "*" in lines[i]:
            classNames.append(re.sub("[a-z]", "", lines[i].split("*")[0] + "*" + lines[i].split("*")[1])) # Remove all non-uppercase letters (reading errors)
            i += 1
        # If it is a Lecture or Lab add it
        elif "LEC" in lines[i] and len(classNames) == namesUsed + 1:
            use = lines[i].split(" ") # Get each piece of information
            name = classNames[namesUsed] + " LEC"
            namesUsed += 1

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
                try:
                    if use[1][day] != "h":
                        print(f"{date}, {convertTo24(use[2],use[3])} - {convertTo24(lines[i+1].split(' ')[0],lines[i+1].split(' ')[1])}, {name}")
                except:
                    pass

            i += 1
        elif "LAB" in lines[i] and len(classNames) == namesUsed:
            use = lines[i].split(" ")
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
                try:
                    if use[1][day] != "h":
                        print(f"{date}, {convertTo24(use[2],use[3])} - {convertTo24(lines[i+1].split(' ')[0],lines[i+1].split(' ')[1])}, {name}")
                except:
                    pass
            i += 1
        else:
            i += 1

if __name__ == "__main__":
    asyncio.run(maintfunc())