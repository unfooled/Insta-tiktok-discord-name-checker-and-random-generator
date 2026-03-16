# Word Generator Script
# Requirements: Python 3.x
# This script generates a list of real English words (one per line) into a text file.
# It uses the Google 20k English words list (https://github.com/first20hours/google-10000-english/blob/master/20k.txt)

def download_wordlist(url):
    import urllib.request
    response = urllib.request.urlopen(url)
    data = response.read().decode("utf-8")
    return data.splitlines()


import os
import random
import sys

WORDLIST_URL = "https://raw.githubusercontent.com/first20hours/google-10000-english/master/20k.txt"
OUTPUT_FILE = "generated_words.txt"

def clear_console():
    os.system('cls' if os.name == 'nt' else 'clear')

def ensure_colorama():
    try:
        import colorama
    except ImportError:
        print("colorama not found. Installing...")
        import subprocess
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'colorama'])
        clear_console()
        print("colorama installed. Starting script...\n")
    finally:
        globals()['colorama'] = __import__('colorama')
        colorama.init(autoreset=True)

def main():
    ensure_colorama()
    from colorama import Fore, Style

    min_len = None
    max_len = None
    amount = None


    ascii_title = (
        "                                               \n"
        "  ____   ____   ____      ____   ____   ____  \n"
        " /  _ \\ / ___\\ /  _ \\    / ___\\_/ __ \\ /    \\ \n"
        "(  <_> ) /_/  >  <_> )  / /_/  >  ___/|   |  \\ \n"
        " \\____/\\___  / \\____/   \\___  / \\___  >___|  /\n"
        "      /_____/          /_____/      \\/     \\/ \n"
    )

    # Input minimal word length
    clear_console()
    print(Fore.CYAN + Style.BRIGHT + ascii_title)
    print(Fore.LIGHTBLACK_EX + f"? - ? / ?\n")
    min_len = int(input(Fore.YELLOW + "Enter minimal word length: "))

    # Input maximal word length
    clear_console()
    print(Fore.CYAN + Style.BRIGHT + ascii_title)
    print(Fore.LIGHTBLACK_EX + f"{min_len} - ? / ?\n")
    max_len = int(input(Fore.YELLOW + "Enter maximal word length: "))

    # Input amount
    clear_console()
    print(Fore.CYAN + Style.BRIGHT + ascii_title)
    print(Fore.LIGHTBLACK_EX + f"{min_len} - {max_len} / ?\n")
    amount = int(input(Fore.YELLOW + "How many words to generate? "))

    # Final summary before generating
    clear_console()
    print(Fore.CYAN + Style.BRIGHT + ascii_title)
    print(Fore.LIGHTBLACK_EX + f"{min_len} - {max_len} / {amount}\n")

    print(Fore.GREEN + "Downloading word list...\n")
    words = download_wordlist(WORDLIST_URL)
    filtered = [w for w in words if min_len <= len(w) <= max_len]
    if len(filtered) < amount:
        print(Fore.RED + f"Warning: Only {len(filtered)} words available with the given length constraints.\n")
        amount = len(filtered)
    selected = random.sample(filtered, amount)

    out_path = os.path.join(os.path.dirname(__file__), OUTPUT_FILE)
    with open(out_path, "w", encoding="utf-8") as f:
        for word in selected:
            f.write(word + "\n")

    print(Fore.GREEN + f"{amount} words written to {OUTPUT_FILE}\n")
    print(Fore.MAGENTA + "Done!\n")

if __name__ == "__main__":
    main()
