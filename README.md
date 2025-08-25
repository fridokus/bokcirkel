<div align="center">
   <h1>📚 Bokcirkel</h1>
   <h3>The ✨ chic ✨ Discord bot for book clubs</h3>
   <img src="https://em-content.zobj.net/source/microsoft-teams/363/books_1f4da.png" width="80" alt="books emoji"/>
</div>

---

## 🚀 Features

- 📖 **Track your reading**: Set your progress, catch up, and never lose your place.
- 🏆 **Achievements**: Earn badges for reading, streaks, reviews, notes, and more!
- 🔔 **Shame & Streaks**: Stay motivated (or get shamed!) to keep up with your club.
- 💬 **Suggest, quote, and review**: Share your thoughts, favorite lines, and book ideas.
- 👑 **Admin tools**: Manage your club with powerful commands.

---

## 📝 Quickstart

```bash
git clone https://github.com/fridokus/bokcirkel.git
cd bokcirkel
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```


1. **Create a Discord bot** at [Discord Developer Portal](https://discord.com/developers/applications/)
2. **Save your bot token** in a file called `.token` in the project root.
3. **Get a Hardcover API key** from [Hardcover.app](https://hardcover.app/developers) and save it in a file called `.hardcover-api-key` in the project root (the file should contain only the API key).
4. **Invite the bot** to your server with the right permissions.
5. **Run the bot:**
    ```bash
    python bokcirkel.py
    ```

---

## Hardcover API Integration

Bokcirkel integrates with the [Hardcover API](https://hardcover.app/) to fetch book data, enrich suggestions, and provide up-to-date info for your club. This means:
- 📚 Book suggestions are smarter and more accurate
- 🖼️ Book covers, authors, and details are auto-fetched
- 🔍 Seamless experience when adding or searching for books

---

## Workflows & Usage

### 1. **Start Reading**
- Use `!read` to set your current page/chapter.
- Use `!caughtup` when you reach the club's target.

### 2. **Suggest & Review**
- Suggest books with `!suggest`.
- Review finished books with `!review`.

### 3. **Track Achievements**
- See your badges with `!achievements`.
- Earn rewards for reading, streaks, reviews, notes, quotes, and more!

### 4. **Stay Motivated**
- If you fall behind, you might get shamed (`!shame`).
- Keep up streaks for special rewards!

### 5. **Admin Tools**
- Admins can use `!deleteallchannels` and more (see `!help`).

---

## 🌟 Example Achievements

| Badge | How to Earn |
|-------|-------------|
| 📚 Bookworm | Finish 1 book |
| 🏅 Avid Reader | Finish 10 books |
| 🔥 Streak Starter | 3-day reading streak |
| 😳 Shame Spiral | Be shamed 3 days in a row |
| 📝 Note Taker | Add 1 note |
| 💬 Quoter | Add 1 quote |
| ⭐ Reviewer | Write 1 review |

---

## 💡 Tips
- Use `!help` in Discord for a quick command guide.
- Achievements and streaks are tracked automatically.
- Admins see extra commands in `!help`.

---

## 👤 Credits

Made with ❤️ by Fridokus (Oskar Fridell)
