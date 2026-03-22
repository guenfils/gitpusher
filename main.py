#!/usr/bin/env python3
"""
Git Pusher — Upload any project to GitHub & GitLab in one click.
Developed by Guenson (github.com/guenfils | gitlab.com/guenson)
"""
import sys
import os

# Make sure the app root is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import customtkinter as ctk

# Dark theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

from ui.app import App


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
