# C2L4B-BOT

Discord bot for managing CTF (Capture The Flag) competitions and challenges for the CSLAB CTF team.

## Features

- **CTF Management**: Create and organize CTF channels automatically
- **Challenge Tracking**: Create individual threads for each challenge
- **Archive System**: Move completed CTFs to archived categories
- **Remote Administration**: Update and reload bot commands without server access

## Commands

### CTF Management Commands

| Command | Description | Usage |
|---------|-------------|-------|
| `ctf_create` | Creates a new CTF channel in the active-ctfs category | `!ctf_create <ctf_name>` |
| `ctf_chal` | Creates a challenge thread inside a CTF channel | `!ctf_chal <ctf_name> <category> <title> <description>` |
| `ctf_archive` | Moves a CTF channel from active-ctfs to archived-ctfs | `!ctf_archive <ctf_name>` |

### Admin Commands

| Command | Description | Usage |
|---------|-------------|-------|
| `update` | Pulls latest changes from git repository and reloads the bot | `!update` |
| `reload` | Reloads all command modules without pulling changes | `!reload` |
| `restart` | Completely restarts the bot process | `!restart` |

## Requirements

- Python
- discord.py
- python-dotenv

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

Required roles:

- `Membros` - For CTF management commands
- `admin` - For administrative commands

## TODO

### Great Library Feature

Implement a knowledge base system, to provide quick access to tools documentation and cheat sheets.

**Planned functionality:**

- JSON-based storage for tool documentation and commands
- Quick lookup system (e.g., `!nmap` returns nmap cheat sheet with common flags)
- Categories for different tool types (network scanning, web exploitation, reverse engineering, etc.)
- Community-contributed entries
- Searchable command reference

**Example structure:**

```json
{
  "nmap": {
    "description": "Network exploration tool and security scanner",
    "common_flags": [
      "-sV: Version detection",
      "-sC: Default scripts",
      "-p-: Scan all ports"
    ],
    "examples": [...]
  }
}
```

### Other Planned Features

- Challenge status tracking (solved/unsolved)
- Ctftime integration
- Event creation

## License

MIT License

## Contributing

Contributions are welcome. Please open an issue or submit a pull request.

## Authors

- r3ber - Initial work
