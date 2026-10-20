
from flask import Flask, render_template, redirect, url_for

app = Flask(__name__)

Size = 6
alive = set(range(Size * Size))


def click(sq):
    if sq not in alive or len(alive) == 0:
        return

    alive.remove(sq)


@app.route("/", methods=["GET", "POST"])
def home():
    from flask import request

    if request.method == "POST":
        sq = int(request.form["square"])
        click(sq)
        return redirect(url_for("home"))

    return render_template(
        "index.html",
        size=Size,
        alive=alive,
        remaining=len(alive)
    )


if __name__ == "__main__":
    app.run(debug=True)
