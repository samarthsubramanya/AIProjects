full_dot = '●'
empty_dot = '○'


def create_character(name, strength, intelligence, charisma):
	if not isinstance(name, str):
		return "The character name should be a string."
	if name == "":
		return "The character should have a name."
	if len(name) > 10:
		return "The character name is too long."
	if " " in name:
		return "The character name should not contain spaces."

	stats = (strength, intelligence, charisma)
	if not all(isinstance(s, int) for s in stats):
		return "All stats should be integers."
	if not all(s >= 1 for s in stats):
		return "All stats should be no less than 1."
	if not all(s <= 4 for s in stats):
		return "All stats should be no more than 4."
	if sum(stats) != 7:
		return "The character should start with 7 points."

	def bar(value):
		full = full_dot * value
		empty = empty_dot * (10 - value)
		return full + empty

	return (
		f"{name}\n"
		f"STR {bar(strength)}\n"
		f"INT {bar(intelligence)}\n"
		f"CHA {bar(charisma)}"
	)

