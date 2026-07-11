import tomllib

# loading configurations from config file
with open("./config.toml", "rb") as f:
    config = tomllib.load(f)

location = config["logger"]["logs_file_location"]
fileName = config["logger"]["logs_file_name"]
storeLogs = config["logger"]["store_logs"]
printLogs = config["logger"]["print_logs"]

# emptying the log file
with open(f"{location}/{fileName}.txt", "w"):
    pass

def log(text: str) -> None:
    if storeLogs:
        with open(f"{location}/{fileName}.txt", "a") as f:
            print(text, file=f)

    if printLogs:
        print(text)
