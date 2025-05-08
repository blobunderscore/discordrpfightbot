import discord
from discord.ext import commands
from discord import app_commands
import random
import os

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True  # Needed for user mentions

class DuelBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        self.duels = {}


    async def setup_hook(self):
        await self.tree.sync()

bot = DuelBot()

class DuelRequest(discord.ui.View):
    def __init__(self, challenger: discord.User, opponent: discord.User):
        super().__init__(timeout=30)
        self.challenger = challenger
        self.opponent = opponent

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.opponent.id:
            await interaction.response.send_message("Не тебя зовут, ходячий синдром восьмиклассника", ephemeral=True)
            return

        await interaction.message.edit(content="Дуэль принята!", view=None)
        await interaction.channel.send(
            f"Началась битва между {self.challenger.mention} и {self.opponent.mention}!"
        )
        battle_view = BattleView(self.challenger, self.opponent)
        bot.duels[interaction.channel.id] = battle_view
        await interaction.channel.send(
            f"Сейчас действует {battle_view.current_player.mention}!",
            view=battle_view
        )

    @discord.ui.button(label="Decline", style=discord.ButtonStyle.danger)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.opponent.id:
            await interaction.response.send_message("Не тебя зовут, ходячий синдром восьмиклассника", ephemeral=True)
            return
        await interaction.message.edit(content="Дуэль отменена, т.к. чел петух", view=None)

class BattleView(discord.ui.View):
    def __init__(self, p1: discord.User, p2: discord.User):
        super().__init__(timeout=60)
        self.players = {
            p1.id: {"user": p1, "hp": 100, "dodge": False},
            p2.id: {"user": p2, "hp": 100, "dodge": False}
        }
        self.turn_order = [p1.id, p2.id]
        self.current_turn = 0

    @property
    def current_player(self):
        return self.players[self.turn_order[self.current_turn]]["user"]

    @property
    def target_player(self):
        return self.players[self.turn_order[(self.current_turn + 1) % 2]]["user"]

    def switch_turn(self):
        self.current_turn = (self.current_turn + 1) % 2

    def end_battle(self):
        # Clean up stored battle
        for player in self.players.values():
            if player["user"]:
                channel_id = player["user"].dm_channel.id if player["user"].dm_channel else None
                if channel_id in bot.duels:
                    del bot.duels[channel_id]

        self.stop()

    async def process_turn(self, interaction: discord.Interaction, move: str):
        attacker = self.current_player
        defender = self.target_player
        atk = self.players[attacker.id]
        dfd = self.players[defender.id]

        msg = ""

        if move == "punch":
            dmg = random.randint(10, 20)
            if dfd["dodge"]:
                if random.random() < 0.5:
                    dmg = 0
                    msg = f"{defender.mention} увернулся от удара {attacker.mention}!"
                else:
                    msg = f"{attacker.mention} смог попасть по {defender.mention}!"
                dfd["dodge"] = False
            dfd["hp"] -= dmg
            if dmg > 0:
                msg = f"👊 {attacker.mention} ударил {defender.mention} и нанес {dmg} урона!"

        elif move == "kick":
            dmg = 5
            if dfd["dodge"]:
                if random.random() < 0.5:
                    dmg = 0
                    msg = f"{defender.mention} увернулся от удара ногой!"
                else:
                    msg = f"{attacker.mention} попал ударом ногой по {defender.mention}"
                dfd["dodge"] = False
            dfd["hp"] -= dmg
            if dmg > 0:
                msg = f"{attacker.mention} пнул {defender.mention} и нанес {dmg} урона!     "

        elif move == "dodge":
            atk["dodge"] = True
            msg = f"{attacker.mention} готовится увернуться от следующей атаки!"

        elif move == "block":
            atk["dodge"] = False  # reset dodge
            msg = f"🛡{attacker.mention} блокирует следующую атаку!"

        # Check for defeat
        if dfd["hp"] <= 0:
            await interaction.response.send_message(
                f"{defender.mention} проиграл бой! {attacker.mention} победил!", ephemeral=False
            )
            self.end_battle()
            return

        self.switch_turn()
        await interaction.response.send_message(msg, ephemeral=False)

        await interaction.channel.send(
            f"Сейчас атакует {self.current_player.mention}!",
            view=self
        )

    @discord.ui.button(label="Punch", style=discord.ButtonStyle.primary)
    async def punch(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.current_player.id:
            await interaction.response.send_message("Не твоя очередь, олух!", ephemeral=True)
            return
        await self.process_turn(interaction, "punch")

    @discord.ui.button(label="Kick", style=discord.ButtonStyle.primary)
    async def kick(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.current_player.id:
            await interaction.response.send_message("Не твоя очередь, олух!", ephemeral=True)
            return
        await self.process_turn(interaction, "kick")

    @discord.ui.button(label="Dodge", style=discord.ButtonStyle.secondary)
    async def dodge(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.current_player.id:
            await interaction.response.send_message("Не твоя очередь, олух!", ephemeral=True)
            return
        await self.process_turn(interaction, "dodge")

    @discord.ui.button(label="Block", style=discord.ButtonStyle.secondary)
    async def block(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.current_player.id:
            await interaction.response.send_message("Не твоя очередь, олух!", ephemeral=True)
            return
        await self.process_turn(interaction, "block")


@bot.tree.command(name="duel", description="Challenge another user to a duel!")
@app_commands.describe(opponent="The user you want to fight")
async def duel(interaction: discord.Interaction, opponent: discord.User):
    if opponent.id == interaction.user.id:
        await interaction.response.send_message("Я понимаю что ты ненавидишь себя, но резать вены я тебе не позволю.", ephemeral=True)
        return
    if interaction.channel.id in bot.duels:
        await interaction.response.send_message("На данный момент уже происходит дуэль!", ephemeral=True)
        return

    view = DuelRequest(interaction.user, opponent)
    await interaction.response.send_message(
        f"{interaction.user.mention} вызывает {opponent.mention} на битву!", view=view
    )

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    bot.run(os.getenv("DISCORD_TOKEN"))
