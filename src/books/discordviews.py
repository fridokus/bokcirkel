import discord
from ..result_types import Ok, Err


class BaseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=30)

    async def disable_buttons(self, interaction):
        for b in self.children:
            if isinstance(b, discord.ui.Button):
                b.disabled = True
        await interaction.response.edit_message(view=self)


class ApplyView(
    BaseView
):  # Create a class called MyView that subclasses discord.ui.View
    def __init__(self, service, book_info, ctx):
        self.service = service
        self.book_info = book_info
        self.ctx = ctx
        super().__init__()

    @discord.ui.button(
        label="Read this book", style=discord.ButtonStyle.primary, emoji="📖"
    )
    async def read(self, interaction, _):
        if self.ctx.author != interaction.user:
            return
        match self.service.create_or_update_book(
            self.ctx.channel.id,
            self.book_info.title,
            self.book_info.author,
            self.book_info.year,
            self.book_info.pages,
            self.book_info.rating,
            self.book_info.img_url,
        ):
            case Ok(embed):
                await self.ctx.send(
                    embed=embed, view=RenameChannelView(self.ctx, self.book_info.title)
                )
            case Err(msg):
                await self.ctx.send(
                    embed=discord.Embed(
                        title="Error", description=msg, color=discord.Color.red()
                    )
                )
        await self.disable_buttons(interaction)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="🗑️")
    async def cancel(self, interaction, _):
        if self.ctx.author != interaction.user:
            return
        await self.disable_buttons(interaction)


class RenameChannelView(BaseView):
    def __init__(self, ctx, title: str):
        self.ctx = ctx
        self.title = title
        super().__init__()

    @discord.ui.button(
        label="Rename channel", style=discord.ButtonStyle.primary, emoji="✅"
    )
    async def confirm(self, interaction, _):
        if self.ctx.author != interaction.user:
            return
        await self.ctx.channel.edit(name=f"📚 {self.title}")
        await self.disable_buttons(interaction)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="🗑️")
    async def cancel(self, interaction, _):
        if self.ctx.author != interaction.user:
            return
        await self.disable_buttons(interaction)
