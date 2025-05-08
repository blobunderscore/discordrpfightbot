import discord
from discord.ext import commands
import random

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

active_duels = {}

class Duel:
    def __init__(self, user1, user2):
        self.user1 = user1
        self.user2 = user2
        self.hp = {user1.id: 100, user2.id: 100}
        self.turn = user1.id
        self.dodge_next = {user1.id: False, user2.id: False}

    def is_turn(self, user_id):
        return self.turn == user_id

    def switch_turn(self):
        self.turn = self.user1.id if self.turn == self.user2.id else self.user2.id

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}!')

@bot.slash_command(name="duel", description="Challenge someone to a duel!")
async def duel(ctx, opponent: discord.Member):
    if ctx.author.id == opponent.id:
        await ctx.respond("You can't duel yourself!", ephemeral=True)
        return

    view = AcceptDeclineView(ctx.author, opponent)
    await ctx.respond(f"{ctx.author.mention} is inviting {opponent.mention} to a duel!", view=view)

class AcceptDeclineView(discord.ui.View):
    def __init__(self, challenger, opponent):
        super().__init__(timeout=60)
        self.challenger = challenger
        self.opponent = opponent

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.success)
    async def accept(self, button, interaction):
        if interaction.user != self.opponent:
            await interaction.response.send_message("You're not the one being challenged!", ephemeral=True)
            return

        duel = Duel(self.challenger, self.opponent)
        active_duels[self.challenger.id] = duel
        active_duels[self.opponent.id] = duel

        await interaction.response.send_message(f"Duel started between {self.challenger.mention} and {self.opponent.mention}!\nIt's {self.challenger.mention}'s turn.", view=FightView(duel))

    @discord.ui.button(label="Decline", style=discord.ButtonStyle.danger)
    async def decline(self, button, interaction):
        if interaction.user != self.opponent:
            await interaction.response.send_message("You're not the one being challenged!", ephemeral=True)
            return
        await interaction.response.send_message("Duel declined.")

class FightView(discord.ui.View):
    def __init__(self, duel):
        super().__init__(timeout=None)
        self.duel = duel

    async def handle_turn(self, interaction, move):
        attacker = interaction.user
        defender = self.duel.user1 if self.duel.turn != self.duel.user1.id else self.duel.user2

        if not self.duel.is_turn(attacker.id):
            await interaction.response.send_message("It's not your turn!", ephemeral=True)
            return

        dmg = 0
        msg = ""

        if move == "punch":
            dmg = random.randint(10, 20)
            msg = f"{attacker.mention} punches and deals {dmg} damage!"
        elif move == "kick":
            dmg = 5
            msg = f"{attacker.mention} kicks and deals {dmg} damage!"
        elif move == "dodge":
            self.duel.dodge_next[attacker.id] = True
            msg = f"{attacker.mention} prepares to dodge the next attack!"
        elif move == "block":
            self.duel.dodge_next[attacker.id] = "block"
            msg = f"{attacker.mention} prepares to block the next attack!"

        if move in ["punch", "kick"]:
            if self.duel.dodge_next[defender.id] == True:
                if random.random() < 0.5:
                    dmg = 0
                    msg += f"\n{defender.mention} dodged the attack!"
                self.duel.dodge_next[defender.id] = False
            elif self.duel.dodge_next[defender.id] == "block":
                dmg = int(dmg * 0.65)
                msg += f"\n{defender.mention} blocked and reduced the damage to {dmg}!"
                self.duel.dodge_next[defender.id] = False

            self.duel.hp[defender.id] -= dmg

        if self.duel.hp[defender.id] <= 0:
            msg += f"\n{defender.mention} has been defeated! {attacker.mention} wins!"
            active_duels.pop(self.duel.user1.id, None)
            active_duels.pop(self.duel.user2.id, None)
            await interaction.response.edit_message(content=msg, view=None)
        else:
            self.duel.switch_turn()
            msg += f"\nNow it's {defender.mention}'s turn!"
            await interaction.response.edit_message(content=msg, view=FightView(self.duel))

    @discord.ui.button(label="Punch", style=discord.ButtonStyle.primary)
    async def punch(self, button, interaction):
        await self.handle_turn(interaction, "punch")

    @discord.ui.button(label="Kick", style=discord.ButtonStyle.secondary)
    async def kick(self, button, interaction):
        await self.handle_turn(interaction, "kick")

    @discord.ui.button(label="Dodge", style=discord.ButtonStyle.success)
    async def dodge(self, button, interaction):
        await self.handle_turn(interaction, "dodge")

    @discord.ui.button(label="Block", style=discord.ButtonStyle.danger)
    async def block(self, button, interaction):
        await self.handle_turn(interaction, "block")

import os
bot.run(os.getenv("DISCORD_TOKEN"))
