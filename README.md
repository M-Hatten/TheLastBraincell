# Project Overview
## What is The Last Pixel?
The Last Pixel is a game where all players can see a shared-state game board with tiles on it.
When one person clicks a tile, that tile is removed from the board for all players, and they are given
a brief cooldown period.

Whoever clicks the last tile - the last pixel - scores a point, which is added to their name on the leaderboard.
After the board is cleared, each person is informed of their win or loss before the board is reset for the next round.

## To play the game...
If you play the game while our Amazon web server is up, you can play it right now by going to this link:
    https://lastpixel.duckdns.org/

If the server is down, you'll either have to host it locally yourself or set up / visit a publicly available server.


To play, enter a username in the prompt. 
> If you aren't already on the leaderboard, you'll be added with 0 points, but if your name was already on
  the leaderboard, you can pick up where you left off, as all points you get will be added to that entry.
> The leaderboard resets weekly, so your name may be removed when you revisit.

Once your name is set, you can start clicking on tiles on the game board.
> There is a short cool-down period (around 5 seconds) after clicking a tile where you can't select another tile.
> Keep the rate in mind if you want to select the last pixel before someone else.

When the board is cleared, whoever clicked the last pixel is declared the winner, awarded a point, and the board resets.




# Installation and Setup

To run the application locally, install the entire project from this repo and extract them into their own directory.
Open a terminal and navigate to that directory.

We set up a python3 virtual environment and ran the server with uvicorn. A fresh virtual environment needs to install those 
dependencies before running.

As a general outline, the commands to start the server should look something like this:
    ```bash
    python3 -m venv .venv 
    source .venv/bin/activate
    python -m pip install fastapi "uvicorn[standard]"
    python -m uvicorn main:app
    ```

If you already have a virtual environment set up, or already have the dependencies installed to it, you
can skip commands 1 or 3, respectively.

Once the uvicorn server is running, the terminal should show the local server IP on your host machine, and start 
listening for and printing user connections.

The local game should be accessible at http://127.0.0.1:8000, but reference your terminal output to confirm.


Running the application from a publicly accessible server, such as an AWS instance, requires more setup that will be outlined
in a different section of this documentation.



# Application Details

## Technologies Used
- Python 3 and FastAPI (backend)
- Uvicorn (to run the web server)
- WebSockets (real-time two-way communication)
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

## How it Works

Uvicorn loads the FastAPI application defined in main.py 
- A FastAPI app is made on program startup that points to the index.html webpage.
- main.py handles user sessions through fastAPI websocket connections
    - These connections are uniquely identified and stored individually
- There is a DEBUG mode in the main app that turns off the rate limit on user inputs
    - This is ideal for testing locally on a host to make sure everything works

boardflash.py is where the entire board and its functions come in
- The board has 36 square tiles(pixels) that players can click.
      - There is a function that keeps track of how many pixels did the player click. 
- Once all the pixels are clicked, whoever clicked the last one will get the display "You win!" and "You lose!" for those that didn't.
- After the display, the board will reset to full after a few seconds. 


database.py handles the leaderboard code, and game.db stores it
- The SQLite leaderboard stores leaderboard data independently of the main app in game.db, so
  data persists across main app resets.
- main.py makes a reference to and calls on the database when it needs to add an entry or
  give someone a point
- The leaderboard resets each week on Sunday at 8AM Chicago time

index.html

style.css


# AWS Server Information



# Project information

This project was made by William Kessler, Alyssa Moore, Milo Hatten, and Sean Roberts.

Sean:
> I was responsible for the main.py file, for the SQLite database, and for tying everything together.
> 
> I used ChatGPT6 to do a significant portion of the heavy lifting when it came to connecting everything
> together, since throughout development we had a number of files, each made with different coding practices.
> It was also a huge help in problem-solving and troubleshooting, and let me commit more working changes at a time.
>
> Here's a link to view the conversation I had with ChatGPT6:
> https://chatgpt.com/share/6afdd1cf-d058-83ea-8e33-5d4b57869517
>
Alyssa:
> I was responsible for creating the board itself.
> I did use Claude AI to figure out how to display win or lose through users. This was a bit difficult but thanks to my groupmate, Sean, he was able to rearrange somethings so it can connect to the fastapi. 
>
> Link to chat: https://claude.ai/share/76adcaab-fc49-45b1-b70d-e228b7672661

## Known Limitations and Future Improvements

We made the application not require or store login information, to reduce project scope and give users
an easy experience. Not storing or checking login information has the known drawback of not providing
a true ownership of a name or score. Anyone can come along and make points in a name that they didn't make.
This was a trade-off we made during development.

For the future, we would probably store login credentials, and provide a way to retrieve or reset login
credentials via email. That functionality was outside our intended scope for this project during the first
couple of sprints.

We could also have board options for players. There would be some of different shapes and many more pixels to click. This was an idea we considered for this project, however, given the time we had, we had to go with a simple 6x6 board. 
