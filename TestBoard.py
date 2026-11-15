# Name: Alyssa Moore
# The only AI that was used: Claude AI
# Usage:
#  1. Explaining what Flask and CSS is and looks like
#  2. how to use json with a webpage
#  3. How to display win or lose among two-players

# using flask instead since it works with webpage

import time
import threading 
from flask import Flask, render_template_string, redirect, url_for, jsonify, request

Size = 6

app = Flask(__name__)

alive = set(range(Size * Size))
lock = threading.Lock() # for taking turns clicking
winner = None # who clears the last pixel
over_at = None # for when game ended


winner = None 
Over_at = None
# Everything inside the webpage
page = """
<style>
  #board { display: grid; grid-template-columns: repeat({{ size }}, 40px); gap: 4px; }
  .square { width: 40px; height: 40px; background: #4a90e2; cursor: pointer; }
  .square.gone { visibility: hidden; }
</style>

<input id="name" type="text">

<div id="board">
  {% for i in range(size * size) %}
    <div class="square" data-id="{{ i }}"></div>
  {% endfor %}
</div>
<p id="status">{{ size * size }} left</p> 
<p id = "count">Clicks: 0</p>

<script>
<script>
  const me = Math.random().toString(36).slice(2);   // this browser's player id
  const status = document.getElementById("status");
  const countEl = document.getElementById("count");
  const squares = document.querySelectorAll(".square");

  function render(data) {
    const stillAlive = new Set(data.alive);
    squares.forEach(sq =>
      sq.classList.toggle("gone", !stillAlive.has(Number(sq.dataset.id))));
    countEl.textContent = `You cleared: ${data.mine}`;

    if (data.result === "win") status.textContent = "You win!";
    else if (data.result === "lost") status.textContent = "You lost!";
    else status.textContent = `${data.left} left`;
  }

  squares.forEach(sq => {
    sq.addEventListener("click", async () => {
      const res = await fetch(`/click/${sq.dataset.id}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ player: me })
      });
      render(await res.json());
    });
  });

  document.getElementById("reset").addEventListener("click", () =>
    fetch("/reset", { method: "POST" }));

  setInterval(async () => {                         
    const res = await fetch(`/state/${me}`);
    render(await res.json());
  }, 500);
</script>


"""
# Notes: 
# Showing a grid with each square being on 6 pixels size
# makes the square size and the background and make cursor
# once you click on the square, the square will be invisible but stil there
# Giving each square a number or id. FOr square clicking
# This tells how many are left
# when square is clicked run this function
# when the square is removed, add gone rule to it
# if someone clicks on last pixel, message, else keep saying how much is left
# count.textContent = `Clicks: ${data.clicks}`; <- where it keeps track of the clicks

def reset_game():
    global winner, over_at
    alive.clear()
    alive.update(range(Size*Size))
    winner = None
    over_at = None

reset_game()

def state_for(pid):
    result = None
    if winner is not None:
        result = "win" if winner == pid else "lost"
    return jsonify(alive=sorted(alive), left=len(alive))
                   

@app.route("/")
def index():
    return render_template_string(page, size=Size)   # no reset here anymore

@app.route("/click/<int:i>", methods=["POST"])
def click(i):
    global winner, over_at
    pid = request.get_json().get("player")
    with lock:
        if winner is None and i in alive:
            alive.remove(i)
            if not alive:                      # whoever empties the board wins
                winner = pid
                over_at = time.time()
        return state_for(pid)

@app.route("/state/<pid>")
def state(pid):
    with lock:
        if over_at and time.time() - over_at > 3:   # new game 3 seconds after a win
            reset_game()
        return state_for(pid)

@app.route("/reset", methods=["POST"])
def reset():
    with lock:
        reset_game()
        return jsonify(ok=True)

#####

"""
@app.route("/") 
def index():
    global clicks 
    clicks = 0 
    alive.clear()
    alive.update(range(Size * Size))   # every page load starts a new game
    return render_template_string(page, size=Size) # puts the board on the page

# The clicking part
@app.route("/click/<int:i>", methods=["POST"])
def click(i):
    global clicks 
    removed = i in alive and len(alive) > 0
    if removed:
        alive.remove(i)
        clicks += 1 # counting every click
    return jsonify(removed=removed, left=len(alive), won=len(alive) == 0, clicks = clicks)
    #Javascript converts deleting the squares into data

# Resetting the board function
@app.route("/reset", methods=["POST"])
def reset():
  alive.clear()
  alive.update(range(Size * Size))
  return jsonify(left=len(alive))

    

if __name__ == "__main__":
    app.run(debug=True)

    

Backup:
const status = document.getElementById("status");
  const reset = document.getElementById("reset");
  const count = document.getElementById("count");
  const name = documen.getElementBtId("name");

  document.querySelectorAll(".square").forEach(sq => { 
    sq.addEventListener("click", async () => { 
      const res = await fetch(`/click/${sq.dataset.id}`, { method: "POST" }); 
      const data = await res.json(); 
      if (data.removed) sq.classList.add("gone"); 
      count.textContent = `Clicks: ${data.clicks}`;
      status.textContent = data.won ? "You found the Last Pixel!" : `${data.left} left`;
      if (data.won) setTimeout(newGame, 2000);
    });
  });

  async function newGame(){
    const r = await fetch("/reset", {method: "POST"});
    const data = await r.json();
    document.querySelectorAll(".square").forEach(sq => sq.classList.remove("gone"));
    status.textContent = `${data.left} left`;
    count.textContent = `Clicks: ${data.clicks}`;
    }

    reset.addEventListener("click", newGame);
"""
#Testing 
# Run code first 
# Then http://127.0.0.1:5000