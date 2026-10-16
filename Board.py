# Creating the board itself
# Name: Alyssa Moore

# Using tkinder

import tkinter as tk


Size = 6 # 6 by 6 grid 
Cell = 40 # pixel size

root = tk.Tk()
root.title("The Last Pixel")
board = tk.Frame(root)
board.pack(padx=10, pady=10) # for testing

#status
status = tk.Label(root, text=f"{Size * Size} left") # tells how many are left
status.pack(pady=(0,10))

alive = set() # LIVE

# a bit of AI usage
# clicking the buttons function
def click(sq):
    # if there is no square to click or game over
    if sq not in alive or len(alive) == 0:
        return 
    alive.remove(sq)
    sq.config(bg=root.cget("bg")) # once clicking the square it turns into the background
    status.config(text="Last Pixel Clicked!" if len(alive) == 0 else f"{len(alive)} left")
    # keeping the squares until there are none

#Now building the actual board
for r in range(Size): #row
    for c in range(Size): #column
        sq = tk.Frame(board, width=Cell, height=Cell, bg="#4a90e2")
        sq.grid(row=r, column=c, padx=2,pady=2) # the squares 
        # tieing the click function with the left mouse button
        sq.bind("<Button-1>", lambda e, s=sq:click(s)) 
        
        alive.add(sq)

#BEGINNING GAME WHEN RUNNING
root.mainloop()