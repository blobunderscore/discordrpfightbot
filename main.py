import discord
from discord.ext import commands
from discord import app_commands
import random
import os

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="/", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print("Synced slash commands.")

bot = MyBot()

# Simple in-memory battle tracker
active_duels = {}

class DuelRequestView(discord.ui.View):
    def __init__(self, challenger: discord.Member, opponent: discord.Member):
        super().__init__(timeout=60)
        self.challenger = challenger
        self.opponent = opponent

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.opponent:
            await interaction.response.send_message("You're not the one being challenged!", ephemeral=True)
            return

        # Start the duel
        duel_id = f"{self.challenger.id}-{self.opponent.id}"
        active_duels[duel_id] = {
            "players": [self.challenger, self.opponent],
            "hp": {self.challenger.id: 100, self.opponent.id: 100},
            "turn": 0,
            "dodge": {self.challenger.id: False, self.opponent.id: False}
        }

        await interaction.response.edit_message(content=f"⚔️ {self.challenger.mention} vs {self.opponent.mention} — Let the duel begin!", view=None)
        await interaction.followup.send(f"It's {self.challenger.mention}'s turn!", view=BattleView(self.challenger, self.opponent, duel_id))

    @discord.ui.button(label="Decline", style=discord.ButtonStyle.danger)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.opponent:
            await interaction.response.send_message("You're not the one being challenged!", ephemeral=True)
            return

        await interaction.message.edit(content="❌ Duel declined.", view=None)
        await interaction.response.send_message("Maybe next time!", ephemeral=True)

class BattleView(discord.ui.View):
    def __init__(self, player: discord.Member, opponent: discord.Member, duel_id: str):
        super().__init__(timeout=60)
        self.player = player
        self.opponent = opponent
        self.duel_id = duel_id

    def check_turn(self):
        duel = active_duels[self.duel_id]
        return duel["players"][duel["turn"]] == self.player

    def next_turn(self):
        duel = active_duels[self.duel_id]
        duel["turn"] = 1 - duel["turn"]
        next_player = duel["players"][duel["turn"]]
        return next_player

    def apply_damage(self, target_id: int, damage: int):
        duel = active_duels[self.duel_id]
        if duel["dodge"].get(target_id):
            duel["dodge"][target_id] = False
            return 0  # dodged!
        duel["hp"][target_id] -= damage
        return damage

    async def resolve_turn(self, interaction: discord.Interaction):
        duel = active_duels[self.duel_id]
        hp = duel["hp"]
        p1, p2 = duel["players"]
        if hp[p1.id] <= 0 or hp[p2.id] <= 0:
            winner = p1 if hp[p2.id] <= 0 else p2
            await interaction.response.send_message(f"💥 {winner.mention} wins the duel!", view=None)
            del active_duels[self.duel_id]
        else:
            next_player = self.next_turn()
            await interaction.response.send_message(f"It's now {next_player.mention}'s turn!", view=BattleView(next_player, self.player, self.duel_id))

    @discord.ui.button(label="Punch", style=discord.ButtonStyle.primary)
    async def punch(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.check_turn():
            await interaction.response.send_message("It's not your turn!", ephemeral=True)
            return
        damage = random.randint(10, 20)
        target = self.opponent
        actual = self.apply_damage(target.id, damage)
        await interaction.followup.send(f"👊 {self.player.mention} punched {target.mention} for {actual} damage!")
        await self.resolve_turn(interaction)

    @discord.ui.button(label="Kick", style=discord.ButtonStyle.primary)
    async def kick(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.check_turn():
            await interaction.response.send_message("It's not your turn!", ephemeral=True)
            return
        damage = 5
        target = self.opponent
        actual = self.apply_damage(target.id, damage)
        await interaction.followup.send(f"🦵 {self.player.mention} kicked {target.mention} for {actual} damage!")
        await self.resolve_turn(interaction)

    @discord.ui.button(label="Dodge", style=discord.ButtonStyle.secondary)
    async def dodge(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.check_turn():
            await interaction.response.send_message("It's not your turn!", ephemeral=True)
            return
        dodge_success = random.random() < 0.5
        duel = active_duels[self.duel_id]
        duel["dodge"][self.player.id] = dodge_success
        msg = f"🌀 {self.player.mention} is preparing to dodge the next attack!" if dodge_success else f"😵 {self.player.mention} tried to dodge but failed!"
        await interaction.followup.send(msg)
        await self.resolve_turn(interaction)

    @discord.ui.button(label="Block", style=discord.ButtonStyle.secondary)
    async def block(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.check_turn():
            await interaction.response.send_message("It's not your turn!", ephemeral=True)
            return
        duel = active_duels[self.duel_id]
        # Reduce next attack's damage
        duel["dodge"][self.player.id] = "block"
        await interaction.followup.send(f"🛡️ {self.player.mention} is blocking the next attack!")
        await self.resolve_turn(interaction)

@bot.tree.command(name="duel", description="Challenge someone to a duel!")
@app_commands.describe(opponent="The person you want to duel")
async def duel(interaction: discord.Interaction, opponent: discord.Member):
    if interaction.user.id == opponent.id:
        await interaction.response.send_message("You can't duel yourself!", ephemeral=True)
        return
    await interaction.response.send_message(
        f"{interaction.user.mention} is challenging {opponent.mention} to a duel!",
        view=DuelRequestView(interaction.user, opponent)
    )

bot.run(os.getenv("DISCORD_TOKEN"))
