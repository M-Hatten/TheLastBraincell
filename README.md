# Project Overview
## What is The Last Pixel?
The Last Pixel is a game where all players can see a shared-state game board with tiles on it.
When one person clicks a tile, that tile is removed from the board for all players, and they are given
a brief cooldown period.

Whoever clicks the last tile - the last pixel - scores a point, which is added to their name on the leaderboard.
After the board is cleared, the winner is announced to all before the board is cleared and reset for the next round.

## To play the game...
If you play the game while our Amazon web server is up, you can play it right now by going to this link:
    https://lastpixel.duckdns.org/

If the server is down, you'll either have to host it locally yourself or set up / visit a publicly available server.


To play, enter a username in the prompt. 
> If you aren't already on the leaderboard, you'll be added with 0 points, but if your name was already on
  the leaderboard, you can pick up where you left off, as all points you get will be added to that entry.
> The leaderboard resets weekly, so your name may be removed when you revisit

Once your name is set, you can start clicking on tiles on the game board.
> There is a short cool-down period (around 5 seconds) after clicking a tile where you can't select another tile
> Keep the rate in mind if you want to select the last pixel before someone else

When the board is cleared, whoever clicked the last pixel is declared the winner, awarded a point, and the board resets.




# Installation and Setup

To run the application locally, install the main files from this repo and extract them into their own directory.
Open a terminal and navigate to that directory.

We set up a python3 virtual environment and ran the server with uvicorn. You may have to install those 
dependencies before running.

As a general outline, the commands to start the server should look something like this:
    python3 -m venv .venv 
    source .venv/bin/activate
    python -m pip install fastapi "uvicorn[standard]"
    python -m uvicorn main:app --reload

If you already have a virtual environment set up, or already have the dependencies installed to it, you
can skip commands 1 or 3, respectively.

Once the uvicorn server is running, the terminal should show the local server IP on your host machine, and start 
listening for and printing user connections.

The local game should be accessible at http://127.0.0.1:8000, but reference your terminal output to confirm.




# Application Details

## Technologies Used
- Python 3 and FastAPI (backend)
- Uvicorn (to run the web server)
- WebSockets (kept track of multiplayer sessions)
- HTML, CSS, JavaScript (frontend)
- SQLite (persistent leaderboard)


## File structure
main.py
- The primary fastAPI server that controls WebSocket connections, game coordination
boardflash.py
- Controls board state, pixel removal, reset logic
database.py
- An SQLite leaderboard that resets weekly, but stores data across server restarts
index.html
- Game interface and client-side JavaScript
static/style.css
- Game styling
game.db
- Persistent SQLite database
README.md
- This document. Includes setup instructions and other documentation
AWS_backend_changelog.txt
- Record of AWS/backend changes



# Project information

## Known Limitations and Future Improvements

We made the application not require or store login information, to reduce project scope and give users
an easy experience. Not storing or checking login information has the known drawback of not providing
a true ownership of a name or score. Anyone can come along and make points in a name that they didn't make.
This was a trade-off we made during development.

For the future, we would probably store login credentials, and provide a way to retrieve or reset login
credentials via email. That functionality was outside our intended scope for this project during the first
couple of sprints.
