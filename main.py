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
@commands.has_role('Leaderboard')
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
@commands.has_role('Leaderboard')
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
async def enable_update(ctx, name_lb, chan_id):
	leaderboard_id = get_id_leaderboard(name_lb, ctx.guild.id)
	
	if leaderboard_id == -1:
		await ctx.send("The leaderboard does not exist.")
		return
		
	c = db.cursor()
	c.execute(''' UPDATE Leaderboard SET chan_id=?, to_update=1 WHERE name = ? AND id_server = ? ''', (chan_id, name_lb, ctx.guild.id))
	res = c.fetchone()
	c.close()
	
	await ctx.send("Update enabled for " + name_lb)
	
@bot.command()
async def disable_update(ctx, name_lb):
	leaderboard_id = get_id_leaderboard(name_lb, ctx.guild.id)
	
	if leaderboard_id == -1:
		await ctx.send("The leaderboard does not exist.")
		return
		
	c = db.cursor()
	c.execute(''' UPDATE Leaderboard SET to_update=0 WHERE name = ? AND id_server = ? ''', (name_lb, ctx.guild.id))
	res = c.fetchone()
	c.close()
	
	await ctx.send("Update disabled for " + name_lb)
	
@bot.command()
@commands.has_role('Leaderboard')
async def vote_for(ctx, name_lb, entry, score):
	users_mentions = ctx.message.mentions
	if not users_mentions:
		await ctx.send("You must give a user by mentionning him/her.")
		return
	
	await utility_vote(ctx, name_lb, entry, score, users_mentions[0].id)
	
@bot.command()
async def vote(ctx, name_lb, entry, score):
	await utility_vote(ctx, name_lb, entry, score, ctx.message.author.id)

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

@bot.command()
async def show(ctx, name_lb):
	await utility_show(ctx, name_lb, ctx.guild.id)
	

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
		create_database()
	
	c.close()	
	
@bot.event
async def on_command_error(ctx, error):
	if isinstance(error, commands.CommandNotFound):
		await ctx.send('Unknown command.', delete_after=3)
		return
	elif isinstance(error, commands.CheckFailure):
		await ctx.send("You're not authorized to execute this command.")
		return 
	elif isinstance(error, commands.MissingRequiredArgument):
		await ctx.send("Missing arguments. !help for display help")
		return
	raise error
	
@bot.command()
async def ping(ctx):
	await ctx.message.delete()
	await ctx.send('Yup, I\'m awake.', delete_after=5)

	
#### Utilities functions ####

async def utility_vote(ctx, name_lb, entry, score, id_member):	
	try:
		score = int(score)
	except:
		await ctx.send("Score (third argument) must be a number.")
		return
		
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
		
	chan_update = bot.get_channel(get_chan_update(name_lb, ctx.guild.id))
	if chan_update:
		await utility_show(chan_update, name_lb, ctx.guild.id)

async def utility_show(chan, name_lb, guild_id):
	leaderboard_id = get_id_leaderboard(name_lb, guild_id)
	
	if leaderboard_id == -1:
		await chan.send("The leaderboard does not exist.")
		return
		
	c = db.cursor()
	c.execute(''' SELECT E.id, E.name, AVG(V.score) FROM Entry AS E
				  JOIN Vote as V ON V.id_entry = E.id
				  WHERE E.id_leaderboard = ?
				  GROUP BY E.name ''', (leaderboard_id,))
	
	# ID, name, average score
	entries = c.fetchall()
	votes = {}
	for entry in entries:
		c.execute(''' SELECT M.id, V.score FROM Member as M
					  JOIN Vote as V ON V.id_member = M.id
					  JOIN Entry as E ON E.id = V.id_entry
					  WHERE E.id_leaderboard = ? AND E.id = ? ''', (leaderboard_id, entry[0]))
		votes[entry[1]] = c.fetchall()
	
	#Sort by score
	entries = sorted(entries, key=lambda entry: entry[2], reverse=True)
	leaderboard = ""

	#Format for discord messages
	i = 1
	for entry in entries:
	
		#If mention failed (if the member left the server) the function crashes
		vote_by_member = ' - '.join((lambda vote : [bot.get_user(v[0]).mention + " " + str(v[1]) for v in vote])(votes[entry[1]]))
		leaderboard += "`" + str(i) + ".` " + entry[1] + " " + str(entry[2]) + " \|\| " + vote_by_member + "\n"
		i += 1
	
	embed = discord.Embed(title=name_lb, type='rich', color=discord.Color.green(), description=leaderboard)
	await chan.send(embed=embed)

def create_database():
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
		
def get_chan_update(name_lb, guild_id):
	c = db.cursor()
	c.execute(''' SELECT to_update, chan_id FROM Leaderboard WHERE name = ? AND id_server = ? ''', (name_lb, guild_id))
	res = c.fetchone()
	c.close()
	
	# res -> (to_update, chan_id)
	if res[0] != 0:
		return res[1]
	else :
		return None
	
	
bot.run(BOT_TOKEN)
