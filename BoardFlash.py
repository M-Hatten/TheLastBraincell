# Name: Alyssa Moore
# The only AI that was used: Claude AI
# Usage:
#  1. Explaining what Flask and CSS is and looks like
#  2. how to use json with a webpage

# using flask instead since it works with webpage

from flask import Flask, render_template_string, redirect, url_for, jsonify

Size = 6

app = Flask(__name__)

alive = set(range(Size * Size))

# Everything inside the webpage
page = """
<style>
  #board { display: grid; grid-template-columns: repeat({{ size }}, 40px); gap: 4px; }
  .square { width: 40px; height: 40px; background: #4a90e2; cursor: pointer; }
  .square.gone { visibility: hidden; }
</style>


<div id="board">
  {% for i in range(size * size) %}
    <div class="square" data-id="{{ i }}"></div>
  {% endfor %}
</div>
<p id="status">{{ size * size }} left</p> 

<script>
  const status = document.getElementById("status");
  document.querySelectorAll(".square").forEach(sq => { 
    sq.addEventListener("click", async () => { 
      const res = await fetch(`/click/${sq.dataset.id}`, { method: "POST" }); 
      const data = await res.json(); 
      if (data.removed) sq.classList.add("gone"); 
      status.textContent = data.won ? "You found the Last Pixel!" : `${data.left} left`;
      
    });
  });
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

@app.route("/") 
def index():
    alive.clear()
    alive.update(range(Size * Size))   # every page load starts a new game
    return render_template_string(page, size=Size) # puts the board on the page

# The clicking part
@app.route("/click/<int:i>", methods=["POST"])
def click(i):
    removed = i in alive and len(alive) > 0
    if removed:
        alive.remove(i)
    return jsonify(removed=removed, left=len(alive), won=len(alive) == 0)
    #Javascript converts deleting the squares into data

if __name__ == "__main__":
    app.run(debug=True)