import logging
from pathlib import Path

import discord
from discord.ext import commands
from google import genai
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from ..books import model

_playlist_prompt = """You are a character from {book_title} by {book_author}. Create a playlist of five songs/pieces that reflect your personality, experiences, and worldview. Choose songs that you would realistically listen to, or that capture the themes, emotions, and struggles in your life. For each song, give a short explanation (1–2 sentences) in your own voice, describing why it fits you or your story. Keep the tone consistent with your character’s personality and speaking style. Format the result as a clear, numbered playlist. P.S. less than 5000 characters."""

_discussion_prompt = """"You are a character from {book_title} by {book_author}. Imagine you are sitting in on our book club. Write 5–7 discussion questions or prompts that you would bring up, written in your own voice and perspective. The topics should reflect your personality, values, biases, and experiences. Make them open-ended, encouraging readers to reflect, debate, and connect with the story. Stay true to how you would actually speak or think, even if your tone is humorous, tragic, arrogant, naive, or wise. P.S. less than 5000 characters."""


# TODO: Clean up the code and move it to a separate service file.
class GenAI(commands.Cog):
    """Separate Cog for GenAI stuff to keep it in one place."""

    def __init__(self, bot: commands.Bot, engine: Engine):
        try:
            # Load Gemini API key from file
            api_key_file = Path(".gemini-api-key")
            if not api_key_file.exists():
                raise FileNotFoundError(
                    "Missing .gemini-api-key file with your Gemini API token."
                )

            with api_key_file.open("r", encoding="utf-8") as f:
                api_key = f.read().strip()
            self.client = genai.Client(api_key=api_key)
        except Exception as e:
            logging.warning(f"Error loading Gemini API key: {e}")
        self.bot = bot
        self.engine = engine
        super().__init__()

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """Event handler for when the bot is ready."""
        logging.info("GenAI Cog is ready.")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def playlist(self, ctx: commands.Context):
        try:
            logging.info("Generating playlist...")
            if self.client is None:
                embed = discord.Embed(
                    title="❌ Gemini API Error",
                    description="Gemini API client is not initialized.",
                    color=discord.Color.red(),
                )
                await ctx.send(embed=embed)
                return
            with Session(self.engine) as session:
                book_club = session.get(model.BookClub, ctx.channel.id)
                if not book_club:
                    embed = discord.Embed(
                        title="📚 Book Club Not Found",
                        description="Book club not found.",
                        color=discord.Color.orange(),
                    )
                    await ctx.send(embed=embed)
                    return
                logging.info(
                    f"Generating playlist for book: {book_club.book.title} by {book_club.book.author}"
                )
                await ctx.send("Generating playlist, please wait...")
                response = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=_playlist_prompt.format(
                        book_title=book_club.book.title,
                        book_author=book_club.book.author,
                    ),
                )
                logging.info(f"Response from Gemini: {response.text}")
                embed = discord.Embed(
                    title="🎶 Recommended Playlist 🎶",
                    description=response.text,
                    color=discord.Color.purple(),
                )
                await ctx.send(embed=embed)
        except:
            logging.exception("Error generating playlist")
            embed = discord.Embed(
                title="❌ Error",
                description="An error occurred while generating the playlist.",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def discussion(self, ctx: commands.Context):
        try:
            logging.info("Generating discussion prompts...")
            if self.client is None:
                embed = discord.Embed(
                    title="❌ Gemini API Error",
                    description="Gemini API client is not initialized.",
                    color=discord.Color.red(),
                )
                await ctx.send(embed=embed)
                return
            with Session(self.engine) as session:
                book_club = session.get(model.BookClub, ctx.channel.id)
                if not book_club:
                    embed = discord.Embed(
                        title="📚 Book Club Not Found",
                        description="Book club not found.",
                        color=discord.Color.orange(),
                    )
                    await ctx.send(embed=embed)
                    return
                logging.info(
                    f"Generating discussion prompts for book: {book_club.book.title} by {book_club.book.author}"
                )
                await ctx.send("Generating discussion prompts, please wait...")
                response = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=_discussion_prompt.format(
                        book_title=book_club.book.title,
                        book_author=book_club.book.author,
                    ),
                )
                logging.info(f"Response from Gemini: {response.text}")
                embed = discord.Embed(
                    title="💬 Discussion Prompts 💬",
                    description=response.text,
                    color=discord.Color.purple(),
                )
                await ctx.send(embed=embed)
        except:
            logging.exception("Error generating discussion prompts")
            embed = discord.Embed(
                title="❌ Error",
                description="An error occurred while generating the discussion prompts.",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)
