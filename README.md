# shaidow
Tool enabling an LLM to "shadow" you while you use your terminal

## Overview

This tool uses tmux/[byobu](https://www.byobu.org/) to create a two-pane terminal window. The first pane is just a regular old terminal. The second pane is a DM with an AI chatbot. Imagine you're screen-sharing what you're doing in the first pane with the bot in the second pane, and the second pane shows comments and tips from the bot. You can switch your focus to the second pane to chat directly with the bot, or you can solely use the first pane and provide occasional feedback through typical `# shell comments`