# C2L4B-BOT

Discord bot for managing CTF (Capture The Flag) competitions and challenges for the CSLAB CTF team.

## Features

- **CTF Management**: Create and organize CTF channels automatically
- **Challenge Tracking**: Create individual threads for each challenge with status tracking
- **Archive System**: Move completed CTFs to archived categories
- **Event Scheduling**: Create Discord events from CTFTime URLs
- **Team Scoreboard**: Track individual solves and team progress
- **Great Library**: Access documentation and cheat sheets through bot commands
- **CTFTime Integration**: View team rankings, information and schedule events
- **Remote Administration**: Update and reload bot commands without server access

## Project Structure

```
C2L4B-BOT/
├── bot.py                      # Main bot entry point
├── config.py                   # Configuration and environment variables
├── requirements.txt            # Python dependencies
├── .env                        # Environment variables (not in repo)
│
├── cogs/                       # Bot command modules (Cogs)
│   ├── __init__.py            # Package initialization
│   ├── admin.py               # Admin commands (sync, update, reload, restart)
│   ├── ctf.py                 # CTF management (create, archive, challenges)
│   ├── ctftime.py             # CTFTime API integration
│   ├── library.py             # Knowledge library search
│   └── scoreboard.py          # Internal team scoreboard
│
├── data/                       # Bot data storage
│   └── scoreboard.json        # Team member statistics
│
├── great-library/              # Knowledge base (Markdown files)
│   ├── index.json             # Library index
│   └── *.md                   # Tool/technique documentation
│
└── README.md                   # Project documentation
```

### Key Files

- **`bot.py`**: Main entry point that initializes the Discord bot and loads all cogs
- **`config.py`**: Centralized configuration management (tokens, IDs, paths)
- **`cogs/`**: Modular command groups, each handling specific functionality
- **`data/`**: Persistent storage for bot data (scoreboard, stats)
- **`great-library/`**: Markdown-based knowledge base for CTF tools and techniques

### Environment Variables

The bot requires a `.env` file with:
```env
token=YOUR_DISCORD_BOT_TOKEN
announchannel=ANNOUNCEMENT_CHANNEL_ID
```

## Commands

### CTF Management Commands

| Command | Description | Usage |
|---------|-------------|-------|
| `ctf_create` | Creates a new CTF channel in the active-ctfs category | `!ctf_create <ctf_name>` |
| `ctf_chal` | Creates a challenge thread inside a CTF channel | `!ctf_chal <ctf_name> <category> <title> <description>` |
| `ctf_archive` | Moves a CTF channel from active-ctfs to archived-ctfs | `!ctf_archive <ctf_name>` |
| `schedule`      | Creates a Discord event from a CTFTime event URL and provides a link to add it to your Google Calendar | `!schedule <ctftime_url>` or `/schedule <ctftime_url>` |
| `export_event`  | Generates a Google Calendar link for any scheduled Discord event   | `!export_event <event_id>` or `/export_event <event_id>` |

**Note:**  
After creating or exporting an event, the bot will provide a link that lets you quickly add the event to your personal Google Calendar with all relevant details pre-filled.

### Challenge Status Commands

| Command | Description | Usage |
|---------|-------------|-------|
| `wip` | Marks the current challenge as Work In Progress | `!wip` (inside thread) |
| `solved` | Marks the current challenge as solved | `!solved` (inside thread) |
| `writeup_done` | Marks that the writeup is complete | `!writeup_done` (inside thread) |
| `unsolved` | Removes the solved mark from the challenge | `!unsolved` (inside thread) |
| `status` | Shows the current status of the challenge | `!status` (inside thread) |

### Scoreboard Commands

| Command | Description | Usage |
|---------|-------------|-------|
| `leaderboard` | Shows the internal team ranking | `!leaderboard` |
| `profile` | Shows stats for a specific user | `!profile` or `!profile @user` |

### Library Commands

| Command | Description | Usage |
|---------|-------------|-------|
| `lib` | Search the library for an entry | `!lib <name>` or `!lib <name> <section>` |
| `lib_list` | List all available entries in the library | `!lib_list` |
| `lib_sections` | List sections of a specific entry | `!lib_sections <name>` |

### CTFTime Commands

| Command | Description | Usage |
|---------|-------------|-------|
| `ctftime_top_portugal` | Gets the top 10 CTF teams from Portugal | `!ctftime_top_portugal` |
| `ctftime_team_info` | Gets details of our CTF team from CTFTime | `!ctftime_team_info` |

### Admin Commands

| Command | Description | Usage |
|---------|-------------|-------|
| `sync` | Syncs slash commands with Discord | `!sync` |
| `update` | Pulls latest changes from git repository and reloads the bot | `!update` |
| `reload` | Reloads all command modules without pulling changes | `!reload` |
| `restart` | Completely restarts the bot process | `!restart` |

## Challenge Status Flow

Challenges follow this status progression:

1. **Open** - Challenge created, no one working on it yet
2. **[WIP]** - Someone is actively working on the challenge
3. **[SOLVED - MISSING WRITEUP]** - Challenge solved, writeup pending
4. **[SOLVED - WRITEUP DONE]** - Challenge solved with writeup complete

## Great Library

The library provides quick access to documentation and cheat sheets for common CTF tools and concepts.

**Structure:**

```bash
great-library/
├── index.json
├── crypto/
├── forensics/
├── pwn/
├── reverse/
├── tools/
└── web/
```

Each entry is a Markdown file with sections defined by `##` headers. Use `!lib <name> <section>` to view specific sections.

## Requirements

- Python 3.10+
- discord.py
- python-dotenv
- requests
- aiohttp

## Installation

1. Clone the repository:

    ```bash
    git clone https://github.com/r3ber/C2L4B-BOT.git
    cd C2L4B-BOT
    ```

2. Install dependencies:

    ```bash
    pip install -r requirements.txt
    ```

3. Create a `.env` file with your Discord bot token:

    ```env
    token=YOUR_DISCORD_BOT_TOKEN
    announchannel=CHANNEL_ID_FOR_SOLVE_ANNOUNCEMENTS
    ```

4. Run the bot:

    ```bash
    python3 bot.py
    ```

## Configuration

The bot requires the following Discord permissions:

- Read Messages/View Channels
- Send Messages
- Manage Channels
- Create Public Threads
- Manage Threads
- Manage Events

Required roles:

- `Membros` - For CTF management commands
- `admin` - For administrative commands

## License

MIT License

## Contributing

Contributions are welcome. Please open an issue or submit a pull request.

## Authors

- r3ber - Initial work
- pedroseco7 - Collaborative work
