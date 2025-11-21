# ⚔️ CK3 Log Analyzer ⚔️

## Program

**This program analyzes error.log and sorts errors by mod directory.**


## ✨ Features:
- ✅ **Automatically sorts found errors into files and directories.**
- ✅ **Option to use a text editor to open error lines.**
- ✅ **Built-in function to check mod compatibility.**
- ✅ **English and Russian language**
---
[![Screen-Shot-10-17-25-at-12-12-PM.png](https://i.postimg.cc/tRLN15xH/Screen-Shot-10-17-25-at-12-12-PM.png)](https://postimg.cc/F1VL80pP)
### Option
- To run, use the main executable file - ck3_log_parser.py.
- I created it .exe using auto-py-to-exe, adding other files to (Additional Files) during creation.
---

While simple, it's a useful utility. It makes navigating errors slightly easier, though not all. The parser still doesn't understand error context—you'll need to open the error line in error.log yourself and look nearby to find the context.

Some mods, especially older ones, use outdated pointers, triggers, or functions. This tool may slightly ease your search for bugs and fixes.

Regarding mod compatibility: no fancy tricks here. The parser checks which mods you have and which ones use the same files. It detects `00_holding` wherever possible. If the "other mods" list is too long, double-click it to open a separate window listing conflicting mods. This helps you decide whether to disable them or adjust their load order.

There was an idea to make a real-time parser with directory sorting, but my hardware nearly died from the load, and it worked poorly. So, static analysis only. Launch the game, wait until the main menu loads, then start scanning. It's preliminary—more errors will accumulate during gameplay.

That's about it. Might be useful to someone.

ck3_log_parser_Multithreading.py
--------------------------------
Multithreaded mod indexing
Uses a thread pool (ThreadPoolExecutor) to simultaneously crawl the mod directories in the Workshop and local folders to quickly build a file map and prepare a database for error distribution.
## ✨ Features:
- ✅ **Error classification - single-threaded**
- ✅ **The indexing of mods - multithreaded**
