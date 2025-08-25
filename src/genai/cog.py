import logging
from pathlib import Path

import discord
from discord.ext import commands
from google import genai
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from ..books import model

_playlist_prompt = """Recommend a playlist of five songs/pieces based on the book {book_title} by {book_author}. Recommend them in the voice of one of the character's of the book and use bullet points for each song and an explanation of why you recommend them. Keep the number of characters in your response to less than 5000 characters."""


class GenAI(commands.Cog):
    """Separate Cog for GenAI stuff to keep it in one place."""

    def __init__(self, bot: commands.Bot, engine: Engine):
        try:
            # Load Gemini API key from file
            api_key_file = Path(".gemini-api-key")
            if not api_key_file.exists():
                raise FileNotFoundError("Missing .gemini-api-key file with your Gemini API token.")

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
            if self.client is None:
                embed = discord.Embed(
                    title="❌ Gemini API Error",
                    description="Gemini API client is not initialized.",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)
                return
            with Session(self.engine) as session:
                book_club = session.get(model.BookClub, ctx.channel.id)
                if not book_club:
                    embed = discord.Embed(
                        title="📚 Book Club Not Found",
                        description="Book club not found.",
                        color=discord.Color.orange()
                    )
                    await ctx.send(embed=embed)
                    return
                logging.info(f"Generating playlist for book: {book_club.book.title} by {book_club.book.author}")
                await ctx.send("Generating playlist, please wait...")
                response = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=_playlist_prompt.format(
                        book_title=book_club.book.title,
                        book_author=book_club.book.author,
                    ),
                )
                # Add color and emojis to the embed
                embed = discord.Embed(
                    title="🎶 Recommended Playlist 🎶",
                    description=response.text,
                    color=discord.Color.purple()
                )
                embed.set_footer(text="Enjoy your musical journey! ✨")
                await ctx.send(embed=embed)
        except:
            logging.exception("Error generating playlist")
            embed = discord.Embed(
                title="❌ Error",
                description="An error occurred while generating the playlist.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
