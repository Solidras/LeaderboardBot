import os
import asyncio
import discord
import random
import sqlite3

from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')

bot = commands.Bot(command_prefix='!')

db = sqlite3.connect('./database.db')

#### Bot commands ####

@bot.command()
async def create_leaderboard(ctx, name):
	c = db.cursor()
	
	create_guild_if_not_exist(ctx.guild.id)
	try:
		c.execute(''' INSERT INTO Leaderboard (name, id_server) VALUES (?, ?) ''', (name, ctx.guild.id))
		db.commit()
		await ctx.send("Leaderboard " + name + " created")
	except sqlite3.Error:
		await ctx.send("ERROR : Leaderboard " + name + " already exists")	
	
	c.close()
	
@bot.command()
async def add_entry(ctx, name_lb, entry):

	leaderboard_id = get_id_leaderboard(name_lb, ctx.guild.id)
	
	if leaderboard_id == -1:
		await ctx.send("The leaderboard does not exist.")
		return
		
	c = db.cursor()
	try:
		c.execute(''' INSERT INTO Entry (name, id_leaderboard) VALUES (?, ?) ''', (entry, leaderboard_id))
		db.commit()
		await ctx.send("Entry " + entry + " created")
	except sqlite3.Error:
		await ctx.send("ERROR : Entry " + entry + " already exists")
	
	
@bot.command()
async def vote(ctx, name_lb, entry, score):
	id_member = ctx.message.author.id
	
	create_member_if_not_exist(id_member)
	
	leaderboard_id = get_id_leaderboard(name_lb, ctx.guild.id)
	
	if leaderboard_id == -1:
		await ctx.send("The leaderboard does not exist.")
		return
		
	entry_id = get_id_entry(entry, leaderboard_id)
	
	if entry_id == -1:
		await ctx.send("The entry does not exist.")
		return
		
	if not (0 <= score <= 10):
		await ctx.send("The score must be between 0 and 10.")
		return
	
	c = db.cursor()
	try:
		c.execute(''' INSERT OR REPLACE INTO Vote (id_member, id_entry, score) 
					  VALUES (?, ?, ?) ''', (id_member, entry_id, score))
		db.commit()
		await ctx.send("Vote saved!")
	except sqlite3.Error:
		await ctx.send("Error during voting.")
		print(type(e).__name__)

@bot.command()
async def show_all_leaderboards(ctx):
	leaderboard = []
	
	c = db.cursor()
	c.execute(''' SELECT name FROM Leaderboard WHERE id_server = ? ''', (ctx.guild.id,))
	for lb in c:
		leaderboard.append(lb[0])
	c.close
	
	embed = discord.Embed(title='List of leaderboards', type='rich', color=discord.Color.green(), description='\n'.join(leaderboard))
	await ctx.send(embed=embed)
	

#### Bot event handlers ####

@bot.event
async def on_ready():
	print('Logged in as')
	print(bot.user.name)
	print(bot.user.id)
	print('------')
	
	c = db.cursor()
	c.execute(''' SELECT count(name) FROM sqlite_master WHERE type='table' AND name='Server' ''')

	#if the count is 0, then table does not exist
	if c.fetchone()[0]!=1:
		await create_database()
	
	c.close()
	
	
@bot.event
async def on_command_error(ctx, error):
	if isinstance(error, commands.CommandNotFound):
		await ctx.send('Unknown command.', delete_after=3)
		return
	raise error
	
@bot.command()
async def ping(ctx):
	await ctx.message.delete()
	await ctx.send('Yup, I\'m awake.', delete_after=5)

	
#### Utilities functions ####

async def create_database():
	query = open('create_database.sql', 'r').read()
	
	c = db.cursor()
	c.executescript(query)
	db.commit()
	c.close()
	
def create_guild_if_not_exist(id):
	c = db.cursor()
	c.execute(''' INSERT OR IGNORE INTO Server(id) VALUES (?) ''', (id,))
	db.commit()
	c.close()
	
def create_member_if_not_exist(id):
	c = db.cursor()
	c.execute(''' INSERT OR IGNORE INTO Member(id) VALUES (?) ''', (id,))
	db.commit()
	c.close()

# Return id of the leaderboard. -1 if not found.
def get_id_leaderboard(name, guild_id):
	c = db.cursor()
	c.execute(''' SELECT id FROM Leaderboard WHERE name = ? AND id_server = ? ''', (name, guild_id))
	res = c.fetchone()
	c.close()
	
	if res:
		return res[0]
	else:
		return -1
	
def get_id_entry(name, leaderboard_id):
	c = db.cursor()
	c.execute(''' SELECT * FROM Entry WHERE name = ? AND id_leaderboard = ? ''', (name, leaderboard_id))
	res = c.fetchone()
	c.close()
	
	if res:
		return res[0]
	else:
		return -1
	
	
bot.run(BOT_TOKEN)
