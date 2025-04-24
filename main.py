from calendar import Calendar

calendar = Calendar()
today = calendar.today()
print(f"Today is {today}.")
print("")
calendar.print_from(today)
