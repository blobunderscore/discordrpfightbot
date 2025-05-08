import os
import discord
import random
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True  # Needed for user mentions

bot = commands.Bot(command_prefix="!", intents=intents)

DUELS = {}  # Stores active duels


class DuelRequestView(discord.ui.View):
    def __init__(self, challenger: discord.User, opponent: discord.User):
        super().__init__(timeout=60)
        self.challenger = challenger
        self.opponent = opponent

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.opponent:
            await interaction.response.send_message("Only the challenged user can accept!", ephemeral=True)
            return

        await interaction.response.send_message("Duel accepted! Starting the battle...", ephemeral=False)
        view = BattleView(self.challenger, self.opponent)
        msg = await interaction.channel.send(f"⚔️ Battle between {self.challenger.mention} and {self.opponent.mention} begins!\nIt's {self.challenger.mention}'s turn!", view=view)
        view.message = msg

    @discord.ui.button(label="Decline", style=discord.ButtonStyle.danger)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.opponent:
            await interaction.response.send_message("Only the challenged user can decline!", ephemeral=True)
            return
        await interaction.response.send_message("Duel declined.")


class BattleView(discord.ui.View):
    def __init__(self, player: discord.User, opponent: discord.User):
        super().__init__(timeout=60)
        self.player = player
        self.opponent = opponent
        self.turn = player.id
        self.hp = {player.id: 100, opponent.id: 100}
        self.block = {player.id: False, opponent.id: False}
        self.dodge = {player.id: False, opponent.id: False}
        self.message = None

    def check_turn(self, interaction: discord.Interaction):
        return interaction.user.id == self.turn

    def switch_turn(self):
        self.turn = self.opponent.id if self.turn == self.player.id else self.player.id

    def apply_damage(self, target_id, amount):
        if self.dodge.get(target_id):
            self.dodge[target_id] = False
            return 0  # Dodged!

        if self.block.get(target_id):
            amount = int(amount * 0.65)
            self.block[target_id] = False

        self.hp[target_id] -= amount
        return amount

    async def check_winner(self, interaction: discord.Interaction):
        if self.hp[self.player.id] <= 0:
            await self.message.edit(content=f"💀 {self.player.mention} has been defeated! {self.opponent.mention} wins!", view=None)
            self.stop()
            return True
        elif self.hp[self.opponent.id] <= 0:
            await self.message.edit(content=f"💀 {self.opponent.mention} has been defeated! {self.player.mention} wins!", view=None)
            self.stop()
            return True
        return False

    async def resolve_turn(self, interaction: discord.Interaction):
        if await self.check_winner(interaction):
            return

        self.switch_turn()
        await self.message.edit(content=f"HP:\n{self.player.mention}: {self.hp[self.player.id]} ❤️\n{self.opponent.mention}: {self.hp[self.opponent.id]} ❤️\n\nIt's <@{self.turn}>'s turn!")

    @discord.ui.button(label="Punch", style=discord.ButtonStyle.primary)
    async def punch(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.check_turn(interaction):
            await interaction.response.send_message("It's not your turn!", ephemeral=True)
            return

        damage = random.randint(10, 20)
        target_id = self.opponent.id if interaction.user.id == self.player.id else self.player.id
        actual = self.apply_damage(target_id, damage)

        await interaction.response.send_message(f"👊 {interaction.user.mention} punched <@{target_id}> for {actual} damage!")
        await self.resolve_turn(interaction)

    @discord.ui.button(label="Kick", style=discord.ButtonStyle.primary)
    async def kick(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.check_turn(interaction):
            await interaction.response.send_message("It's not your turn!", ephemeral=True)
            return

        damage = 5
        target_id = self.opponent.id if interaction.user.id == self.player.id else self.player.id
        actual = self.apply_damage(target_id, damage)

        await interaction.response.send_message(f"🦵 {interaction.user.mention} kicked <@{target_id}> for {actual} damage!")
        await self.resolve_turn(interaction)

    @discord.ui.button(label="Block", style=discord.ButtonStyle.secondary)
    async def block(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.check_turn(interaction):
            await interaction.response.send_message("It's not your turn!", ephemeral=True)
            return

        self.block[interaction.user.id] = True
        await interaction.response.send_message(f"🛡️ {interaction.user.mention} is ready to block the next attack!")
        await self.resolve_turn(interaction)

    @discord.ui.button(label="Dodge", style=discord.ButtonStyle.secondary)
    async def dodge(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.check_turn(interaction):
            await interaction.response.send_message("It's not your turn!", ephemeral=True)
            return

        success = random.random() < 0.5
        if success:
            self.dodge[interaction.user.id] = True
            msg = f"💨 {interaction.user.mention} is ready to dodge the next attack!"
        else:
            msg = f"💨 {interaction.user.mention} tried to dodge but failed!"

        await interaction.response.send_message(msg)
        await self.resolve_turn(interaction)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands.")
    except Exception as e:
        print(f"Failed to sync commands: {e}")


@bot.tree.command(name="duel", description="Challenge someone to a duel!")
@app_commands.describe(opponent="The user to challenge")
async def duel(interaction: discord.Interaction, opponent: discord.User):
    if interaction.user.id == opponent.id:
        await interaction.response.send_message("You can't duel yourself!", ephemeral=True)
        return

    view = DuelRequestView(interaction.user, opponent)
    await interaction.response.send_message(f"{interaction.user.mention} has challenged {opponent.mention} to a duel!", view=view)


bot.run(os.getenv("DISCORD_TOKEN"))
